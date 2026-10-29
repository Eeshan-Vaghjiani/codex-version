
"""Single-condition prediction service for Random Forest V2.

The V2 model is experimental and not clinically validated.
The API must perform symptom confirmation and independent
red-flag checks before calling this service.
"""

import math
from functools import lru_cache

import pandas as pd

from app.ml.model_loader import load_v2_model_bundle
from app.core.errors import ServiceNotReadyError


# No score cutoff has been clinically validated for this model.


@lru_cache(maxsize=1)
def get_v2_bundle():
    """Load the validated V2 model once per process."""
    try:
        return load_v2_model_bundle()
    except Exception as error:
        raise ServiceNotReadyError(
            "The V2 model artifacts are unavailable or invalid; no fallback prediction was produced."
        ) from error


def build_v2_feature_frame(
    age: int,
    sex: str,
    symptom_features: list[str],
    explicitly_absent_features: list[str] | None = None,
) -> pd.DataFrame:
    """Encode confirmed evidence codes into V2's 66 features.

    Unreported symptoms remain unknown.
    Rejected NLP suggestions must not be supplied as absent.
    """

    bundle = get_v2_bundle()
    supported = set(bundle["symptom_features"])

    if not isinstance(symptom_features, list):
        raise ValueError("symptom_features must be a list.")

    if explicitly_absent_features is None:
        explicitly_absent_features = []

    if not isinstance(explicitly_absent_features, list):
        raise ValueError(
            "explicitly_absent_features must be a list."
        )

    for name, codes in (
        ("symptom_features", symptom_features),
        (
            "explicitly_absent_features",
            explicitly_absent_features,
        ),
    ):
        if not all(isinstance(code, str) for code in codes):
            raise ValueError(
                f"{name} must contain evidence code strings."
            )

        if len(codes) != len(set(codes)):
            raise ValueError(
                f"{name} contains duplicate codes."
            )

    present = set(symptom_features)
    absent = set(explicitly_absent_features)

    unsupported = (present | absent) - supported

    if unsupported:
        raise ValueError(
            "Unsupported V2 evidence codes: "
            f"{sorted(unsupported)}"
        )

    if present & absent:
        raise ValueError(
            "Symptoms cannot be both present and absent."
        )

    if not present:
        raise ValueError(
            "At least one confirmed model symptom feature "
            "is required for prediction."
        )

    if type(age) is not int or not 0 <= age <= 120:
        raise ValueError("Age must be between 0 and 120.")

    if not isinstance(sex, str) or sex.upper() not in ("M", "F"):
        raise ValueError("Sex must be M or F.")

    values = {
        feature: 0.0
        for feature in bundle["features"]
    }

    values["AGE"] = float(age)
    values["SEX_M"] = 1.0 if sex.upper() == "M" else 0.0

    for code in present:
        values[f"{code}__present"] = 1.0

    for code in absent:
        values[f"{code}__absent"] = 1.0

    return pd.DataFrame(
        [values],
        columns=bundle["features"],
    )


def predict_v2_single(
    age: int,
    sex: str,
    symptom_features: list[str],
    explicitly_absent_features: list[str] | None = None,
) -> dict:
    """Return one leading condition and uncertainty information."""

    bundle = get_v2_bundle()

    feature_frame = build_v2_feature_frame(
        age=age,
        sex=sex,
        symptom_features=symptom_features,
        explicitly_absent_features=explicitly_absent_features,
    )

    probabilities = [
        float(score)
        for score in bundle["model"].predict_proba(
            feature_frame
        )[0]
    ]

    classes = bundle["classes"]

    if len(probabilities) != len(classes):
        raise ValueError(
            "V2 prediction scores do not match model classes."
        )

    if (
        any(
            not math.isfinite(score) or score < 0
            for score in probabilities
        )
        or not math.isclose(
            sum(probabilities),
            1.0,
            abs_tol=1e-4,
        )
    ):
        raise ValueError("Invalid V2 model scores.")

    ranked = sorted(
        range(len(classes)),
        key=lambda index: (
            -probabilities[index],
            index,
        ),
    )

    first = ranked[0]
    second = ranked[1]

    top_score = probabilities[first]
    second_score = probabilities[second]
    margin = top_score - second_score

    # Saved scores are uncalibrated, and the synthetic extension classes
    # lack independent validation. A large score cannot establish certainty.
    uncertainty_reasons = ["research_model_not_clinically_validated"]
    uncertain = True

    return {
        "model_version": bundle["model_version"],
        "feature_count": feature_frame.shape[1],
        "active_symptom_features": list(symptom_features),
        "predictions": [
            {
                "rank": rank,
                "condition": classes[index],
                "probability": round(probabilities[index], 6),
                "confidence_percent": round(probabilities[index] * 100, 2),
            }
            for rank, index in enumerate(ranked[:3], 1)
        ],
        "uncertain": uncertain,
        "uncertainty_reasons": uncertainty_reasons,
        "score_margin": round(margin, 4),
        "uncertainty_message": (
            "The model prediction is uncertain. "
            "Consider seeking professional medical advice. "
            "This result is not a diagnosis."
            if uncertain
            else
            "The model identified a leading condition, "
            "but this result is not a medical diagnosis."
        ),
        "score_note": (
            "The confidence score is uncalibrated. "
            "It is not a clinically validated probability "
            "that you have this condition."
        ),
    }


def partition_v2_symptom_features(
    symptom_features: list[str],
) -> dict:
    """Separate V2-supported evidence from unsupported codes.

    Unsupported confirmed symptoms are retained for reporting
    but must never be silently encoded as V2 model inputs.
    """

    if not isinstance(symptom_features, list):
        raise ValueError("symptom_features must be a list.")

    if not all(
        isinstance(code, str)
        for code in symptom_features
    ):
        raise ValueError(
            "symptom_features must contain evidence code strings."
        )

    supported_codes = set(
        get_v2_bundle()["symptom_features"]
    )

    supported = list(dict.fromkeys(
        code
        for code in symptom_features
        if code in supported_codes
    ))

    unsupported = list(dict.fromkeys(
        code
        for code in symptom_features
        if code not in supported_codes
    ))

    return {
        "supported_features": supported,
        "unsupported_features": unsupported,
        "has_supported_features": bool(supported),
    }
