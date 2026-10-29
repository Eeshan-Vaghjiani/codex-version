
"""Evaluate the 23-class experimental model on held-out DDXPlus data.

This measures performance on the original 21 conditions only.
It does not establish clinical accuracy for COVID-19 or allergic rhinitis.
"""

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
VALIDATION = BASE / "validation"
MODEL_DIR = BASE / "training_smoke_test"
OUTPUT = BASE / "evaluation"

OUTPUT.mkdir(parents=True, exist_ok=True)

schema = json.loads(
    (ROOT / "docs/v2_experimental_feature_schema.json")
    .read_text(encoding="utf-8")
)

model = joblib.load(
    MODEL_DIR / "prototype_rf_23class.joblib"
)

X = pd.read_csv(
    VALIDATION / "X_validate.csv",
    dtype="uint8"
)

y = pd.read_csv(
    VALIDATION / "y_validate.csv"
)["PATHOLOGY"]

provenance = pd.read_csv(
    VALIDATION / "provenance_validate.csv"
)

assert len(X) == len(y) == len(provenance)
assert X.columns.tolist() == schema["feature_names"]
assert X.shape[1] == model.n_features_in_ == 64

assert (provenance["source_split"] == "validate").all()
assert (provenance["source_dataset"] == "DDXPlus").all()

new_conditions = {"COVID-19", "Allergic rhinitis"}
assert not set(y.unique()).intersection(new_conditions)

labels = sorted(y.unique())
assert len(labels) == 21
assert len(model.classes_) == 23

print("V2 RANDOM FOREST EVALUATION")
print("--------------------------------")
print("Validation cases:", len(X))
print("Evaluated conditions:", len(labels))
print("Model conditions:", len(model.classes_))

print("\nGenerating predictions...")

predictions = model.predict(X)

accuracy = accuracy_score(y, predictions)

precision, recall, f1, _ = (
    precision_recall_fscore_support(
        y,
        predictions,
        labels=labels,
        average="macro",
        zero_division=0
    )
)

print("\nHELD-OUT DDXPLUS RESULTS")
print("--------------------------------")
print(f"Accuracy:        {accuracy:.4f}")
print(f"Macro Precision: {precision:.4f}")
print(f"Macro Recall:    {recall:.4f}")
print(f"Macro F1-score:  {f1:.4f}")

print("\nPredictions of unvalidated new conditions:")
for disease in sorted(new_conditions):
    count = int((predictions == disease).sum())
    print(f"  {disease}: {count}")

report = classification_report(
    y,
    predictions,
    labels=labels,
    output_dict=True,
    zero_division=0
)

pd.DataFrame(report).transpose().to_csv(
    OUTPUT / "classification_report.csv"
)

# Include all model labels so incorrect predictions of
# the two new conditions remain visible.
all_labels = list(model.classes_)

matrix = confusion_matrix(
    y,
    predictions,
    labels=all_labels
)

pd.DataFrame(
    matrix,
    index=all_labels,
    columns=all_labels
).to_csv(OUTPUT / "confusion_matrix.csv")

errors = Counter(
    (actual, predicted)
    for actual, predicted in zip(y, predictions)
    if actual != predicted
)

print("\nMOST COMMON MISCLASSIFICATIONS")
print("--------------------------------")

for (actual, predicted), count in errors.most_common(10):
    print(f"{actual} -> {predicted}: {count}")

results = {
    "evaluation_split": "DDXPlus validate",
    "validation_cases": len(X),
    "evaluated_conditions": len(labels),
    "model_conditions": len(all_labels),
    "accuracy": float(accuracy),
    "macro_precision": float(precision),
    "macro_recall": float(recall),
    "macro_f1": float(f1),
    "clinical_validation": False,
    "new_condition_validation_available": False,
    "model_status": "engineering_smoke_test_only"
}

(OUTPUT / "evaluation_metrics.json").write_text(
    json.dumps(results, indent=2) + "\n",
    encoding="utf-8"
)

print("\nReports saved to:", OUTPUT)
print("Clinical accuracy: NOT ESTABLISHED")
print("\nEvaluation complete!")
