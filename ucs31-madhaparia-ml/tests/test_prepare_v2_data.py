
import random
import unittest

from scripts.prepare_v2_data import make_partial_binary_case


class TestV2DataPreparation(unittest.TestCase):

    def setUp(self):
        self.metadata = {
            "E_91": {"data_type": "B", "is_antecedent": False},
            "E_201": {"data_type": "B", "is_antecedent": False},
            "E_94": {"data_type": "B", "is_antecedent": False},
            "E_97": {"data_type": "B", "is_antecedent": False},
            "E_88": {"data_type": "B", "is_antecedent": False},
            "E_55": {"data_type": "M", "is_antecedent": False},
            "E_10": {"data_type": "B", "is_antecedent": True},
        }

        self.original = [
            "E_91", "E_201", "E_94", "E_97", "E_55", "E_10"
        ]

    def generate(self, seed=42):
        return make_partial_binary_case(
            self.original,
            self.metadata,
            list(self.metadata),
            random.Random(seed),
            min_reported=2,
            max_reported=3,
        )

    def test_reported_symptoms_are_original(self):
        case = self.generate()

        self.assertIsNotNone(case)
        self.assertTrue(
            set(case["present"]).issubset(set(self.original))
        )

    def test_no_negative_symptoms_invented(self):
        case = self.generate()

        self.assertEqual(case["absent"], [])

    def test_unknown_and_present_are_separate(self):
        case = self.generate()

        self.assertFalse(
            set(case["present"]) & set(case["unknown"])
        )

        self.assertIn("E_88", case["unknown"])

    def test_excludes_history_and_multichoice(self):
        case = self.generate()

        self.assertNotIn("E_10", case["present"])
        self.assertNotIn("E_55", case["present"])
        self.assertNotIn("E_10", case["unknown"])
        self.assertNotIn("E_55", case["unknown"])

    def test_preserves_incomplete_information(self):
        case = self.generate()

        self.assertGreaterEqual(len(case["present"]), 2)
        self.assertLessEqual(len(case["present"]), 3)

        original_binary = {
            "E_91", "E_201", "E_94", "E_97"
        }

        self.assertTrue(
            original_binary - set(case["present"])
        )

    def test_generation_is_reproducible(self):
        self.assertEqual(
            self.generate(seed=42),
            self.generate(seed=42)
        )

    def test_skips_insufficient_symptoms(self):
        case = make_partial_binary_case(
            ["E_91", "E_201"],
            self.metadata,
            list(self.metadata),
            random.Random(42),
        )

        self.assertIsNone(case)

    def test_rejects_invalid_limits(self):
        with self.assertRaises(ValueError):
            make_partial_binary_case(
                self.original,
                self.metadata,
                list(self.metadata),
                random.Random(42),
                min_reported=0,
                max_reported=3,
            )


if __name__ == "__main__":
    unittest.main()
