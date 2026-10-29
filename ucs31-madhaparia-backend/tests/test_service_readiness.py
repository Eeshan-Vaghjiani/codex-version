import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

import app.main as main_module
from app.core.config import Settings
from app.core.errors import ServiceNotReadyError
from app.main import (
    MAX_CONFIRMED_CODES,
    MAX_SYMPTOM_TEXT_LENGTH,
    app,
)
from app.nlp.symptom_mapper import build_confirmation_output
from tests.assessment_helpers import finish_followups


client = TestClient(app)


class EmptyCatalogueDb:
    def scalar(self, statement):
        return None


@pytest.fixture
def authenticated_patient():
    app.dependency_overrides[
        main_module.get_current_user
    ] = lambda: SimpleNamespace(
        id=uuid.uuid4(),
        email="patient@example.com",
        role="patient",
    )

    yield

    app.dependency_overrides.clear()


def test_empty_symptom_catalogue_is_reported():
    with pytest.raises(ServiceNotReadyError) as error:
        build_confirmation_output(
            "I have fever",
            EmptyCatalogueDb(),
        )

    assert "seed_symptom_catalog" in str(error.value)


def test_nlp_map_returns_503_when_catalogue_is_empty():
    app.dependency_overrides[
        main_module.get_db
    ] = lambda: EmptyCatalogueDb()

    try:
        response = client.post(
            "/nlp/map",
            json={
                "text": "I have fever"
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503

    assert (
        "seed_symptom_catalog"
        in response.json()["detail"]
    )


def test_predict_returns_503_without_active_model_version(
    monkeypatch,
    authenticated_patient,
):
    def no_active_model_version(db):
        raise ServiceNotReadyError(
            "No active machine-learning "
            "model version is configured."
        )

    monkeypatch.setattr(
        main_module,
        "get_active_model_version",
        no_active_model_version,
    )

    response = finish_followups(
        client,
        {
            "age": 25,
            "sex": "M",
            "text": "I have fever and cough",
            "confirmed_codes": [
                "fever",
                "cough",
            ],
        },
    )

    assert response.status_code == 503

    assert (
        "No active machine-learning model version"
        in response.json()["detail"]
    )


def test_schema_outage_preserves_emergency_mapping_at_startup(monkeypatch):
    def unavailable_schema():
        raise RuntimeError("Test schema unavailable")

    class UnavailableDb:
        def execute(self, statement):
            raise SQLAlchemyError("Test database unavailable")

        def scalar(self, statement):
            raise SQLAlchemyError("Test database unavailable")

    monkeypatch.setattr(main_module, "check_schema", unavailable_schema)
    previous_ready = getattr(app.state, "database_ready", None)
    app.dependency_overrides[main_module.get_db] = lambda: UnavailableDb()
    try:
        with TestClient(app) as startup_client:
            health = startup_client.get("/health")
            assert health.status_code == 200
            assert health.json()["status"] == "degraded"
            urgent = startup_client.post("/nlp/map", json={"text": "I am struggling to breathe"})
            assert urgent.status_code == 200
            assert urgent.json()["has_red_flag"] is True
            assert urgent.json()["safety_status"] == "urgent_review"
            routine = startup_client.post("/nlp/map", json={"text": "I have a cough"})
            assert routine.status_code == 503
    finally:
        app.dependency_overrides.clear()
        if previous_ready is None:
            del app.state.database_ready
        else:
            app.state.database_ready = previous_ready


def test_symptom_text_too_long_returns_422():
    response = client.post(
        "/nlp/map",
        json={
            "text": "a" * (
                MAX_SYMPTOM_TEXT_LENGTH + 1
            )
        },
    )

    assert response.status_code == 422


def test_too_many_confirmed_codes_returns_422():
    response = client.post(
        "/symptoms/confirm",
        json={
            "text": "I have fever",
            "confirmed_codes": ["fever"] * (
                MAX_CONFIRMED_CODES + 1
            ),
        },
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "secret",
    [
        "",
        "change-me",
        "replace_with_a_secure_random_secret",
        "too-short",
    ],
)
def test_weak_jwt_secret_is_rejected(secret):
    with pytest.raises(ValidationError) as error:
        Settings(
            _env_file=None,
            jwt_secret_key=secret,
        )

    assert "JWT_SECRET_KEY must be set" in str(
        error.value
    )
