"""Malformed model inputs fail before reaching inference."""
from unittest.mock import patch

import pytest

from inference.prediction_confidence import assess_prediction
from inference.v2_predictor import predict_v2
from scripts.v2_feature_encoder import encode_v2_record


@pytest.mark.parametrize("labels", [["same", "same"], ["", "other"]])
def test_duplicate_or_empty_labels_rejected(labels):
    with pytest.raises(ValueError, match="unique non-empty"):
        assess_prediction(labels, [.7, .3])


@pytest.mark.parametrize("age", [True, False, None, {}, float("nan"), float("inf"), 121, -1])
def test_invalid_encoder_demographics_rejected(age):
    with pytest.raises(ValueError):
        encode_v2_record({"age": age, "sex": "M", "present": ["E_91"],
                          "absent": [], "unknown": []}, ["E_91"])


@pytest.mark.parametrize("sex", [None, 1, True, {}, "", "X"])
def test_invalid_encoder_sex_rejected(sex):
    with pytest.raises(ValueError):
        encode_v2_record({"age": 21, "sex": sex, "present": ["E_91"],
                          "absent": [], "unknown": []}, ["E_91"])


def test_predictor_bounds_match_backend():
    with patch("inference.v2_predictor.load_v2_resources", return_value=(None, ["AGE"])):
        with pytest.raises(ValueError, match="120"):
            predict_v2({"AGE": 121})


@pytest.mark.parametrize("scores", [[float("nan"), .5], [float("inf"), 0], [-.1, 1.1], [.3, .3]])
def test_malformed_scores_never_become_confidence(scores):
    with pytest.raises(ValueError):
        assess_prediction(["A", "B"], scores)
