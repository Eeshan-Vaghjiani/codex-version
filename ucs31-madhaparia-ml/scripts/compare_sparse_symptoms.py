
"""Compare V1 and V2 using limited patient symptom inputs.

Both saved models receive the same selected symptoms from
the same held-out DDXPlus validation patients.

This is a simulated evaluation, not clinical validation.
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

SYMPTOM_COUNTS = (1, 3, 5)
BATCH_SIZE = 2000
RANDOM_SEED = 20261021


# --------------------------------------------------
# 1. Calculate evaluation metrics
# --------------------------------------------------

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


# --------------------------------------------------
# 2. Main evaluation
# --------------------------------------------------

def main():

    print("ISSUE 29 - SPARSE SYMPTOM COMPARISON")
    print("------------------------------------")

    # --------------------------------------------------
    # 3. Load saved feature schemas
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

    supported = set(v2_codes)

    # --------------------------------------------------
    # 4. Load original V1 evidence metadata
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

    # --------------------------------------------------
    # 5. Load saved models
    # --------------------------------------------------

    v1_model = joblib.load(
        ROOT / "models/respiratory_random_forest_v1.joblib"
    )

    v2_model = joblib.load(
        ROOT / "models/rf_v2_23class_prototype.joblib"
    )

    # --------------------------------------------------
    # 6. Verify model compatibility
    # --------------------------------------------------

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
        str(label) for label in v1_model.classes_
    )

    assert len(labels) == 21
    assert len(v2_model.classes_) == 23

    # --------------------------------------------------
    # 7. Prepare prediction storage
    # --------------------------------------------------

    actual = []

    predictions = {
        count: {
            "V1": [],
            "V2": [],
        }
        for count in SYMPTOM_COUNTS
    }

    batches = {
        count: {
            "V1": [],
            "V2": [],
        }
        for count in SYMPTOM_COUNTS
    }

    batch_labels = []

    # --------------------------------------------------
    # 8. Predict batches
    # --------------------------------------------------

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

            result_v1 = v1_model.predict(X_v1)
            result_v2 = v2_model.predict(X_v2)

            predictions[count]["V1"].extend(
                result_v1.tolist()
            )

            predictions[count]["V2"].extend(
                result_v2.tolist()
            )

            batches[count]["V1"].clear()
            batches[count]["V2"].clear()

        actual.extend(batch_labels)
        batch_labels.clear()

    # --------------------------------------------------
    # 9. Read validation patients
    # --------------------------------------------------

    print("\nReading held-out validation patients...")
    print("Minimum available symptoms: 5")
    print("Random seed:", RANDOM_SEED)

    csv.field_size_limit(2_147_483_647)

    eligible_index = 0

    with SOURCE.open(
        encoding="utf-8",
        newline="",
    ) as file:

        for patient in csv.DictReader(file):

            disease = patient["PATHOLOGY"]

            if disease not in labels:
                continue

            raw_evidence = set(
                ast.literal_eval(patient["EVIDENCES"])
            )

            available = sorted(
                raw_evidence & supported
            )

            if len(available) < 5:
                continue

            # Select the same five symptoms
            # reproducibly for each patient.

            rng = random.Random(
                RANDOM_SEED + eligible_index
            )

            selected = rng.sample(available, 5)

            eligible_index += 1

            age = float(patient["AGE"])
            sex = patient["SEX"].strip().upper()

            assert sex in ("M", "F")

            sex_m = float(sex == "M")

            # --------------------------------------------------
            # 10. Evaluate 1, 3 and 5 reported symptoms
            # --------------------------------------------------

            for count in SYMPTOM_COUNTS:

                reported = selected[:count]
                reported_set = set(reported)

                # V1: use the original evidence encoder
                # with only the selected symptoms.

                encoded_v1 = encode_evidences(
                    reported,
                    v1_evidences,
                    v1_evidence_index,
                )

                row_v1 = (
                    [age, sex_m]
                    + encoded_v1
                )

                # V2: selected symptoms are present.
                # Unreported symptoms remain unknown.

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

    # --------------------------------------------------
    # 11. Validate evaluation counts
    # --------------------------------------------------

    assert len(actual) == eligible_index
    assert len(actual) == 24389

    print("\nEVALUATION DATA")
    print("------------------------------------")

    print(
        "Same patients for all tests:",
        len(actual),
    )

    print(
        "True conditions:",
        len(labels),
    )

    print(
        "V1 prediction classes:",
        len(v1_model.classes_),
    )

    print(
        "V2 prediction classes:",
        len(v2_model.classes_),
    )

    # --------------------------------------------------
    # 12. Calculate V1 and V2 metrics
    # --------------------------------------------------

    results = {}
    rows = []

    print("\nSPARSE SYMPTOM RESULTS")
    print("------------------------------------")

    for count in SYMPTOM_COUNTS:

        results[str(count)] = {}

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
                "reported_symptoms": count,
                "model": version,
                **metrics,
            })

            print(
                f"{count} symptoms | {version} | "
                f"Accuracy: {metrics['accuracy']:.4f} | "
                f"Macro F1: {metrics['macro_f1']:.4f}"
            )

    # --------------------------------------------------
    # 13. NEW: V2 per-condition classification reports
    # --------------------------------------------------

    for count in (3, 5):

        print(
            f"\nV2 PER-CONDITION RESULTS - "
            f"{count} REPORTED SYMPTOMS"
        )

        print("----------------------------------------")

        report_text = classification_report(
            actual,
            predictions[count]["V2"],
            labels=labels,
            digits=3,
            zero_division=0,
        )

        print(report_text)

        print("\nMOST FREQUENT TRUE CONDITIONS")

        for disease, frequency in Counter(actual).most_common(5):
            print(f"{disease}: {frequency:,}")

        # Check how often V2 predicts the two
        # additional conditions without true examples.

        extra = Counter(
            prediction
            for prediction in predictions[count]["V2"]
            if prediction not in labels
        )

        print("\nADDITIONAL V2 CLASS PREDICTIONS")
        print(
            "COVID-19:",
            extra["COVID-19"],
        )

        print(
            "Allergic rhinitis:",
            extra["Allergic rhinitis"],
        )

    # --------------------------------------------------
    # 14. Save summary results
    # --------------------------------------------------

    OUTPUT.mkdir(
        parents=True,
        exist_ok=True,
    )

    csv_path = OUTPUT / "sparse_symptom_metrics.csv"
    json_path = OUTPUT / "sparse_symptom_metrics.json"

    pd.DataFrame(rows).to_csv(
        csv_path,
        index=False,
    )

    # --------------------------------------------------
    # 15. NEW: Save per-condition V2 reports
    # --------------------------------------------------

    for count in (3, 5):

        report_path = (
            OUTPUT
            / f"v2_{count}_symptoms_classification_report.csv"
        )

        report_dict = classification_report(
            actual,
            predictions[count]["V2"],
            labels=labels,
            output_dict=True,
            zero_division=0,
        )

        pd.DataFrame(report_dict).transpose().to_csv(
            report_path
        )

    # --------------------------------------------------
    # 16. Save JSON comparison report
    # --------------------------------------------------

    report = {
        "evaluation_source": "DDXPlus validation split",
        "patient_count": len(actual),
        "same_patients_for_every_test": True,
        "symptom_counts": list(SYMPTOM_COUNTS),
        "random_seed": RANDOM_SEED,
        "selection_method": (
            "Randomly select five supported positive "
            "symptoms per eligible case; evaluate "
            "nested subsets of 1, 3 and 5 symptoms."
        ),
        "true_condition_count": len(labels),
        "age_and_sex_included": True,
        "results": results,
        "limitations": [
            "All records are simulated DDXPlus cases.",
            "Only cases with at least five supported symptoms are included.",
            "The evaluation uses structured symptom codes, not free-text NLP.",
            "No unreported symptoms are explicitly marked absent.",
            "V1 and V2 were trained using different feature representations.",
            "Performance may depend on the selected symptom combinations.",
            "Neither model has been validated on real-world sparse reports.",
            "COVID-19 and allergic rhinitis have no true cases in this evaluation.",
            "The evaluation does not establish clinical safety or accuracy.",
        ],
    }

    json_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )

    # --------------------------------------------------
    # 17. Confirm saved files
    # --------------------------------------------------

    print("\nRESULTS SAVED")
    print("------------------------------------")

    print(csv_path)
    print(json_path)

    for count in (3, 5):
        print(
            OUTPUT
            / f"v2_{count}_symptoms_classification_report.csv"
        )

    print("\nStep 21 PASSED!")


if __name__ == "__main__":
    main()
