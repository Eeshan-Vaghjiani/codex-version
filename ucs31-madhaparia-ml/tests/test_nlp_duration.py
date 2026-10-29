
import unittest

from nlp.symptom_mapper import build_confirmation_output


class TestNLPDuration(unittest.TestCase):

    def get_symptom(self, text, code):
        result = build_confirmation_output(text)

        return next(
            (
                symptom
                for symptom in result["recognised_symptoms"]
                if symptom["code"] == code
            ),
            None
        )

    def test_cough_two_days(self):
        symptom = self.get_symptom(
            "I have had a cough for two days",
            "cough"
        )

        self.assertIsNotNone(symptom)
        self.assertEqual(symptom["duration_min_days"], 2)
        self.assertEqual(symptom["duration_max_days"], 2)

    def test_cough_three_weeks(self):
        symptom = self.get_symptom(
            "I have had a cough for three weeks",
            "cough"
        )

        self.assertIsNotNone(symptom)
        self.assertEqual(symptom["duration_min_days"], 21)
        self.assertEqual(symptom["duration_max_days"], 21)

    def test_fever_one_week(self):
        symptom = self.get_symptom(
            "I have fever for 1 week",
            "fever"
        )

        self.assertIsNotNone(symptom)
        self.assertEqual(symptom["duration_min_days"], 7)

    def test_no_duration_provided(self):
        symptom = self.get_symptom(
            "I have cough",
            "cough"
        )

        self.assertIsNotNone(symptom)
        self.assertIsNone(symptom["duration_min_days"])
        self.assertIsNone(symptom["duration_max_days"])

    def test_absent_symptom_has_no_duration(self):
        symptom = self.get_symptom(
            "I do not have a cough",
            "cough"
        )

        self.assertIsNotNone(symptom)
        self.assertEqual(symptom["status"], "absent")
        self.assertIsNone(symptom["duration_min_days"])
        self.assertIsNone(symptom["duration_max_days"])


    def test_sister_cough_duration_patient_later(self):
        result = build_confirmation_output(
            "My sister has cough for 2 days but I have cough for 5 days"
        )
        cough = next(
            s for s in result["recognised_symptoms"]
            if s["code"] == "cough"
        )
        self.assertEqual(cough["duration_min_days"], 5)

    def test_patient_cough_duration_first(self):
        result = build_confirmation_output(
            "I have cough for 5 days but my sister has cough for 2 days"
        )
        cough = next(
            s for s in result["recognised_symptoms"]
            if s["code"] == "cough"
        )
        self.assertEqual(cough["duration_min_days"], 5)

    def test_brother_fever_duration_patient_later(self):
        result = build_confirmation_output(
            "My brother has fever for 3 days but I have fever for 1 day"
        )
        fever = next(
            s for s in result["recognised_symptoms"]
            if s["code"] == "fever"
        )
        self.assertEqual(fever["duration_min_days"], 1)

    def test_conflicting_patient_durations(self):
        result = build_confirmation_output(
            "I have cough for 2 days but I have cough for 5 days"
        )
        cough = next(
            s for s in result["recognised_symptoms"]
            if s["code"] == "cough"
        )
        self.assertIsNone(cough["duration_min_days"])

if __name__ == "__main__":
    unittest.main()
