
"""Measure how exact train-validation overlap affects V1 and V2.

Both saved models are evaluated on:
1. All respiratory validation cases
2. Cases with exact training-input matches
3. Cases without exact training-input matches

This audit does not rule out near-duplicates or other leakage.
"""

import ast
import csv
import hashlib
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    f1_score,
)


ROOT = Path(__file__).resolve().parents[1]

TRAIN = ROOT / "data/raw/release_train_patients"
VALIDATE = ROOT / "data/raw/release_validate_patients"
PROCESSED = ROOT / "data/processed/validate.csv"

OUTPUT = ROOT / "reports/comparison_v1_v2"

BATCH_SIZE = 2000


def fingerprint(patient):
    """Fingerprint raw patient inputs without using the diagnosis."""

    values = [
        int(float(patient["AGE"])),
        patient["SEX"].strip().upper(),
        sorted(ast.literal_eval(patient["EVIDENCES"])),
    ]

    encoded = json.dumps(
        values,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(encoded).digest()


def calculate_metrics(actual, predicted, labels):
    return {
        "cases": len(actual),
        "conditions_represented": len(set(actual)),
        "accuracy": float(
            accuracy_score(actual, predicted)
        ),
        "macro_f1_21_classes": float(
            f1_score(
                actual,
                predicted,
                labels=labels,
                average="macro",
                zero_division=0,
            )
        ),
    }


def main():
    print("ISSUE 29 - DUPLICATE IMPACT AUDIT")
    print("-----------------------------------------")

    csv.field_size_limit(2_147_483_647)

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

    v1 = joblib.load(
        ROOT / "models/respiratory_random_forest_v1.joblib"
    )

    v2 = joblib.load(
        ROOT / "models/rf_v2_23class_prototype.joblib"
    )

    assert list(v1.feature_names_in_) == v1_features
    assert list(v2.feature_names_in_) == v2_features

    assert len(v1_features) == 198
    assert len(v2_features) == 66

    labels = sorted(str(label) for label in v1.classes_)
    label_set = set(labels)

    assert len(labels) == 21
    assert len(v2.classes_) == 23

    # --------------------------------------------------
    # 1. Identify training input fingerprints
    # --------------------------------------------------

    print("\nReading training input signatures...")

    training_signatures = set()
    training_count = 0

    with TRAIN.open(
        encoding="utf-8",
        newline="",
    ) as file:
        for patient in csv.DictReader(file):
            if patient["PATHOLOGY"] not in label_set:
                continue

            training_signatures.add(
                fingerprint(patient)
            )

            training_count += 1

    print("Training records:", training_count)
    print(
        "Unique training inputs:",
        len(training_signatures),
    )

    # --------------------------------------------------
    # 2. Prepare evaluation storage
    # --------------------------------------------------

    groups = {
        "all": {
            "actual": [],
            "v1": [],
            "v2": [],
        },
        "overlap": {
            "actual": [],
            "v1": [],
            "v2": [],
        },
        "non_overlap": {
            "actual": [],
            "v1": [],
            "v2": [],
        },
    }

    batch_v1 = []
    batch_v2 = []
    batch_actual = []
    batch_group = []

    def predict_batch():
        if not batch_actual:
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

        predictions_v1 = v1.predict(X_v1)
        predictions_v2 = v2.predict(X_v2)

        for actual, pred1, pred2, group in zip(
            batch_actual,
            predictions_v1,
            predictions_v2,
            batch_group,
        ):
            for key in ("all", group):
                groups[key]["actual"].append(actual)
                groups[key]["v1"].append(str(pred1))
                groups[key]["v2"].append(str(pred2))

        batch_v1.clear()
        batch_v2.clear()
        batch_actual.clear()
        batch_group.clear()

    # --------------------------------------------------
    # 3. Evaluate aligned validation patients
    # --------------------------------------------------

    print("\nEvaluating validation patients...")

    with (
        VALIDATE.open(
            encoding="utf-8",
            newline="",
        ) as raw_file,
        PROCESSED.open(
            encoding="utf-8",
            newline="",
        ) as processed_file,
    ):
        raw_reader = csv.DictReader(raw_file)
        processed_reader = csv.DictReader(processed_file)

        for patient in raw_reader:
            disease = patient["PATHOLOGY"]

            if disease not in label_set:
                continue

            processed = next(processed_reader, None)

            assert processed is not None
            assert processed["PATHOLOGY"] == disease
            assert int(float(processed["AGE"])) == int(
                float(patient["AGE"])
            )

            sex_m = float(
                patient["SEX"].strip().upper() == "M"
            )

            assert float(processed["SEX_M"]) == sex_m

            # V1: use already verified training-time
            # encoded features from processed validation.
            row_v1 = [
                float(processed[feature])
                for feature in v1_features
            ]

            # V2: use the same raw evidence representation
            # as the corrected full-data comparison.
            evidence = set(
                ast.literal_eval(patient["EVIDENCES"])
            )

            age = float(patient["AGE"])

            row_v2 = (
                [age, sex_m]
                + [
                    float(code in evidence)
                    for code in v2_codes
                ]
                + [0.0] * len(v2_codes)
            )

            assert len(row_v1) == 198
            assert len(row_v2) == 66

            group = (
                "overlap"
                if fingerprint(patient) in training_signatures
                else "non_overlap"
            )

            batch_v1.append(row_v1)
            batch_v2.append(row_v2)
            batch_actual.append(disease)
            batch_group.append(group)

            if len(batch_actual) >= BATCH_SIZE:
                predict_batch()

        assert next(processed_reader, None) is None

    predict_batch()

    # --------------------------------------------------
    # 4. Verify counts
    # --------------------------------------------------

    total = len(groups["all"]["actual"])
    overlap = len(groups["overlap"]["actual"])
    non_overlap = len(groups["non_overlap"]["actual"])

    assert total == 55808
    assert overlap == 2886
    assert non_overlap == 52922

    print("\nDATASET COUNTS")
    print("-----------------------------------------")
    print("All validation cases:", total)
    print("Overlapping cases:", overlap)
    print("Non-overlapping cases:", non_overlap)

    # --------------------------------------------------
    # 5. Calculate metrics for each group
    # --------------------------------------------------

    results = {}

    print("\nPERFORMANCE BY DATASET GROUP")
    print("-----------------------------------------")

    for group_name in ("all", "overlap", "non_overlap"):
        group = groups[group_name]

        print(f"\n{group_name.upper()}")

        results[group_name] = {}

        for model_name, field in (
            ("V1", "v1"),
            ("V2", "v2"),
        ):
            metrics = calculate_metrics(
                group["actual"],
                group[field],
                labels,
            )

            results[group_name][model_name] = metrics

            print(
                f"{model_name} | "
                f"Cases: {metrics['cases']:,} | "
                f"Conditions: "
                f"{metrics['conditions_represented']} | "
                f"Accuracy: {metrics['accuracy']:.4f} | "
                f"Macro F1: "
                f"{metrics['macro_f1_21_classes']:.4f}"
            )

    # --------------------------------------------------
    # 6. Calculate accuracy change
    # --------------------------------------------------

    print("\nACCURACY CHANGE AFTER EXCLUDING EXACT DUPLICATES")
    print("-----------------------------------------")

    accuracy_changes = {}

    for model_name in ("V1", "V2"):
        full_accuracy = results["all"][model_name]["accuracy"]
        clean_accuracy = results["non_overlap"][
            model_name
        ]["accuracy"]

        change_pp = 100 * (
            clean_accuracy - full_accuracy
        )

        accuracy_changes[model_name] = change_pp

        print(
            f"{model_name}: {change_pp:+.2f} "
            "percentage points"
        )

    # --------------------------------------------------
    # 7. Save audit
    # --------------------------------------------------

    OUTPUT.mkdir(
        parents=True,
        exist_ok=True,
    )

    report = {
        "training_records": training_count,
        "unique_training_inputs": len(
            training_signatures
        ),
        "validation_cases": total,
        "exact_overlap_cases": overlap,
        "non_overlap_cases": non_overlap,
        "exact_overlap_percent": (
            100 * overlap / total
        ),
        "results": results,
        "accuracy_change_percentage_points": (
            accuracy_changes
        ),
        "limitations": [
            "Exact matching uses age, sex, and complete raw evidence.",
            "Duplicate-free validation removes exact matches only.",
            "Near-duplicate patterns have not been evaluated.",
            "Synthetic cases may share diagnostic patterns.",
            "Training and validation come from simulated DDXPlus data.",
            "The audit does not establish clinical performance.",
        ],
    }

    output_path = OUTPUT / "duplicate_impact_audit.json"

    output_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )

    print("\nRESULTS SAVED")
    print(output_path)

    print("\nStep 25 PASSED!")


if __name__ == "__main__":
    main()
