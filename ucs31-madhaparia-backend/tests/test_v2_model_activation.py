
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.db.activate_v2_model_version import (
    activate_v2_model_version,
)
from app.db.register_v2_model_version import (
    build_v2_registration_values,
)


class TestV2ModelActivation(unittest.TestCase):

    def setUp(self):
        values = build_v2_registration_values()

        self.v1 = SimpleNamespace(
            model_name="Random Forest",
            version="1.0",
            artifact_filename="respiratory_random_forest_v1.joblib",
            feature_count=198,
            class_count=21,
            is_active=True,
        )

        self.v2 = SimpleNamespace(
            model_name=values["model_name"],
            version=values["version"],
            artifact_filename=values["artifact_filename"],
            feature_count=66,
            class_count=23,
            is_active=False,
        )

        self.db = MagicMock()
        self.db.scalars.return_value.all.return_value = [
            self.v1,
            self.v2,
        ]

    def test_activation_switches_v1_to_v2(self):
        result = activate_v2_model_version(self.db)

        self.assertIs(result, self.v2)
        self.assertFalse(self.v1.is_active)
        self.assertTrue(self.v2.is_active)

        self.db.flush.assert_called_once()
        self.db.commit.assert_not_called()

    def test_activation_fails_when_v2_missing(self):
        self.db.scalars.return_value.all.return_value = [
            self.v1,
        ]

        with self.assertRaisesRegex(
            ValueError,
            "registered exactly once",
        ):
            activate_v2_model_version(self.db)

        self.assertTrue(self.v1.is_active)
        self.db.flush.assert_not_called()
        self.db.commit.assert_not_called()

    def test_activation_fails_on_metadata_mismatch(self):
        self.v2.feature_count = 198

        with self.assertRaisesRegex(
            ValueError,
            "does not match",
        ):
            activate_v2_model_version(self.db)

        self.assertTrue(self.v1.is_active)
        self.assertFalse(self.v2.is_active)
        self.db.flush.assert_not_called()
        self.db.commit.assert_not_called()

    def test_activation_fails_with_multiple_active_models(self):
        self.v2.is_active = True

        with self.assertRaisesRegex(
            ValueError,
            "Multiple active",
        ):
            activate_v2_model_version(self.db)

        self.assertTrue(self.v1.is_active)
        self.assertTrue(self.v2.is_active)
        self.db.flush.assert_not_called()
        self.db.commit.assert_not_called()

    def test_activation_does_not_commit(self):
        activate_v2_model_version(self.db)

        self.db.flush.assert_called_once()
        self.db.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
