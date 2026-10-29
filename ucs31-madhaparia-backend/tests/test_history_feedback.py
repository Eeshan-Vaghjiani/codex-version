import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app


client = TestClient(app)

TEST_USER_ID = uuid.uuid4()
OTHER_USER_ID = uuid.uuid4()


@pytest.fixture(autouse=True)
def override_database_dependency():
    def fake_get_db():
        yield object()

    app.dependency_overrides[
        main_module.get_db
    ] = fake_get_db

    yield

    app.dependency_overrides.clear()


@pytest.fixture
def authenticated_patient():
    fake_user = SimpleNamespace(
        id=TEST_USER_ID,
        email="patient@example.com",
        role="patient",
    )

    app.dependency_overrides[
        main_module.get_current_user
    ] = lambda: fake_user

    return fake_user


def make_fake_prediction(
    *,
    prediction_id=None,
    user_id=TEST_USER_ID,
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


def test_history_requires_authentication():
    response = client.get("/history")

    assert response.status_code == 401

    assert (
        response.json()["detail"]
        == "Authentication required."
    )


def test_history_item_requires_authentication():
    response = client.get(
        f"/history/{uuid.uuid4()}"
    )

    assert response.status_code == 401

    assert (
        response.json()["detail"]
        == "Authentication required."
    )


def test_patient_can_view_own_history(
    monkeypatch,
    authenticated_patient,
):
    fake_prediction = make_fake_prediction()

    captured = {}

    def fake_list_prediction_sessions(
        db,
        user_id,
        limit,
    ):
        captured["user_id"] = user_id
        captured["limit"] = limit

        return [fake_prediction]

    monkeypatch.setattr(
        main_module,
        "list_prediction_sessions",
        fake_list_prediction_sessions,
    )

    response = client.get("/history")

    assert response.status_code == 200

    data = response.json()

    assert data["count"] == 1
    assert len(data["history"]) == 1
    assert (
        data["history"][0]["prediction_id"]
        == str(fake_prediction.id)
    )

    assert (
        captured["user_id"]
        == TEST_USER_ID
    )

    assert captured["limit"] == 20


def test_patient_can_view_own_history_item(
    monkeypatch,
    authenticated_patient,
):
    prediction_id = uuid.uuid4()

    fake_prediction = make_fake_prediction(
        prediction_id=prediction_id,
    )

    captured = {}

    def fake_get_prediction_session(
        db,
        prediction_id,
        user_id,
    ):
        captured["prediction_id"] = (
            prediction_id
        )
        captured["user_id"] = user_id

        return fake_prediction

    monkeypatch.setattr(
        main_module,
        "get_prediction_session",
        fake_get_prediction_session,
    )

    response = client.get(
        f"/history/{prediction_id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert (
        data["prediction_id"]
        == str(prediction_id)
    )

    assert (
        captured["prediction_id"]
        == prediction_id
    )

    assert (
        captured["user_id"]
        == TEST_USER_ID
    )


def test_patient_cannot_view_another_users_prediction(
    monkeypatch,
    authenticated_patient,
):
    another_prediction_id = uuid.uuid4()

    def fake_get_prediction_session(
        db,
        prediction_id,
        user_id,
    ):
        assert (
            prediction_id
            == another_prediction_id
        )

        assert user_id == TEST_USER_ID

        return None

    monkeypatch.setattr(
        main_module,
        "get_prediction_session",
        fake_get_prediction_session,
    )

    response = client.get(
        f"/history/{another_prediction_id}"
    )

    assert response.status_code == 404

    assert (
        response.json()["detail"]
        == "Prediction session was not found."
    )


def test_feedback_requires_authentication():
    response = client.post(
        "/feedback",
        json={
            "prediction_id": str(
                uuid.uuid4()
            ),
            "was_helpful": True,
        },
    )

    assert response.status_code == 401

    assert (
        response.json()["detail"]
        == "Authentication required."
    )


def test_feedback_success(
    monkeypatch,
    authenticated_patient,
):
    prediction_id = uuid.uuid4()
    feedback_id = uuid.uuid4()

    fake_feedback = SimpleNamespace(
        id=feedback_id,
        prediction_session_id=prediction_id,
        was_helpful=True,
        comment="The information was useful.",
        created_at=datetime.now(timezone.utc),
    )

    monkeypatch.setattr(
        main_module,
        "save_feedback",
        lambda db,
        prediction_session_id,
        user_id,
        was_helpful,
        comment: fake_feedback,
    )

    response = client.post(
        "/feedback",
        json={
            "prediction_id": str(
                prediction_id
            ),
            "was_helpful": True,
            "comment": (
                "The information was useful."
            ),
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert (
        data["status"]
        == "feedback_saved"
    )

    assert (
        data["feedback_id"]
        == str(feedback_id)
    )

    assert (
        data["prediction_id"]
        == str(prediction_id)
    )

    assert data["was_helpful"] is True


def test_feedback_for_unknown_prediction_returns_404(
    monkeypatch,
    authenticated_patient,
):
    def fake_save_feedback(
        *args,
        **kwargs,
    ):
        raise LookupError(
            "Prediction session was not found."
        )

    monkeypatch.setattr(
        main_module,
        "save_feedback",
        fake_save_feedback,
    )

    response = client.post(
        "/feedback",
        json={
            "prediction_id": str(
                uuid.uuid4()
            ),
            "was_helpful": True,
        },
    )

    assert response.status_code == 404

    assert (
        response.json()["detail"]
        == "Prediction session was not found."
    )


def test_duplicate_feedback(
    monkeypatch,
    authenticated_patient,
):
    prediction_id = uuid.uuid4()

    def fake_save_feedback(
        *args,
        **kwargs,
    ):
        raise ValueError(
            "Feedback has already been submitted "
            "for this prediction session."
        )

    monkeypatch.setattr(
        main_module,
        "save_feedback",
        fake_save_feedback,
    )

    response = client.post(
        "/feedback",
        json={
            "prediction_id": str(
                prediction_id
            ),
            "was_helpful": True,
            "comment": "Test feedback.",
        },
    )

    assert response.status_code == 400

    assert (
        "Feedback has already been submitted"
        in response.json()["detail"]
    )


def test_feedback_comment_too_long(
    authenticated_patient,
):
    response = client.post(
        "/feedback",
        json={
            "prediction_id": str(
                uuid.uuid4()
            ),
            "was_helpful": True,
            "comment": "A" * 1001,
        },
    )

    assert response.status_code == 422