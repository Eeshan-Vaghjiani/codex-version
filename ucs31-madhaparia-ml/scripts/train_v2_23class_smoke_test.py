
"""Engineering smoke test for the experimental 23-class model.

Not clinically validated. Do not deploy for patient predictions.
"""

import json
import tempfile
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier


ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = (
    Path(tempfile.gettempdir())
    / "v2_23class_experiment"
    / "assembled"
)

OUTPUT_DIR = (
    Path(tempfile.gettempdir())
    / "v2_23class_experiment"
    / "training_smoke_test"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

schema = json.loads(
    (
        ROOT / "docs/v2_experimental_feature_schema.json"
    ).read_text(encoding="utf-8")
)

X = pd.read_csv(
    DATA_DIR / "X_experimental.csv",
    dtype="uint8"
)

y = pd.read_csv(
    DATA_DIR / "y_experimental.csv"
)["PATHOLOGY"]

provenance = pd.read_csv(
    DATA_DIR / "provenance_experimental.csv",
    usecols=["source_group"]
)

assert len(X) == len(y) == len(provenance)
assert X.columns.tolist() == schema["feature_names"]
assert X.shape[1] == 64
assert y.nunique() == 23

candidate_names = {"COVID-19", "Allergic rhinitis"}
candidate_mask = y.isin(candidate_names)

assert candidate_mask.sum() == 24

assert (
    provenance.loc[candidate_mask, "source_group"]
    == "reference_guided_candidate"
).all()

assert (
    provenance.loc[~candidate_mask, "source_group"]
    == "ddxplus_derived"
).all()

# Sample up to 1,500 scenarios per condition.
# The new candidate conditions retain their 12 examples each.
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

X_train = X.iloc[selected]
y_train = y.iloc[selected]

assert y_train.nunique() == 23

print("V2 TRAINING SMOKE TEST")
print("-----------------------------")
print("Total available scenarios:", len(X))
print("Selected training scenarios:", len(X_train))
print("Conditions:", y_train.nunique())
print("Features:", X_train.shape[1])
print("COVID-19 examples:", (y_train == "COVID-19").sum())
print(
    "Allergic rhinitis examples:",
    (y_train == "Allergic rhinitis").sum()
)

model = RandomForestClassifier(
    n_estimators=80,
    max_depth=14,
    min_samples_leaf=2,
    class_weight="balanced_subsample",
    random_state=42,
    n_jobs=-1
)

print("\nTraining experimental Random Forest...")

model.fit(X_train, y_train)

assert model.n_features_in_ == 64
assert len(model.classes_) == 23

model_path = OUTPUT_DIR / "prototype_rf_23class.joblib"

joblib.dump(model, model_path)

manifest = {
    "status": "engineering_smoke_test_only",
    "clinical_validation": False,
    "feature_count": 64,
    "condition_count": 23,
    "training_scenarios": len(X_train),
    "unvalidated_candidate_conditions": sorted(candidate_names),
    "random_seed": 42,
    "not_for_deployment": True
}

(OUTPUT_DIR / "training_manifest.json").write_text(
    json.dumps(manifest, indent=2) + "\n",
    encoding="utf-8"
)

print("\nTraining completed!")
print("Trained conditions:", len(model.classes_))
print("Model saved:", model_path)
print("Status: ENGINEERING TEST ONLY")
print("Clinical accuracy: NOT ESTABLISHED")
