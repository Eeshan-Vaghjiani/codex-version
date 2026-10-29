
"""Evaluate the 23-condition research prototype on DDXPlus validation.

Only the 21 original diseases have true validation labels.
This does NOT establish COVID-19 or allergic-rhinitis accuracy.
"""

import ast
import csv
import json
import tempfile
from collections import Counter
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)

ROOT = Path(__file__).resolve().parents[1]

BASE = (
    Path(tempfile.gettempdir())
    / "v2_23class_experiment"
)

MODEL_PATH = (
    BASE / "trained_prototype"
    / "rf_v2_23class_prototype.joblib"
)

OUTPUT = BASE / "validation_23class_66"

SOURCE = ROOT / "data/raw/release_validate_patients"

SCHEMA_PATH = ROOT / "models/v2_feature_schema.json"

NEW_CONDITIONS = {
    "COVID-19",
    "Allergic rhinitis"
}


def main():
    print("STEP 139 - 23-CONDITION VALIDATION")
    print("------------------------------------")

    assert MODEL_PATH.is_file(), (
        f"Model not found: {MODEL_PATH}"
    )

    if not SOURCE.is_file():
        raise FileNotFoundError(
            f"Validation data not found: {SOURCE}"
        )

    schema = json.loads(
        SCHEMA_PATH.read_text(encoding="utf-8")
    )

    codes = schema["symptom_features"]
    feature_names = schema["feature_names"]

    model = joblib.load(MODEL_PATH)

    assert len(codes) == 32
    assert len(feature_names) == 66
    assert list(model.feature_names_in_) == feature_names

    all_labels = list(model.classes_)

    assert len(all_labels) == 23
    assert NEW_CONDITIONS.issubset(all_labels)

    original_labels = sorted(
        set(all_labels) - NEW_CONDITIONS
    )

    assert len(original_labels) == 21

    csv.field_size_limit(2_147_483_647)

    X_rows = []
    y_rows = []
    source_rows = []

    skipped = 0

    print("Preparing DDXPlus validation records...")

    with SOURCE.open(
        encoding="utf-8",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        for row_number, row in enumerate(
            reader, start=1
        ):
            disease = row["PATHOLOGY"]

            if disease not in original_labels:
                continue

            evidence = set(
                ast.literal_eval(row["EVIDENCES"])
            )

            present = evidence & set(codes)

            if not present:
                skipped += 1
                continue

            age = float(row["AGE"])
            sex = row["SEX"].strip().upper()

            assert 0 <= age <= 120
            assert sex in ("M", "F")

            vector = (
                [age, 1.0 if sex == "M" else 0.0]
                + [
                    float(code in present)
                    for code in codes
                ]
                + [0.0] * len(codes)
            )

            assert len(vector) == 66

            X_rows.append(vector)
            y_rows.append(disease)
            source_rows.append(row_number)

    X = pd.DataFrame(
        X_rows,
        columns=feature_names,
        dtype="float32"
    )

    y = pd.Series(
        y_rows,
        name="PATHOLOGY"
    )

    assert len(X) > 0
    assert set(y.unique()) == set(original_labels)

    print("Validation records:", len(X))
    print("True conditions:", y.nunique())
    print("Model prediction classes:", len(all_labels))
    print("Records skipped (no supported symptoms):", skipped)

    print("\nRunning predictions...", flush=True)

    predictions = model.predict(X)

    accuracy = accuracy_score(
        y,
        predictions
    )

    precision, recall, f1, _ = (
        precision_recall_fscore_support(
            y,
            predictions,
            labels=original_labels,
            average="macro",
            zero_division=0
        )
    )

    print("\nVALIDATION RESULTS")
    print("------------------------------------")
    print(f"Accuracy:        {accuracy:.4f}")
    print(f"Macro Precision: {precision:.4f}")
    print(f"Macro Recall:    {recall:.4f}")
    print(f"Macro F1-score:  {f1:.4f}")

    print("\nNEW-CONDITION FALSE POSITIVES")
    print("------------------------------------")

    prediction_counts = Counter(predictions)

    for disease in sorted(NEW_CONDITIONS):
        print(
            f"{disease}:",
            prediction_counts[disease]
        )

    errors = Counter(
        (actual, predicted)
        for actual, predicted in zip(
            y_rows, predictions
        )
        if actual != predicted
    )

    sinusitis_to_rhinitis = sum(
        count
        for (actual, predicted), count in errors.items()
        if (
            "allergic" in actual.lower()
            and "sinusitis" in actual.lower()
            and predicted == "Allergic rhinitis"
        )
    )

    print(
        "Allergic sinusitis -> Allergic rhinitis:",
        sinusitis_to_rhinitis
    )

    print("\nTOP 10 MISCLASSIFICATIONS")
    print("------------------------------------")

    for (actual, predicted), count in errors.most_common(10):
        print(f"{actual} -> {predicted}: {count}")

    report = classification_report(
        y,
        predictions,
        labels=original_labels,
        output_dict=True,
        zero_division=0
    )

    report_df = (
        pd.DataFrame(report)
        .transpose()
    )

    print("\nLOWEST RECALL CONDITIONS")
    print("------------------------------------")

    print(
        report_df.loc[original_labels]
        .sort_values("recall")
        .head(7)[[
            "precision",
            "recall",
            "f1-score",
            "support"
        ]]
        .round(4)
        .to_string()
    )

    OUTPUT.mkdir(
        parents=True,
        exist_ok=True
    )

    report_df.to_csv(
        OUTPUT / "classification_report.csv"
    )

    raw_matrix = confusion_matrix(
        y,
        predictions,
        labels=all_labels
    )

    normalized_matrix = confusion_matrix(
        y,
        predictions,
        labels=all_labels,
        normalize="true"
    )

    pd.DataFrame(
        raw_matrix,
        index=all_labels,
        columns=all_labels
    ).to_csv(
        OUTPUT / "confusion_matrix_raw.csv"
    )

    pd.DataFrame(
        normalized_matrix,
        index=all_labels,
        columns=all_labels
    ).to_csv(
        OUTPUT / "confusion_matrix_normalized.csv"
    )

    pd.DataFrame({
        "Feature": feature_names,
        "Importance": model.feature_importances_
    }).sort_values(
        "Importance",
        ascending=False
    ).to_csv(
        OUTPUT / "feature_importance.csv",
        index=False
    )

    pd.DataFrame({
        "source_row": source_rows,
        "actual": y_rows,
        "predicted": predictions
    }).to_csv(
        OUTPUT / "predictions.csv",
        index=False
    )

    metrics = {
        "model": "23-condition V2 research prototype",
        "dataset": "DDXPlus validation",
        "validation_records": len(X),
        "true_conditions": 21,
        "prediction_classes": 23,
        "accuracy": float(accuracy),
        "macro_precision_21": float(precision),
        "macro_recall_21": float(recall),
        "macro_f1_21": float(f1),
        "false_positive_covid19": int(
            prediction_counts["COVID-19"]
        ),
        "false_positive_allergic_rhinitis": int(
            prediction_counts["Allergic rhinitis"]
        ),
        "allergic_sinusitis_to_rhinitis": int(
            sinusitis_to_rhinitis
        ),
        "new_condition_sensitivity_evaluated": False,
        "clinical_validation": False
    }

    (OUTPUT / "validation_metrics.json").write_text(
        json.dumps(metrics, indent=2),
        encoding="utf-8"
    )

    print("\nREPORTS SAVED")
    print("------------------------------------")
    print("Output:", OUTPUT)
    print("Confusion matrices: SAVED")
    print("Classification report: SAVED")
    print("Feature importance: SAVED")
    print("New-condition sensitivity established: NO")
    print("Existing models modified: NO")

    print("\nStep 139 PASSED!")


if __name__ == "__main__":
    main()
