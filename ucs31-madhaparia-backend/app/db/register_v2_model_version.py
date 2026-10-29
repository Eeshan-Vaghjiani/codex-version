
"""Register the V2 research model without activating it.

This module does not run automatically or open a database
connection by itself. The caller supplies a database session.
"""

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ModelVersion


V2_METADATA_PATH = (
    Path(__file__).resolve().parents[1]
    / "ml"
    / "artifacts"
    / "model_metadata_v2.json"
)


def build_v2_registration_values() -> dict:
    """Prepare and validate V2 database fields."""

    metadata = json.loads(
        V2_METADATA_PATH.read_text(encoding="utf-8")
    )

    if metadata["model_version"] != "v2_23class_prototype":
        raise ValueError("Unexpected V2 model version.")

    if metadata["active_in_backend"] is not False:
        raise ValueError(
            "V2 registration requires inactive metadata."
        )

    if (
        metadata["number_of_model_features"] != 66
        or metadata["number_of_diseases"] != 23
    ):
        raise ValueError("Unexpected V2 model dimensions.")

    if metadata["clinical_validation"] is not False:
        raise ValueError(
            "Unexpected clinical validation status."
        )

    if metadata["test_metrics"]["evaluated"] is not False:
        raise ValueError(
            "Unexpected V2 held-out test status."
        )

    return {
        "model_name": metadata["model_name"],
        "version": metadata["model_version"],
        "purpose": metadata["purpose"],
        "artifact_filename": metadata["model_file"],
        "feature_count": metadata["number_of_model_features"],
        "class_count": metadata["number_of_diseases"],
        "training_samples": metadata["training_samples"],
        "validation_samples": metadata["validation_samples"],
        "test_samples": metadata["test_samples"],
        "parameters": metadata["model_parameters"],
        "validation_metrics": metadata["validation_metrics"],
        "test_metrics": metadata["test_metrics"],
    }


def register_v2_model_version(
    db: Session,
) -> ModelVersion:
    """Insert or update V2 without activating or switching models.

    Does not commit. The caller controls the transaction.
    """

    values = build_v2_registration_values()

    existing = db.scalar(
        select(ModelVersion).where(
            ModelVersion.model_name == values["model_name"],
            ModelVersion.version == values["version"],
        )
    )

    if existing is None:
        model_version = ModelVersion(
            **values,
            is_active=False,
        )
        db.add(model_version)
    else:
        model_version = existing

        for field, value in values.items():
            setattr(model_version, field, value)

        # Preserve existing activation status.
        # Registration must never switch the active model.

    db.flush()

    return model_version
