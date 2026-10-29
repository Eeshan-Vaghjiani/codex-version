import json
from collections import defaultdict
from pathlib import Path

from app.db.models import Symptom, SymptomAlias


NLP_DIR = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "nlp"
)


def load_json(filename):
    path = NLP_DIR / filename

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def test_canonical_symptom_catalog():
    canonical = load_json(
        "canonical_symptoms.json"
    )

    assert canonical
    assert "sneezing" in {item["code"] for item in canonical}

    codes = [
        symptom["code"]
        for symptom in canonical
    ]

    assert len(codes) == len(set(codes))

    for symptom in canonical:
        assert symptom["code"]
        assert symptom["display_name"]

        assert isinstance(
            symptom["features"],
            list,
        )

        assert isinstance(
            symptom["kind"],
            str,
        )

        assert isinstance(
            symptom["is_red_flag"],
            bool,
        )


def test_symptom_alias_catalog_counts_and_codes():
    canonical = load_json(
        "canonical_symptoms.json"
    )

    english = load_json(
        "english_aliases.json"
    )

    swahili = load_json(
        "swahili_aliases.json"
    )

    canonical_codes = {
        symptom["code"]
        for symptom in canonical
    }

    english_count = sum(
        len(aliases)
        for aliases in english.values()
    )

    swahili_count = sum(
        len(aliases)
        for aliases in swahili.values()
    )

    expected_english = {item["code"]: item["aliases"]["en"] for item in canonical}
    expected_swahili = {item["code"]: item["aliases"]["sw"] for item in canonical
                       if item["aliases"]["sw"]}
    assert english == expected_english
    assert swahili == expected_swahili
    assert english_count == sum(len(item["aliases"]["en"]) for item in canonical)
    assert swahili_count == sum(len(item["aliases"]["sw"]) for item in canonical)

    assert set(english) == canonical_codes
    assert set(swahili).issubset(
        canonical_codes
    )


def test_symptom_aliases_have_no_conflicts():
    english = load_json(
        "english_aliases.json"
    )

    swahili = load_json(
        "swahili_aliases.json"
    )

    seen = defaultdict(set)

    for language, alias_data in (
        ("en", english),
        ("sw", swahili),
    ):
        for code, aliases in alias_data.items():
            normalised_aliases = [
                alias.strip().lower()
                for alias in aliases
            ]

            assert len(
                normalised_aliases
            ) == len(
                set(normalised_aliases)
            )

            for alias in normalised_aliases:
                seen[
                    (language, alias)
                ].add(code)

    conflicts = {
        key: codes
        for key, codes in seen.items()
        if len(codes) > 1
    }

    assert conflicts == {}


def test_symptom_database_model_relationship():
    symptom_table = Symptom.__table__
    alias_table = SymptomAlias.__table__

    assert symptom_table.name == "symptoms"

    assert (
        alias_table.name
        == "symptom_aliases"
    )

    foreign_keys = list(
        alias_table.c.symptom_id.foreign_keys
    )

    assert len(foreign_keys) == 1

    foreign_key = foreign_keys[0]

    assert (
        foreign_key.target_fullname
        == "symptoms.id"
    )

    assert foreign_key.ondelete == "CASCADE"

    constraint_names = {
        constraint.name
        for constraint
        in alias_table.constraints
        if constraint.name
    }

    assert (
        "ck_symptom_aliases_language"
        in constraint_names
    )

    assert (
        "uq_symptom_aliases_symptom_alias_language"
        in constraint_names
    )

    assert (
        Symptom.__mapper__
        .relationships["aliases"]
        .back_populates
        == "symptom"
    )

    assert (
        SymptomAlias.__mapper__
        .relationships["symptom"]
        .back_populates
        == "aliases"
    )
