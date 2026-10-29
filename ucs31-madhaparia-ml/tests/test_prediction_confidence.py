
import pytest

from inference.prediction_confidence import assess_prediction


def test_high_confidence_prediction():
    result = assess_prediction(
        ["Asthma", "Bronchitis", "Influenza"],
        [0.65, 0.25, 0.10],
    )

    assert result["predicted_condition"] == "Asthma"
    assert result["confidence_score"] == 0.65
    assert result["second_condition"] == "Bronchitis"
    assert result["score_margin"] == 0.40
    assert result["uncertain"] is False
    assert result["uncertainty_reasons"] == []


def test_low_confidence_prediction():
    result = assess_prediction(
        ["Asthma", "Bronchitis", "Influenza"],
        [0.45, 0.30, 0.25],
    )

    assert result["predicted_condition"] == "Asthma"
    assert result["uncertain"] is True
    assert "low_model_score" in result["uncertainty_reasons"]


def test_close_competing_conditions():
    result = assess_prediction(
        ["Asthma", "Bronchitis", "Influenza"],
        [0.52, 0.44, 0.04],
    )

    assert result["predicted_condition"] == "Asthma"
    assert result["score_margin"] == 0.08
    assert result["uncertain"] is True
    assert "close_alternative" in result["uncertainty_reasons"]


def test_high_confidence_does_not_mean_diagnosis():
    result = assess_prediction(
        ["Asthma", "Bronchitis"],
        [0.90, 0.10],
    )

    assert result["uncertain"] is False
    assert "not a medical diagnosis" in result["message"]
    assert "uncalibrated" in result["score_note"]


def test_invalid_probability_total():
    with pytest.raises(ValueError):
        assess_prediction(
            ["Asthma", "Bronchitis"],
            [0.60, 0.20],
        )


def test_negative_model_score():
    with pytest.raises(ValueError):
        assess_prediction(
            ["Asthma", "Bronchitis"],
            [1.10, -0.10],
        )


def test_mismatched_classes_and_scores():
    with pytest.raises(ValueError):
        assess_prediction(
            ["Asthma", "Bronchitis", "Influenza"],
            [0.70, 0.30],
        )
