
"""Train the provisional 21-condition Random Forest V2.

Uses DDXPlus-derived training scenarios only.
Research prototype; not clinically validated.
"""

import json
import tempfile
from collections import Counter
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

ROOT = Path(__file__).resolve().parents[1]

SOURCE = (
    Path(tempfile.gettempdir())
    / "ddxplus_v2_encoded"
)

OUTPUT = (
    Path(tempfile.gettempdir())
    / "v2_23class_experiment"
    / "final_candidate"
)

OUTPUT.mkdir(parents=True, exist_ok=True)

schema = json.loads(
    (ROOT / "models/v2_feature_schema.json")
    .read_text(encoding="utf-8")
)

X = pd.read_csv(
    SOURCE / "X_train.csv",
    dtype=np.float32
)

y = pd.read_csv(
    SOURCE / "y_train.csv"
)["PATHOLOGY"]

provenance = pd.read_csv(
    SOURCE / "provenance.csv",
    usecols=["source_dataset", "source_split"]
)

assert len(X) == len(y) == len(provenance) == 443067
assert X.columns.tolist() == schema["feature_names"]
assert X.shape[1] == 66
assert y.nunique() == 21

assert (provenance["source_dataset"] == "DDXPlus").all()
assert (provenance["source_split"] == "train").all()

assert X["AGE"].between(0, 120).all()
assert X["SEX_M"].isin([0, 1]).all()

print("V2 FULL TRAINING")
print("--------------------------------")
print("Training scenarios:", len(X))
print("Conditions:", y.nunique())
print("Numerical features:", X.shape[1])
print("Age and sex: INCLUDED")
print("Synthetic COVID-19 examples: EXCLUDED")
print("Synthetic allergic rhinitis examples: EXCLUDED")

model = RandomForestClassifier(
    n_estimators=80,
    max_depth=14,
    min_samples_leaf=2,
    class_weight="balanced_subsample",
    random_state=42,
    n_jobs=-1
)

print("\nTraining Random Forest V2...")
print("This may take several minutes.")

model.fit(X, y)

assert model.n_features_in_ == 66
assert len(model.classes_) == 21

model_path = OUTPUT / "rf_v2_21class_66features.joblib"
joblib.dump(model, model_path)

counts = Counter(y)

manifest = {
    "version": "V2_candidate",
    "status": "research_prototype_not_clinically_validated",
    "training_source": "DDXPlus train",
    "training_scenarios": len(X),
    "condition_count": len(model.classes_),
    "feature_names": schema["feature_names"],
    "class_labels": model.classes_.tolist(),
    "class_counts": dict(counts),
    "random_seed": 42,
    "uses_age": True,
    "uses_sex": True,
    "synthetic_extension_included": False,
    "not_for_clinical_deployment": True
}

(OUTPUT / "model_manifest.json").write_text(
    json.dumps(manifest, indent=2) + "\n",
    encoding="utf-8"
)

print("\nTRAINING COMPLETED!")
print("--------------------------------")
print("Trained conditions:", len(model.classes_))
print("Numerical features:", model.n_features_in_)
print("Model saved:", model_path)
print("Clinical validation: NOT ESTABLISHED")
print("\nStep 102 PASSED!")
