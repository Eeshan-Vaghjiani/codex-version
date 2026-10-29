"""
Create an administrator account, or promote an existing user.

Usage:

    python -m app.db.create_admin admin@example.com

The password is asked for interactively. For a new account it
can also be supplied through the ADMIN_PASSWORD environment
variable. An existing account keeps its current password.
"""

import getpass
import os
import sys

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.db.models import User
from app.services.auth import (
    get_user_by_email,
    normalise_email,
)


MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128


def read_password() -> str:
    password = os.environ.get("ADMIN_PASSWORD")

    if password is None:
        password = getpass.getpass("Password: ")

        if getpass.getpass("Repeat password: ") != password:
            raise SystemExit("Passwords do not match.")

    if not (
        MIN_PASSWORD_LENGTH
        <= len(password)
        <= MAX_PASSWORD_LENGTH
    ):
        raise SystemExit(
            "Password must be between "
            f"{MIN_PASSWORD_LENGTH} and "
            f"{MAX_PASSWORD_LENGTH} characters."
        )

    return password


def create_admin(email: str) -> None:
    email = normalise_email(email)

    if "@" not in email:
        raise SystemExit(
            f"Not a valid email address: {email}"
        )

    db = SessionLocal()

    try:
        user = get_user_by_email(db, email)

        if user is None:
            user = User(
                email=email,
                password_hash=hash_password(
                    read_password()
                ),
                role="admin",
            )

            db.add(user)
            action = "created"

        elif user.role == "admin":
            action = "already an administrator"

        else:
            user.role = "admin"
            action = "promoted to administrator"

        db.commit()

        print("Email:", user.email)
        print("Role:", user.role)
        print("Result:", action)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python -m app.db.create_admin <email>"
        )

    create_admin(sys.argv[1])
