import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app


client = TestClient(app)

ADMIN_ID = uuid.uuid4()
PATIENT_ID = uuid.uuid4()


@pytest.fixture(autouse=True)
def override_database_dependency():
    def fake_get_db():
        yield object()

    app.dependency_overrides[
        main_module.get_db
    ] = fake_get_db

    yield

    app.dependency_overrides.clear()


def make_admin():
    return SimpleNamespace(
        id=ADMIN_ID,
        email="admin@example.com",
        role="admin",
    )


def make_patient():
    return SimpleNamespace(
        id=PATIENT_ID,
        email="patient@example.com",
        role="patient",
    )


def make_prediction(
    *,
    user_id=PATIENT_ID,
    prediction_id=None,
):
    return SimpleNamespace(
        id=prediction_id or uuid.uuid4(),
        user_id=user_id,
        age=25,
        sex="M",
        input_text="I have fever and cough",
        confirmed_codes=[
            "fever",
            "cough",
        ],
        status="prediction_complete",
        has_red_flag=False,
        predictions=[
            {
                "rank": 1,
                "condition": "Tuberculosis",
                "display_name": "Tuberculosis",
                "model_confidence_percent": 90.0,
                "description": "Test description.",
            }
        ],
        created_at=datetime.now(timezone.utc),
    )


def make_feedback():
    return SimpleNamespace(
        id=uuid.uuid4(),
        prediction_session_id=uuid.uuid4(),
        was_helpful=True,
        comment="Useful information.",
        created_at=datetime.now(timezone.utc),
    )


def test_guest_cannot_access_admin_history():
    response = client.get(
        "/admin/history"
    )

    assert response.status_code == 401

    assert (
        response.json()["detail"]
        == "Authentication required."
    )


def test_patient_cannot_access_admin_history():
    app.dependency_overrides[
        main_module.get_current_user
    ] = make_patient

    response = client.get(
        "/admin/history"
    )

    assert response.status_code == 403

    assert (
        response.json()["detail"]
        == "Administrator access required."
    )


def test_admin_can_view_all_history(
    monkeypatch,
):
    app.dependency_overrides[
        main_module.get_current_user
    ] = make_admin

    prediction_one = make_prediction()

    prediction_two = make_prediction(
        user_id=uuid.uuid4(),
    )

    monkeypatch.setattr(
        main_module,
        "list_all_prediction_sessions",
        lambda db, limit: [
            prediction_one,
            prediction_two,
        ],
    )

    response = client.get(
        "/admin/history"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["count"] == 2
    assert len(data["history"]) == 2

    assert (
        data["history"][0]["prediction_id"]
        == str(prediction_one.id)
    )

    assert (
        data["history"][1]["prediction_id"]
        == str(prediction_two.id)
    )


def test_admin_can_view_any_prediction(
    monkeypatch,
):
    app.dependency_overrides[
        main_module.get_current_user
    ] = make_admin

    prediction_id = uuid.uuid4()

    prediction = make_prediction(
        prediction_id=prediction_id,
        user_id=uuid.uuid4(),
    )

    monkeypatch.setattr(
        main_module,
        "get_any_prediction_session",
        lambda db, prediction_id: prediction,
    )

    response = client.get(
        f"/admin/history/{prediction_id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert (
        data["prediction_id"]
        == str(prediction_id)
    )

    assert (
        data["user_id"]
        == str(prediction.user_id)
    )


def test_patient_cannot_access_admin_history_item():
    app.dependency_overrides[
        main_module.get_current_user
    ] = make_patient

    response = client.get(
        f"/admin/history/{uuid.uuid4()}"
    )

    assert response.status_code == 403

    assert (
        response.json()["detail"]
        == "Administrator access required."
    )


def test_admin_missing_prediction_returns_404(
    monkeypatch,
):
    app.dependency_overrides[
        main_module.get_current_user
    ] = make_admin

    monkeypatch.setattr(
        main_module,
        "get_any_prediction_session",
        lambda db, prediction_id: None,
    )

    response = client.get(
        f"/admin/history/{uuid.uuid4()}"
    )

    assert response.status_code == 404

    assert (
        response.json()["detail"]
        == "Prediction session was not found."
    )


def test_admin_can_view_all_feedback(
    monkeypatch,
):
    app.dependency_overrides[
        main_module.get_current_user
    ] = make_admin

    feedback_one = make_feedback()
    feedback_two = make_feedback()

    monkeypatch.setattr(
        main_module,
        "list_all_feedback",
        lambda db, limit: [
            feedback_one,
            feedback_two,
        ],
    )

    response = client.get(
        "/admin/feedback"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["count"] == 2
    assert len(data["feedback"]) == 2

    assert (
        data["feedback"][0]["feedback_id"]
        == str(feedback_one.id)
    )


def test_patient_cannot_access_admin_feedback():
    app.dependency_overrides[
        main_module.get_current_user
    ] = make_patient

    response = client.get(
        "/admin/feedback"
    )

    assert response.status_code == 403

    assert (
        response.json()["detail"]
        == "Administrator access required."
    )


def test_guest_cannot_access_admin_feedback():
    response = client.get(
        "/admin/feedback"
    )

    assert response.status_code == 401

    assert (
        response.json()["detail"]
        == "Authentication required."
    )