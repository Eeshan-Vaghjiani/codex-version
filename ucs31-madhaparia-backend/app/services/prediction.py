import pandas as pd

from app.ml.model_loader import (
    model,
    model_features,
    disease_classes,
)


def build_feature_frame(
    age: int,
    sex: str,
    symptom_features: list[str],
) -> pd.DataFrame:
    values = {
        feature: 0.0
        for feature in model_features
    }

    values["AGE"] = float(age)
    values["SEX_M"] = 1.0 if sex.upper() == "M" else 0.0

    invalid_features = [
        feature
        for feature in symptom_features
        if feature not in values
    ]

    if invalid_features:
        raise ValueError(
            "Unsupported model features were supplied: "
            f"{invalid_features}"
        )

    for feature in symptom_features:
        values[feature] = 1.0

    frame = pd.DataFrame(
        [[values[feature] for feature in model_features]],
        columns=model_features,
    )

    return frame


def predict_top_conditions(
    age: int,
    sex: str,
    symptom_features: list[str],
    top_k: int = 3,
):
    if not symptom_features:
        raise ValueError(
            "At least one confirmed model symptom feature "
            "is required for prediction."
        )

    feature_frame = build_feature_frame(
        age=age,
        sex=sex,
        symptom_features=symptom_features,
    )

    probabilities = model.predict_proba(feature_frame)[0]

    model_classes = list(model.classes_)

    if model_classes != list(disease_classes):
        raise ValueError(
            "Model class order does not match "
            "disease_classes.json."
        )

    ranked_results = sorted(
        zip(model_classes, probabilities),
        key=lambda item: item[1],
        reverse=True,
    )[:top_k]

    predictions = []

    for rank, (condition, probability) in enumerate(
        ranked_results,
        start=1,
    ):
        predictions.append(
            {
                "rank": rank,
                "condition": condition,
                "probability": round(float(probability), 6),
                "confidence_percent": round(
                    float(probability) * 100,
                    2,
                ),
            }
        )

    return {
        "feature_count": feature_frame.shape[1],
        "active_symptom_features": symptom_features,
        "predictions": predictions,
    }