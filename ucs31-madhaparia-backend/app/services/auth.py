from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.db.models import User


def normalise_email(email: str) -> str:
    return email.strip().lower()


def get_user_by_email(
    db: Session,
    email: str,
) -> User | None:
    email = normalise_email(email)

    return db.scalar(
        select(User).where(User.email == email)
    )


def create_patient_user(
    db: Session,
    email: str,
    password: str,
) -> User:
    email = normalise_email(email)

    if get_user_by_email(db, email) is not None:
        raise ValueError(
            "An account with this email already exists."
        )

    user = User(
        email=email,
        password_hash=hash_password(password),
        role="patient",
    )

    db.add(user)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise ValueError(
            "An account with this email already exists."
        ) from error

    db.refresh(user)

    return user


def authenticate_user(
    db: Session,
    email: str,
    password: str,
) -> User | None:
    user = get_user_by_email(
        db,
        email,
    )

    if user is None:
        return None

    if not verify_password(
        password,
        user.password_hash,
    ):
        return None

    return user