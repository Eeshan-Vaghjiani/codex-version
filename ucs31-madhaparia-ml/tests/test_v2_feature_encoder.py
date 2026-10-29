
import unittest

from scripts.v2_feature_encoder import (
    load_v2_symptom_features,
    get_v2_feature_names,
    encode_v2_record,
)


class TestV2FeatureEncoder(unittest.TestCase):

    def setUp(self):
        self.features = ["E_91", "E_201", "E_94"]

        self.record = {
            "age": 24,
            "sex": "F",
            "present": ["E_91"],
            "absent": [],
            "unknown": ["E_201", "E_94"],
        }

    def test_full_feature_schema(self):
        features = load_v2_symptom_features()
        names = get_v2_feature_names(features)

        self.assertEqual(len(features), 32)
        self.assertEqual(len(names), 66)
        self.assertEqual(len(names), len(set(names)))

    def test_present_and_unknown(self):
        vector = encode_v2_record(
            self.record, self.features
        )

        self.assertEqual(
            vector,
            [24.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        )

    def test_explicit_absence(self):
        record = {
            **self.record,
            "absent": ["E_201"],
            "unknown": ["E_94"],
        }

        vector = encode_v2_record(record, self.features)

        self.assertEqual(
            vector,
            [24.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0]
        )

    def test_rejects_conflicting_states(self):
        record = {
            **self.record,
            "absent": ["E_91"],
        }

        with self.assertRaises(ValueError):
            encode_v2_record(record, self.features)

    def test_rejects_unsupported_symptoms(self):
        record = {
            **self.record,
            "unknown": ["E_201", "E_94", "E_999"],
        }

        with self.assertRaises(ValueError):
            encode_v2_record(record, self.features)

    def test_rejects_duplicate_codes(self):
        record = {
            **self.record,
            "present": ["E_91", "E_91"],
        }

        with self.assertRaises(ValueError):
            encode_v2_record(record, self.features)

    def test_rejects_invalid_age(self):
        record = {**self.record, "age": 150}

        with self.assertRaises(ValueError):
            encode_v2_record(record, self.features)

    def test_rejects_invalid_sex(self):
        record = {**self.record, "sex": "X"}

        with self.assertRaises(ValueError):
            encode_v2_record(record, self.features)


if __name__ == "__main__":
    unittest.main()
