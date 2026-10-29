
"""Compare V2 Random Forest with and without age and sex.

Engineering evaluation on DDXPlus.
Not validated for real clinical use.
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
    recall_score,
    confusion_matrix,
)

ROOT = Path(__file__).resolve().parents[1]
BASE = Path(tempfile.gettempdir()) / "v2_23class_experiment"

ORIGINAL = Path(tempfile.gettempdir()) / "ddxplus_v2_encoded"
EXPERIMENT = BASE / "assembled"
VALIDATION = BASE / "validation"
OUTPUT = BASE / "age_sex_comparison"

OUTPUT.mkdir(parents=True, exist_ok=True)

schema_66 = json.loads(
    (ROOT / "models/v2_feature_schema.json")
    .read_text(encoding="utf-8")
)

schema_64 = json.loads(
    (ROOT / "docs/v2_experimental_feature_schema.json")
    .read_text(encoding="utf-8")
)

# Load the original 66-feature training data.
X66 = pd.read_csv(
    ORIGINAL / "X_train.csv",
    dtype=np.float32
)

y66 = pd.read_csv(
    ORIGINAL / "y_train.csv"
)["PATHOLOGY"]

# The combined dataset preserves the original rows first.
y_combined = pd.read_csv(
    EXPERIMENT / "y_experimental.csv"
)["PATHOLOGY"]

assert len(X66) == len(y66) == 443067
assert len(y_combined) == 443091
assert y66.reset_index(drop=True).equals(
    y_combined.iloc[:443067].reset_index(drop=True)
)

assert X66.columns.tolist() == schema_66["feature_names"]
assert schema_66["feature_names"][2:] == schema_64["feature_names"]

# Recreate the exact sampling from Steps 91 and 95.
rng = np.random.default_rng(42)
selected = []

labels_combined = y_combined.to_numpy()

for disease in sorted(y_combined.unique()):
    indices = np.flatnonzero(labels_combined == disease)
    count = min(len(indices), 1500)

    selected.extend(
        rng.choice(
            indices,
            size=count,
            replace=False
        ).tolist()
    )

assert len(selected) == 30285

# Remove the 24 candidate cases while preserving
# the exact existing training-row selections.
selected_original = [
    index for index in selected
    if index < len(X66)
]

assert len(selected_original) == 30261

X_train = X66.iloc[selected_original]
y_train = y66.iloc[selected_original]

assert y_train.nunique() == 21

# Confirm the symptom inputs match the 64-feature baseline.
X64_original = pd.read_csv(
    BASE / "X_original_train.csv",
    dtype="uint8"
)

assert np.array_equal(
    X_train.iloc[:, 2:].to_numpy().astype("uint8"),
    X64_original.iloc[selected_original].to_numpy()
)

# Load identical held-out cases for both models.
X_val_66 = pd.read_csv(
    VALIDATION / "X_validate_66.csv",
    dtype=np.float32
)

X_val_64 = pd.read_csv(
    VALIDATION / "X_validate.csv",
    dtype="uint8"
)

y_val = pd.read_csv(
    VALIDATION / "y_validate.csv"
)["PATHOLOGY"]

assert len(X_val_66) == len(X_val_64) == len(y_val) == 55808
assert X_val_66.columns.tolist() == schema_66["feature_names"]
assert X_val_64.columns.tolist() == schema_64["feature_names"]

assert np.array_equal(
    X_val_66.iloc[:, 2:].to_numpy().astype("uint8"),
    X_val_64.to_numpy()
)

baseline_64 = joblib.load(
    BASE / "baseline_comparison" / "rf_21class_baseline.joblib"
)

print("V2 AGE AND SEX COMPARISON")
print("-----------------------------------")
print("Training scenarios:", len(X_train))
print("Validation cases:", len(y_val))
print("Conditions:", y_train.nunique())
print("64-feature baseline: loaded")
print("66-feature model: preparing")

model_66 = RandomForestClassifier(
    n_estimators=80,
    max_depth=14,
    min_samples_leaf=2,
    class_weight="balanced_subsample",
    random_state=42,
    n_jobs=-1
)

print("\nTraining 66-feature Random Forest...")
model_66.fit(X_train, y_train)

pred_64 = baseline_64.predict(X_val_64)
pred_66 = model_66.predict(X_val_66)

diseases = sorted(y_val.unique())


def metrics(pred):
    precision, recall, f1, _ = (
        precision_recall_fscore_support(
            y_val,
            pred,
            labels=diseases,
            average="macro",
            zero_division=0
        )
    )

    return {
        "Accuracy": accuracy_score(y_val, pred),
        "Macro Precision": precision,
        "Macro Recall": recall,
        "Macro F1": f1,
    }


m64 = metrics(pred_64)
m66 = metrics(pred_66)

print("\nOVERALL COMPARISON")
print("-------------------------------------------")
print(f"{'Metric':<20} {'64 features':>11} {'66 features':>11}")

for metric in m64:
    print(
        f"{metric:<20} "
        f"{m64[metric]:>11.4f} "
        f"{m66[metric]:>11.4f}"
    )

important = [
    "Bronchospasm / acute asthma exacerbation",
    "Acute COPD exacerbation / infection",
    "Acute rhinosinusitis",
    "Chronic rhinosinusitis",
    "Tuberculosis",
]

print("\nIMPORTANT DISEASE RECALL")
print("-------------------------------------------")
print(f"{'Disease':<42} {'64':>7} {'66':>7}")

for disease in important:
    r64 = recall_score(
        y_val, pred_64,
        labels=[disease],
        average="macro",
        zero_division=0
    )

    r66 = recall_score(
        y_val, pred_66,
        labels=[disease],
        average="macro",
        zero_division=0
    )

    print(f"{disease:<42} {r64:>7.3f} {r66:>7.3f}")

# Save the comparison for our Jupyter notebooks.
comparison = pd.DataFrame({
    "Metric": list(m64),
    "64_features": list(m64.values()),
    "66_features": list(m66.values()),
})

comparison.to_csv(
    OUTPUT / "model_comparison.csv",
    index=False
)

matrix = confusion_matrix(
    y_val, pred_66, labels=diseases
)

pd.DataFrame(
    matrix, index=diseases, columns=diseases
).to_csv(OUTPUT / "confusion_matrix_66_raw.csv")

pd.DataFrame(
    confusion_matrix(
        y_val, pred_66,
        labels=diseases,
        normalize="true"
    ),
    index=diseases,
    columns=diseases
).to_csv(OUTPUT / "confusion_matrix_66_normalized.csv")

joblib.dump(
    model_66,
    OUTPUT / "rf_21class_66features.joblib"
)

print("\nComparison completed!")
print("Reports and model saved:", OUTPUT)
print("Clinical accuracy: NOT ESTABLISHED")

