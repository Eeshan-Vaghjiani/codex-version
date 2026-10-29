
"""Backend-facing adapter for the Random Forest V2 prototype.

Converts confirmed DDXPlus evidence codes into the saved
66-feature V2 representation and runs the existing predictor.

Important:
- Rejected NLP suggestions are NOT explicit symptom absences.
- Unreported symptoms remain unknown.
- The frozen prototype never learned a split on an absence column. Explicit
  absences are preserved for state integrity but do not affect its raw scores.
- Duration and severity are not supported model inputs.
- The backend must perform red-flag checks before prediction.
- Model outputs are not medical diagnoses.
"""

import json
from pathlib import Path

from inference.v2_predictor import predict_v2
from scripts.v2_feature_encoder import (
    encode_v2_record,
    get_v2_feature_names,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "models/v2_feature_schema.json"


def load_backend_v2_schema():
    """Load and verify the saved V2 feature ordering."""

    schema = json.loads(
        SCHEMA_PATH.read_text(encoding="utf-8")
    )

    symptom_features = schema["symptom_features"]
    feature_names = schema["feature_names"]

    expected_names = get_v2_feature_names(
        symptom_features
    )

    if feature_names != expected_names:
        raise ValueError(
            "Saved V2 schema has an invalid feature order."
        )

    if len(symptom_features) != 32:
        raise ValueError(
            "Expected 32 supported V2 symptom codes."
        )

    if len(feature_names) != 66:
        raise ValueError(
            "Expected 66 V2 model input features."
        )

    return symptom_features, feature_names


def build_v2_backend_features(
    age,
    sex,
    confirmed_features,
    explicitly_absent_features=None,
):
    """Build a complete V2 feature dictionary from backend inputs.

    confirmed_features:
        DDXPlus codes confirmed as present by the patient.

    explicitly_absent_features:
        Codes explicitly denied by the patient, if supported.

    Rejected NLP suggestions must not be passed as absent.
    """

    symptom_features, feature_names = (
        load_backend_v2_schema()
    )

    if not isinstance(confirmed_features, list):
        raise ValueError(
            "confirmed_features must be a list."
        )

    if explicitly_absent_features is None:
        explicitly_absent_features = []

    if not isinstance(explicitly_absent_features, list):
        raise ValueError(
            "explicitly_absent_features must be a list."
        )

    for name, codes in (
        ("confirmed_features", confirmed_features),
        (
            "explicitly_absent_features",
            explicitly_absent_features,
        ),
    ):
        if not all(
            isinstance(code, str)
            for code in codes
        ):
            raise ValueError(
                f"{name} must contain symptom code strings."
            )

        if len(codes) != len(set(codes)):
            raise ValueError(
                f"{name} contains duplicate symptom codes."
            )

    present = set(confirmed_features)
    absent = set(explicitly_absent_features)
    supported = set(symptom_features)

    unsupported = (present | absent) - supported

    if unsupported:
        raise ValueError(
            "Unsupported V2 evidence codes: "
            f"{sorted(unsupported)}"
        )

    conflicting = present & absent

    if conflicting:
        raise ValueError(
            "Symptoms cannot be both present and absent: "
            f"{sorted(conflicting)}"
        )

    unknown = supported - present - absent

    record = {
        "age": age,
        "sex": sex,
        "present": sorted(present),
        "absent": sorted(absent),
        "unknown": sorted(unknown),
    }

    encoded_values = encode_v2_record(
        record,
        symptom_features,
    )

    if len(encoded_values) != len(feature_names):
        raise ValueError(
            "Encoded V2 feature count is incorrect."
        )

    return dict(
        zip(feature_names, encoded_values)
    )


def predict_v2_from_backend(
    age,
    sex,
    confirmed_features,
    explicitly_absent_features=None,
):
    """Predict from backend-compatible symptom evidence codes.

    This function must only be called after the backend
    has completed symptom confirmation and red-flag checks.
    """

    if not confirmed_features:
        raise ValueError(
            "At least one confirmed symptom is required."
        )

    feature_values = build_v2_backend_features(
        age=age,
        sex=sex,
        confirmed_features=confirmed_features,
        explicitly_absent_features=explicitly_absent_features,
    )

    result = predict_v2(feature_values)

    result["feature_count"] = len(feature_values)

    result["active_symptom_features"] = list(
        confirmed_features
    )

    result["explicitly_absent_features"] = list(
        explicitly_absent_features or []
    )

    return result
