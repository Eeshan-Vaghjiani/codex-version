
"""Confidence and uncertainty handling for Random Forest V2."""

import math


def assess_prediction(
    classes,
    probabilities,
    min_confidence=0.50,
    min_margin=0.10,
):
    """
    Summarise model prediction scores and flag uncertainty.

    Thresholds are provisional prototype rules, not clinical
    decision thresholds. Model scores are not calibrated
    probabilities of a patient's disease.
    """

    classes = [str(label) for label in classes]
    scores = [float(value) for value in probabilities]

    if len(classes) < 2 or len(classes) != len(scores):
        raise ValueError("Classes and scores must have matching lengths >= 2.")

    if len(classes) != len(set(classes)) or any(not label for label in classes):
        raise ValueError("Classes must have unique non-empty labels.")

    if not 0 <= min_confidence <= 1:
        raise ValueError("min_confidence must be between 0 and 1.")

    if not 0 <= min_margin <= 1:
        raise ValueError("min_margin must be between 0 and 1.")

    if any(not math.isfinite(value) or value < 0 for value in scores):
        raise ValueError("Model scores must be finite and non-negative.")

    if not math.isclose(sum(scores), 1.0, abs_tol=1e-4):
        raise ValueError("Model scores must sum to approximately 1.")

    # Rank conditions by model score, highest first.
    ranked = sorted(
        range(len(scores)),
        key=lambda index: (-scores[index], index),
    )

    top = ranked[0]
    second = ranked[1]

    top_score = scores[top]
    second_score = scores[second]
    margin = top_score - second_score

    reasons = []

    if top_score < min_confidence:
        reasons.append("low_model_score")

    if margin < min_margin:
        reasons.append("close_alternative")

    uncertain = bool(reasons)

    if uncertain:
        message = (
            "The model's prediction is uncertain. "
            "The suggested condition should not be treated "
            "as a diagnosis. Consider professional medical advice."
        )
    else:
        message = (
            "The model identified a leading condition, "
            "but this prediction is not a medical diagnosis."
        )

    return {
        "predicted_condition": classes[top],
        "confidence_score": round(top_score, 4),
        "second_condition": classes[second],
        "second_score": round(second_score, 4),
        "score_margin": round(margin, 4),
        "uncertain": uncertain,
        "uncertainty_reasons": reasons,
        "message": message,
        "score_note": (
            "This is an uncalibrated model score, not a "
            "clinically validated disease probability."
        ),
    }
