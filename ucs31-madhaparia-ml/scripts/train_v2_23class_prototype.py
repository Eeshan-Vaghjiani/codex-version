
"""Train a 23-condition Random Forest research prototype.

Uses DDXPlus-derived training examples and synthetic
COVID-19 / allergic-rhinitis examples.

Does not alter previous V1 or V2 models.
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

BASE = (
    Path(tempfile.gettempdir())
    / "v2_23class_experiment"
)

DATA_DIR = BASE / "assembled_66"
OUTPUT_DIR = BASE / "trained_prototype"

SCHEMA_PATH = ROOT / "models/v2_feature_schema.json"

SEED = 42
MAX_ORIGINAL_PER_CONDITION = 2000

NEW_CONDITIONS = {
    "COVID-19",
    "Allergic rhinitis"
}


def main():
    print("STEP 137 - TRAIN 23-CONDITION RANDOM FOREST")
    print("--------------------------------------------")

    schema = json.loads(
        SCHEMA_PATH.read_text(encoding="utf-8")
    )

    feature_names = schema["feature_names"]

    assert len(feature_names) == 66

    print("Loading assembled training data...", flush=True)

    X = pd.read_csv(
        DATA_DIR / "X_experimental.csv",
        dtype=np.float32
    )

    y = pd.read_csv(
        DATA_DIR / "y_experimental.csv"
    )["PATHOLOGY"]

    provenance = pd.read_csv(
        DATA_DIR / "provenance_experimental.csv",
        usecols=["source_group"]
    )["source_group"]

    assert len(X) == len(y) == len(provenance)
    assert len(X) == 443867

    assert X.columns.tolist() == feature_names
    assert not X.isna().any().any()

    labels = set(y.unique())

    assert len(labels) == 23
    assert NEW_CONDITIONS.issubset(labels)

    original_labels = sorted(labels - NEW_CONDITIONS)

    assert len(original_labels) == 21

    original_mask = (
        provenance == "ddxplus_derived"
    ).to_numpy()

    synthetic_mask = (
        provenance == "reference_guided_synthetic"
    ).to_numpy()

    assert int(original_mask.sum()) == 443067
    assert int(synthetic_mask.sum()) == 800
    assert np.all(original_mask | synthetic_mask)

    y_array = y.to_numpy()
    rng = np.random.default_rng(SEED)

    selected = []

    # Sample original conditions to reduce imbalance
    # and speed up training.
    for disease in original_labels:
        indices = np.flatnonzero(
            original_mask & (y_array == disease)
        )

        assert len(indices) > 0

        sample_size = min(
            len(indices),
            MAX_ORIGINAL_PER_CONDITION
        )

        chosen = rng.choice(
            indices,
            size=sample_size,
            replace=False
        )

        selected.extend(chosen.tolist())

    # Keep all synthetic training scenarios.
    synthetic_indices = np.flatnonzero(
        synthetic_mask
    )

    selected.extend(synthetic_indices.tolist())

    selected = np.array(selected, dtype=int)

    # Shuffle training rows.
    rng.shuffle(selected)

    X_train = X.iloc[selected]
    y_train = y.iloc[selected]

    counts = Counter(y_train)

    assert len(counts) == 23
    assert counts["COVID-19"] == 400
    assert counts["Allergic rhinitis"] == 400

    print("\nTRAINING SUMMARY")
    print("--------------------------------------------")
    print("Total selected scenarios:", len(selected))
    print("Conditions:", len(counts))
    print("Features:", X_train.shape[1])
    print("COVID-19:", counts["COVID-19"])
    print("Allergic rhinitis:", counts["Allergic rhinitis"])

    print("\nTraining Random Forest...", flush=True)

    model = RandomForestClassifier(
        n_estimators=180,
        max_depth=18,
        min_samples_leaf=2,
        max_features="sqrt",
        random_state=SEED,
        n_jobs=-1
    )

    model.fit(X_train, y_train)

    assert len(model.classes_) == 23

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    model_path = (
        OUTPUT_DIR
        / "rf_v2_23class_prototype.joblib"
    )

    joblib.dump(
        model,
        model_path,
        compress=3
    )

    importance = sorted(
        zip(
            feature_names,
            model.feature_importances_
        ),
        key=lambda item: item[1],
        reverse=True
    )

    manifest = {
        "model_type": "RandomForestClassifier",
        "model_status": "research_prototype",
        "seed": SEED,
        "feature_count": len(feature_names),
        "feature_names": feature_names,
        "classes": model.classes_.tolist(),
        "training_count": len(selected),
        "training_counts_by_class": dict(counts),
        "ddxplus_sampling_cap_per_class": (
            MAX_ORIGINAL_PER_CONDITION
        ),
        "synthetic_conditions": sorted(NEW_CONDITIONS),
        "clinical_validation": False,
        "independent_validation_of_synthetic_conditions": False
    }

    manifest_path = (
        OUTPUT_DIR
        / "training_manifest.json"
    )

    manifest_path.write_text(
        json.dumps(
            manifest,
            indent=2
        ),
        encoding="utf-8"
    )

    print("\nTOP 10 FEATURES")
    print("--------------------------------------------")

    for name, value in importance[:10]:
        print(f"{name}: {value:.4f}")

    print("\nMODEL STATUS")
    print("--------------------------------------------")
    print("Training completed: YES")
    print("Trained conditions:", len(model.classes_))
    print("Independent evaluation completed: NO")
    print("Clinical validation: NO")
    print("Existing V1/V2 models modified: NO")
    print("Model saved:", model_path)
    print("Manifest saved:", manifest_path)

    print("\nStep 137 PASSED!")


if __name__ == "__main__":
    main()
