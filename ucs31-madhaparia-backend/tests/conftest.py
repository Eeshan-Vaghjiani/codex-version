"""
Shared test configuration.

The test suite never uses the database configured in .env.
It needs TEST_DATABASE_URL to point at a PostgreSQL database
that is safe to use for testing (for example a local one).

For each test run a temporary schema is created inside that
database, the Alembic migrations are applied to it, the symptom
catalogue and model version are seeded, and the schema is
dropped again when the run finishes.
"""

import os
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


PROJECT_ROOT = Path(__file__).resolve().parents[1]

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

TEST_SCHEMA = f"test_{uuid.uuid4().hex[:12]}"


if not TEST_DATABASE_URL:
    pytest.exit(
        "TEST_DATABASE_URL is not set. Point it at a PostgreSQL "
        "database that is safe to use for testing, for example: "
        "postgresql+psycopg://postgres:postgres@localhost:5432/"
        "respiratory_test",
        returncode=2,
    )


# These must be set before any "app" module is imported, because
# the settings and the database engine are created at import time.
# Environment variables take priority over values in .env.
os.environ["DATABASE_URL"] = (
    make_url(TEST_DATABASE_URL)
    .update_query_dict(
        {
            "options": f"-csearch_path={TEST_SCHEMA}",
        }
    )
    .render_as_string(hide_password=False)
)

os.environ["JWT_SECRET_KEY"] = (
    "test-only-secret-key-not-used-anywhere-else"
)


@pytest.fixture(scope="session", autouse=True)
def test_database():
    admin_engine = create_engine(
        TEST_DATABASE_URL,
        isolation_level="AUTOCOMMIT",
    )

    with admin_engine.connect() as connection:
        connection.execute(
            text(f'CREATE SCHEMA "{TEST_SCHEMA}"')
        )

    try:
        from alembic import command
        from alembic.config import Config

        from app.core.database import engine
        from app.db.seed_model_version import (
            seed_model_version,
        )
        from app.db.seed_symptom_catalog import (
            seed_symptom_catalog,
        )

        command.upgrade(
            Config(str(PROJECT_ROOT / "alembic.ini")),
            "head",
        )

        seed_symptom_catalog()
        # Legacy suites explicitly exercise V1/V2 contracts. V3 tests activate
        # the new default inside isolated transactions.
        seed_model_version(version="1.0")

        yield

        engine.dispose()

    finally:
        with admin_engine.connect() as connection:
            connection.execute(
                text(
                    f'DROP SCHEMA "{TEST_SCHEMA}" CASCADE'
                )
            )

        admin_engine.dispose()
