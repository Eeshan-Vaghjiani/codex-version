
import unittest

from app.services.v2_prediction import (
    build_v2_feature_frame,
    partition_v2_symptom_features,
    predict_v2_single,
)


class TestV2PredictionService(unittest.TestCase):

    def test_feature_count_and_present_symptom(self):
        frame = build_v2_feature_frame(
            age=25,
            sex="M",
            symptom_features=["E_91"],
        )

        self.assertEqual(frame.shape, (1, 66))
        self.assertEqual(frame.iloc[0]["AGE"], 25.0)
        self.assertEqual(frame.iloc[0]["SEX_M"], 1.0)
        self.assertEqual(
            frame.iloc[0]["E_91__present"],
            1.0,
        )

    def test_unknown_symptom_is_not_absent(self):
        frame = build_v2_feature_frame(
            age=25,
            sex="F",
            symptom_features=["E_91"],
        )

        self.assertEqual(
            frame.iloc[0]["E_91__absent"],
            0.0,
        )
        self.assertEqual(
            frame.iloc[0]["E_201__present"],
            0.0,
        )
        self.assertEqual(
            frame.iloc[0]["E_201__absent"],
            0.0,
        )

    def test_explicit_absence(self):
        frame = build_v2_feature_frame(
            age=25,
            sex="F",
            symptom_features=["E_91"],
            explicitly_absent_features=["E_201"],
        )

        self.assertEqual(
            frame.iloc[0]["E_201__absent"],
            1.0,
        )

    def test_conflicting_evidence_rejected(self):
        with self.assertRaises(ValueError):
            build_v2_feature_frame(
                age=25,
                sex="M",
                symptom_features=["E_91"],
                explicitly_absent_features=["E_91"],
            )

    def test_unsupported_features_partitioned(self):
        result = partition_v2_symptom_features([
            "E_91",
            "E_55_@_V_101",
            "E_55_@_V_89",
        ])

        self.assertEqual(
            result["supported_features"],
            ["E_91"],
        )
        self.assertEqual(
            result["unsupported_features"],
            ["E_55_@_V_101", "E_55_@_V_89"],
        )

    def test_unsupported_only_cannot_predict(self):
        result = partition_v2_symptom_features([
            "E_55_@_V_101",
        ])

        self.assertFalse(
            result["has_supported_features"]
        )

    def test_no_confirmed_symptoms_rejected(self):
        with self.assertRaises(ValueError):
            predict_v2_single(
                age=25,
                sex="M",
                symptom_features=[],
            )

    def test_ranked_research_candidates_preserve_uncertainty(self):
        result = predict_v2_single(
            age=25,
            sex="M",
            symptom_features=["E_91", "E_201"],
        )

        self.assertEqual(
            result["model_version"],
            "v2_23class_prototype",
        )
        self.assertEqual(
            result["feature_count"],
            66,
        )
        self.assertEqual(
            len(result["predictions"]),
            3,
        )
        self.assertEqual(
            result["predictions"][0]["rank"],
            1,
        )
        self.assertIsInstance(
            result["uncertain"],
            bool,
        )
        self.assertTrue(result["uncertain"])
        self.assertIn("research_model_not_clinically_validated", result["uncertainty_reasons"])
        self.assertEqual([p["rank"] for p in result["predictions"]], [1, 2, 3])
        scores = [p["probability"] for p in result["predictions"]]
        self.assertEqual(scores, sorted(scores, reverse=True))
        for prediction in result["predictions"]:
            self.assertAlmostEqual(prediction["confidence_percent"], prediction["probability"] * 100, delta=.006)
        self.assertIn(
            "uncertainty_message",
            result,
        )
        self.assertIn(
            "score_note",
            result,
        )


if __name__ == "__main__":
    unittest.main()
