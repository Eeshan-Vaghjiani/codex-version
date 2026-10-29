import json
from pathlib import Path

from sqlalchemy import delete, select

from app.core.database import SessionLocal
from app.db.models import Symptom, SymptomAlias


NLP_DIR = Path(__file__).resolve().parents[1] / "nlp"

CANONICAL_PATH = NLP_DIR / "canonical_symptoms.json"
ENGLISH_ALIASES_PATH = NLP_DIR / "english_aliases.json"
SWAHILI_ALIASES_PATH = NLP_DIR / "swahili_aliases.json"
RETIRED_ALIASES_PATH = NLP_DIR / "retired_aliases.json"


def load_json(path: Path):
    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def retire_managed_aliases(db) -> int:
    """Remove only explicitly reviewed obsolete managed triples.

    Unknown/custom aliases remain untouched. Callers own the transaction.
    """
    retirement = load_json(RETIRED_ALIASES_PATH)
    if retirement.get("schema_version") != 1:
        raise ValueError("Unsupported managed-alias retirement schema")
    removed = 0
    for item in retirement["aliases"]:
        symptom_id = select(Symptom.id).where(Symptom.code == item["code"]).scalar_subquery()
        result = db.execute(delete(SymptomAlias).where(
            SymptomAlias.symptom_id == symptom_id,
            SymptomAlias.alias == item["alias"],
            SymptomAlias.language == item["language"],
        ))
        removed += result.rowcount
    return removed


def seed_symptom_catalog() -> None:
    canonical_symptoms = load_json(
        CANONICAL_PATH
    )

    english_aliases = load_json(
        ENGLISH_ALIASES_PATH
    )

    swahili_aliases = load_json(
        SWAHILI_ALIASES_PATH
    )

    db = SessionLocal()

    try:
        symptoms_by_code = {}

        for item in canonical_symptoms:
            code = item["code"]

            symptom = db.scalar(
                select(Symptom).where(
                    Symptom.code == code
                )
            )

            if symptom is None:
                symptom = Symptom(
                    code=code,
                    display_name=item[
                        "display_name"
                    ],
                    features=item.get(
                        "features",
                        [],
                    ),
                    kind=item.get(
                        "kind",
                        "symptom",
                    ),
                    is_red_flag=item.get(
                        "is_red_flag",
                        False,
                    ),
                )

                db.add(symptom)

            else:
                symptom.display_name = item[
                    "display_name"
                ]

                symptom.features = item.get(
                    "features",
                    [],
                )

                symptom.kind = item.get(
                    "kind",
                    "symptom",
                )

                symptom.is_red_flag = item.get(
                    "is_red_flag",
                    False,
                )

            symptoms_by_code[code] = symptom

        db.flush()
        retire_managed_aliases(db)

        alias_sources = (
            ("en", english_aliases),
            ("sw", swahili_aliases),
        )

        for language, alias_data in alias_sources:
            for code, aliases in alias_data.items():
                symptom = symptoms_by_code[
                    code
                ]

                for alias_text in aliases:
                    alias_text = (
                        alias_text.strip()
                    )

                    existing_alias = db.scalar(
                        select(
                            SymptomAlias
                        ).where(
                            SymptomAlias.symptom_id
                            == symptom.id,
                            SymptomAlias.alias
                            == alias_text,
                            SymptomAlias.language
                            == language,
                        )
                    )

                    if existing_alias is None:
                        db.add(
                            SymptomAlias(
                                symptom_id=(
                                    symptom.id
                                ),
                                alias=alias_text,
                                language=language,
                            )
                        )

        db.commit()

        symptom_count = len(
            db.scalars(
                select(Symptom)
            ).all()
        )

        alias_count = len(
            db.scalars(
                select(SymptomAlias)
            ).all()
        )

        english_count = len(
            db.scalars(
                select(SymptomAlias).where(
                    SymptomAlias.language
                    == "en"
                )
            ).all()
        )

        swahili_count = len(
            db.scalars(
                select(SymptomAlias).where(
                    SymptomAlias.language
                    == "sw"
                )
            ).all()
        )

        print(
            f"Symptoms: {symptom_count}"
        )

        print(
            f"Aliases: {alias_count}"
        )

        print(
            f"English aliases: "
            f"{english_count}"
        )

        print(
            f"Swahili aliases: "
            f"{swahili_count}"
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_symptom_catalog()
