import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.core.config import settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.main import app
from app.services.auth import normalise_email


client = TestClient(app)

TEST_USER_ID = uuid.uuid4()


@pytest.fixture(autouse=True)
def override_database_dependency():
    def fake_get_db():
        yield object()

    app.dependency_overrides[
        main_module.get_db
    ] = fake_get_db

    yield

    app.dependency_overrides.clear()


def test_email_normalisation():
    result = normalise_email(
        "  Patient.Test@Example.COM  "
    )

    assert result == "patient.test@example.com"


def test_password_hashing_and_verification():
    password = "TestPassword123!"

    hashed = hash_password(password)

    assert hashed != password
    assert hashed.startswith("$argon2")
    assert verify_password(
        password,
        hashed,
    ) is True

    assert verify_password(
        "WrongPassword123!",
        hashed,
    ) is False


def test_access_token_contains_user_and_role():
    token = create_access_token(
        user_id=str(TEST_USER_ID),
        role="patient",
    )

    payload = decode_access_token(token)

    assert payload["sub"] == str(
        TEST_USER_ID
    )

    assert payload["role"] == "patient"
    assert "exp" in payload


def test_expired_access_token_is_rejected():
    payload = {
        "sub": str(TEST_USER_ID),
        "role": "patient",
        "exp": (
            datetime.now(timezone.utc)
            - timedelta(minutes=1)
        ),
    }

    token = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(
        jwt.ExpiredSignatureError
    ):
        decode_access_token(token)


def test_invalid_access_token_is_rejected():
    with pytest.raises(
        jwt.InvalidTokenError
    ):
        decode_access_token(
            "not-a-valid-jwt-token"
        )


def test_patient_registration_success(
    monkeypatch,
):
    fake_user = SimpleNamespace(
        id=TEST_USER_ID,
        email="patient@example.com",
        role="patient",
        created_at=datetime.now(
            timezone.utc
        ),
    )

    captured = {}

    def fake_create_patient_user(
        db,
        email,
        password,
    ):
        captured["email"] = email
        captured["password"] = password

        return fake_user

    monkeypatch.setattr(
        main_module,
        "create_patient_user",
        fake_create_patient_user,
    )

    response = client.post(
        "/auth/register",
        json={
            "email": "patient@example.com",
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["id"] == str(TEST_USER_ID)
    assert data["email"] == "patient@example.com"
    assert data["role"] == "patient"

    assert (
        captured["email"]
        == "patient@example.com"
    )

    assert (
        captured["password"]
        == "TestPassword123!"
    )


def test_public_registration_cannot_create_admin(
    monkeypatch,
):
    fake_user = SimpleNamespace(
        id=TEST_USER_ID,
        email="patient@example.com",
        role="patient",
        created_at=datetime.now(
            timezone.utc
        ),
    )

    def fake_create_patient_user(
        db,
        email,
        password,
    ):
        return fake_user

    monkeypatch.setattr(
        main_module,
        "create_patient_user",
        fake_create_patient_user,
    )

    response = client.post(
        "/auth/register",
        json={
            "email": "patient@example.com",
            "password": "TestPassword123!",
            "role": "admin",
        },
    )

    assert response.status_code == 201

    assert (
        response.json()["role"]
        == "patient"
    )


def test_duplicate_registration_returns_409(
    monkeypatch,
):
    def fake_create_patient_user(
        db,
        email,
        password,
    ):
        raise ValueError(
            "An account with this email "
            "already exists."
        )

    monkeypatch.setattr(
        main_module,
        "create_patient_user",
        fake_create_patient_user,
    )

    response = client.post(
        "/auth/register",
        json={
            "email": "patient@example.com",
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 409

    assert (
        "already exists"
        in response.json()["detail"]
    )


def test_invalid_registration_email_returns_422():
    response = client.post(
        "/auth/register",
        json={
            "email": "not-an-email",
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 422


def test_short_registration_password_returns_422():
    response = client.post(
        "/auth/register",
        json={
            "email": "patient@example.com",
            "password": "short",
        },
    )

    assert response.status_code == 422


def test_login_success(
    monkeypatch,
):
    fake_user = SimpleNamespace(
        id=TEST_USER_ID,
        email="patient@example.com",
        role="patient",
    )

    monkeypatch.setattr(
        main_module,
        "authenticate_user",
        lambda db, email, password: (
            fake_user
        ),
    )

    monkeypatch.setattr(
        main_module,
        "create_access_token",
        lambda user_id, role: (
            "test-access-token"
        ),
    )

    response = client.post(
        "/auth/login",
        json={
            "email": "patient@example.com",
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert (
        data["access_token"]
        == "test-access-token"
    )

    assert data["token_type"] == "bearer"

    assert (
        data["expires_in_minutes"]
        == settings.access_token_expire_minutes
    )


def test_wrong_password_returns_401(
    monkeypatch,
):
    monkeypatch.setattr(
        main_module,
        "authenticate_user",
        lambda db, email, password: None,
    )

    response = client.post(
        "/auth/login",
        json={
            "email": "patient@example.com",
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401

    assert (
        response.json()["detail"]
        == "Invalid email or password."
    )


def test_nonexistent_user_login_returns_401(
    monkeypatch,
):
    monkeypatch.setattr(
        main_module,
        "authenticate_user",
        lambda db, email, password: None,
    )

    response = client.post(
        "/auth/login",
        json={
            "email": "missing@example.com",
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 401


def test_auth_me_requires_authentication():
    response = client.get(
        "/auth/me"
    )

    assert response.status_code == 401

    assert (
        response.json()["detail"]
        == "Authentication required."
    )


def test_auth_me_returns_current_user():
    fake_user = SimpleNamespace(
        id=TEST_USER_ID,
        email="patient@example.com",
        role="patient",
        created_at=datetime.now(
            timezone.utc
        ),
    )

    app.dependency_overrides[
        main_module.get_current_user
    ] = lambda: fake_user

    response = client.get(
        "/auth/me"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == str(TEST_USER_ID)
    assert data["email"] == "patient@example.com"
    assert data["role"] == "patient"