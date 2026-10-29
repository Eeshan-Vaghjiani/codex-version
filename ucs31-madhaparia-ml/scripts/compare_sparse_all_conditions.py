
"""Evaluate V1 and V2 with limited symptoms across all 21 conditions.

Every original respiratory validation patient is included.
For each scenario, disclose up to 1, 2, or 3 supported
evidence codes, using the same information for both models.

The evaluation uses simulated DDXPlus records.
It does not establish clinical performance.
"""

import ast
import csv
import json
import random
from collections import Counter
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    precision_recall_fscore_support,
)

from prepare_data import encode_evidences


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/raw/release_validate_patients"
OUTPUT = ROOT / "reports/comparison_v1_v2"

SYMPTOM_COUNTS = (1, 2, 3)
BATCH_SIZE = 2000
SEED = 20261021


def calculate_metrics(actual, predicted, labels):
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
    print("ISSUE 29 - ALL-CONDITION SPARSE EVALUATION")
    print("------------------------------------------")

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
    supported = set(v2_codes)

    v1_evidences = json.loads(
        (ROOT / "data/raw/release_evidences.json")
        .read_text(encoding="utf-8")
    )

    v1_evidence_features = v1_features[2:]
    v1_evidence_index = {
        feature: i
        for i, feature in enumerate(v1_evidence_features)
    }

    v1_model = joblib.load(
        ROOT / "models/respiratory_random_forest_v1.joblib"
    )

    v2_model = joblib.load(
        ROOT / "models/rf_v2_23class_prototype.joblib"
    )

    assert v1_features[:2] == ["AGE", "SEX_M"]
    assert list(v1_model.feature_names_in_) == v1_features
    assert list(v2_model.feature_names_in_) == v2_features

    assert len(v1_features) == 198
    assert len(v2_features) == 66

    assert v2_features == (
        ["AGE", "SEX_M"]
        + [f"{code}__present" for code in v2_codes]
        + [f"{code}__absent" for code in v2_codes]
    )

    labels = sorted(
        str(label)
        for label in v1_model.classes_
    )

    assert len(labels) == 21
    assert len(v2_model.classes_) == 23

    actual = []

    predictions = {
        count: {"V1": [], "V2": []}
        for count in SYMPTOM_COUNTS
    }

    batches = {
        count: {"V1": [], "V2": []}
        for count in SYMPTOM_COUNTS
    }

    disclosure_counts = {
        count: Counter()
        for count in SYMPTOM_COUNTS
    }

    batch_labels = []

    def predict_batch():
        if not batch_labels:
            return

        for count in SYMPTOM_COUNTS:
            X_v1 = pd.DataFrame(
                batches[count]["V1"],
                columns=v1_features,
                dtype="float32",
            )

            X_v2 = pd.DataFrame(
                batches[count]["V2"],
                columns=v2_features,
                dtype="float32",
            )

            predictions[count]["V1"].extend(
                v1_model.predict(X_v1).tolist()
            )

            predictions[count]["V2"].extend(
                v2_model.predict(X_v2).tolist()
            )

            batches[count]["V1"].clear()
            batches[count]["V2"].clear()

        actual.extend(batch_labels)
        batch_labels.clear()

    print("Reading all original respiratory validation cases...")

    csv.field_size_limit(2_147_483_647)

    patient_index = 0

    with SOURCE.open(
        encoding="utf-8",
        newline="",
    ) as file:

        for patient in csv.DictReader(file):
            disease = patient["PATHOLOGY"]

            if disease not in labels:
                continue

            evidence = set(
                ast.literal_eval(patient["EVIDENCES"])
            )

            available = sorted(
                evidence & supported
            )

            assert available, (
                "Original respiratory case has no "
                "supported V2 evidence."
            )

            # Select up to three codes reproducibly.
            rng = random.Random(
                SEED + patient_index
            )

            selected = rng.sample(
                available,
                min(3, len(available)),
            )

            patient_index += 1

            age = float(patient["AGE"])
            sex = patient["SEX"].strip().upper()

            assert sex in ("M", "F")
            sex_m = float(sex == "M")

            for count in SYMPTOM_COUNTS:
                reported = selected[:count]
                reported_set = set(reported)

                disclosure_counts[count][
                    len(reported)
                ] += 1

                # V1: original encoder, restricted
                # to the selected evidence codes.
                encoded_v1 = encode_evidences(
                    reported,
                    v1_evidences,
                    v1_evidence_index,
                )

                row_v1 = [
                    age,
                    sex_m,
                ] + encoded_v1

                # V2: reported evidence is present.
                # Unreported evidence remains unknown.
                row_v2 = (
                    [age, sex_m]
                    + [
                        float(code in reported_set)
                        for code in v2_codes
                    ]
                    + [0.0] * len(v2_codes)
                )

                assert len(row_v1) == 198
                assert len(row_v2) == 66

                batches[count]["V1"].append(row_v1)
                batches[count]["V2"].append(row_v2)

            batch_labels.append(disease)

            if len(batch_labels) >= BATCH_SIZE:
                predict_batch()

    predict_batch()

    assert len(actual) == 55808
    assert len(set(actual)) == 21

    print("\nDATASET COVERAGE")
    print("------------------------------------------")
    print("Validation patients:", len(actual))
    print("Conditions represented:", len(set(actual)))
    print("V1 prediction classes:", len(v1_model.classes_))
    print("V2 prediction classes:", len(v2_model.classes_))

    results = {}
    rows = []

    print("\nSPARSE INPUT COMPARISON")
    print("------------------------------------------")

    for count in SYMPTOM_COUNTS:
        results[str(count)] = {}

        print(f"\nUP TO {count} REPORTED SYMPTOM(S)")

        for version in ("V1", "V2"):
            predicted = predictions[count][version]

            assert len(predicted) == len(actual)

            metrics = calculate_metrics(
                actual,
                predicted,
                labels,
            )

            extra = Counter(
                prediction
                for prediction in predicted
                if prediction not in labels
            )

            results[str(count)][version] = {
                **metrics,
                "extra_class_predictions": dict(extra),
            }

            rows.append({
                "maximum_reported_symptoms": count,
                "model": version,
                **metrics,
            })

            print(
                f"{version} | "
                f"Accuracy: {metrics['accuracy']:.4f} | "
                f"Macro F1: {metrics['macro_f1']:.4f}"
            )

        print(
            "Actual disclosed symptom counts:",
            dict(sorted(disclosure_counts[count].items()))
        )

    # Per-condition results across all 21 conditions.
    report_dict = classification_report(
        actual,
        predictions[3]["V2"],
        labels=labels,
        output_dict=True,
        zero_division=0,
    )

    report_text = classification_report(
        actual,
        predictions[3]["V2"],
        labels=labels,
        digits=3,
        zero_division=0,
    )

    print("\nV2 PER-CONDITION RESULTS")
    print("UP TO 3 REPORTED SYMPTOMS")
    print("------------------------------------------")
    print(report_text)

    print("\nV2 LOWEST-RECALL CONDITIONS")
    print("------------------------------------------")

    lowest = sorted(
        labels,
        key=lambda label: report_dict[label]["recall"],
    )

    for label in lowest[:8]:
        info = report_dict[label]
        print(
            f"{label}: "
            f"Recall={info['recall']:.3f}, "
            f"Support={int(info['support'])}"
        )

    OUTPUT.mkdir(
        parents=True,
        exist_ok=True,
    )

    csv_path = (
        OUTPUT / "sparse_all_conditions_metrics.csv"
    )

    json_path = (
        OUTPUT / "sparse_all_conditions_metrics.json"
    )

    class_path = (
        OUTPUT / "v2_all_conditions_3_symptoms_report.csv"
    )

    pd.DataFrame(rows).to_csv(
        csv_path,
        index=False,
    )

    pd.DataFrame(report_dict).transpose().to_csv(
        class_path
    )

    report = {
        "evaluation_source": "DDXPlus validation split",
        "patient_count": len(actual),
        "true_condition_count": len(labels),
        "same_patients_for_all_tests": True,
        "maximum_reported_symptoms": list(SYMPTOM_COUNTS),
        "random_seed": SEED,
        "disclosure_counts": {
            str(count): dict(disclosure_counts[count])
            for count in SYMPTOM_COUNTS
        },
        "results": results,
        "limitations": [
            "All cases are simulated DDXPlus records.",
            "Tests disclose up to 1, 2, or 3 positive evidence codes.",
            "Not every patient has three supported evidence codes.",
            "Evidence codes are not equivalent to verified NLP extraction.",
            "Age and sex are included for both models.",
            "Unreported evidence is encoded as zero for both models.",
            "The models were trained on different feature representations.",
            "Different selected symptom subsets may change the results.",
            "COVID-19 and allergic rhinitis have no ground-truth cases.",
            "This does not establish real-world or clinical performance.",
        ],
    }

    json_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )

    print("\nRESULTS SAVED")
    print("------------------------------------------")
    print(csv_path)
    print(json_path)
    print(class_path)

    print("\nStep 23 PASSED!")


if __name__ == "__main__":
    main()
