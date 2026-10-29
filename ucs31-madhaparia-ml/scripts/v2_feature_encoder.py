
"""Numerical feature encoding for Random Forest V2."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_v2_symptom_features():
    def read_json(path):
        with path.open(encoding="utf-8") as f:
            return json.load(f)

    canonical = read_json(ROOT / "nlp/canonical_symptoms.json")
    v1_features = read_json(ROOT / "models/model_features.json")
    metadata = read_json(ROOT / "data/raw/release_evidences.json")

    mapped = {
        code
        for symptom in canonical
        for code in symptom.get("features", [])
    }

    features = sorted(
        code for code in v1_features
        if code in mapped
        and code in metadata
        and metadata[code].get("data_type") == "B"
        and not metadata[code].get("is_antecedent", False)
    )

    if not features:
        raise ValueError("No supported binary features found")

    return features


def get_v2_feature_names(symptom_features):
    return (
        ["AGE", "SEX_M"]
        + [f"{code}__present" for code in symptom_features]
        + [f"{code}__absent" for code in symptom_features]
    )


def encode_v2_record(record, symptom_features):
    """Encode a validated present/absent/unknown symptom record."""

    if len(symptom_features) != len(set(symptom_features)):
        raise ValueError("Duplicate symptom feature names")

    expected = set(symptom_features)
    states = {}

    for status in ("present", "absent", "unknown"):
        values = record[status]

        if not isinstance(values, list):
            raise ValueError(f"{status} must be a list")

        if len(values) != len(set(values)):
            raise ValueError(f"Duplicate codes in {status}")

        states[status] = set(values)

    present = states["present"]
    absent = states["absent"]
    unknown = states["unknown"]

    if (
        present & absent
        or present & unknown
        or absent & unknown
    ):
        raise ValueError("Conflicting symptom states")

    if present | absent | unknown != expected:
        raise ValueError("Missing or unsupported symptom codes")

    if isinstance(record["age"], bool):
        raise ValueError("Age must be a number, not a boolean")
    try:
        age = float(record["age"])
    except (TypeError, ValueError):
        raise ValueError("Age must be a number") from None

    if not 0 <= age <= 120:
        raise ValueError("Age outside supported range")

    if not isinstance(record["sex"], str):
        raise ValueError("Unsupported sex value")
    sex = record["sex"].strip().upper()

    if sex not in ("M", "F"):
        raise ValueError("Unsupported sex value")

    return (
        [age, 1.0 if sex == "M" else 0.0]
        + [float(code in present) for code in symptom_features]
        + [float(code in absent) for code in symptom_features]
    )
