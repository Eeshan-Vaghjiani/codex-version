
"""Tests for V2 model loading and backward compatibility."""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.ml import model_loader


class TestV2ModelLoader(unittest.TestCase):

    def test_v1_remains_available(self):
        bundle = model_loader.load_model_bundle()

        self.assertEqual(len(bundle["features"]), 198)
        self.assertEqual(len(bundle["classes"]), 21)
        self.assertEqual(
            bundle["metadata"]["model_version"],
            "1.0",
        )

    def test_v2_loads_correctly(self):
        bundle = model_loader.load_v2_model_bundle()

        self.assertEqual(len(bundle["features"]), 66)
        self.assertEqual(
            len(bundle["symptom_features"]),
            32,
        )
        self.assertEqual(len(bundle["classes"]), 23)
        self.assertEqual(
            bundle["model_version"],
            "v2_23class_prototype",
        )

    def test_v2_feature_order(self):
        bundle = model_loader.load_v2_model_bundle()

        self.assertEqual(
            list(bundle["model"].feature_names_in_),
            bundle["features"],
        )

    def test_v1_application_imports_unchanged(self):
        self.assertEqual(
            model_loader.model.n_features_in_,
            198,
        )
        self.assertEqual(
            len(model_loader.model_features),
            198,
        )

    def test_missing_v2_artifact(self):
        missing_path = Path(
            "nonexistent_v2_model_artifact.joblib"
        )

        with patch.object(
            model_loader,
            "V2_MODEL_PATH",
            missing_path,
        ):
            with self.assertRaises(FileNotFoundError):
                model_loader.load_v2_model_bundle()

    def test_rejects_invalid_v2_schema(self):
        schema = json.loads(
            model_loader.V2_SCHEMA_PATH.read_text(
                encoding="utf-8"
            )
        )

        schema["feature_names"] = (
            schema["feature_names"][:-1]
        )

        with tempfile.TemporaryDirectory() as directory:
            temporary_schema = (
                Path(directory) / "bad_schema.json"
            )

            temporary_schema.write_text(
                json.dumps(schema),
                encoding="utf-8",
            )

            with patch.object(
                model_loader,
                "V2_SCHEMA_PATH",
                temporary_schema,
            ):
                with self.assertRaises(ValueError):
                    model_loader.load_v2_model_bundle()

    def test_rejects_incorrect_class_count(self):
        schema = json.loads(
            model_loader.V2_SCHEMA_PATH.read_text(
                encoding="utf-8"
            )
        )

        fake_model = SimpleNamespace(
            n_features_in_=66,
            feature_names_in_=schema["feature_names"],
            classes_=["Only one condition"],
            predict_proba=lambda X: None,
        )

        with patch(
            "app.ml.model_loader.joblib.load",
            return_value=fake_model,
        ):
            with self.assertRaises(ValueError):
                model_loader.load_v2_model_bundle()

    def test_rejects_incorrect_model_feature_order(self):
        schema = json.loads(
            model_loader.V2_SCHEMA_PATH.read_text(
                encoding="utf-8"
            )
        )

        wrong_order = list(schema["feature_names"])
        wrong_order[2], wrong_order[3] = (
            wrong_order[3],
            wrong_order[2],
        )

        fake_model = SimpleNamespace(
            n_features_in_=66,
            feature_names_in_=wrong_order,
            classes_=[
                f"Condition {index}"
                for index in range(23)
            ],
            predict_proba=lambda X: None,
        )

        with patch(
            "app.ml.model_loader.joblib.load",
            return_value=fake_model,
        ):
            with self.assertRaises(ValueError):
                model_loader.load_v2_model_bundle()


if __name__ == "__main__":
    unittest.main()
