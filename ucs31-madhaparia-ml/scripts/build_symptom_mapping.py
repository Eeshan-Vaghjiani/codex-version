"""
Build the canonical DDXPlus symptom/evidence mapping used by the NLP layer.

The script reads:
    - data/raw/release_evidences.json
    - models/model_features.json

It writes:
    - nlp/feature_catalog.json

Only evidence features used by the final Random Forest model are included.
AGE and SEX_M are handled separately by the application and are therefore
not treated as symptom mappings.
"""

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

EVIDENCE_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "release_evidences.json"
)

MODEL_FEATURES_PATH = (
    PROJECT_ROOT
    / "models"
    / "model_features.json"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "nlp"
    / "feature_catalog.json"
)


def load_json(path):
    with open(
        path,
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


def extract_model_features(data):
    """
    Support either a direct JSON list or a dictionary containing
    the feature list.
    """

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in (
            "model_features",
            "features",
            "selected_features"
        ):
            if key in data:
                return data[key]

    raise ValueError(
        "Could not find model feature list "
        "inside model_features.json"
    )


def split_encoded_feature(feature):
    """
    E_97 -> (E_97, None)

    E_55_@_V_89 ->
        (E_55, V_89)
    """

    if "_@_" in feature:
        return feature.split(
            "_@_",
            1
        )

    return feature, None


def get_value_meaning(
    evidence_info,
    value_code
):
    """
    Convert a DDXPlus V_xx code into its readable value.
    """

    meanings = (
        evidence_info.get(
            "value_meaning"
        )
        or {}
    )

    meaning = meanings.get(
        value_code
    )

    if isinstance(
        meaning,
        dict
    ):
        return (
            meaning.get("en")
            or meaning.get("fr")
            or value_code
        )

    if isinstance(
        meaning,
        str
    ):
        return meaning

    return value_code


def build_canonical_entry(
    feature,
    evidences
):
    """
    Convert one active model feature into a reusable canonical
    NLP mapping entry.
    """

    evidence_code, value_code = (
        split_encoded_feature(
            feature
        )
    )

    evidence_info = (
        evidences.get(
            evidence_code
        )
    )

    if evidence_info is None:
        raise KeyError(
            f"Evidence metadata missing for "
            f"{evidence_code}"
        )

    question = (
        evidence_info.get(
            "question_en"
        )
        or evidence_info.get(
            "name"
        )
        or evidence_code
    )

    value_meaning = None

    if value_code is not None:
        value_meaning = (
            get_value_meaning(
                evidence_info,
                value_code
            )
        )

        canonical_name = (
            f"{question}: "
            f"{value_meaning}"
        )

    else:
        canonical_name = question

    return {
        "canonical_id": feature,
        "canonical_name": canonical_name,
        "ddxplus_evidence": evidence_code,
        "ddxplus_value": value_code,
        "value_meaning": value_meaning,
        "model_features": [
            feature
        ],
        "data_type": (
            evidence_info.get(
                "data_type"
            )
        ),
        "is_antecedent": bool(
            evidence_info.get(
                "is_antecedent",
                False
            )
        ),
        "aliases": {
            "en": [],
            "sw": []
        }
    }


def main():

    if not EVIDENCE_PATH.exists():
        raise FileNotFoundError(
            f"Missing DDXPlus evidence file: "
            f"{EVIDENCE_PATH}"
        )

    if not MODEL_FEATURES_PATH.exists():
        raise FileNotFoundError(
            f"Missing model feature file: "
            f"{MODEL_FEATURES_PATH}"
        )

    evidences = load_json(
        EVIDENCE_PATH
    )

    model_feature_data = load_json(
        MODEL_FEATURES_PATH
    )

    model_features = (
        extract_model_features(
            model_feature_data
        )
    )

    demographic_features = {
        "AGE",
        "SEX_M"
    }

    evidence_features = [
        feature
        for feature in model_features
        if feature
        not in demographic_features
    ]

    canonical_entries = []

    for feature in evidence_features:
        canonical_entries.append(
            build_canonical_entry(
                feature,
                evidences
            )
        )

    mapped_features = {
        feature
        for entry in canonical_entries
        for feature in entry[
            "model_features"
        ]
    }

    if mapped_features != set(
        evidence_features
    ):
        raise ValueError(
            "Canonical mapping does not "
            "cover every active evidence "
            "feature."
        )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        OUTPUT_PATH,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            canonical_entries,
            file,
            indent=2,
            ensure_ascii=False
        )

    unique_evidence_codes = {
        entry[
            "ddxplus_evidence"
        ]
        for entry
        in canonical_entries
    }

    symptom_count = sum(
        not entry[
            "is_antecedent"
        ]
        for entry
        in canonical_entries
    )

    history_count = sum(
        entry[
            "is_antecedent"
        ]
        for entry
        in canonical_entries
    )

    print()
    print(
        "Canonical symptom mapping build"
    )
    print(
        "-------------------------------"
    )

    print(
        "Model features loaded:",
        len(model_features)
    )

    print(
        "Demographic features excluded:",
        len(
            demographic_features
            & set(
                model_features
            )
        )
    )

    print(
        "Canonical mappings created:",
        len(
            canonical_entries
        )
    )

    print(
        "Unique DDXPlus evidence codes:",
        len(
            unique_evidence_codes
        )
    )

    print(
        "Symptom/evidence mappings:",
        symptom_count
    )

    print(
        "History/antecedent mappings:",
        history_count
    )

    print(
        "Every active feature mapped:",
        mapped_features
        == set(
            evidence_features
        )
    )

    print()
    print(
        "Saved to:",
        OUTPUT_PATH
    )

    print()
    print(
        "First 5 canonical mappings:"
    )

    for entry in (
        canonical_entries[:5]
    ):
        print(
            "-",
            entry[
                "canonical_id"
            ],
            "->",
            entry[
                "canonical_name"
            ]
        )


if __name__ == "__main__":
    main()