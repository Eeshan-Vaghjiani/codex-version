
import unittest

from nlp.symptom_mapper import build_confirmation_output


class TestNLPPatientContext(unittest.TestCase):

    def get_result(self, text, code):
        result = build_confirmation_output(text)

        symptom = next(
            (
                item
                for item in result["recognised_symptoms"]
                if item["code"] == code
            ),
            None
        )

        return symptom, result["has_red_flag"]

    def test_sister_cough_not_patient(self):
        symptom, _ = self.get_result(
            "My sister has a cough, not me",
            "cough"
        )
        self.assertIsNotNone(symptom)
        self.assertEqual(symptom["status"], "absent")

    def test_sister_cough_patient_unknown(self):
        symptom, _ = self.get_result(
            "My sister has a cough",
            "cough"
        )
        self.assertIsNotNone(symptom)
        self.assertEqual(symptom["status"], "unknown")

    def test_past_fever_resolved(self):
        symptom, _ = self.get_result(
            "I had fever last week but not now",
            "fever"
        )
        self.assertIsNotNone(symptom)
        self.assertEqual(symptom["status"], "absent")

    def test_past_fever_still_present(self):
        symptom, _ = self.get_result(
            "I had fever last week and still have it",
            "fever"
        )
        self.assertIsNotNone(symptom)
        self.assertEqual(symptom["status"], "present")

    def test_brother_chest_pain_not_patient(self):
        symptom, _ = self.get_result(
            "My brother has chest pain, not me",
            "chest_pain"
        )
        self.assertIsNotNone(symptom)
        self.assertEqual(symptom["status"], "absent")

    def test_other_person_red_flag_denied(self):
        symptom, red_flag = self.get_result(
            "My sister is coughing up blood, not me",
            "coughing_blood"
        )
        self.assertIsNotNone(symptom)
        self.assertEqual(symptom["status"], "absent")
        self.assertFalse(red_flag)


    def test_other_person_red_flag_unknown(self):
        symptom, red_flag = self.get_result(
            "My sister is coughing up blood",
            "coughing_blood"
        )

        self.assertEqual(symptom["status"], "unknown")
        self.assertFalse(red_flag)

    def test_uncertain_patient_red_flag(self):
        symptom, red_flag = self.get_result(
            "I don't know if I am coughing up blood",
            "coughing_blood"
        )

        self.assertEqual(symptom["status"], "unknown")
        self.assertTrue(red_flag)

    def test_patient_emergency_with_other_person(self):
        symptom, red_flag = self.get_result(
            "My sister is coughing up blood and I am struggling to breathe",
            "shortness_of_breath"
        )

        self.assertEqual(symptom["status"], "present")
        self.assertTrue(red_flag)


    def test_sister_positive_patient_denies_blood(self):
        symptom, red_flag = self.get_result(
            "My sister is coughing up blood but I am not coughing up blood",
            "coughing_blood"
        )

        self.assertEqual(symptom["status"], "absent")
        self.assertFalse(red_flag)

    def test_patient_denies_brother_has_breathing_problem(self):
        symptom, red_flag = self.get_result(
            "I am not struggling to breathe but my brother is struggling to breathe",
            "shortness_of_breath"
        )

        self.assertEqual(symptom["status"], "absent")
        self.assertFalse(red_flag)

    def test_brother_and_patient_breathing_problem(self):
        symptom, red_flag = self.get_result(
            "My brother is struggling to breathe but I am struggling to breathe",
            "shortness_of_breath"
        )

        self.assertEqual(symptom["status"], "present")
        self.assertTrue(red_flag)


    def test_sister_breathing_patient_different_alias(self):
        symptom, red_flag = self.get_result(
            "My sister is struggling to breathe but I can't catch my breath",
            "shortness_of_breath"
        )
        self.assertEqual(symptom["status"], "present")
        self.assertTrue(red_flag)

    def test_patient_breathing_sister_different_alias(self):
        symptom, red_flag = self.get_result(
            "I can't catch my breath but my sister is struggling to breathe",
            "shortness_of_breath"
        )
        self.assertEqual(symptom["status"], "present")
        self.assertTrue(red_flag)

    def test_sister_blood_patient_denies_different_alias(self):
        symptom, red_flag = self.get_result(
            "My sister is coughing up blood but I have no blood in my sputum",
            "coughing_blood"
        )
        self.assertEqual(symptom["status"], "absent")
        self.assertFalse(red_flag)

    def test_sister_blood_patient_positive_different_alias(self):
        symptom, red_flag = self.get_result(
            "My sister is coughing up blood but I have blood in my sputum",
            "coughing_blood"
        )
        self.assertEqual(symptom["status"], "present")
        self.assertTrue(red_flag)


if __name__ == "__main__":
    unittest.main()
