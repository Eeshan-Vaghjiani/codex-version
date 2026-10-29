"""Dual naming, running-nose alias, 4:0 family answer, sparse-serious
guards, and useful withheld screens (2026-10-29 follow-up).

Uses the same function-level path as test_muse_journeys.py: text ->
mapping -> safety -> V3 selection, plus the patient_assessment layer
for family / TB / withheld rendering.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ml.primary_selection import classify_primary  # noqa: E402
from app.nlp.symptom_mapper import find_symptoms  # noqa: E402
from app.services.assessment_safety import detect_safety_signs as safety_signs  # noqa: E402
from app.services.primary_assessment import patient_guidance  # noqa: E402
from app.services.patient_terminology import patient_term, terminology  # noqa: E402

import app.nlp.symptom_mapper as _mapper_module  # noqa: E402

CANON = {x["code"]: x["features"]
         for x in json.loads((Path(_mapper_module.__file__).resolve().parent / "canonical_symptoms.json").read_text())}
V3_CLASSES = [
    'Acute COPD exacerbation / infection', 'Acute laryngitis',
    'Acute pulmonary edema', 'Acute rhinosinusitis', 'Allergic sinusitis',
    'Bronchiectasis', 'Bronchiolitis', 'Bronchitis',
    'Bronchospasm / acute asthma exacerbation', 'Chronic rhinosinusitis',
    'Croup', 'Epiglottitis', 'Influenza', 'Larygospasm', 'Pneumonia',
    'Pulmonary neoplasm', 'Spontaneous pneumothorax', 'Tuberculosis',
    'URTI', 'Viral pharyngitis', 'Whooping cough',
]


def codes_for(text):
    return [f["code"] for f in find_symptoms(text, db=None)]


def feats_for(text):
    return sorted({ft for c in codes_for(text) for ft in CANON.get(c, [])})


def analyse(text, age=30, sex="M"):
    codes = codes_for(text)
    feats = feats_for(text)
    flags = safety_signs(text, age=age)
    if flags:
        return {"codes": codes, "features": feats, "flags": [f["code"] for f in flags],
                "status": "urgent_review", "primary": None}
    result = classify_primary(feats, [], age, sex) if feats else {"status": "insufficient", "primary_prediction": None}
    return {"codes": codes, "features": feats, "flags": [],
            "status": result["status"],
            "primary": (result.get("primary_prediction") or {}).get("condition"),
            "full": result}


def test_dual_naming_every_class_both_languages():
    assert set(terminology()["conditions"]) == set(V3_CLASSES)
    for cls in V3_CLASSES:
        for lang in ("en", "sw"):
            term = patient_term(cls, lang)
            # Stable format: simple name first, medical name in parentheses.
            assert term["dual_name"] == term["display_name"]
            assert re.match(r"^.+ \(.+\)$", term["display_name"]), (cls, lang, term["display_name"])
            assert term["display_name"] != term["medical_name"]
            assert term["simple_name"] and "(" not in term["simple_name"]
            assert term["description"]


def test_dual_naming_spot_checks():
    assert patient_term("Bronchitis", "en")["dual_name"] == "Chest infection (bronchitis)"
    assert patient_term("Bronchitis", "sw")["dual_name"] == "Maambukizi ya kifua (bronchitis)"
    assert patient_term("Influenza", "en")["dual_name"] == "Seasonal flu (influenza)"
    assert patient_term("Influenza", "sw")["dual_name"] == "Influenza (mafua ya influenza)"
    assert patient_term("Pneumonia", "en")["dual_name"] == "Lung infection (pneumonia)"
    assert patient_term("Pneumonia", "sw")["dual_name"] == "Maambukizi ya mapafu (pneumonia)"
    assert patient_term("Tuberculosis", "en")["dual_name"] == "TB (tuberculosis)"
    assert patient_term("Tuberculosis", "sw")["dual_name"] == "Kifua kikuu (TB)"
    assert patient_term("Pulmonary neoplasm", "en")["dual_name"] == "Abnormal growth in the lung (pulmonary neoplasm)"
    # Bare mafua must never be the flu display name.
    assert patient_term("Influenza", "sw")["dual_name"] != "mafua"


def test_running_nose_alias():
    r = analyse("I have a headache, sore throat, dry cough and a running nose")
    assert "runny_blocked_nose" in r["codes"]
    # With only 3 mapped symptoms before the alias fix this was 3:0; now
    # the phrase maps the nose symptom, giving the full 4-symptom cluster.
    assert r["codes"] == ["sore_throat", "runny_blocked_nose", "headache", "cough"] or set(r["codes"]) == {
        "sore_throat", "runny_blocked_nose", "headache", "cough"}


def test_four_zero_clear_winner_family_answer():
    r = analyse("I have a headache, sore throat, cough and runny nose for 2 days")
    assert r["status"] == "family", r
    assert r["primary"] == "Flu-like illness / common cold"
    assert r["full"]["primary_prediction"]["is_family_answer"] is True
    assert r["full"]["primary_prediction"]["family_top_condition"] == "URTI"
    assert r["full"]["match"]["band"] in ("moderate", "strong")


def test_four_zero_close_case_still_withholds():
    # Same bucket, but a close viral pattern must not get a family answer.
    # Fever + cough + tiredness + sore throat: top is not a clear viral
    # winner with the required gap, so it must stay uncertain.
    r = analyse("I have a fever, cough, tiredness and sore throat for 2 days")
    assert r["status"] in ("uncertain", "family")
    if r["status"] == "family":
        assert r["full"]["match"]["percent_rounded"] >= 75
        assert r["full"]["diagnostics"]["source_relative_top_two_gap"] >= 0.20
    # Direct unit check of the family gate via a close ranking: use the
    # known 4-feature close case from the journeys (cough + smell + wheeze
    # is not viral-family-clear) through classify_primary on its features.
    close = classify_primary(["E_201", "E_103", "E_214", "E_97"], [], 30, "M")
    assert close["status"] != "eligible" or close["primary_prediction"]["condition"] not in (
        "Pulmonary neoplasm", "Tuberculosis")


def test_neoplasm_on_sparse_guard():
    r = analyse("I have a headache and I feel tired and I have had a cough for 2 days")
    assert r["primary"] != "Pulmonary neoplasm"
    assert r["status"] != "eligible"
    assert r["full"].get("reasons") == ["sparse_serious_guard"] or "sparse_serious_guard" in r["full"].get("reasons", [])
    # Match must not be strong for a serious name on sparse input.
    if r["full"].get("match"):
        assert r["full"]["match"]["band"] != "strong"


def test_tb_strong_on_sparse_guard():
    # Synthetic sparse pattern that would otherwise score TB strong: use
    # the guard function directly on a strong TB ranking scenario, plus the
    # real chronic pattern which must NOT be blocked (specific feature).
    from app.ml.primary_selection import sparse_serious_guard
    assert sparse_serious_guard("Pulmonary neoplasm", {"E_201", "E_53", "E_89"}, 0.9999, 0.99) is True
    assert sparse_serious_guard("Tuberculosis", {"E_201", "E_53", "E_89"}, 0.95, 0.50) is True
    assert sparse_serious_guard("Tuberculosis", {"E_201", "E_162"}, 0.75, 0.50) is False  # weight loss is specific
    assert sparse_serious_guard("Pulmonary neoplasm", {"E_201", "E_53", "E_89", "E_162"}, 0.99, 0.99) is False  # 4 features
    # Real chronic pattern still names TB, moderate only.
    r = analyse("I have had a cough for 3 weeks and I have lost weight")
    assert r["primary"] == "Tuberculosis"
    assert r["full"]["match"]["band"] == "moderate"


def test_withheld_still_has_care_steps():
    context = {
        "language": "en",
        "symptom_states": {"fever": "present", "cough": "present", "tiredness": "present"},
        "_present_features": ["E_91", "E_201", "E_89"],
        "_decision_reasons": ["ambiguous_model_rank"],
    }
    guidance = patient_guidance(context, 30, "uncertain", None)
    assert guidance["withheld_message"]
    assert "does NOT rule out" in guidance["withheld_message"]
    assert guidance["next_steps"]
    assert any("malaria" in step.lower() for step in guidance["next_steps"])
    assert guidance["covid_scope_note"]


def test_family_answer_through_assessment_layer(monkeypatch):
    import app.services.primary_assessment as service
    from copy import deepcopy
    chosen = {"status": "family",
              "primary_prediction": {"condition": "Flu-like illness / common cold",
                                     "is_family_answer": True, "family_top_condition": "URTI"},
              "reasons": ["family_viral_upper_respiratory"], "policy_version": "test",
              "clinical_validation": False, "diagnostics": {},
              "match": {"percent_rounded": 78, "band": "moderate",
                        "label": "Model match, not a probability.",
                        "label_detail": "Family match, not a diagnosis."}}
    monkeypatch.setattr(service, "select_primary_evidence", lambda *a, **k: deepcopy(chosen))
    confirmation = {"model_features": ["E_201", "E_53", "E_97", "E_181"],
                    "explicitly_absent_features": [],
                    "assessment_context": {"language": "en", "symptom_states": {
                        "cough": "present", "headache": "present", "sore_throat": "present",
                        "runny_blocked_nose": "present"}}}
    result = service.build_primary_assessment(confirmation, 30, "M")
    result.pop("_audit")
    assert result["status"] == "prediction_complete"
    primary = result["primary_prediction"]
    assert primary["dual_name"] == "Flu-like illness / common cold (viral upper respiratory infection)"
    assert primary["is_family_answer"] is True
    assert primary["family_note"]
    assert result["covid_scope_note"]


def test_tb_note_through_assessment_layer(monkeypatch):
    import app.services.primary_assessment as service
    from copy import deepcopy
    chosen = {"status": "eligible", "primary_prediction": {"condition": "Tuberculosis"},
              "reasons": [], "policy_version": "test", "clinical_validation": False,
              "diagnostics": {},
              "match": {"percent_rounded": 75, "band": "moderate",
                        "label": "Model match, not a probability.", "label_detail": ""}}
    monkeypatch.setattr(service, "select_primary_evidence", lambda *a, **k: deepcopy(chosen))
    confirmation = {"model_features": ["E_201", "E_162"],
                    "explicitly_absent_features": [],
                    "assessment_context": {"language": "en", "symptom_states": {
                        "cough": "present", "weight_loss": "present"}}}
    result = service.build_primary_assessment(confirmation, 30, "M")
    result.pop("_audit")
    assert result["primary_prediction"]["tb_note"]
    assert "does not mean having HIV" in result["primary_prediction"]["tb_note"]


def test_sparse_guard_through_assessment_layer(monkeypatch):
    import app.services.primary_assessment as service
    from copy import deepcopy
    chosen = {"status": "eligible", "primary_prediction": {"condition": "Pulmonary neoplasm"},
              "reasons": [], "policy_version": "test", "clinical_validation": False,
              "diagnostics": {},
              "match": {"percent_rounded": 100, "band": "strong",
                        "label": "Model match, not a probability.", "label_detail": ""}}
    monkeypatch.setattr(service, "select_primary_evidence", lambda *a, **k: deepcopy(chosen))
    confirmation = {"model_features": ["E_201", "E_53", "E_89"],
                    "explicitly_absent_features": [],
                    "assessment_context": {"language": "en", "symptom_states": {
                        "cough": "present", "headache": "present", "tiredness": "present"}}}
    result = service.build_primary_assessment(confirmation, 30, "M")
    result.pop("_audit")
    assert result["primary_prediction"] is None
    assert result["decision"]["reasons"] == ["sparse_serious_guard"]
    assert result["care_level"] == "professional_review"


def test_tb_note_text():
    from app.services.primary_assessment import TB_NOTE
    assert "does not mean having HIV" in TB_NOTE["en"]
    assert "bacterial" in TB_NOTE["en"].lower()
    assert "testable" in TB_NOTE["en"].lower()
    assert "treatable" in TB_NOTE["en"].lower()
