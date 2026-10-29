
"""V2 API, PostgreSQL history and red-flag integration test.

Runs only through pytest's isolated test database schema.
Never run this directly against the application database.
"""

import uuid
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

import app.main as main_module
from app.core.database import SessionLocal
from app.db.activate_v2_model_version import (
    activate_v2_model_version,
)
from app.db.models import PredictionSession, User
from app.db.register_v2_model_version import (
    register_v2_model_version,
)
from app.main import app


def test_v2_prediction_history_and_red_flag():
    # The pytest test schema is prepared by conftest.py.
    # Register and activate V2 only inside that schema.
    with SessionLocal() as db:
        user = User(
            email=f"v2-test-{uuid.uuid4().hex}@example.com",
            password_hash="test-only-not-a-real-password",
            role="patient",
        )

        db.add(user)
        db.flush()

        user_id = user.id

        register_v2_model_version(db)
        v2 = activate_v2_model_version(db)

        v2_id = v2.id

        db.commit()

    # Use the real database dependency and real prediction
    # service. Override only authentication with the test user.
    app.dependency_overrides[
        main_module.get_current_user
    ] = lambda: SimpleNamespace(
        id=user_id,
        role="patient",
    )

    try:
        with TestClient(app) as client:

            # ------------------------------------------
            # 1. Normal V2 prediction
            # ------------------------------------------
            response = client.post(
                "/predict",
                json={
                    "age": 25,
                    "sex": "M",
                    "text": "I have fever na kikohozi and a runny nose for two days but no difficulty breathing",
                    "confirmed_codes": [
                        "fever",
                        "cough",
                        "runny_blocked_nose",
                    ],
                },
            )

            assert response.status_code == 200, (
                response.text
            )

            result = response.json()

            assert result["status"] == "assessment_uncertain"
            assert result["model_version"] == (
                "v2_23class_prototype"
            )
            assert result["primary_prediction"] is None
            assert result["predictions"] == []
            assert result["decision"]["reasons"] == ["legacy_model_requires_reassessment"]
            assert result["uncertain"] is True
            assert result["clinical_validation"] is False

            prediction_id = uuid.UUID(
                result["prediction_id"]
            )

            # ------------------------------------------
            # 2. Verify the saved database record
            # ------------------------------------------
            with SessionLocal() as db:
                saved = db.get(
                    PredictionSession,
                    prediction_id,
                )

                assert saved is not None
                assert saved.user_id == user_id
                assert saved.model_version_id == v2_id
                assert saved.status == (
                    "assessment_uncertain"
                )
                assert saved.predictions == []
                assert saved.assessment_context["symptom_states"]["cough"] == "present"
                assert saved.has_red_flag is False

            # ------------------------------------------
            # 3. Verify patient history endpoint
            # ------------------------------------------
            history_response = client.get("/history")

            assert history_response.status_code == 200

            history = history_response.json()["history"]

            matching = [
                item
                for item in history
                if item["prediction_id"] == str(
                    prediction_id
                )
            ]

            assert len(matching) == 1
            assert matching[0]["predictions"] == []
            assert matching[0]["uncertain"] is True
            assert matching[0]["clinical_validation"] is False
            assert matching[0]["model_version"] == result["model_version"]
            assert "score_note" not in matching[0]
            detail_response = client.get(f"/history/{prediction_id}")
            assert detail_response.status_code == 200
            detail = detail_response.json()
            for key in ("predictions", "assessment_context", "uncertain", "decision", "model_version", "health_guidance", "disclaimer"):
                assert detail[key] == result[key]
            assert "score_note" not in detail


            # ------------------------------------------
            # 4. Red-flag case must bypass V2
            # ------------------------------------------
            with patch.object(
                main_module,
                "predict_v2_single",
                side_effect=AssertionError(
                    "V2 must not run for red flags."
                ),
            ) as mocked_predict:

                urgent_response = client.post(
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

                assert urgent_response.status_code == 200, (
                    urgent_response.text
                )

                mocked_predict.assert_not_called()

            urgent = urgent_response.json()

            assert urgent["status"] == "urgent_review"
            assert urgent["has_red_flag"] is True
            assert urgent["predictions"] == []

            urgent_id = uuid.UUID(
                urgent["prediction_id"]
            )

            # ------------------------------------------
            # 5. Verify urgent session in database
            # ------------------------------------------
            with SessionLocal() as db:
                saved_urgent = db.get(
                    PredictionSession,
                    urgent_id,
                )

                assert saved_urgent is not None
                assert saved_urgent.has_red_flag is True
                assert saved_urgent.model_version_id is None
                assert saved_urgent.predictions == []

        print(
            "\nSTEP 111 PASSED:"
            " V2 prediction, history and red flags."
        )

    finally:
        app.dependency_overrides.pop(
            main_module.get_current_user,
            None,
        )
