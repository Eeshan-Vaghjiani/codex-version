
"""Compare saved Random Forest V1 and V2 models on identical cases.

Uses the held-out DDXPlus validation split.

V1 uses its original training-time evidence encoder.
V2 uses its existing present/absent symptom representation.

COVID-19 and allergic rhinitis do not have independent
ground-truth cases in this evaluation.
"""

import ast
import csv
import json
from collections import Counter
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
)

from prepare_data import encode_evidences


ROOT = Path(__file__).resolve().parents[1]

SOURCE = ROOT / "data/raw/release_validate_patients"
OUTPUT = ROOT / "reports/comparison_v1_v2"

BATCH_SIZE = 2000


def calculate_metrics(actual, predicted, labels):
    """Calculate accuracy and macro-averaged metrics."""

    precision, recall, f1, _ = (
        precision_recall_fscore_support(
            actual,
            predicted,
            labels=labels,
            average="macro",
            zero_division=0,
        )
    )

    return {
        "accuracy": float(
            accuracy_score(actual, predicted)
        ),
        "macro_precision": float(precision),
        "macro_recall": float(recall),
        "macro_f1": float(f1),
    }


def main():
    print("ISSUE 29 - CORRECTED V1 VS V2 COMPARISON")
    print("-----------------------------------------")

    # --------------------------------------------------
    # 1. Load feature schemas
    # --------------------------------------------------

    v1_features = json.loads(
        (ROOT / "models/model_features.json")
        .read_text(encoding="utf-8")
    )

    v2_schema = json.loads(
        (ROOT / "models/v2_feature_schema.json")
        .read_text(encoding="utf-8")
    )

    v2_features = v2_schema["feature_names"]
    v2_codes = v2_schema["symptom_features"]

    # --------------------------------------------------
    # 2. Load saved models
    # --------------------------------------------------

    v1_model = joblib.load(
        ROOT / "models/respiratory_random_forest_v1.joblib"
    )

    v2_model = joblib.load(
        ROOT / "models/rf_v2_23class_prototype.joblib"
    )

    # --------------------------------------------------
    # 3. Verify model compatibility
    # --------------------------------------------------

    assert len(v1_features) == v1_model.n_features_in_ == 198
    assert len(v2_features) == v2_model.n_features_in_ == 66

    assert len(v1_model.classes_) == 21
    assert len(v2_model.classes_) == 23

    assert list(v1_model.feature_names_in_) == v1_features
    assert list(v2_model.feature_names_in_) == v2_features

    assert v2_features == (
        ["AGE", "SEX_M"]
        + [f"{code}__present" for code in v2_codes]
        + [f"{code}__absent" for code in v2_codes]
    )

    original_labels = sorted(
        str(label) for label in v1_model.classes_
    )

    assert set(original_labels).issubset(
        set(v2_model.classes_)
    )

    supported_codes = set(v2_codes)

    # --------------------------------------------------
    # 4. Prepare original V1 evidence encoder
    # --------------------------------------------------

    v1_evidences = json.loads(
        (ROOT / "data/raw/release_evidences.json")
        .read_text(encoding="utf-8")
    )

    v1_evidence_features = v1_features[2:]

    v1_evidence_index = {
        feature: i
        for i, feature in enumerate(v1_evidence_features)
    }

    assert v1_features[:2] == ["AGE", "SEX_M"]

    print("V1 original evidence encoder: ENABLED")
    print("V1 feature count:", len(v1_features))
    print("V2 feature count:", len(v2_features))

    # --------------------------------------------------
    # 5. Prepare evaluation lists
    # --------------------------------------------------

    actual = []
    predictions_v1 = []
    predictions_v2 = []

    batch_v1 = []
    batch_v2 = []
    batch_labels = []

    skipped = 0

    # --------------------------------------------------
    # 6. Predict a batch for both saved models
    # --------------------------------------------------

    def predict_batch():
        if not batch_labels:
            return

        X_v1 = pd.DataFrame(
            batch_v1,
            columns=v1_features,
            dtype="float32",
        )

        X_v2 = pd.DataFrame(
            batch_v2,
            columns=v2_features,
            dtype="float32",
        )

        pred1 = v1_model.predict(X_v1)
        pred2 = v2_model.predict(X_v2)

        actual.extend(batch_labels)

        predictions_v1.extend(
            pred1.tolist()
        )

        predictions_v2.extend(
            pred2.tolist()
        )

        batch_v1.clear()
        batch_v2.clear()
        batch_labels.clear()

    # --------------------------------------------------
    # 7. Read identical held-out validation patients
    # --------------------------------------------------

    print("\nReading held-out validation patients...")

    csv.field_size_limit(2_147_483_647)

    with SOURCE.open(
        encoding="utf-8",
        newline="",
    ) as file:

        for patient in csv.DictReader(file):
            disease = patient["PATHOLOGY"]

            if disease not in original_labels:
                continue

            raw_evidences = ast.literal_eval(
                patient["EVIDENCES"]
            )

            evidence = set(raw_evidences)

            # Preserve the original V2 evaluation
            # patient-selection rule.
            if not evidence.intersection(supported_codes):
                skipped += 1
                continue

            age = float(patient["AGE"])

            sex = patient["SEX"].strip().upper()

            assert 0 <= age <= 120
            assert sex in ("M", "F")

            sex_m = 1.0 if sex == "M" else 0.0

            # ------------------------------------------
            # V1: Original training-time evidence encoding
            # ------------------------------------------

            encoded_v1 = encode_evidences(
                raw_evidences,
                v1_evidences,
                v1_evidence_index,
            )

            row_v1 = (
                [age, sex_m]
                + encoded_v1
            )

            assert len(row_v1) == 198

            # ------------------------------------------
            # V2: Existing present/absent encoding
            # ------------------------------------------

            # Unreported evidence remains unknown.
            # It is NOT automatically marked absent.

            row_v2 = (
                [age, sex_m]
                + [
                    float(code in evidence)
                    for code in v2_codes
                ]
                + [0.0] * len(v2_codes)
            )

            assert len(row_v2) == 66

            # Add the same patient to both batches.

            batch_v1.append(row_v1)
            batch_v2.append(row_v2)
            batch_labels.append(disease)

            if len(batch_labels) >= BATCH_SIZE:
                predict_batch()

    # Process any remaining patients.
    predict_batch()

    # --------------------------------------------------
    # 8. Verify evaluation counts
    # --------------------------------------------------

    assert len(actual) == len(predictions_v1)
    assert len(actual) == len(predictions_v2)

    assert len(actual) == 55808

    # --------------------------------------------------
    # 9. Calculate performance metrics
    # --------------------------------------------------

    results = {
        "V1": calculate_metrics(
            actual,
            predictions_v1,
            original_labels,
        ),
        "V2": calculate_metrics(
            actual,
            predictions_v2,
            original_labels,
        ),
    }

    # --------------------------------------------------
    # 10. Display dataset details
    # --------------------------------------------------

    print("\nEVALUATION DATA")
    print("-----------------------------------------")

    print(
        "Same validation patients:",
        len(actual),
    )

    print(
        "Original conditions:",
        len(original_labels),
    )

    print(
        "V1 prediction classes:",
        len(v1_model.classes_),
    )

    print(
        "V2 prediction classes:",
        len(v2_model.classes_),
    )

    print(
        "Skipped (no supported V2 symptom):",
        skipped,
    )

    # --------------------------------------------------
    # 11. Display V1 vs V2 results
    # --------------------------------------------------

    print("\nMODEL COMPARISON")
    print("-----------------------------------------------")

    print(
        f"{'Metric':<20} "
        f"{'V1':>10} "
        f"{'V2':>10}"
    )

    metric_names = [
        "accuracy",
        "macro_precision",
        "macro_recall",
        "macro_f1",
    ]

    for metric in metric_names:
        print(
            f"{metric:<20} "
            f"{results['V1'][metric]:>10.4f} "
            f"{results['V2'][metric]:>10.4f}"
        )

    # --------------------------------------------------
    # 12. Count V2 predictions of additional conditions
    # --------------------------------------------------

    extra_predictions = Counter(
        prediction
        for prediction in predictions_v2
        if prediction not in original_labels
    )

    print(
        "\nV2 PREDICTIONS OUTSIDE "
        "THE 21 TRUE CONDITIONS"
    )

    print("-----------------------------------------------")

    for name in [
        "COVID-19",
        "Allergic rhinitis",
    ]:
        print(
            f"{name}: {extra_predictions[name]}"
        )

    # --------------------------------------------------
    # 13. Save comparison results
    # --------------------------------------------------

    OUTPUT.mkdir(
        parents=True,
        exist_ok=True,
    )

    rows = [
        {
            "metric": metric,
            "v1": results["V1"][metric],
            "v2": results["V2"][metric],
        }
        for metric in metric_names
    ]

    pd.DataFrame(rows).to_csv(
        OUTPUT / "comparison_metrics.csv",
        index=False,
    )

    report = {
        "evaluation_source": "DDXPlus validation split",
        "same_patients_for_both_models": True,
        "validation_scenarios": len(actual),
        "true_condition_count": len(original_labels),
        "v1_feature_count": 198,
        "v2_feature_count": 66,
        "v1_prediction_classes": 21,
        "v2_prediction_classes": 23,
        "v1_encoding": "Original training-time evidence encoder",
        "v2_encoding": "Present/absent symptom representation",
        "v1": results["V1"],
        "v2": results["V2"],
        "v2_extra_class_predictions": dict(
            extra_predictions
        ),
        "limitations": [
            "DDXPlus cases are simulated, not clinical patient data.",
            "V1 and V2 use different feature representations.",
            "V1 and V2 receive different amounts of symptom information.",
            "True labels cover only the original 21 conditions.",
            "COVID-19 and allergic rhinitis sensitivity cannot be evaluated.",
            "Sparse-symptom performance has not yet been evaluated.",
            "The results do not establish clinical performance.",
        ],
    }

    (
        OUTPUT / "comparison_metrics.json"
    ).write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )

    # --------------------------------------------------
    # 14. Confirm saved files
    # --------------------------------------------------

    print("\nRESULTS SAVED")
    print("-----------------------------------------")

    print(
        OUTPUT / "comparison_metrics.csv"
    )

    print(
        OUTPUT / "comparison_metrics.json"
    )

    print("\nStep 18 PASSED!")


if __name__ == "__main__":
    main()
