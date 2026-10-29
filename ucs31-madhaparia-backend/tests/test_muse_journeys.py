"""20 Kenyan journeys, function-level (text -> mapping -> safety -> V3 selection).

These run without a database or a browser: they use the same functions the
API uses (find_symptoms, detect_safety_signs, classify_primary). A full
server/browser run is NOT claimed here; see TEST_REPORT.md for what ran.
Criteria are the Codex prompt's journeys, in the same order.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ml.primary_selection import classify_primary  # noqa: E402
from app.nlp.breathing_tier import classify_breathing_with_check  # noqa: E402
from app.nlp.symptom_mapper import find_symptoms  # noqa: E402
from app.services.assessment_safety import (  # noqa: E402
    detect_safety_signs as safety_signs,
)
from app.services.primary_assessment import patient_guidance  # noqa: E402

import app.nlp.symptom_mapper as _mapper_module

CANON = {x["code"]: x["features"]
         for x in json.loads((Path(_mapper_module.__file__).resolve().parent / "canonical_symptoms.json").read_text())}


def analyse(text, age=30, sex="M"):
    codes = [f["code"] for f in find_symptoms(text, db=None)]
    feats = sorted({ft for c in codes for ft in CANON.get(c, [])})
    flags = safety_signs(text, age=age)
    if flags:
        return {"codes": codes, "features": feats, "flags": [f["code"] for f in flags],
                "status": "urgent_review", "primary": None}
    result = classify_primary(feats, [], age, sex) if feats else {"status": "insufficient", "primary_prediction": None}
    return {"codes": codes, "features": feats, "flags": [],
            "status": result["status"],
            "primary": (result.get("primary_prediction") or {}).get("condition"),
            "match": result.get("match")}


def test_j01_headache_fatigue_never_tb_or_tumour():
    r = analyse("I have a headache and I feel tired")
    assert r["primary"] not in ("Tuberculosis", "Pulmonary neoplasm")
    assert r["status"] == "uncertain" and r["primary"] is None


def test_j02_cough_only_withheld():
    r = analyse("I have a cough")
    assert r["status"] == "uncertain" and r["primary"] is None


def test_j03_fever_cough_two_days_withheld():
    r = analyse("I have a fever and cough for 2 days")
    assert r["status"] == "uncertain" and r["primary"] is None


def test_j04_fever_cough_tiredness_withheld():
    r = analyse("I have a fever, cough and tiredness for 2 days")
    assert r["status"] == "uncertain" and r["primary"] is None


def test_j05_chronic_cough_weight_loss_tb_only_moderate():
    r = analyse("I have had a cough for 3 weeks and I have lost weight")
    assert r["primary"] == "Tuberculosis"
    assert r["match"]["band"] == "moderate"  # never strong/confident on 2 symptoms


def test_j06_cant_breathe_emergency():
    r = analyse("I can't breathe")
    assert r["status"] == "urgent_review"
    assert "shortness_of_breath" in r["flags"]


def test_j07_difficulty_breathing_walking_can_speak_urgent():
    assert classify_breathing_with_check(
        "napumua kwa shida", at_rest=False, can_speak_full_sentence=True) == "urgent"
    r = analyse("I have difficulty breathing when I walk but I can speak fine")
    assert r["status"] == "urgent_review"


def test_j08_can_breathe_fine_does_not_trigger():
    r = analyse("I can breathe fine but I have a cough")
    assert r["flags"] == []
    assert r["status"] != "urgent_review"


def test_j09_loss_of_smell_only_recognised_no_covid_label():
    r = analyse("I lost my sense of smell")
    assert "loss_of_smell" in r["codes"]
    assert r["primary"] != "COVID-19"
    out = patient_guidance({"language": "en", "symptom_states": {"loss_of_smell": "present"},
                            "symptom_durations": {}, "duration": {}, "severity": {},
                            "follow_up_answers": [], "questions_asked": []},
                           30, decision_status="uncertain", primary=None)
    assert "COVID" in out["covid_scope_note"]


def test_j10_loss_of_smell_cough_fever_no_covid_label():
    r = analyse("I lost my sense of smell, I have a cough and fever")
    assert "loss_of_smell" in r["codes"]
    assert r["primary"] != "COVID-19"


def test_j11_loss_of_taste_fever_note_not_feature():
    r = analyse("I lost my sense of taste and I have a fever")
    assert "loss_of_taste" in r["codes"]
    assert "E_103" not in r["features"] or True  # taste adds no model feature
    assert r["features"] == ["E_91"]


def test_j12_severe_chest_pain_urgent():
    r = analyse("I have a severe chest pain")
    assert r["status"] == "urgent_review"


def test_j13_fainting_urgent():
    r = analyse("I fainted")
    assert r["status"] == "urgent_review" and "fainting" in r["flags"]


def test_j14_blue_lips_urgent():
    r = analyse("My lips turned blue")
    assert r["status"] == "urgent_review" and "blue_lips" in r["flags"]


def test_j15_coughing_blood_urgent():
    r = analyse("I am coughing a lot of blood")
    assert r["status"] == "urgent_review" and "coughing_blood" in r["flags"]


def test_j16_confusion_urgent():
    r = analyse("I feel confused")
    assert r["status"] == "urgent_review" and "confusion" in r["flags"]


def test_j17_fever_in_baby_age_zero_urgent():
    r = analyse("My baby has a fever", age=0)
    assert r["status"] == "urgent_review" and "infant_fever" in r["flags"]


def test_j18_headache_fever_stiff_neck_urgent():
    r = analyse("I have a headache, fever and stiff neck")
    assert r["status"] == "urgent_review"
    assert "headache_fever_stiff_neck" in r["flags"]


def test_j19_generic_fever_pain_fatigue_no_respiratory_name():
    r = analyse("I have a fever, pain and I feel tired")
    assert r["primary"] is None and r["status"] == "uncertain"


def test_j_extra_severe_flu_like_no_test_not_covid():
    # No test, no COVID class: a severe viral illness must never be
    # labelled COVID automatically. Here the text maps to no model
    # feature at all, so nothing is named.
    r = analyse("I have a severe flu-like illness but no test")
    assert r["primary"] != "COVID-19" and r["primary"] is None


def test_j20_close_call_withheld_not_blind_top_pick():
    # Top two are close (acute vs chronic rhinosinusitis, gap 0.12) and the
    # bucket threshold withholds the name. The strict gap-gate case
    # (gap < 0.10 -> close_alternative) is unit-tested with a stubbed
    # ranking in test_muse_p0_improvements.py, because the real V3
    # distribution is usually extremely peaked.
    r = analyse("I have a cough, loss of smell and wheezing after coughing")
    assert r["status"] == "uncertain" and r["primary"] is None
