
"""Prediction interface for the 23-condition Random Forest V2 prototype."""

import json
import math
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd

from inference.prediction_confidence import assess_prediction


ROOT = Path(__file__).resolve().parents[1]

MODEL_PATH = ROOT / "models" / "rf_v2_23class_prototype.joblib"
SCHEMA_PATH = ROOT / "models" / "v2_feature_schema.json"


@lru_cache(maxsize=1)
def load_v2_resources():
    """Load and verify the saved model and feature schema."""

    model = joblib.load(MODEL_PATH)

    schema = json.loads(
        SCHEMA_PATH.read_text(encoding="utf-8")
    )

    feature_names = schema["feature_names"]

    if (len(feature_names) != 66
            or not all(isinstance(name, str) and name for name in feature_names)
            or len(set(feature_names)) != 66):
        raise ValueError("Expected exactly 66 V2 features.")

    if model.n_features_in_ != len(feature_names):
        raise ValueError("Model and feature schema do not match.")

    if len(model.classes_) != 23:
        raise ValueError("Expected exactly 23 prediction classes.")

    if len(set(str(label) for label in model.classes_)) != 23:
        raise ValueError("Model classes must be unique.")

    if not callable(getattr(model, "predict_proba", None)):
        raise ValueError("Saved model must support predict_proba.")

    if hasattr(model, "feature_names_in_"):
        if list(model.feature_names_in_) != feature_names:
            raise ValueError("Model feature order does not match schema.")

    return model, feature_names


def predict_v2(feature_values):
    """
    Predict one leading condition from 66 encoded features.

    feature_values must contain all features listed in the V2
    schema. Confidence scores are uncalibrated model outputs.
    """

    model, feature_names = load_v2_resources()

    if not isinstance(feature_values, dict):
        raise ValueError("Features must be supplied as a dictionary.")

    expected = set(feature_names)
    supplied = set(feature_values)

    if expected != supplied:
        missing = sorted(expected - supplied)
        unexpected = sorted(supplied - expected)

        raise ValueError(
            f"Feature mismatch. Missing: {missing}; "
            f"Unexpected: {unexpected}"
        )

    row = {}

    for feature in feature_names:
        try:
            value = float(feature_values[feature])
        except (ValueError, TypeError):
            raise ValueError(
                f"Invalid value for feature: {feature}"
            ) from None

        if not math.isfinite(value):
            raise ValueError(
                f"Non-finite value for feature: {feature}"
            )

        if feature == "AGE":
            if value < 0:
                raise ValueError("AGE must be non-negative.")
            if value > 120:
                raise ValueError("AGE must not exceed 120.")
        elif value not in (0.0, 1.0):
            raise ValueError(
                f"{feature} must be encoded as 0 or 1."
            )

        row[feature] = value

    # A symptom cannot be simultaneously present and absent.
    for feature in feature_names:
        if not feature.endswith("__present"):
            continue

        absent_feature = feature.replace(
            "__present", "__absent"
        )

        if absent_feature in row:
            if row[feature] == 1 and row[absent_feature] == 1:
                raise ValueError(
                    f"Conflicting symptom states: {feature}"
                )

    X = pd.DataFrame([row], columns=feature_names)

    scores = model.predict_proba(X)[0]

    result = assess_prediction(
        classes=model.classes_,
        probabilities=scores,
    )

    result["model_version"] = "v2_23class_prototype"

    # Score separation alone cannot establish clinical certainty. The frozen
    # research artifact has no independent real-patient validation, including
    # for its two synthetic extension classes. Keep its raw scores unchanged.
    result["model_score_ambiguous"] = result["uncertain"]
    result["uncertain"] = True
    result["uncertainty_reasons"].append("not_clinically_validated")
    result["model_status"] = "research_prototype"
    result["clinical_validation"] = False
    result["message"] = (
        "This experimental model suggests a condition pattern, but cannot "
        "establish a diagnosis or rule out serious illness."
    )
    used_features = {
        feature_names[int(index)]
        for estimator in getattr(model, "estimators_", [])
        for index in estimator.tree_.feature if index >= 0
    }
    result["learned_absence_features"] = sorted(
        feature for feature in used_features if feature.endswith("__absent")
    )
    result["duration_features_supported"] = False

    return result
