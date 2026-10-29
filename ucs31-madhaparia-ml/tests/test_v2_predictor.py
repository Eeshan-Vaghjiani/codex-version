
import json
from pathlib import Path

import pytest

from inference.v2_predictor import (
    load_v2_resources,
    predict_v2,
)


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def sample_features():
    schema = json.loads(
        (ROOT / "models/v2_feature_schema.json").read_text(
            encoding="utf-8"
        )
    )

    features = {
        name: 0.0
        for name in schema["feature_names"]
    }

    features["AGE"] = 30
    features["SEX_M"] = 0

    return features


def test_v2_model_resources():
    model, features = load_v2_resources()

    assert len(model.classes_) == 23
    assert len(features) == 66


def test_v2_prediction(sample_features):
    result = predict_v2(sample_features)

    model, _ = load_v2_resources()

    assert result["predicted_condition"] in model.classes_
    assert 0 <= result["confidence_score"] <= 1
    assert isinstance(result["uncertain"], bool)
    assert result["model_version"] == "v2_23class_prototype"
    assert "uncalibrated" in result["score_note"]
    assert result["uncertain"] is True
    assert result["clinical_validation"] is False
    assert "not_clinically_validated" in result["uncertainty_reasons"]
    assert result["learned_absence_features"] == []
    assert result["duration_features_supported"] is False


def test_missing_feature_rejected(sample_features):
    del sample_features["AGE"]

    with pytest.raises(ValueError, match="Feature mismatch"):
        predict_v2(sample_features)


def test_invalid_binary_feature_rejected(sample_features):
    sample_features["SEX_M"] = 2

    with pytest.raises(ValueError, match="0 or 1"):
        predict_v2(sample_features)


def test_negative_age_rejected(sample_features):
    sample_features["AGE"] = -5

    with pytest.raises(ValueError, match="non-negative"):
        predict_v2(sample_features)


def test_conflicting_symptom_states_rejected(sample_features):
    sample_features["E_103__present"] = 1
    sample_features["E_103__absent"] = 1

    with pytest.raises(ValueError, match="Conflicting"):
        predict_v2(sample_features)
