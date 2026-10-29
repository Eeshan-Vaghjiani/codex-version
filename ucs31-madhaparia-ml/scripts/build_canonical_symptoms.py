"""
Build the user-facing canonical symptom mapping for the NLP layer.

Reads:
    - nlp/feature_catalog.json

Writes:
    - nlp/canonical_symptoms.json

Each canonical symptom can map to one or more active Random Forest
features. Safety-only symptoms are also allowed to have no model
features.
"""

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

FEATURE_CATALOG_PATH = (
    PROJECT_ROOT
    / "nlp"
    / "feature_catalog.json"
)

ENGLISH_ALIASES_PATH = (
    PROJECT_ROOT
    / "nlp"
    / "english_aliases.json"
)

SWAHILI_ALIASES_PATH = (
    PROJECT_ROOT
    / "nlp"
    / "swahili_aliases.json"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "nlp"
    / "canonical_symptoms.json"
)


CANONICAL_SYMPTOMS = [
    {
        "code": "fever",
        "display_name": "Fever",
        "features": ["E_91"],
        "kind": "symptom",
        "is_red_flag": False,
    },
    {
        "code": "chills",
        "display_name": "Chills / shivering",
        "features": ["E_94"],
        "kind": "symptom",
        "is_red_flag": False,
    },
    {
        "code": "cough",
        "display_name": "Cough",
        "features": ["E_201"],
        "kind": "symptom",
        "is_red_flag": False,
    },
    {
        "code": "intense_coughing_fits",
        "display_name": "Intense coughing fits",
        "features": ["E_203"],
        "kind": "symptom",
        "is_red_flag": False,
    },
    {
        "code": "vomiting_after_coughing",
        "display_name": "Vomiting after coughing",
        "features": ["E_166"],
        "kind": "symptom",
        "is_red_flag": False,
    },
    {
        "code": "productive_cough",
        "display_name": "Coughing up coloured or more phlegm",
        "features": ["E_77"],
        "kind": "symptom",
        "is_red_flag": False,
    },
    {
        "code": "coughing_blood",
        "display_name": "Coughing up blood",
        "features": ["E_45"],
        "kind": "symptom",
        "is_red_flag": True,
    },
    {
        "code": "shortness_of_breath",
        "display_name": "Significant shortness of breath",
        "features": ["E_66"],
        "kind": "symptom",
        "is_red_flag": True,
    },
    {
        "code": "night_breathlessness",
        "display_name": "Woken at night by choking or breathlessness",
        "features": ["E_67"],
        "kind": "symptom",
        "is_red_flag": False,
    },
    {
        "code": "wheezing",
        "display_name": "Wheezing when breathing out",
        "features": ["E_214"],
        "kind": "symptom",
        "is_red_flag": False,
    },
    {
        "code": "wheeze_after_coughing",
        "display_name": "Noisy breathing or wheeze after coughing",
        "features": ["E_112"],
        "kind": "symptom",
        "is_red_flag": False,
    },
    {
        "code": "stridor",
        "display_name": "High-pitched sound when breathing in",
        "features": ["E_194"],
        "kind": "symptom",
        "is_red_flag": True,
    },
    {
        "code": "drooling",
        "display_name": "Drooling or more saliva than usual",
        "features": ["E_190"],
        "kind": "symptom",
        "is_red_flag": True,
    },
    {
        "code": "difficulty_swallowing",
        "display_name": "Difficulty swallowing",
        "features": ["E_65"],
        "kind": "symptom",
        "is_red_flag": False,
    },
    {
        "code": "sore_throat",
        "display_name": "Sore throat",
        "features": ["E_97"],
        "kind": "symptom",
        "is_red_flag": False,
    },
    {
        "code": "hoarse_voice",
        "display_name": "Hoarse or changed voice",
        "features": ["E_212"],
        "kind": "symptom",
        "is_red_flag": False,
    },
    {
        "code": "runny_blocked_nose",
        "display_name": "Runny or blocked nose",
        "features": ["E_181"],
        "kind": "symptom",
        "is_red_flag": False,
    },
    {
        "code": "nasal_discharge",
        "display_name": "Green or yellow nasal discharge",
        "features": ["E_182"],
        "kind": "symptom",
        "is_red_flag": False,
    },
    {
        "code": "loss_of_smell",
        "display_name": "Loss of smell",
        "features": ["E_103"],
        "kind": "symptom",
        "is_red_flag": False,
    },
    {
        "code": "itchy_nose_throat",
        "display_name": "Itchy nose or throat",
        "features": ["E_169"],
        "kind": "symptom",
        "is_red_flag": False,
    },
    {
        "code": "itchy_eyes",
        "display_name": "Itchy eyes",
        "features": ["E_170"],
        "kind": "symptom",
        "is_red_flag": False,
    },
    {
        "code": "headache",
        "display_name": "Headache",
        "features": [
            "E_53",
            "E_55_@_V_89",
        ],
        "kind": "symptom",
        "is_red_flag": False,
    },
    {
        "code": "chest_pain",
        "display_name": "Chest pain",
        "features": [
            "E_53",
            "E_55_@_V_101",
        ],
        "kind": "symptom",
        "is_red_flag": False,
    },
    {
        "code": "chest_pain_at_rest",
        "display_name": "Chest pain even at rest",
        "features": ["E_14"],
        "kind": "symptom",
        "is_red_flag": True,
    },
    {
        "code": "pain_deep_breath",
        "display_name": "Pain when breathing in deeply",
        "features": ["E_220"],
        "kind": "symptom",
        "is_red_flag": False,
    },
    {
        "code": "worse_lying_down",
        "display_name": "Worse lying down, better sitting up",
        "features": ["E_217"],
        "kind": "symptom",
        "is_red_flag": False,
    },
    {
        "code": "worse_with_exertion",
        "display_name": "Worse with exertion, better with rest",
        "features": ["E_218"],
        "kind": "symptom",
        "is_red_flag": False,
    },
    {
        "code": "tiredness",
        "display_name": "Constant tiredness",
        "features": ["E_89"],
        "kind": "symptom",
        "is_red_flag": False,
    },
    {
        "code": "activity_fatigue",
        "display_name": "Too tired for usual activities",
        "features": ["E_88"],
        "kind": "symptom",
        "is_red_flag": False,
    },
    {
        "code": "muscle_aches",
        "display_name": "Muscle aches",
        "features": ["E_144"],
        "kind": "symptom",
        "is_red_flag": False,
    },
    {
        "code": "heavy_sweating",
        "display_name": "Heavy sweating",
        "features": ["E_50"],
        "kind": "symptom",
        "is_red_flag": False,
    },
    {
        "code": "loss_of_appetite",
        "display_name": "Loss of appetite",
        "features": ["E_161"],
        "kind": "symptom",
        "is_red_flag": False,
    },
    {
        "code": "weight_loss",
        "display_name": "Unintended weight loss",
        "features": ["E_162"],
        "kind": "symptom",
        "is_red_flag": False,
    },
    {
        "code": "blue_lips",
        "display_name": "Blue lips or face",
        "features": [],
        "kind": "symptom",
        "is_red_flag": True,
    },
    {
        "code": "confusion",
        "display_name": "Confusion",
        "features": [],
        "kind": "symptom",
        "is_red_flag": True,
    },
    {
        "code": "fainting",
        "display_name": "Fainting",
        "features": [],
        "kind": "symptom",
        "is_red_flag": True,
    },
]


def load_json(path):
    with open(
        path,
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def validate_unique_codes(entries):
    codes = [
        entry["code"]
        for entry in entries
    ]

    if len(codes) != len(set(codes)):
        raise ValueError(
            "Duplicate canonical symptom codes found."
        )


def validate_features(
    entries,
    active_features,
):
    invalid = []

    for entry in entries:
        for feature in entry["features"]:
            if feature not in active_features:
                invalid.append(
                    (
                        entry["code"],
                        feature,
                    )
                )

    if invalid:
        raise ValueError(
            "Canonical symptoms contain features "
            f"not used by the final model: {invalid}"
        )


def validate_english_aliases(
    entries,
    english_aliases,
):
    canonical_codes = {
        entry["code"]
        for entry in entries
    }

    alias_codes = set(
        english_aliases.keys()
    )

    missing = (
        canonical_codes
        - alias_codes
    )

    unknown = (
        alias_codes
        - canonical_codes
    )

    if missing:
        raise ValueError(
            "Missing English aliases for: "
            f"{sorted(missing)}"
        )

    if unknown:
        raise ValueError(
            "English aliases contain unknown "
            f"canonical codes: {sorted(unknown)}"
        )

    seen_aliases = {}

    for code, aliases in (
        english_aliases.items()
    ):
        if not aliases:
            raise ValueError(
                f"No English aliases supplied "
                f"for {code}"
            )

        for alias in aliases:
            normalized = (
                alias
                .strip()
                .lower()
            )

            if not normalized:
                raise ValueError(
                    f"Empty alias found for {code}"
                )

            if normalized in seen_aliases:
                previous_code = (
                    seen_aliases[
                        normalized
                    ]
                )

                if previous_code != code:
                    raise ValueError(
                        "English alias used by "
                        "multiple symptoms: "
                        f"{alias!r} -> "
                        f"{previous_code}, {code}"
                    )

            seen_aliases[
                normalized
            ] = code

def validate_swahili_aliases(
    entries,
    swahili_aliases,
):
    canonical_codes = {
        entry["code"]
        for entry in entries
    }

    alias_codes = set(
        swahili_aliases.keys()
    )

    unknown = (
        alias_codes
        - canonical_codes
    )

    if unknown:
        raise ValueError(
            "Swahili aliases contain unknown "
            f"canonical codes: {sorted(unknown)}"
        )

    seen_aliases = {}

    for code, aliases in (
        swahili_aliases.items()
    ):
        if not aliases:
            raise ValueError(
                f"No Swahili aliases supplied "
                f"for {code}"
            )

        for alias in aliases:
            normalized = (
                alias
                .strip()
                .lower()
            )

            if not normalized:
                raise ValueError(
                    f"Empty Swahili alias found "
                    f"for {code}"
                )

            if normalized in seen_aliases:
                previous_code = (
                    seen_aliases[
                        normalized
                    ]
                )

                if previous_code != code:
                    raise ValueError(
                        "Swahili alias used by "
                        "multiple symptoms: "
                        f"{alias!r} -> "
                        f"{previous_code}, {code}"
                    )

            seen_aliases[
                normalized
            ] = code

def add_aliases(
    entries,
    english_aliases,
    swahili_aliases,
):
    output = []

    for entry in entries:
        item = entry.copy()

        item["aliases"] = {
            "en": english_aliases[
                entry["code"]
            ],
            "sw": swahili_aliases.get(
                entry["code"],
                [],
            ),
        }

        output.append(item)

    return output

def main():
    if not FEATURE_CATALOG_PATH.exists():
        raise FileNotFoundError(
            f"Missing feature catalog: "
            f"{FEATURE_CATALOG_PATH}"
        )

    feature_catalog = load_json(
        FEATURE_CATALOG_PATH
    )

    english_aliases = load_json(
        ENGLISH_ALIASES_PATH
    )

    swahili_aliases = load_json(
        SWAHILI_ALIASES_PATH
    )
    
    validate_english_aliases(
        CANONICAL_SYMPTOMS,
        english_aliases,
    )

    validate_swahili_aliases(
        CANONICAL_SYMPTOMS,
        swahili_aliases,
    )

    active_features = {
        feature
        for entry in feature_catalog
        for feature in entry[
            "model_features"
        ]
    }

    validate_unique_codes(
        CANONICAL_SYMPTOMS
    )

    validate_features(
        CANONICAL_SYMPTOMS,
        active_features,
    )

    validate_english_aliases(
        CANONICAL_SYMPTOMS,
        english_aliases,
    )

    canonical_symptoms = (
        add_aliases(
            CANONICAL_SYMPTOMS,
            english_aliases,
            swahili_aliases,
        )
    )

    with open(
        OUTPUT_PATH,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            canonical_symptoms,
            file,
            indent=2,
            ensure_ascii=False,
        )

    red_flags = [
        entry
        for entry in canonical_symptoms
        if entry["is_red_flag"]
    ]

    multi_feature = [
        entry
        for entry in canonical_symptoms
        if len(entry["features"]) > 1
    ]

    safety_only = [
        entry
        for entry in canonical_symptoms
        if (
            entry["is_red_flag"]
            and not entry["features"]
        )
    ]

    print()
    print(
        "Canonical symptom mapping"
    )
    print(
        "-------------------------"
    )

    print(
        "Canonical symptoms:",
        len(canonical_symptoms)
    )

    print(
        "Red-flag symptoms:",
        len(red_flags)
    )

    print(
        "Multi-feature symptoms:",
        len(multi_feature)
    )

    print(
        "Safety-only symptoms:",
        len(safety_only)
    )

    print(
        "Invalid model features: 0"
    )

    english_alias_count = sum(
        len(entry["aliases"]["en"])
        for entry in canonical_symptoms
    )

    print(
        "English aliases:",
        english_alias_count
    )

    swahili_alias_count = sum(
        len(entry["aliases"]["sw"])
        for entry in canonical_symptoms
    )

    print(
        "Swahili aliases:",
        swahili_alias_count
    )

    print()
    print(
        "Multi-feature mappings:"
    )

    for entry in multi_feature:
        print(
            "-",
            entry["display_name"],
            "->",
            entry["features"],
        )

    print()
    print(
        "Saved to:",
        OUTPUT_PATH
    )


if __name__ == "__main__":
    main()