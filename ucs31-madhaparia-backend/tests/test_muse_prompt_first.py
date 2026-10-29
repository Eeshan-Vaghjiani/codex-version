"""Prompt-first, questions truly optional (Eeshan, 2026-10-29).

Settled rule: if the initial prompt already answers it, ask nothing.
Questions are OPTIONAL, only when something is unclear AND the answer
would change the prediction or the action. Safety (breathing) is the
only exception and comes first, once. If the user answers "no" (or
"not sure") to all follow-ups, the app must still give something
useful from the ORIGINAL prompt, never a blank screen.

Test names state which discriminator each question is for, as required.
"""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ml.primary_selection import classify_primary  # noqa: E402
from app.nlp.symptom_mapper import find_symptoms  # noqa: E402
from app.services import primary_assessment as service  # noqa: E402
from app.services.consultation import next_consultation_question  # noqa: E402
import app.nlp.symptom_mapper as _mapper_module  # noqa: E402

CANON = {x["code"]: x["features"]
         for x in json.loads((Path(_mapper_module.__file__).resolve().parent / "canonical_symptoms.json").read_text())}
CATALOGUE = {c: SimpleNamespace(code=c, features=r) for c, r in CANON.items()}


def codes_for(text):
    return [f["code"] for f in find_symptoms(text, db=None)]


def feats(codes):
    return sorted({ft for c in codes for ft in CANON.get(c, [])})


def next_q(states, asked=None):
    details = {c: {"code": c, "features": CANON[c]} for c in states}
    return next_consultation_question(states, details, {}, asked or [], CATALOGUE, 30, "M")


def assessment(present_codes, states):
    confirmation = {
        "model_features": feats(present_codes),
        "explicitly_absent_features": [],
        "_symptom_details": {c: {"code": c, "display_name": c.replace("_", " ")}
                             for c in states if states[c] == "present"},
        "assessment_context": {"language": "en", "symptom_states": states, "severity": {}},
    }
    result = service.build_primary_assessment(confirmation, 30, "M")
    result.pop("_audit", None)
    return result


CLUSTER = {"headache": "present", "sore_throat": "present",
           "cough": "present", "runny_blocked_nose": "present"}


def test_prompt_first_clear_cluster_asks_zero_follow_ups():
    # Clear cluster, breathing already known absent ("I can breathe
    # fine"): ZERO questions, straight to the family answer.
    assert next_q({**CLUSTER, "shortness_of_breath": "absent"}) is None
    assert classify_primary(feats(list(CLUSTER)), ["E_66"], 30, "M")["status"] == "family"


def test_prompt_first_clear_cluster_asks_only_safety_when_breathing_unknown():
    # Safety is the only exception: breathing unknown -> exactly one
    # safety question, then (answering "no") zero more questions.
    assert next_q({**CLUSTER, "shortness_of_breath": "unknown"}) == "breathing_difficulty"
    assert next_q({**CLUSTER, "shortness_of_breath": "absent"},
                  asked=["breathing_difficulty"]) is None


def test_prompt_first_clear_cluster_survives_safety_answer_no():
    # Regression for the 4:0 -> 4:1 bug: answering "no" to breathing
    # must NOT turn a clear family answer into a withheld blank.
    result = classify_primary(feats(list(CLUSTER)), ["E_66"], 30, "M")
    assert result["status"] == "family"
    assert result["primary_prediction"]["condition"] == "Flu-like illness / common cold"
    assert result["match"]["percent_rounded"] == 83


def test_initially_clear_case_stops_after_safety_even_if_negative_demotes_it():
    # Batch-1 sweep failure cluster (8 cases): wheezing + nasal
    # discharge + hoarse voice is Bronchiolitis 88% strong on the
    # initial prompt, but breathing-absent drops it to 0.641 vs a
    # 0.657 bucket minimum, and the old code then asked 6-7 more
    # questions that could only demote it further. With the
    # initial-clear anchor, safety is the only question; after it,
    # no more questions are asked. The final result may still be
    # withheld-with-guidance under the validated bucket minimum —
    # documented in LIMITATIONS — but it is never a blank screen and
    # never bought with extra questions.
    states = {"wheezing": "present", "nasal_discharge": "present",
              "hoarse_voice": "present", "shortness_of_breath": "absent"}
    details = {c: {"code": c, "features": CANON[c]} for c in states}
    assert next_consultation_question(states, details, {}, ["breathing_difficulty"],
                                       CATALOGUE, 30, "M", True) is None
    # Without the anchor, the current-evidence check would reopen the
    # queue on this same state (proving the anchor is what stops it).
    assert next_consultation_question(states, details, {}, ["breathing_difficulty"],
                                       CATALOGUE, 30, "M") is not None


def test_initially_clear_safety_no_does_not_change_model_evidence():
    # Prepare-level freeze: wheezing + nasal discharge + hoarse voice
    # is initially clear (Bronchiolitis). Answering "no" to the safety
    # question must leave model_features at the initial set (no E_66
    # absent added) and ask no further question, so the final result
    # is the initial name, not a withheld screen.
    from app.nlp.symptom_mapper import build_confirmation_output
    from app.services.consultation import prepare_consultation
    text = "wheezing and green nasal discharge and hoarse voice"
    mapping = build_confirmation_output(text, None)
    present = [r["code"] for r in mapping["recognised_symptoms"] if r.get("status") == "present"]
    confirmation = {"recognised_symptoms": mapping["recognised_symptoms"],
                    "confirmed_codes": present, "has_red_flag": False,
                    "assessment_context": {}}
    class _Scalars:
        def all(self):
            return [SimpleNamespace(code=c, features=r, display_name=c) for c, r in CANON.items()]
    class _DB:
        def scalars(self, *a, **k):
            return _Scalars()
    initial = prepare_consultation(confirmation, [], "en", _DB(), 30, "M")
    assert initial["follow_up_question"]["id"] == "breathing_difficulty"
    after = prepare_consultation(confirmation,
                                 [{"question_id": "breathing_difficulty", "answer": "no"}],
                                 "en", _DB(), 30, "M")
    assert after["follow_up_question"] is None
    assert after["model_features"] == initial["model_features"]
    assert "E_66" not in after["explicitly_absent_features"]
    assert after["assessment_context"]["symptom_states"]["shortness_of_breath"] == "absent"


def test_question_only_when_unclear_vague_prompt_asks_discriminators_only():
    # Vague prompt (tiredness + headache): each allowed question is a
    # discriminator that would change the answer -- fever, cough, sore
    # throat, runny/blocked nose -- plus safety first. Duration and
    # severity are advice-only and must never be asked before a result.
    states = {"tiredness": "present", "headache": "present"}
    asked = []
    seen = []
    while True:
        q = next_q(states, asked=asked)
        if q is None:
            break
        seen.append(q)
        asked.append(q)
        code = {"breathing_difficulty": "shortness_of_breath"}.get(q, q)
        states[code] = "absent"
    assert seen == ["breathing_difficulty", "fever", "cough", "sore_throat", "runny_blocked_nose"]
    assert "general_duration" not in seen and "symptom_severity" not in seen


def test_all_no_fallback_tiredness_headache_never_blank_never_neoplasm():
    # All follow-ups answered "no": the original prompt (tiredness +
    # headache) still gets the full withheld screen with guidance, never
    # a blank output and never a tumour name.
    result = assessment(["tiredness", "headache"],
                        {"tiredness": "present", "headache": "present",
                         "shortness_of_breath": "absent", "fever": "absent",
                         "cough": "absent", "sore_throat": "absent",
                         "runny_blocked_nose": "absent"})
    assert result["primary_prediction"] is None
    assert result["withheld_title"]
    assert result["next_steps"], "all-no must still give care guidance"
    assert "does NOT mean you are fine" in result["withheld_message"]
    assert "24-48 hours" in result["withheld_message"]
    assert "neoplasm" not in json.dumps(result).lower()


def test_all_no_fallback_tiredness_headache_fever_gives_malaria_step():
    # Fever in Kenya is the useful "something" for a fever case even
    # when every discriminator is answered "no".
    result = assessment(["tiredness", "headache", "fever"],
                        {"tiredness": "present", "headache": "present", "fever": "present",
                         "shortness_of_breath": "absent", "cough": "absent",
                         "sore_throat": "absent", "runny_blocked_nose": "absent"})
    assert result["primary_prediction"] is None
    joined = " ".join(result["next_steps"])
    assert "malaria" in joined.lower()


def test_i_have_cold_recognised_as_common_cold_context():
    assert "common_cold" in codes_for("i have cold")
    assert "common_cold" in codes_for("have cold")
    assert "common_cold" in codes_for("cold")
    assert "common_cold" in codes_for("I have a cold")
    # "I feel cold" is chills, a different code, and must stay separate.
    assert codes_for("I feel cold") == ["chills"]
    assert "common_cold" not in codes_for("I feel cold")


def test_i_have_cold_gives_family_guidance_not_nothing():
    # A cold on its own has no model features, so it must not be a
    # blank: it gets the family answer, labelled as coming from the
    # user's own words, with NO invented model percent.
    result = assessment(["common_cold"], {"common_cold": "present",
                                          "shortness_of_breath": "absent"})
    primary = result["primary_prediction"]
    assert primary is not None, "cold alone must not be blank"
    assert primary["condition"] == "Flu-like illness / common cold"
    assert primary["is_family_answer"] is True
    assert primary["is_context_family_answer"] is True
    assert "match_percent_rounded" not in primary
    assert result["status"] == "prediction_complete"
    assert result["decision"]["status"] == "possible_explanation"
    # Prompt-first: a context cold asks no follow-ups once breathing
    # is known.
    assert next_q({"common_cold": "present", "shortness_of_breath": "absent"}) is None


def test_i_have_flu_gives_family_guidance_not_nothing():
    assert "flu_like" in codes_for("i have flu")
    result = assessment(["flu_like"], {"flu_like": "present",
                                       "shortness_of_breath": "absent"})
    assert result["primary_prediction"] is not None
    assert result["primary_prediction"]["is_family_answer"] is True


def test_codex_292acf1_symptom_aware_withheld_guidance_adapted_no_medicine():
    # Codex 292acf1 take, adapted: a withheld result's next steps are
    # tailored to the reported symptoms (headache+fever red-flag line,
    # tiredness line), but Codex's paracetamol lines are NOT taken:
    # Muse never recommends a specific medicine.
    result = assessment(["tiredness", "headache", "fever"],
                        {"tiredness": "present", "headache": "present", "fever": "present"})
    joined = " ".join(result["next_steps"])
    assert "stiff neck" in joined
    assert "tiredness or weakness" in joined.lower() or "Unusual tiredness" in joined
    assert "paracetamol" not in json.dumps(result).lower()
    assert "antibiotic" not in json.dumps(result).lower()


def test_sweep_batch1_red_flag_alias_gaps_fixed():
    # Batch-1 sweep: chest_pain_at_rest, stridor and drooling had no
    # Swahili aliases, and "chest pain even at rest" (the display
    # name itself) was not an alias, so those red flags were missed
    # and the case withheld with "unsupported_information" instead of
    # bypassing to urgent review. New Kiswahili aliases are draft and
    # unreviewed, as with all Kiswahili copy in this branch.
    from app.nlp.symptom_mapper import detect_safety_signs
    assert "chest_pain_at_rest" in codes_for("chest pain even at rest")
    assert "chest_pain_at_rest" in codes_for("maumivu ya kifua hata wakati wa kupumzika")
    assert "chest_pain_at_rest" in codes_for("kifua kuuma hata ukipumzika")
    assert "drooling" in codes_for("mate mengi")
    assert "stridor" in codes_for("sauti ya juu unapovuta pumzi")
    assert any(f["code"] == "chest_pain_at_rest" for f in detect_safety_signs("chest pain even at rest"))


def test_can_breathe_fine_is_absent_not_unmatched_and_asks_zero_questions():
    # Sweep check (2026-10-29): "I can breathe fine" was left as
    # unmatched wording, which vetoed an otherwise clear result in
    # build_primary_assessment (cluster + "I can breathe fine"
    # withheld instead of family). Now it maps to shortness_of_breath
    # absent, so the cluster gives the family answer with ZERO
    # follow-ups and the cold gives the context family, also zero.
    # find_symptoms returns the matched code; its status (absent) is
    # decided by build_confirmation_output, asserted below.
    assert "shortness_of_breath" in codes_for("I can breathe fine and I have a cough")
    assert "cough" in codes_for("I can breathe fine and I have a cough")
    from app.nlp.symptom_mapper import build_confirmation_output
    out = build_confirmation_output("headache, sore throat, cough, running nose, I can breathe fine", None)
    by_code = {r["code"]: r.get("status") for r in out["recognised_symptoms"]}
    assert by_code.get("shortness_of_breath") == "absent"
    assert out.get("unmatched_wording") == []
    assert next_q({"headache": "present", "sore_throat": "present", "cough": "present",
                   "runny_blocked_nose": "present", "shortness_of_breath": "absent"}) is None
    assert next_q({"common_cold": "present", "shortness_of_breath": "absent"}) is None


def test_headache_tiredness_cough_never_names_neoplasm():
    # The original sparse-serious failure: headache + tiredness +
    # cough must not name Pulmonary neoplasm, even though the raw V3
    # ranking is peaked on those features.
    result = classify_primary(feats(["headache", "tiredness", "cough"]), [], 30, "M")
    assert result["primary_prediction"] is None or \
        result["primary_prediction"]["condition"] != "Pulmonary neoplasm"
    assert result["status"] == "uncertain"
