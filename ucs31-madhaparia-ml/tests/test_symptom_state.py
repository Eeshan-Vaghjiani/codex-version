
import unittest

from nlp.symptom_state import (
    build_symptom_profile,
    load_symptom_codes,
)


class TestSymptomState(unittest.TestCase):

    def test_present_absent_unknown(self):
        profile = build_symptom_profile({
            "cough": "present",
            "headache": "absent",
        })

        self.assertEqual(profile["cough"]["status"], "present")
        self.assertEqual(profile["headache"]["status"], "absent")
        self.assertEqual(profile["fever"]["status"], "unknown")

    def test_all_supported_symptoms(self):
        profile = build_symptom_profile({})
        self.assertEqual(
            set(profile.keys()),
            load_symptom_codes()
        )

    def test_symptom_duration(self):
        profile = build_symptom_profile(
            {"cough": "present"},
            {"cough": (4, 7)}
        )

        self.assertEqual(
            profile["cough"]["duration_min_days"], 4
        )
        self.assertEqual(
            profile["cough"]["duration_max_days"], 7
        )

    def test_unsupported_symptom(self):
        with self.assertRaises(ValueError):
            build_symptom_profile({
                "unsupported_symptom": "present"
            })

    def test_invalid_status(self):
        with self.assertRaises(ValueError):
            build_symptom_profile({
                "cough": "maybe"
            })

    def test_duration_for_absent_symptom(self):
        with self.assertRaises(ValueError):
            build_symptom_profile(
                {"cough": "absent"},
                {"cough": (2, 5)}
            )

    def test_invalid_duration_range(self):
        with self.assertRaises(ValueError):
            build_symptom_profile(
                {"cough": "present"},
                {"cough": (7, 3)}
            )

    def test_negative_duration(self):
        with self.assertRaises(ValueError):
            build_symptom_profile(
                {"cough": "present"},
                {"cough": (-2, 5)}
            )


if __name__ == "__main__":
    unittest.main()
