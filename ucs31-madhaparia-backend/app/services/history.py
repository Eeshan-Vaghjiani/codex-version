import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Feedback, PredictionSession


def save_prediction_session(
    db: Session,
    *,
    user_id: uuid.UUID,
    age: int,
    sex: str,
    input_text: str,
    confirmed_codes: list[str],
    model_features: list[str],
    status: str,
    has_red_flag: bool,
    predictions: list[dict],
    model_version_id: uuid.UUID | None = None,
    assessment_context: dict | None = None,
) -> PredictionSession:
    session = PredictionSession(
        user_id=user_id,
        age=age,
        sex=sex,
        input_text=input_text,
        confirmed_codes=confirmed_codes,
        model_features=model_features,
        status=status,
        has_red_flag=has_red_flag,
        predictions=predictions,
        model_version_id=model_version_id,
        assessment_context=assessment_context or {},
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    return session


def get_prediction_session(
    db: Session,
    prediction_id: uuid.UUID,
    user_id: uuid.UUID,
) -> PredictionSession | None:
    statement = select(PredictionSession).where(
        PredictionSession.id == prediction_id,
        PredictionSession.user_id == user_id,
    )

    return db.scalar(statement)


def list_prediction_sessions(
    db: Session,
    user_id: uuid.UUID,
    limit: int = 20,
) -> list[PredictionSession]:
    statement = (
        select(PredictionSession)
        .where(
            PredictionSession.user_id == user_id
        )
        .order_by(
            PredictionSession.created_at.desc()
        )
        .limit(limit)
    )

    return list(
        db.scalars(statement).all()
    )

def list_all_prediction_sessions(
    db: Session,
    limit: int = 100,
) -> list[PredictionSession]:
    statement = (
        select(PredictionSession)
        .order_by(
            PredictionSession.created_at.desc()
        )
        .limit(limit)
    )

    return list(
        db.scalars(statement).all()
    )


def get_any_prediction_session(
    db: Session,
    prediction_id: uuid.UUID,
) -> PredictionSession | None:
    return db.get(
        PredictionSession,
        prediction_id,
    )


def list_all_feedback(
    db: Session,
    limit: int = 100,
) -> list[Feedback]:
    statement = (
        select(Feedback)
        .order_by(
            Feedback.created_at.desc()
        )
        .limit(limit)
    )

    return list(
        db.scalars(statement).all()
    )


def save_feedback(
    db: Session,
    *,
    prediction_session_id: uuid.UUID,
    user_id: uuid.UUID,
    was_helpful: bool,
    comment: str | None,
) -> Feedback:
    prediction_session = get_prediction_session(
        db,
        prediction_id=prediction_session_id,
        user_id=user_id,
    )

    if prediction_session is None:
        raise LookupError(
            "Prediction session was not found."
        )

    existing_feedback = db.scalar(
        select(Feedback).where(
            Feedback.prediction_session_id
            == prediction_session_id
        )
    )

    if existing_feedback is not None:
        raise ValueError(
            "Feedback has already been submitted "
            "for this prediction session."
        )

    feedback = Feedback(
        prediction_session_id=prediction_session_id,
        was_helpful=was_helpful,
        comment=comment,
    )

    db.add(feedback)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise ValueError(
            "Feedback has already been submitted "
            "for this prediction session."
        ) from error

    db.refresh(feedback)

    return feedback