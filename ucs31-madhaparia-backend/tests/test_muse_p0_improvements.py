"""Muse P0 improvements, 2026-10-29. Pure-logic tests, no database.

Covers: rounded match band + labelling, close-gap gate (logic, via a stubbed
ranking, because the real V3 distribution is usually extremely peaked so the
bucket threshold withholds most close cases before the gap gate is reached),
graded breathing tier (EN + SW + negatives), loss-of-taste note, bronchitis
terminology, withheld wording, COVID scope note, duration advice-only, and
the 2x unknown follow-up stop constant.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ml.primary_selection import (  # noqa: E402
    MIN_CLOSE_GAP,
    classify_primary,
    patient_match,
)
from app.ml.v3_predictor import predict_v3  # noqa: E402
from app.nlp.breathing_tier import (  # noqa: E402
    classify_breathing_tier,
    classify_breathing_with_check,
)
from app.nlp.symptom_mapper import detect_safety_signs  # noqa: E402
from app.services.consultation import MAX_UNKNOWN_ANSWERS  # noqa: E402
from app.services.consultation_guidance import consultation_guidance  # noqa: E402
from app.services.health_guidance import COVID_SCOPE_NOTE, get_urgent_guidance  # noqa: E402
from app.services.patient_terminology import patient_term  # noqa: E402
from app.services.primary_assessment import patient_guidance  # noqa: E402


def _context(**overrides):
    ctx = {
        "language": "en",
        "symptom_states": {},
        "symptom_durations": {},
        "duration": {},
        "severity": {},
        "follow_up_answers": [],
        "questions_asked": [],
    }
    ctx.update(overrides)
    return ctx


# --- Score band ---
def test_match_band_whole_percent_and_label():
    m = patient_match(0.923, 0.40)
    assert m["percent_rounded"] == 92
    assert isinstance(m["percent_rounded"], int)
    assert m["band"] == "strong"
    assert "not a probability" in m["label"].lower()
    assert "not a diagnosis" in m["label_detail"].lower()
    assert "not overall accuracy" in m["label_detail"].lower()


def test_match_band_low_and_moderate():
    assert patient_match(0.55, 0.20)["band"] == "low"
    assert patient_match(0.65, 0.20)["band"] == "moderate"
    # 80+ without a clear gap is NOT strong.
    assert patient_match(0.85, 0.05)["band"] != "strong"


def test_match_band_never_two_decimal():
    m = patient_match(0.9675, 0.30)
    assert m["percent_rounded"] == 97
    assert "." not in str(m["percent_rounded"])


# --- Gap gate (logic, stubbed ranking) ---
def _stub_ranking(monkeypatch, top, second):
    import app.ml.primary_selection as selector

    def fake_predict(present, absent, age, sex, top_k=2):
        return {
            "predictions": [
                {"condition": top[0], "raw_relative_score": top[1],
                 "supporting_features": list(present), "supporting_absent_features": list(absent)},
                {"condition": second[0], "raw_relative_score": second[1],
                 "supporting_features": [], "supporting_absent_features": []},
            ]
        }

    monkeypatch.setattr(selector, "predict_v3", fake_predict)


def test_gap_gate_withholds_close_alternative(monkeypatch):
    _stub_ranking(monkeypatch, ("URTI", 0.80), ("Viral pharyngitis", 0.75))
    result = classify_primary(["E_201", "E_91"], [], 30, "M")
    assert result["status"] == "uncertain"
    assert "close_alternative" in result["reasons"]
    assert result["primary_prediction"] is None
    assert "match" not in result


def test_gap_gate_dangerous_close_second(monkeypatch):
    _stub_ranking(monkeypatch, ("Bronchitis", 0.85), ("Pneumonia", 0.70))
    result = classify_primary(["E_201", "E_91"], [], 30, "M")
    assert result["status"] == "uncertain"
    assert "dangerous_close_second" in result["reasons"]


def test_gap_gate_eligible_with_match(monkeypatch):
    _stub_ranking(monkeypatch, ("Bronchitis", 0.90), ("URTI", 0.05))
    result = classify_primary(["E_201", "E_91"], [], 30, "M")
    assert result["status"] == "eligible"
    assert result["match"]["percent_rounded"] == 90
    assert result["match"]["band"] == "strong"


# --- Graded breathing tier ---
def test_breathing_emergency_en_and_sw():
    for text in ("I can't breathe", "I cannot breathe", "gasping for air",
                 "I cannot speak", "siwezi kupumua", "ninashindwa kupumua"):
        assert classify_breathing_tier(text) == "emergency", text


def test_breathing_urgent_on_exertion():
    assert classify_breathing_tier("napumua kwa shida") == "urgent"
    assert classify_breathing_tier("I have difficulty breathing") == "urgent"
    assert classify_breathing_with_check(
        "napumua kwa shida", at_rest=False, can_speak_full_sentence=True) == "urgent"
    assert classify_breathing_with_check(
        "napumua kwa shida", at_rest=True, can_speak_full_sentence=True) == "emergency"
    assert classify_breathing_with_check(
        "napumua kwa shida", at_rest=False, can_speak_full_sentence=False) == "emergency"
    assert classify_breathing_with_check("napumua kwa shida") == "needs_severity_check"


def test_breathing_negatives_do_not_trigger():
    for text in ("I can breathe fine", "napumua vizuri", "no difficulty breathing"):
        assert classify_breathing_tier(text) is None, text
        assert detect_safety_signs(text) == [], text


def test_safety_signs_carry_tier():
    flags = detect_safety_signs("I cannot breathe")
    assert flags and flags[0]["code"] == "shortness_of_breath"
    assert flags[0]["breathing_tier"] == "emergency"
    flags = detect_safety_signs("napumua kwa shida")
    assert flags and flags[0]["breathing_tier"] == "urgent"


def test_urgent_guidance_graded():
    assert "NOW" in get_urgent_guidance("en", tier="emergency")["health_guidance"]
    assert "TODAY" in get_urgent_guidance("en", tier="urgent")["health_guidance"]
    assert "dharura" in get_urgent_guidance("sw", tier="emergency")["health_guidance"].lower() or \
        "SASA" in get_urgent_guidance("sw", tier="emergency")["health_guidance"]


# --- Loss of taste: recognised note, not a model feature ---
def test_loss_of_taste_recognised_without_model_feature():
    from app.nlp.symptom_mapper import find_symptoms

    found = find_symptoms("I lost my sense of taste", db=None)
    codes = [f["code"] for f in found]
    assert "loss_of_taste" in codes
    # find_symptoms returns codes only; features come from the canonical map.
    import json
    from pathlib import Path
    import app.nlp.symptom_mapper as mapper_module

    canon = {x["code"]: x["features"] for x in json.loads(
        (Path(mapper_module.__file__).resolve().parent / "canonical_symptoms.json").read_text())}
    assert canon["loss_of_taste"] == []


def test_covid_note_on_taste_or_smell():
    ctx = _context(symptom_states={"loss_of_taste": "present"})
    out = patient_guidance(ctx, 30, decision_status="uncertain", primary=None)
    assert "COVID" in out["covid_scope_note"]
    assert "does not rule out COVID" in out["covid_scope_note"] or "not rule out" in out["covid_scope_note"]
    assert "COVID" in COVID_SCOPE_NOTE["en"]


# --- Terminology ---
def test_bronchitis_plain_alias():
    term = patient_term("Bronchitis", "en")
    assert term["display_name"] == "Chest infection (bronchitis)"
    term_sw = patient_term("Bronchitis", "sw")
    assert term_sw["display_name"] == "Maambukizi ya kifua (bronchitis)"


# --- Withheld wording ---
def test_withheld_message_never_reassures():
    ctx = _context(_decision_reasons=["close_alternative"])
    out = patient_guidance(ctx, 30, decision_status="uncertain", primary=None)
    assert "does NOT mean you are fine" in out["withheld_message"]
    assert "does NOT rule out" in out["withheld_message"]
    assert "24-48" in out["withheld_message"]
    assert "too close" in out["withheld_reason"]


# --- Duration: advice only, never a model feature ---
def test_duration_advice_acute_and_chronic():
    acute = consultation_guidance(_context(duration={"min_days": 2, "text": "2 days"}), 30)
    assert any("malaria" in s.lower() for s in acute["next_steps"])
    chronic = consultation_guidance(_context(duration={"min_days": 20, "text": "3 weeks"}), 30)
    assert any("TB" in s for s in chronic["next_steps"])


def test_duration_does_not_change_model_score():
    first = predict_v3(["E_201", "E_91"], [], 30, "M", top_k=2)
    second = predict_v3(["E_201", "E_91"], [], 30, "M", top_k=2)
    assert first["predictions"] == second["predictions"]
    # predict_v3 takes no duration argument at all: duration is advice-only.
    assert "duration" not in predict_v3.__code__.co_varnames


# --- Follow-up stops ---
def test_unknown_stop_constant():
    assert MAX_UNKNOWN_ANSWERS == 2
    assert MIN_CLOSE_GAP == 0.10
