from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ServiceNotReadyError
from app.db.models import ModelVersion


def get_active_model_version(
    db: Session,
) -> ModelVersion:
    active_versions = list(
        db.scalars(
            select(ModelVersion)
            .where(
                ModelVersion.is_active.is_(True)
            )
            .order_by(
                ModelVersion.created_at.desc()
            )
        ).all()
    )

    if not active_versions:
        raise ServiceNotReadyError(
            "No active machine-learning "
            "model version is configured. "
            "Run: python -m app.db.seed_model_version"
        )

    if len(active_versions) > 1:
        raise ServiceNotReadyError(
            "Multiple active machine-learning "
            "model versions are configured. "
            "Run: python -m app.db.seed_model_version"
        )

    return active_versions[0]