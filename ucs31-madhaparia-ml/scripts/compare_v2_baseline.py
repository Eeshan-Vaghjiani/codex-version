
"""Compare 21-condition baseline against 23-condition prototype.

Engineering evaluation on DDXPlus only; not clinical validation.
"""

import json
import tempfile
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
)

ROOT = Path(__file__).resolve().parents[1]
BASE = Path(tempfile.gettempdir()) / "v2_23class_experiment"
DATA = BASE / "assembled"
VALIDATION = BASE / "validation"
OUTPUT = BASE / "baseline_comparison"

OUTPUT.mkdir(parents=True, exist_ok=True)

schema = json.loads(
    (ROOT / "docs/v2_experimental_feature_schema.json")
    .read_text(encoding="utf-8")
)

X = pd.read_csv(DATA / "X_experimental.csv", dtype="uint8")
y = pd.read_csv(DATA / "y_experimental.csv")["PATHOLOGY"]

X_val = pd.read_csv(
    VALIDATION / "X_validate.csv", dtype="uint8"
)
y_val = pd.read_csv(
    VALIDATION / "y_validate.csv"
)["PATHOLOGY"]

assert X.columns.tolist() == schema["feature_names"]
assert X_val.columns.tolist() == schema["feature_names"]

new_conditions = {"COVID-19", "Allergic rhinitis"}

# Recreate the exact sampling used in Step 91.
rng = np.random.default_rng(42)
selected = []

labels = y.to_numpy()

for disease in sorted(y.unique()):
    indices = np.flatnonzero(labels == disease)
    count = min(len(indices), 1500)

    chosen = rng.choice(
        indices,
        size=count,
        replace=False
    )

    selected.extend(chosen.tolist())

sampled_X = X.iloc[selected]
sampled_y = y.iloc[selected]

assert len(sampled_X) == 30285

# Remove only the 24 candidate examples.
keep = ~sampled_y.isin(new_conditions)

X_train = sampled_X.loc[keep]
y_train = sampled_y.loc[keep]

assert len(X_train) == 30261
assert y_train.nunique() == 21

print("V2 BASELINE COMPARISON")
print("-----------------------------")
print("Baseline training scenarios:", len(X_train))
print("Baseline conditions:", y_train.nunique())
print("Validation scenarios:", len(X_val))

baseline = RandomForestClassifier(
    n_estimators=80,
    max_depth=14,
    min_samples_leaf=2,
    class_weight="balanced_subsample",
    random_state=42,
    n_jobs=-1
)

print("\nTraining 21-condition baseline...")
baseline.fit(X_train, y_train)

prototype = joblib.load(
    BASE
    / "training_smoke_test"
    / "prototype_rf_23class.joblib"
)

labels_21 = sorted(y_val.unique())

assert len(labels_21) == 21
assert set(baseline.classes_) == set(labels_21)
assert len(prototype.classes_) == 23

print("\nEvaluating both models...")

pred_21 = baseline.predict(X_val)
pred_23 = prototype.predict(X_val)


def calculate_metrics(predictions):
    precision, recall, f1, _ = (
        precision_recall_fscore_support(
            y_val,
            predictions,
            labels=labels_21,
            average="macro",
            zero_division=0
        )
    )

    return {
        "accuracy": float(
            accuracy_score(y_val, predictions)
        ),
        "macro_precision": float(precision),
        "macro_recall": float(recall),
        "macro_f1": float(f1),
    }


results_21 = calculate_metrics(pred_21)
results_23 = calculate_metrics(pred_23)

print("\nRESULTS")
print("---------------------------------------")
print(f"{'Metric':<19} {'21-class':>10} {'23-class':>10}")

for metric in [
    "accuracy",
    "macro_precision",
    "macro_recall",
    "macro_f1"
]:
    print(
        f"{metric:<19} "
        f"{results_21[metric]:>10.4f} "
        f"{results_23[metric]:>10.4f}"
    )

allergic_cases = y_val == "Allergic sinusitis"

recall_21 = (
    (pred_21[allergic_cases] == "Allergic sinusitis").mean()
)

recall_23 = (
    (pred_23[allergic_cases] == "Allergic sinusitis").mean()
)

print("\nALLERGIC SINUSITIS RECALL")
print("---------------------------------------")
print(f"21-class baseline: {recall_21:.4f}")
print(f"23-class model:    {recall_23:.4f}")

false_rhinitis = int(
    (
        (y_val == "Allergic sinusitis")
        & (pred_23 == "Allergic rhinitis")
    ).sum()
)

print("\nAllergic sinusitis incorrectly predicted")
print("as allergic rhinitis:", false_rhinitis)

results = {
    "evaluation": "DDXPlus held-out validation",
    "baseline_21": results_21,
    "prototype_23": results_23,
    "allergic_sinusitis_recall_21": float(recall_21),
    "allergic_sinusitis_recall_23": float(recall_23),
    "false_allergic_rhinitis_predictions": false_rhinitis,
    "clinical_validation": False,
}

(OUTPUT / "comparison.json").write_text(
    json.dumps(results, indent=2) + "\n",
    encoding="utf-8"
)

joblib.dump(
    baseline,
    OUTPUT / "rf_21class_baseline.joblib"
)

print("\nComparison complete!")
print("Results saved:", OUTPUT)
