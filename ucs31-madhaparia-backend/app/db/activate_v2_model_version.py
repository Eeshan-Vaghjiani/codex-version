
"""Controlled activation of the V2 research prototype.

Activation requires an existing registered V2 record.
The caller controls the transaction and commit.
This module does not activate anything automatically.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ModelVersion
from app.db.register_v2_model_version import (
    build_v2_registration_values,
)
from app.ml.model_loader import load_v2_model_bundle


def activate_v2_model_version(db: Session) -> ModelVersion:
    """Switch the active model to registered V2.

    Does not commit. The caller controls the transaction.
    """

    expected = build_v2_registration_values()

    # Validate the actual model artifact before switching.
    bundle = load_v2_model_bundle()

    if bundle["model_version"] != expected["version"]:
        raise ValueError("V2 artifact version mismatch.")

    versions = list(
        db.scalars(
            select(ModelVersion).with_for_update()
        ).all()
    )

    matching = [
        version
        for version in versions
        if (
            version.model_name == expected["model_name"]
            and version.version == expected["version"]
        )
    ]

    if len(matching) != 1:
        raise ValueError(
            "V2 must be registered exactly once "
            "before activation."
        )

    v2 = matching[0]

    if (
        v2.artifact_filename != expected["artifact_filename"]
        or v2.feature_count != 66
        or v2.class_count != 23
    ):
        raise ValueError(
            "Registered V2 metadata does not match "
            "the expected model artifact."
        )

    active_versions = [
        version
        for version in versions
        if version.is_active
    ]

    if len(active_versions) > 1:
        raise ValueError(
            "Multiple active model versions detected."
        )

    for version in versions:
        version.is_active = (version is v2)

    db.flush()

    return v2
