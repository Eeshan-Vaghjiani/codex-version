"""Pieces taken with credit from the Codex branch (f423bde / 85ccf0e).

Taken, because they fit Muse's branch cleanly and do not break its guards:
- Everyday EN/SW/Sheng aliases for existing codes (Codex f423bde).
- Four honest context codes with NO model features (weakness, dizziness,
  common_cold, flu_like): recognising the patient's words without inventing
  a disease, a feature or a diagnosis.
- Sudden neurological change as an emergency safety flag (Codex 85ccf0e
  focal block): sudden one-sided weakness, face drooping, slurred speech.
  General weakness ("sina nguvu", "I feel weak") is context only and must
  NOT trigger this flag.
- Fuller COVID out-of-scope wording (Codex terminology covid_scope_message).

Deliberately NOT taken here (see CHANGELOG comparison): the Codex gap gate
(it withholds the approved 4:0 family cluster and has no sparse-serious
guard), the bronchitis display variant (decided format is
"Chest infection (bronchitis)"), any paracetamol recommendation (no
specific medicine is recommended), the 5-question cap (superseded by the
uncapped-gathering authorisation), and the weakness-clarification question
(new safety pathway, needs its own review).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.nlp.symptom_mapper import find_symptoms  # noqa: E402
from app.services.assessment_safety import detect_safety_signs  # noqa: E402
from app.services.health_guidance import COVID_SCOPE_NOTE  # noqa: E402

import app.nlp.symptom_mapper as _mapper_module  # noqa: E402

CANON = {x["code"]: x for x in json.loads(
    (Path(_mapper_module.__file__).resolve().parent / "canonical_symptoms.json").read_text())}


def codes_for(text):
    return [f["code"] for f in find_symptoms(text, db=None)]


def test_codex_everyday_aliases_map_to_existing_codes():
    assert "tiredness" in codes_for("nimechoka sana")
    assert "tiredness" in codes_for("ninachoka")
    assert "sore_throat" in codes_for("koo linaniuma")
    assert "runny_blocked_nose" in codes_for("pua inatoka")
    assert "headache" in codes_for("kichwa kinauma")
    assert "chest_pain" in codes_for("chest inauma")
    assert "wheezing" in codes_for("nina sauti ya mluzi")
    assert "chills" in codes_for("I feel cold")
    assert "heavy_sweating" in codes_for("I sweat at night")
    assert "runny_blocked_nose" in codes_for("my nose is runny")
    assert "loss_of_taste" in codes_for("ladha imepotea")


def test_codex_context_codes_recognised_with_no_model_features():
    assert "weakness" in codes_for("sina nguvu")
    assert "weakness" in codes_for("I feel weak")
    assert "dizziness" in codes_for("nina kizunguzungu")
    assert "common_cold" in codes_for("niko na cold")
    assert "flu_like" in codes_for("I have flu")
    for code in ("weakness", "dizziness", "common_cold", "flu_like"):
        assert CANON[code]["features"] == [], code
        assert CANON[code]["kind"] == "context", code


def test_breathing_phrases_from_codex_map_to_breathing_code():
    # Eeshan's checklist phrases: difficulty breathing and cannot-speak
    # are breathing warning signs. In a symptom box, "I can't speak" is
    # treated as speech/breathing difficulty (trade-off, documented in
    # LIMITATIONS: it could also occur in a non-breathing sentence).
    assert "shortness_of_breath" in codes_for("having challenges breathing")
    assert "shortness_of_breath" in codes_for("difficulty breathing at rest")
    assert "shortness_of_breath" in codes_for("I can't speak")
    assert "shortness_of_breath" in codes_for("nimeishiwa na pumzi")
    assert "shortness_of_breath" in codes_for("napumua kwa shida nikiwa nimepumzika")


def test_sudden_neurological_change_is_emergency_not_general_weakness():
    codes = [f["code"] for f in detect_safety_signs("sudden weakness on one side")]
    assert "sudden_neurological_change" in codes
    codes = [f["code"] for f in detect_safety_signs("my face is drooping")]
    assert "sudden_neurological_change" in codes
    codes = [f["code"] for f in detect_safety_signs("I feel weak and tired")]
    assert "sudden_neurological_change" not in codes
    codes = [f["code"] for f in detect_safety_signs("sina nguvu")]
    assert "sudden_neurological_change" not in codes


def test_covid_note_uses_codex_fuller_wording():
    assert "severity alone cannot identify COVID" in COVID_SCOPE_NOTE["en"]
    assert "less reliable with newer variants" in COVID_SCOPE_NOTE["en"]
    assert "haliondoi COVID" in COVID_SCOPE_NOTE["sw"]
