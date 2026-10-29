
"""Tests for the V2 backend integration adapter."""

import unittest
from unittest.mock import patch

from inference.backend_adapter import (
    build_v2_backend_features,
    load_backend_v2_schema,
    predict_v2_from_backend,
)


class TestBackendAdapter(unittest.TestCase):

    def test_schema(self):
        symptom_features, feature_names = load_backend_v2_schema()

        self.assertEqual(len(symptom_features), 32)
        self.assertEqual(len(feature_names), 66)
        self.assertEqual(len(set(feature_names)), 66)

    def test_confirmed_symptoms(self):
        features = build_v2_backend_features(
            age=25,
            sex="M",
            confirmed_features=["E_91", "E_201"],
        )

        self.assertEqual(len(features), 66)
        self.assertEqual(features["AGE"], 25.0)
        self.assertEqual(features["SEX_M"], 1.0)
        self.assertEqual(features["E_91__present"], 1.0)
        self.assertEqual(features["E_201__present"], 1.0)
        self.assertEqual(features["E_91__absent"], 0.0)

    def test_unknown_symptoms_remain_unknown(self):
        features = build_v2_backend_features(
            age=25,
            sex="F",
            confirmed_features=["E_91"],
        )

        self.assertEqual(features["SEX_M"], 0.0)
        self.assertEqual(features["E_201__present"], 0.0)
        self.assertEqual(features["E_201__absent"], 0.0)

    def test_explicit_absence(self):
        features = build_v2_backend_features(
            age=25,
            sex="M",
            confirmed_features=["E_91"],
            explicitly_absent_features=["E_201"],
        )

        self.assertEqual(features["E_91__present"], 1.0)
        self.assertEqual(features["E_201__present"], 0.0)
        self.assertEqual(features["E_201__absent"], 1.0)

    def test_conflicting_symptom_states(self):
        with self.assertRaises(ValueError):
            build_v2_backend_features(
                age=25,
                sex="M",
                confirmed_features=["E_91"],
                explicitly_absent_features=["E_91"],
            )

    def test_unsupported_symptom(self):
        with self.assertRaises(ValueError):
            build_v2_backend_features(
                age=25,
                sex="M",
                confirmed_features=["E_999"],
            )

    def test_duplicate_symptoms(self):
        with self.assertRaises(ValueError):
            build_v2_backend_features(
                age=25,
                sex="M",
                confirmed_features=["E_91", "E_91"],
            )

    def test_invalid_age(self):
        with self.assertRaises(ValueError):
            build_v2_backend_features(
                age=150,
                sex="M",
                confirmed_features=["E_91"],
            )

    def test_invalid_sex(self):
        with self.assertRaises(ValueError):
            build_v2_backend_features(
                age=25,
                sex="X",
                confirmed_features=["E_91"],
            )

    def test_requires_confirmed_symptom(self):
        with self.assertRaises(ValueError):
            predict_v2_from_backend(
                age=25,
                sex="M",
                confirmed_features=[],
            )

    @patch("inference.backend_adapter.predict_v2")
    def test_prediction_response(self, mock_predict):
        mock_predict.return_value = {
            "predicted_condition": "Example condition",
            "confidence_score": 0.4,
            "uncertain": True,
            "uncertainty_reasons": ["low_model_score"],
            "model_version": "v2_23class_prototype",
            "message": "Not a medical diagnosis.",
        }

        result = predict_v2_from_backend(
            age=25,
            sex="M",
            confirmed_features=["E_91"],
        )

        mock_predict.assert_called_once()

        self.assertEqual(result["feature_count"], 66)
        self.assertEqual(
            result["active_symptom_features"],
            ["E_91"],
        )
        self.assertEqual(
            result["explicitly_absent_features"],
            [],
        )
        self.assertTrue(result["uncertain"])
        self.assertEqual(
            result["model_version"],
            "v2_23class_prototype",
        )


if __name__ == "__main__":
    unittest.main()
