"""Uncapped symptom gathering (authorised 2026-10-29): 5 is a soft guide,
not a cutoff. No new disease, code or model feature is invented here;
every question below already exists in the repo catalogue with a
trained V3 feature, and every alias below maps to an existing code.
Safety discipline is unchanged: red flag, 2x unknown, and the
information-gain stop still end the consultation.
"""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ml.primary_selection import classify_primary  # noqa: E402
from app.nlp.symptom_mapper import find_symptoms  # noqa: E402
from app.services.consultation import (  # noqa: E402
    MAX_CONSULTATION_QUESTIONS, POOL, SOFT_QUESTION_GUIDE,
    next_consultation_question,
)

import app.nlp.symptom_mapper as _mapper_module  # noqa: E402

CANON = {r["code"]: r for r in json.loads(
    (Path(_mapper_module.__file__).resolve().parent / "canonical_symptoms.json").read_text())}
CATALOGUE = {c: SimpleNamespace(code=c, features=r["features"]) for c, r in CANON.items()}


def codes_for(text):
    return [f["code"] for f in find_symptoms(text, db=None)]


def test_five_is_soft_guide_not_hard_cap():
    assert SOFT_QUESTION_GUIDE == 5
    assert MAX_CONSULTATION_QUESTIONS == 20
    states = {"fever": "present", "cough": "present", "shortness_of_breath": "absent"}
    details = {"fever": {"code": "fever", "features": ["E_91"]},
               "cough": {"code": "cough", "features": ["E_201"]},
               "shortness_of_breath": {"code": "shortness_of_breath", "features": ["E_66"]}}
    durations = {"cough": {"min_days": 2, "text": "2 days"}}
    # Five questions already asked, none of them the needed discriminator.
    # Under the old hard cap this returned None and the case withheld.
    asked = ["breathing_difficulty", "symptom_duration", "general_duration",
             "symptom_severity", "fatigue_pattern"]
    assert next_consultation_question(states, details, durations, asked, CATALOGUE, 30, "M") == "sore_throat"
    # The hard ceiling still prevents an endless loop.
    assert next_consultation_question(states, details, durations, asked + ["x"] * 15, CATALOGUE, 30, "M") is None


def test_withheld_case_resolves_after_extra_discriminator():
    # Before: fever + cough alone withholds.
    assert classify_primary(["E_91", "E_201"], [], 30, "M")["status"] == "uncertain"
    # After answering the offered sore-throat question "yes":
    result = classify_primary(["E_91", "E_201", "E_97"], [], 30, "M")
    assert result["status"] == "eligible"
    assert result["primary_prediction"]["condition"] == "URTI"
    assert result["match"]["band"] == "moderate"


def test_expanded_pool_uses_only_existing_catalogue_codes():
    for code in POOL:
        assert code in CANON, code
        assert CANON[code]["features"], code
    # Chest pain is deliberately not a routine pool question: a "yes"
    # needs clinical assessment, not a model-guided question.
    assert "chest_pain" not in POOL
    assert "coughing_blood" not in POOL
    assert "stridor" not in POOL


def test_new_kenyan_aliases_map_to_existing_codes():
    assert "night_breathlessness" in codes_for("nakosa pumzi usiku")
    assert "itchy_eyes" in codes_for("macho yanawasha")
    assert "nasal_discharge" in codes_for("nina kamasi za kijani")
    assert "loss_of_smell" in codes_for("siwezi kunusa")
    assert "itchy_nose_throat" in codes_for("pua inawasha")
    assert "activity_fatigue" in codes_for("siwezi kufanya shughuli zangu")


def test_new_pool_questions_exist():
    from app.services.consultation import consultation_question
    for code in ("chills", "night_breathlessness", "nasal_discharge",
                 "loss_of_smell", "itchy_eyes", "loss_of_appetite"):
        payload = consultation_question(code, "en")
        assert payload["text"] and payload["options"]
        payload_sw = consultation_question(code, "sw")
        assert payload_sw["text"] and payload_sw["text"] != payload["text"]
