"""
End-to-end test against the real test database.

Nothing is mocked here: the request goes through validation,
authentication, the NLP catalogue, the model and the database.
"""

import uuid

from fastapi.testclient import TestClient

from app.main import app
from tests.assessment_helpers import finish_followups


client = TestClient(app)

PASSWORD = "TestPassword123!"


def register_and_login(email):
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
        },
    )

    assert response.status_code == 201
    assert response.json()["role"] == "patient"

    response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": PASSWORD,
        },
    )

    assert response.status_code == 200

    return {
        "Authorization": (
            f"Bearer {response.json()['access_token']}"
        )
    }


def test_register_login_predict_history_feedback():
    patient = register_and_login(
        f"patient-{uuid.uuid4().hex}@example.com"
    )

    other_patient = register_and_login(
        f"other-{uuid.uuid4().hex}@example.com"
    )

    # Symptom mapping uses the seeded database catalogue.
    response = client.post(
        "/nlp/map",
        json={
            "text": "I have fever na kikohozi"
        },
    )

    assert response.status_code == 200

    codes = [
        symptom["code"]
        for symptom
        in response.json()["recognised_symptoms"]
    ]

    assert set(codes) == {"fever", "cough"}

    # Prediction is stored for the logged-in patient.
    response = finish_followups(
        client,
        headers=patient,
        payload={
            "age": 25,
            "sex": "M",
            "text": "I have fever na kikohozi",
            "confirmed_codes": codes,
        },
    )

    assert response.status_code == 200

    prediction = response.json()

    assert prediction["status"] == "assessment_uncertain"
    assert prediction["decision"]["reasons"] == ["legacy_model_requires_reassessment"]
    assert prediction["model_version"] == "1.0"
    assert prediction["predictions"] == []
    assert prediction["uncertain"] is True
    assert prediction["assessment_context"]["follow_up_answers"]

    prediction_id = prediction["prediction_id"]

    # The patient sees the record in their history.
    response = client.get(
        "/history",
        headers=patient,
    )

    assert response.status_code == 200
    assert response.json()["count"] == 1

    assert (
        response.json()["history"][0]["prediction_id"]
        == prediction_id
    )

    response = client.get(
        f"/history/{prediction_id}",
        headers=patient,
    )

    assert response.status_code == 200

    # Another patient cannot see it or leave feedback on it.
    response = client.get(
        "/history",
        headers=other_patient,
    )

    assert response.json()["count"] == 0

    response = client.get(
        f"/history/{prediction_id}",
        headers=other_patient,
    )

    assert response.status_code == 404

    feedback = {
        "prediction_id": prediction_id,
        "was_helpful": True,
        "comment": "The information was useful.",
    }

    response = client.post(
        "/feedback",
        headers=other_patient,
        json=feedback,
    )

    assert response.status_code == 404

    response = client.post(
        "/feedback",
        json=feedback,
    )

    assert response.status_code == 401

    # The owner can leave feedback exactly once.
    response = client.post(
        "/feedback",
        headers=patient,
        json=feedback,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "feedback_saved"

    response = client.post(
        "/feedback",
        headers=patient,
        json=feedback,
    )

    assert response.status_code == 400

    assert (
        "Feedback has already been submitted"
        in response.json()["detail"]
    )


def test_login_with_short_wrong_password_returns_401():
    response = client.post(
        "/auth/login",
        json={
            "email": "nobody@example.com",
            "password": "short",
        },
    )

    assert response.status_code == 401

    assert (
        response.json()["detail"]
        == "Invalid email or password."
    )


def test_database_status_reports_real_dialect():
    response = client.get("/database/status")

    assert response.status_code == 200
    assert response.json()["database"] == "postgresql"
