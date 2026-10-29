
import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

import app.main as main

from app.services.v2_prediction import predict_v2_single


class TestPredictionApiRouting(unittest.TestCase):

    def setUp(self):
        self.saved = {}
        self.model_version = SimpleNamespace(
            id=uuid.uuid4(),
            version="v2_23class_prototype",
        )
        self.confirmation = {
            "confirmed_codes": ["cough", "fever", "runny_blocked_nose"],
            "model_features": ["E_201", "E_91", "E_181"],
            "has_red_flag": False,
            "red_flag_symptoms": [],
            # Complete enough context to exercise routing without a database
            # follow-up lookup. Dedicated assessment tests validate replay.
            "recognised_symptoms": [
                {"code": "cough", "features": ["E_201"], "status": "present",
                 "duration_text": "two days", "duration_min_days": 2, "duration_max_days": 2},
                {"code": "fever", "features": ["E_91"], "status": "present"},
                {"code": "runny_blocked_nose", "features": ["E_181"], "status": "present"},
                {"code": "shortness_of_breath", "features": ["E_66"], "status": "absent"},
            ],
        }

        main.app.dependency_overrides[main.get_db] = (
            lambda: object()
        )
        main.app.dependency_overrides[
            main.get_current_user
        ] = lambda: SimpleNamespace(
            id=uuid.uuid4(),
            role="patient",
        )

        self.patchers = [
            patch.object(
                main,
                "confirm_symptoms",
                return_value=self.confirmation,
            ),
            patch.object(
                main,
                "get_active_model_version",
                return_value=self.model_version,
            ),
            patch.object(
                main,
                "save_prediction_session",
                side_effect=self.save_session,
            ),
            patch.object(
                main,
                "predict_v2_single",
                return_value={
                    "model_version": "v2_23class_prototype",
                    "feature_count": 66,
                    "predictions": [{
                        "rank": 1,
                        "condition": "Pneumonia",
                        "probability": 0.65,
                        "confidence_percent": 65.0,
                    }],
                    "uncertain": False,
                    "uncertainty_reasons": [],
                    "uncertainty_message": (
                        "Not a medical diagnosis."
                    ),
                    "score_note": (
                        "Uncalibrated model score."
                    ),
                },
            ),
            patch.object(
                main,
                "predict_top_conditions",
                return_value={
                    "feature_count": 198,
                    "predictions": [{
                        "rank": 1,
                        "condition": "Pneumonia",
                        "probability": 0.65,
                        "confidence_percent": 65.0,
                    }],
                },
            ),
        ]

        self.mocks = [
            patcher.start()
            for patcher in self.patchers
        ]

        self.client = TestClient(main.app)

    def tearDown(self):
        self.client.close()
        for patcher in reversed(self.patchers):
            patcher.stop()
        main.app.dependency_overrides.clear()

    def save_session(self, db, **kwargs):
        self.saved.update(kwargs)
        return SimpleNamespace(id=uuid.uuid4())

    def request_prediction(self):
        return self.client.post(
            "/predict",
            json={
                "age": 25,
                "sex": "M",
                "text": "I have a cough, fever and runny nose for two days but no difficulty breathing",
                "confirmed_codes": self.confirmation["confirmed_codes"],
            },
        )

    def assert_legacy_deferral(self, expected_version):
        response = self.request_prediction()
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["model_version"], expected_version)
        self.assertEqual(data["status"], "assessment_uncertain")
        self.assertEqual(data["predictions"], [])
        self.assertIsNone(data["primary_prediction"])
        self.assertEqual(data["decision"]["reasons"], ["legacy_model_requires_reassessment"])
        self.assertTrue(data["uncertain"])
        self.assertFalse(data["clinical_validation"])
        self.assertNotIn("score_note", data)
        self.assertEqual(self.saved["model_version_id"], self.model_version.id)
        self.assertEqual(self.saved["predictions"], [])
        self.mocks[3].assert_not_called()
        self.mocks[4].assert_not_called()

    def test_v2_defers_without_a_current_patient_policy(self):
        self.assert_legacy_deferral("v2_23class_prototype")

    def test_v1_abstains_without_falling_back_to_v2(self):
        self.model_version.version = "1.0"
        self.assert_legacy_deferral("1.0")

    def test_unsupported_only_abstains_without_model_call(self):
        self.confirmation["model_features"] = ["E_55_@_V_101"]
        self.confirmation["confirmed_codes"] = ["cough"]
        self.confirmation["recognised_symptoms"][0]["features"] = ["E_55_@_V_101"]
        self.confirmation["recognised_symptoms"][1]["status"] = "absent"
        self.confirmation["recognised_symptoms"][2]["status"] = "absent"
        self.assert_legacy_deferral("v2_23class_prototype")

    def test_red_flag_bypasses_model(self):
        self.confirmation["has_red_flag"] = True
        self.confirmation["red_flag_symptoms"] = [{
            "code": "coughing_blood"
        }]

        response = self.request_prediction()

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["status"], "urgent_review")
        self.assertEqual(data["predictions"], [])
        self.assertIsNone(
            self.saved["model_version_id"]
        )
        self.mocks[3].assert_not_called()
        self.mocks[4].assert_not_called()

    def test_real_v2_remains_available_for_internal_comparison(self):
        result = predict_v2_single(
            age=25, sex="M", symptom_features=["E_201", "E_91", "E_181"],
            explicitly_absent_features=["E_66"])
        self.assertEqual(result["model_version"], "v2_23class_prototype")
        self.assertEqual(result["feature_count"], 66)
        self.assertEqual(len(result["predictions"]), 3)
        self.assertEqual(result["predictions"][0]["rank"], 1)
        self.assertIn("score_note", result)


if __name__ == "__main__":
    unittest.main()
