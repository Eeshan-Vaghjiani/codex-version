import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    __table_args__ = (
        CheckConstraint(
            "role IN ('patient', 'admin')",
            name="ck_users_role",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="patient",
        server_default="patient",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    prediction_sessions: Mapped[list["PredictionSession"]] = relationship(
        back_populates="user",
    )

class ModelVersion(Base):
    __tablename__ = "model_versions"

    __table_args__ = (
        UniqueConstraint(
            "model_name",
            "version",
            name="uq_model_versions_model_name_version",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    model_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    purpose: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    artifact_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    feature_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    class_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    training_samples: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    validation_samples: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    test_samples: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    parameters: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    validation_metrics: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    test_metrics: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    prediction_sessions: Mapped[
        list["PredictionSession"]
    ] = relationship(
        back_populates="model_version",
    )


class PredictionSession(Base):
    __tablename__ = "prediction_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
            name="fk_prediction_sessions_user_id_users",
        ),
        nullable=True,
        index=True,
    )

    age: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    sex: Mapped[str] = mapped_column(
        String(1),
        nullable=False,
    )

    input_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    confirmed_codes: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
    )

    model_features: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    has_red_flag: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    assessment_context: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}",
    )

    predictions: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped[User | None] = relationship(
        back_populates="prediction_sessions",
    )

    model_version: Mapped[
        ModelVersion | None
    ] = relationship(
        back_populates="prediction_sessions",
    )

    model_version_id: Mapped[
        uuid.UUID | None
    ] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "model_versions.id",
            ondelete="SET NULL",
            name=(
                "fk_prediction_sessions_"
                "model_version_id_model_versions"
            ),
        ),
        nullable=True,
        index=True,
    )

    feedback_items: Mapped[list["Feedback"]] = relationship(
        back_populates="prediction_session",
        cascade="all, delete-orphan",
    )


class Feedback(Base):
    __tablename__ = "feedback"

    __table_args__ = (
        UniqueConstraint(
            "prediction_session_id",
            name="uq_feedback_prediction_session_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    prediction_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "prediction_sessions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    was_helpful: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    prediction_session: Mapped["PredictionSession"] = relationship(
        back_populates="feedback_items",
    )



class Symptom(Base):
    __tablename__ = "symptoms"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    code: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )

    display_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    features: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    kind: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="symptom",
    )

    is_red_flag: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    aliases: Mapped[list["SymptomAlias"]] = relationship(
        back_populates="symptom",
        cascade="all, delete-orphan",
    )


class SymptomAlias(Base):
    __tablename__ = "symptom_aliases"

    __table_args__ = (
        CheckConstraint(
            "language IN ('en', 'sw')",
            name="ck_symptom_aliases_language",
        ),
        UniqueConstraint(
            "symptom_id",
            "alias",
            "language",
            name="uq_symptom_aliases_symptom_alias_language",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    symptom_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "symptoms.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    alias: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    language: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    symptom: Mapped["Symptom"] = relationship(
        back_populates="aliases",
    )
