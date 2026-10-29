from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def check_schema():
    """
    Confirm that the Alembic migrations have been applied.

    Tables are created by Alembic only. Creating them here as
    well would leave the database without a migration version
    and make "alembic upgrade head" fail afterwards.
    """
    from app.db import models  # noqa: F401

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    missing_tables = sorted(
        set(Base.metadata.tables) - existing_tables
    )

    if missing_tables:
        raise RuntimeError(
            "The database schema is not up to date "
            f"(missing tables: {missing_tables}). "
            "Run: python -m alembic upgrade head"
        )


    if 'prediction_sessions' in existing_tables and 'assessment_context' not in {
        column['name'] for column in inspector.get_columns('prediction_sessions')
    }:
        raise RuntimeError('The database schema is not up to date (missing assessment_context). Run: python -m alembic upgrade head')
