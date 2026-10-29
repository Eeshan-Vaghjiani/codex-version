
import unittest
from unittest.mock import MagicMock

from app.db.models import ModelVersion
from app.db.register_v2_model_version import (
    build_v2_registration_values,
    register_v2_model_version,
)


class TestV2ModelRegistration(unittest.TestCase):

    def test_registration_values(self):
        values = build_v2_registration_values()

        self.assertEqual(
            values["version"],
            "v2_23class_prototype",
        )
        self.assertEqual(values["feature_count"], 66)
        self.assertEqual(values["class_count"], 23)
        self.assertEqual(values["training_samples"], 41061)
        self.assertEqual(values["validation_samples"], 55808)
        self.assertEqual(values["test_samples"], 0)

        self.assertFalse(
            values["test_metrics"]["evaluated"]
        )

    def test_new_v2_record_is_inactive(self):
        db = MagicMock()
        db.scalar.return_value = None

        result = register_v2_model_version(db)

        self.assertIsInstance(result, ModelVersion)
        self.assertEqual(
            result.version,
            "v2_23class_prototype",
        )
        self.assertFalse(result.is_active)

        db.add.assert_called_once_with(result)
        db.flush.assert_called_once()
        db.commit.assert_not_called()

    def test_existing_inactive_v2_stays_inactive(self):
        values = build_v2_registration_values()

        existing = ModelVersion(
            **values,
            is_active=False,
        )

        db = MagicMock()
        db.scalar.return_value = existing

        result = register_v2_model_version(db)

        self.assertIs(result, existing)
        self.assertFalse(result.is_active)

        db.add.assert_not_called()
        db.flush.assert_called_once()
        db.commit.assert_not_called()

    def test_existing_active_status_is_preserved(self):
        values = build_v2_registration_values()

        existing = ModelVersion(
            **values,
            is_active=True,
        )

        db = MagicMock()
        db.scalar.return_value = existing

        result = register_v2_model_version(db)

        self.assertIs(result, existing)
        self.assertTrue(result.is_active)

        db.add.assert_not_called()
        db.flush.assert_called_once()
        db.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
