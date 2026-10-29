
"""Final held-out DDXPlus test evaluation for Random Forest V2.

Research evaluation only. Not real-world clinical validation.
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
BASE = Path(tempfile.gettempdir()) / "v2_23class_experiment"

MODEL_DIR = BASE / "final_candidate"
OUTPUT = BASE / "final_test"

SOURCE = ROOT / "data/raw/release_test_patients"

OUTPUT.mkdir(parents=True, exist_ok=True)
csv.field_size_limit(2_147_483_647)

schema = json.loads(
    (ROOT / "models/v2_feature_schema.json")
    .read_text(encoding="utf-8")
)

manifest = json.loads(
    (MODEL_DIR / "model_manifest.json")
    .read_text(encoding="utf-8")
)

model = joblib.load(
    MODEL_DIR / "rf_v2_21class_66features.joblib"
)

assert manifest["training_source"] == "DDXPlus train"
assert manifest["synthetic_extension_included"] is False

codes = schema["symptom_features"]
feature_names = schema["feature_names"]

assert len(codes) == 32
assert len(feature_names) == 66
assert list(model.feature_names_in_) == feature_names
assert len(model.classes_) == 21

if not SOURCE.is_file():
    raise FileNotFoundError(
        f"Test dataset not found: {SOURCE}"
    )

supported = set(codes)
known_diseases = set(model.classes_)

X_rows = []
y_rows = []
source_rows = []

skipped_disease = 0
skipped_symptoms = 0

print("PREPARING HELD-OUT TEST DATA")
print("--------------------------------")

with SOURCE.open(
    encoding="utf-8", newline=""
) as file:

    reader = csv.DictReader(file)

    for row_number, row in enumerate(reader, start=1):
        disease = row["PATHOLOGY"]

        if disease not in known_diseases:
            skipped_disease += 1
            continue

        evidence = set(ast.literal_eval(row["EVIDENCES"]))
        present = evidence & supported

        if not present:
            skipped_symptoms += 1
            continue

        age = float(row["AGE"])
        sex = row["SEX"].strip().upper()

        assert 0 <= age <= 120
        assert sex in ("M", "F")

        vector = (
            [age, 1.0 if sex == "M" else 0.0]
            + [float(code in present) for code in codes]
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

y = pd.Series(y_rows, name="PATHOLOGY")

assert len(X) == len(y) == len(source_rows)
assert len(X) > 0
assert X.shape[1] == 66
assert set(y.unique()) == known_diseases

print("Test scenarios:", len(X))
print("Conditions:", y.nunique())
print("Features:", X.shape[1])
print("Source: DDXPlus test")
print("Skipped other diseases:", skipped_disease)
print("Skipped without supported symptoms:", skipped_symptoms)

print("\nEvaluating frozen Random Forest V2...")

predictions = model.predict(X)
labels = list(model.classes_)

precision, recall, f1, _ = (
    precision_recall_fscore_support(
        y,
        predictions,
        labels=labels,
        average="macro",
        zero_division=0
    )
)

accuracy = accuracy_score(y, predictions)

print("\nFINAL HELD-OUT TEST RESULTS")
print("--------------------------------")
print(f"Accuracy:        {accuracy:.4f}")
print(f"Macro Precision: {precision:.4f}")
print(f"Macro Recall:    {recall:.4f}")
print(f"Macro F1-score:  {f1:.4f}")

report = classification_report(
    y,
    predictions,
    labels=labels,
    output_dict=True,
    zero_division=0
)

report_df = pd.DataFrame(report).transpose()

report_df.to_csv(
    OUTPUT / "classification_report.csv"
)

matrix = confusion_matrix(
    y, predictions, labels=labels
)

normalized = confusion_matrix(
    y, predictions,
    labels=labels,
    normalize="true"
)

pd.DataFrame(
    matrix,
    index=labels,
    columns=labels
).to_csv(OUTPUT / "confusion_matrix_raw.csv")

pd.DataFrame(
    normalized,
    index=labels,
    columns=labels
).to_csv(OUTPUT / "confusion_matrix_normalized.csv")

importance = pd.DataFrame({
    "Feature": feature_names,
    "Importance": model.feature_importances_
}).sort_values(
    "Importance",
    ascending=False
)

importance.to_csv(
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

per_class = report_df.loc[labels]

print("\nLOWEST RECALL CONDITIONS")
print("--------------------------------")

print(
    per_class.sort_values("recall")
    .head(7)[["precision", "recall", "f1-score", "support"]]
    .round(4)
    .to_string()
)

errors = Counter(
    (actual, predicted)
    for actual, predicted in zip(y_rows, predictions)
    if actual != predicted
)

print("\nTOP 5 MISCLASSIFICATIONS")
print("--------------------------------")

for (actual, predicted), count in errors.most_common(5):
    print(f"{actual} -> {predicted}: {count}")

metrics = {
    "dataset": "DDXPlus",
    "split": "test",
    "model": "V2 21-condition 66-feature Random Forest",
    "test_scenarios": len(X),
    "conditions": 21,
    "features": 66,
    "accuracy": float(accuracy),
    "macro_precision": float(precision),
    "macro_recall": float(recall),
    "macro_f1": float(f1),
    "clinical_validation": False,
    "covid19_validated": False,
    "allergic_rhinitis_validated": False,
}

(OUTPUT / "test_metrics.json").write_text(
    json.dumps(metrics, indent=2) + "\n",
    encoding="utf-8"
)

print("\nReports saved:", OUTPUT)
print("Clinical accuracy: NOT ESTABLISHED")
print("Step 103 PASSED!")
