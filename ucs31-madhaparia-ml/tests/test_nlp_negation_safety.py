
import unittest

from nlp.symptom_mapper import build_confirmation_output


class TestNLPNegationSafety(unittest.TestCase):

    def get_result(self, text):
        result = build_confirmation_output(text)
        statuses = {
            item["code"]: item.get("status")
            for item in result["recognised_symptoms"]
        }
        return statuses, result["has_red_flag"]

    def test_english_negation(self):
        statuses, _ = self.get_result(
            "I have cough but not headache"
        )
        self.assertEqual(statuses.get("cough"), "present")
        self.assertEqual(statuses.get("headache"), "absent")

    def test_multiple_denied_symptoms(self):
        statuses, _ = self.get_result(
            "I have no fever or cough"
        )
        self.assertEqual(statuses.get("fever"), "absent")
        self.assertEqual(statuses.get("cough"), "absent")

    def test_swahili_negation(self):
        statuses, _ = self.get_result(
            "Nina kikohozi lakini sina homa"
        )
        self.assertEqual(statuses.get("cough"), "present")
        self.assertEqual(statuses.get("fever"), "absent")

    def test_swahili_multiple_negation(self):
        statuses, _ = self.get_result(
            "Sina homa wala kikohozi"
        )
        self.assertEqual(statuses.get("fever"), "absent")
        self.assertEqual(statuses.get("cough"), "absent")

    def test_negated_red_flag(self):
        statuses, red_flag = self.get_result(
            "I am not coughing up blood"
        )
        self.assertEqual(
            statuses.get("coughing_blood"), "absent"
        )
        self.assertFalse(red_flag)

    def test_positive_red_flag(self):
        statuses, red_flag = self.get_result(
            "I am coughing up blood"
        )
        self.assertEqual(
            statuses.get("coughing_blood"), "present"
        )
        self.assertTrue(red_flag)

    def test_breathing_difficulty(self):
        statuses, red_flag = self.get_result(
            "I am struggling to breathe"
        )
        self.assertEqual(
            statuses.get("shortness_of_breath"), "present"
        )
        self.assertTrue(red_flag)


    def test_negation_does_not_hide_breathing_emergency(self):
        statuses, red_flag = self.get_result(
            "I have no fever and am struggling to breathe"
        )

        self.assertEqual(statuses.get("fever"), "absent")
        self.assertEqual(
            statuses.get("shortness_of_breath"), "present"
        )
        self.assertTrue(red_flag)



    def test_sneezing_not_confused_with_wheezing(self):
        result = build_confirmation_output(
            "I have a runny nose, sneezing and a mild cough"
        )

        symptoms = {
            item["code"]: item
            for item in result["recognised_symptoms"]
        }

        self.assertIn("runny_blocked_nose", symptoms)
        self.assertIn("cough", symptoms)
        self.assertIn("sneezing", symptoms)

        self.assertEqual(
            symptoms["sneezing"]["status"],
            "present"
        )

        self.assertNotIn("wheezing", symptoms)


    def test_sneezing_english_swahili_negation(self):
        cases = {
            "I am sneezing": "present",
            "I am not sneezing": "absent",
            "Napiga chafya": "present",
            "Sina chafya": "absent",
            "Sipigi chafya": "absent",
        }

        for sentence, expected in cases.items():
            with self.subTest(sentence=sentence):
                result = build_confirmation_output(sentence)

                statuses = {
                    item["code"]: item["status"]
                    for item in result["recognised_symptoms"]
                }

                self.assertEqual(
                    statuses.get("sneezing"),
                    expected
                )
                self.assertFalse(result["has_red_flag"])


if __name__ == "__main__":
    unittest.main()
