"""Verify labels and feature order at artifact loading, before serving."""
import unittest
import os
import subprocess
import sys
from unittest.mock import patch

from app.ml import model_loader


class TestModelBundleIntegrity(unittest.TestCase):
    def test_corrupt_artifact_cannot_disable_independent_emergency_route(self):
        # Fresh import is essential: patching an already imported bundle would
        # not exercise the startup failure that originally disabled the API.
        code = '''
from unittest.mock import patch
from types import SimpleNamespace
import uuid
with patch("joblib.load", side_effect=ValueError("Corrupt test artifact")):
    from app.ml import model_loader
    assert model_loader.model is None
    assert "ValueError" in model_loader.model_readiness_error
    import app.main as main
    from fastapi.testclient import TestClient
    main.app.dependency_overrides[main.get_db] = lambda: object()
    main.app.dependency_overrides[main.get_current_user] = lambda: SimpleNamespace(id=uuid.uuid4(), role="patient")
    client = TestClient(main.app, raise_server_exceptions=False)
    assert client.get("/health").status_code == 200
    mapped = client.post("/nlp/map", json={"text":"I am struggling to breathe"})
    assert mapped.status_code == 200 and mapped.json()["has_red_flag"]
    urgent = client.post("/predict", json={"age":21,"sex":"M","text":"I am struggling to breathe","confirmed_codes":[]})
    assert urgent.status_code == 200 and urgent.json()["status"] == "urgent_review"
    assert urgent.json()["predictions"] == []
    client.close()
'''
        # No lifespan context: this checks request safety independently from
        # the unrelated database migration/readiness check.
        result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                                env=os.environ.copy(), timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_v2_metadata_reports_actual_feature_support(self):
        bundle = model_loader.load_v2_model_bundle()
        self.assertEqual(bundle["model_status"], "research_prototype")
        self.assertFalse(bundle["clinical_validation"])
        self.assertEqual(bundle["learned_absence_features"], [])
        self.assertFalse(bundle["duration_features_supported"])

    def test_v1_rejects_reordered_class_file(self):
        original = model_loader._load_json
        def read(path):
            values = original(path)
            return list(reversed(values)) if path == model_loader.CLASSES_PATH else values
        with patch.object(model_loader, "_load_json", side_effect=read):
            with self.assertRaisesRegex(ValueError, "class order"):
                model_loader.load_model_bundle()

    def test_v1_rejects_reordered_feature_file(self):
        original = model_loader._load_json
        def read(path):
            values = original(path)
            return list(reversed(values)) if path == model_loader.FEATURES_PATH else values
        with patch.object(model_loader, "_load_json", side_effect=read):
            with self.assertRaisesRegex(ValueError, "feature order"):
                model_loader.load_model_bundle()

    def test_v1_rejects_duplicate_feature_names(self):
        original = model_loader._load_json
        def read(path):
            values = original(path)
            if path == model_loader.FEATURES_PATH:
                values[1] = values[0]
            return values
        with patch.object(model_loader, "_load_json", side_effect=read):
            with self.assertRaisesRegex(ValueError, "unique names"):
                model_loader.load_model_bundle()


if __name__ == "__main__":
    unittest.main()
