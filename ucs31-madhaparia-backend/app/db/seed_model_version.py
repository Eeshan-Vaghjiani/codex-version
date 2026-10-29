import json
from pathlib import Path

from sqlalchemy import select

from app.core.database import SessionLocal
from app.db.models import ModelVersion


METADATA_PATH = (
    Path(__file__).resolve().parents[1]
    / "ml"
    / "artifacts"
    / "model_metadata.json"
)


def load_metadata():
    with METADATA_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def seed_model_version(version="v3_partial_evidence"):
    if version == "v3_partial_evidence":
        from app.db.register_v3_model_version import activate_v3_model_version
        with SessionLocal() as db:
            try:
                saved = activate_v3_model_version(db)
                db.commit()
                print(f"Active model: {saved.version}; {saved.class_count} conditions, {saved.feature_count} partial-evidence features")
                return
            except Exception:
                db.rollback()
                raise
    if version != "1.0":
        raise ValueError("Unsupported model initialization version")
    metadata = load_metadata()

    db = SessionLocal()

    try:
        all_versions = list(
            db.scalars(
                select(ModelVersion)
            ).all()
        )

        for model_version in all_versions:
            model_version.is_active = False

        existing = db.scalar(
            select(ModelVersion).where(
                ModelVersion.model_name
                == metadata["model_name"],
                ModelVersion.version
                == metadata["model_version"],
            )
        )

        if existing is None:
            model_version = ModelVersion(
                model_name=metadata[
                    "model_name"
                ],
                version=metadata[
                    "model_version"
                ],
                purpose=metadata[
                    "purpose"
                ],
                artifact_filename=metadata[
                    "model_file"
                ],
                feature_count=metadata[
                    "number_of_model_features"
                ],
                class_count=metadata[
                    "number_of_diseases"
                ],
                training_samples=metadata[
                    "training_samples"
                ],
                validation_samples=metadata[
                    "validation_samples"
                ],
                test_samples=metadata[
                    "test_samples"
                ],
                parameters=metadata[
                    "model_parameters"
                ],
                validation_metrics=metadata[
                    "validation_metrics"
                ],
                test_metrics=metadata[
                    "test_metrics"
                ],
                is_active=True,
            )

            db.add(model_version)

        else:
            existing.purpose = metadata[
                "purpose"
            ]

            existing.artifact_filename = (
                metadata["model_file"]
            )

            existing.feature_count = metadata[
                "number_of_model_features"
            ]

            existing.class_count = metadata[
                "number_of_diseases"
            ]

            existing.training_samples = metadata[
                "training_samples"
            ]

            existing.validation_samples = metadata[
                "validation_samples"
            ]

            existing.test_samples = metadata[
                "test_samples"
            ]

            existing.parameters = metadata[
                "model_parameters"
            ]

            existing.validation_metrics = metadata[
                "validation_metrics"
            ]

            existing.test_metrics = metadata[
                "test_metrics"
            ]

            existing.is_active = True

        db.commit()

        saved = db.scalar(
            select(ModelVersion).where(
                ModelVersion.model_name
                == metadata["model_name"],
                ModelVersion.version
                == metadata["model_version"],
            )
        )

        print(
            "Model:",
            saved.model_name,
        )

        print(
            "Version:",
            saved.version,
        )

        print(
            "Features:",
            saved.feature_count,
        )

        print(
            "Classes:",
            saved.class_count,
        )

        print(
            "Active:",
            saved.is_active,
        )

        print(
            "Artifact:",
            saved.artifact_filename,
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_model_version()