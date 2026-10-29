
"""PostgreSQL integration tests for V2 model registration.

These tests run inside the isolated pytest schema.
All V2 changes are rolled back after each test.
"""

import pytest
from sqlalchemy import select

from app.core.database import SessionLocal
from app.db.models import ModelVersion
from app.db.register_v2_model_version import (
    register_v2_model_version,
)
from app.db.activate_v2_model_version import (
    activate_v2_model_version,
)
from app.services.model_versions import (
    get_active_model_version,
)


@pytest.fixture
def db_session():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.rollback()
        db.close()


def test_v2_registration_keeps_v1_active(db_session):
    original = get_active_model_version(db_session)

    assert original.version == "1.0"

    v2 = register_v2_model_version(db_session)

    assert v2.version == "v2_23class_prototype"
    assert v2.feature_count == 66
    assert v2.class_count == 23
    assert v2.is_active is False

    active = get_active_model_version(db_session)

    assert active.id == original.id
    assert active.version == "1.0"

    db_session.rollback()

    # Registration was not committed.
    stored_v2 = db_session.scalar(
        select(ModelVersion).where(
            ModelVersion.version == "v2_23class_prototype"
        )
    )

    assert stored_v2 is None


def test_v2_activation_can_be_rolled_back(db_session):
    original = get_active_model_version(db_session)

    assert original.version == "1.0"

    v2 = register_v2_model_version(db_session)

    activated = activate_v2_model_version(db_session)

    assert activated.id == v2.id
    assert activated.is_active is True

    active = get_active_model_version(db_session)

    assert active.version == "v2_23class_prototype"

    # Undo registration and activation together.
    db_session.rollback()

    restored = get_active_model_version(db_session)

    assert restored.version == "1.0"
    assert restored.id == original.id

    stored_v2 = db_session.scalar(
        select(ModelVersion).where(
            ModelVersion.version == "v2_23class_prototype"
        )
    )

    assert stored_v2 is None


def test_invalid_v2_registration_blocks_activation(db_session):
    register_v2_model_version(db_session)

    v2 = db_session.scalar(
        select(ModelVersion).where(
            ModelVersion.version == "v2_23class_prototype"
        )
    )

    v2.feature_count = 198

    with pytest.raises(
        ValueError,
        match="does not match",
    ):
        activate_v2_model_version(db_session)

    db_session.rollback()

    assert get_active_model_version(db_session).version == "1.0"
