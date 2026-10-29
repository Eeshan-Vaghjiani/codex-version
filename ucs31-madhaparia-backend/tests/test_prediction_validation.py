import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.core.database import SessionLocal
from app.main import app
from tests.assessment_helpers import finish_followups


client = TestClient(app)

TEST_USER_ID = uuid.uuid4()


@pytest.fixture(autouse=True)
def override_dependencies():
    def fake_get_db():
        db = SessionLocal()

        try:
            yield db
        finally:
            db.close()

    def fake_get_current_user():
        return SimpleNamespace(
            id=TEST_USER_ID,
            email="patient@example.com",
            role="patient",
        )

    app.dependency_overrides[
        main_module.get_db
    ] = fake_get_db

    app.dependency_overrides[
        main_module.get_current_user
    ] = fake_get_current_user

    yield

    app.dependency_overrides.clear()


@pytest.fixture
def mock_prediction_save(monkeypatch):
    saved = {}

    def fake_save_prediction_session(
        db,
        **kwargs,
    ):
        saved.update(kwargs)

        return SimpleNamespace(
            id=uuid.uuid4()
        )

    monkeypatch.setattr(
        main_module,
        "save_prediction_session",
        fake_save_prediction_session,
    )

    return saved


def test_v1_sparse_assessment_abstains_and_preserves_ownership(
    mock_prediction_save,
):
    response = finish_followups(
        client,
        {
            "age": 25,
            "sex": "M",
            "text": "I have fever na kikohozi",
            "confirmed_codes": [
                "fever",
                "cough",
            ],
        },
    )

    assert response.status_code == 200

    data = response.json()

    # Intentional contract: V1 cannot distinguish unknown from absent evidence.
    assert data["status"] == "assessment_uncertain"
    assert data["model_version"] == "1.0"
    assert data["has_red_flag"] is False
    assert data["predictions"] == []
    assert data["uncertain"] is True
    assert data["decision"]["reasons"] == ["legacy_model_requires_reassessment"]
    assert "prediction_id" in data

    assert (
        mock_prediction_save["user_id"]
        == TEST_USER_ID
    )

    assert (
        mock_prediction_save["model_version_id"]
        is not None
    )

    # Enriched prediction fields are checked on dense V2 research outputs in
    # test_v2_prediction_api_unit; this V1 path must not display a candidate.
    assert "confidence_explanation" not in data
    assert "health_guidance" in data
    assert "disclaimer" in data


def test_red_flag_blocks_prediction(
    mock_prediction_save,
):
    response = client.post(
        "/predict",
        json={
            "age": 25,
            "sex": "M",
            "text": "I am coughing up blood",
            "confirmed_codes": [
                "coughing_blood",
            ],
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "urgent_review"
    assert data["has_red_flag"] is True
    assert data["predictions"] == []
    assert "prediction_id" in data
    assert "health_guidance" in data
    assert "disclaimer" in data

    assert (
        mock_prediction_save["user_id"]
        == TEST_USER_ID
    )

    assert (
        mock_prediction_save["model_version_id"]
        is None
    )


def test_invalid_age():
    response = client.post(
        "/predict",
        json={
            "age": 150,
            "sex": "M",
            "text": "I have fever",
            "confirmed_codes": [
                "fever",
            ],
        },
    )

    assert response.status_code == 422


def test_invalid_sex():
    response = client.post(
        "/predict",
        json={
            "age": 25,
            "sex": "X",
            "text": "I have fever",
            "confirmed_codes": [
                "fever",
            ],
        },
    )

    assert response.status_code == 422


def test_invalid_confirmed_symptom():
    response = client.post(
        "/predict",
        json={
            "age": 25,
            "sex": "M",
            "text": "I have fever",
            "confirmed_codes": [
                "skin_rash",
            ],
        },
    )

    assert response.status_code == 400

    assert (
        "skin_rash"
        in response.json()["detail"]
    )


def test_no_confirmed_model_feature_returns_clarification():
    response = client.post(
        "/predict",
        json={
            "age": 25,
            "sex": "M",
            "text": "I have fever",
            "confirmed_codes": [],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "insufficient_evidence"
    assert data["predictions"] == [] and data["primary_prediction"] is None
    assert data["decision"]["status"] == "insufficient_information"

def test_prediction_requires_authentication():
    app.dependency_overrides.pop(
        main_module.get_current_user,
        None,
    )

    response = client.post(
        "/predict",
        json={
            "age": 25,
            "sex": "M",
            "text": "I have fever",
            "confirmed_codes": [
                "fever",
            ],
        },
    )

    assert response.status_code == 401

    assert (
        response.json()["detail"]
        == "Authentication required."
    )
