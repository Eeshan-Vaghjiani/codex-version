"""Upgrade safety for explicit obsolete aliases; user catalogue additions survive."""
import json

from sqlalchemy import select

from app.core.database import SessionLocal
from app.db import seed_symptom_catalog as seeder
from app.db.models import Symptom, SymptomAlias
from app.nlp.symptom_mapper import build_confirmation_output


def test_retirement_list_contains_only_absent_current_managed_triples():
    retired = seeder.load_json(seeder.RETIRED_ALIASES_PATH)["aliases"]
    sources = {"en": seeder.load_json(seeder.ENGLISH_ALIASES_PATH),
               "sw": seeder.load_json(seeder.SWAHILI_ALIASES_PATH)}
    assert retired
    keys = {(row["code"], row["language"], row["alias"]) for row in retired}
    assert len(keys) == len(retired)
    assert ("wheezing", "en", "tight chest") in keys
    assert ("productive_cough", "en", "mucus") in keys
    for row in retired:
        assert row["reason"]
        assert row["alias"] not in sources[row["language"]].get(row["code"], [])


def test_seed_retires_only_reviewed_aliases_and_is_idempotent(monkeypatch):
    db = SessionLocal()
    try:
        wheeze = db.scalar(select(Symptom).where(Symptom.code == "wheezing"))
        productive = db.scalar(select(Symptom).where(Symptom.code == "productive_cough"))
        custom = SymptomAlias(symptom_id=wheeze.id, alias="custom clinic wheeze phrase", language="en")
        db.add_all([
            SymptomAlias(symptom_id=wheeze.id, alias="tight chest", language="en"),
            SymptomAlias(symptom_id=productive.id, alias="mucus", language="en"),
            custom,
        ])
        db.flush()
        assert seeder.retire_managed_aliases(db) == 2
        assert seeder.retire_managed_aliases(db) == 0
        assert db.scalar(select(SymptomAlias).where(SymptomAlias.id == custom.id)) is not None
        # The upgraded DB now has the same source meaning as fresh installations.
        tight = build_confirmation_output("I have a tight chest", db)
        assert {item["code"] for item in tight["recognised_symptoms"]} == {"chest_tightness"}
        mucus = build_confirmation_output("I have mucus in my nose", db)
        assert not any(item["code"] == "productive_cough" for item in mucus["recognised_symptoms"])
    finally:
        db.rollback()
        db.close()
