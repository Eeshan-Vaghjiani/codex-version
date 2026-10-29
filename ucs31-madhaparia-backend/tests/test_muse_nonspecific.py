"""Non-specific input must never be a blank output (2026-10-29 urgent fix).

Two exact cases from Eeshan:
1. "Tiredness and headache" -> E_53 + E_89, no respiratory anchor, so
   classify_primary returns non_specific_input / no_supported_respiratory
   anchor, primary None, BEFORE the ranking. The raw V3 ranking underneath
   is Pulmonary neoplasm 1.000 on those 2 features alone: a model artefact
   of two non-specific features. The anchor gate is what blocks that tumour
   name, and it must NOT be removed to force a name.
2. Tiredness + headache + fever (mild) -> E_53 + E_89 + E_91, still no
   anchor, primary None. Raw V3 top is only Epiglottitis 0.216, so no
   single disease can be named. Mild severity does NOT change the model:
   severity is advice-only in V3, so picking "mild" cannot unlock a name.
   The fix is a full useful output, not a forced disease name: plain
   explanation, flu-like care, a malaria-test step for fever in Kenya,
   warning signs, 24-48 hour review, and discriminator follow-ups that
   can resolve the case when a respiratory symptom is added.
"""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ml.primary_selection import classify_primary  # noqa: E402
from app.nlp.symptom_mapper import find_symptoms  # noqa: E402
from app.services import primary_assessment as service  # noqa: E402
from app.services.consultation import (  # noqa: E402
    consultation_question, next_consultation_question,
)

import app.nlp.symptom_mapper as _mapper_module  # noqa: E402

CANON = {x["code"]: x["features"]
         for x in json.loads((Path(_mapper_module.__file__).resolve().parent / "canonical_symptoms.json").read_text())}
CATALOGUE = {c: SimpleNamespace(code=c, features=r) for c, r in CANON.items()}


def codes_for(text):
    return [f["code"] for f in find_symptoms(text, db=None)]


def feats(codes):
    return sorted({ft for c in codes for ft in CANON.get(c, [])})


def assessment(present_codes, states, severity=None):
    confirmation = {
        "model_features": feats(present_codes),
        "explicitly_absent_features": [],
        "assessment_context": {
            "language": "en",
            "symptom_states": states,
            "severity": severity or {},
        },
    }
    result = service.build_primary_assessment(confirmation, 30, "M")
    result.pop("_audit", None)
    return result


def test_tiredness_headache_maps_to_two_non_anchor_features():
    assert set(codes_for("Tiredness and headache")) == {"tiredness", "headache"}
    assert set(codes_for("I have a headache and I feel tired")) == {"tiredness", "headache"}
    result = classify_primary(feats(["tiredness", "headache"]), [], 30, "M")
    assert result["status"] == "uncertain"
    assert result["primary_prediction"] is None
    assert result["reasons"] == ["non_specific_input"]
    assert result["diagnostics"]["policy_reason"] == "no_supported_respiratory_anchor"


def test_tiredness_headache_withheld_output_is_never_blank():
    result = assessment(
        ["tiredness", "headache"],
        {"tiredness": "present", "headache": "present"})
    assert result["status"] == "assessment_uncertain"
    assert result["primary_prediction"] is None
    assert result["decision"]["reasons"] == ["non_specific_input"]
    # Full output: title, plain explanation, withheld wording, guidance.
    assert result["withheld_title"] == "No single respiratory condition can be named from these symptoms alone"
    assert "general symptoms" in result["non_specific_explanation"]
    assert "does NOT mean you are fine" in result["withheld_message"]
    assert "24-48 hours" in result["withheld_message"]
    assert result["next_steps"], "withheld must carry care guidance, never a bare message"
    assert any("Rest" in step for step in result["next_steps"])
    assert any("temperature" in step for step in result["next_steps"])
    # No serious name anywhere on the patient output.
    rendered = json.dumps(result)
    assert "Pulmonary neoplasm" not in rendered
    assert "neoplasm" not in rendered.lower()
    # Discriminator follow-ups are offered, not a dead end.
    offered = [q["code"] for q in result["discriminator_questions"]]
    assert offered == ["cough", "sore_throat", "runny_blocked_nose", "fever", "shortness_of_breath"]


def test_consultation_asks_discriminators_before_giving_up():
    # Prompt-first (Eeshan, 2026-10-29): step through
    # next_consultation_question for tiredness + headache, answering
    # "no" each time. The question sequence is now safety first, then
    # ONLY discriminators that would change the answer (fever, cough,
    # sore throat, runny/blocked nose). Duration and severity are
    # advice-only in V3 and are deliberately NOT asked before a result:
    # asking them first is what wasted the user's time. Answering "no"
    # to all discriminators ends the consultation (the withheld screen
    # with guidance is the result), never a blank screen.
    states = {"tiredness": "present", "headache": "present"}
    details = {"tiredness": {"code": "tiredness", "features": ["E_89"]},
               "headache": {"code": "headache", "features": ["E_53"]}}
    durations, asked = {}, []
    expected = ["breathing_difficulty", "fever", "cough",
                "sore_throat", "runny_blocked_nose"]
    for question_id in expected:
        nxt = next_consultation_question(states, details, durations, asked, CATALOGUE, 30, "M")
        assert nxt == question_id, (asked, nxt)
        asked.append(question_id)
        code = {"breathing_difficulty": "shortness_of_breath"}.get(question_id, question_id)
        states[code] = "absent"
        details[code] = {"code": code, "features": CANON[code]}
    assert next_consultation_question(states, details, durations, asked, CATALOGUE, 30, "M") is None
    assert "general_duration" not in asked and "symptom_severity" not in asked


def test_tiredness_headache_resolves_after_respiratory_symptoms_added():
    # The follow-up resolution: the user adds cough, sore throat and a
    # runny nose, and the tiredness is transient, so the consultation
    # drops the tiredness feature (prepare_consultation sets tiredness
    # features to [] for a transient fatigue pattern). The remaining
    # four-feature respiratory pattern is the 4:0 family case.
    result = classify_primary(feats(["headache", "cough", "sore_throat", "runny_blocked_nose"]), [], 30, "M")
    assert result["status"] == "family"
    assert result["primary_prediction"]["condition"] == "Flu-like illness / common cold"
    assert result["match"]["percent_rounded"] == 78
    # Documented honestly: if the tiredness is persistent it stays in
    # the evidence, the 5-feature pattern scores only 45%, and the case
    # still withholds rather than being given a forced weak name.
    diluted = classify_primary(
        feats(["tiredness", "headache", "cough", "sore_throat", "runny_blocked_nose"]), [], 30, "M")
    assert diluted["status"] == "uncertain"
    assert diluted["primary_prediction"] is None


def test_fever_mild_case_withheld_with_malaria_note_and_followups():
    # Tiredness + headache + fever, severity mild: still no anchor, and
    # mild must not change the decision (severity is advice-only in V3).
    result = assessment(
        ["tiredness", "headache", "fever"],
        {"tiredness": "present", "headache": "present", "fever": "present"},
        severity={"fever": "mild"})
    assert result["status"] == "assessment_uncertain"
    assert result["primary_prediction"] is None
    assert result["decision"]["reasons"] == ["non_specific_input"]
    assert result["withheld_title"]
    assert "general symptoms" in result["non_specific_explanation"]
    # Fever in Kenya must trigger the malaria-test step: the useful
    # "something" for a fever case, instead of a forced disease name.
    assert any("malaria test" in step for step in result["next_steps"])
    assert any("24-48" in step or "worsen" in step for step in result["next_steps"]) or "24-48 hours" in result["withheld_message"]
    offered = [q["code"] for q in result["discriminator_questions"]]
    assert "cough" in offered and "sore_throat" in offered
    assert "runny_blocked_nose" in offered and "shortness_of_breath" in offered
    assert "fever" not in offered  # already reported
    rendered = json.dumps(result)
    assert "Epiglottitis" not in rendered
    assert "Pulmonary neoplasm" not in rendered


def test_fever_case_resolves_after_cough_and_sore_throat_added():
    # Adding cough + sore throat to tiredness + headache + fever gives
    # Seasonal flu (influenza) as a single primary at a low match, not
    # a forced strong name and never Epiglottitis / neoplasm.
    result = assessment(
        ["tiredness", "headache", "fever", "cough", "sore_throat"],
        {"tiredness": "present", "headache": "present", "fever": "present",
         "cough": "present", "sore_throat": "present"})
    assert result["status"] == "prediction_complete"
    primary = result["primary_prediction"]
    assert primary["condition"] == "Influenza"
    assert primary["dual_name"] == "Seasonal flu (influenza)"
    assert primary["match_band"] in ("low", "moderate")


def test_discriminator_wording_matches_consultation_questions():
    for code in ("cough", "sore_throat", "runny_blocked_nose", "fever", "breathing_difficulty"):
        payload = consultation_question(code, "en")
        payload_sw = consultation_question(code, "sw")
        stored_code = "shortness_of_breath" if code == "breathing_difficulty" else code
        stored = next(q for q in service.DISCRIMINATOR_CODES if q == stored_code)
        en, sw = service.DISCRIMINATOR_QUESTIONS[stored]
        assert en == payload["text"], (code, en, payload["text"])
        assert sw == payload_sw["text"], (code, sw, payload_sw["text"])
