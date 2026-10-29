import unittest

from nlp.symptom_mapper import (
    build_confirmation_output,
    find_symptoms,
)


class TestSymptomMapper(unittest.TestCase):

    def get_codes(self, text):
        matches = find_symptoms(text)

        return {
            match["code"]
            for match in matches
        }

    def test_english_symptoms(self):
        codes = self.get_codes(
            "I have fever and cough"
        )

        self.assertEqual(
            codes,
            {
                "fever",
                "cough",
            },
        )

    def test_swahili_symptoms(self):
        codes = self.get_codes(
            "Nina homa na kikohozi"
        )

        self.assertEqual(
            codes,
            {
                "fever",
                "cough",
            },
        )

    def test_mixed_language_input(self):
        codes = self.get_codes(
            "Nina homa and I have a sore throat"
        )

        self.assertEqual(
            codes,
            {
                "fever",
                "sore_throat",
            },
        )

    def test_mixed_swahili_english_input(self):
        codes = self.get_codes(
            "I have kikohozi and "
            "kupumua kwa shida"
        )

        self.assertEqual(
            codes,
            {
                "cough",
                "shortness_of_breath",
            },
        )

    def test_headache_mapping(self):
        output = build_confirmation_output(
            "homa na kichwa kuuma"
        )

        symptoms = {
            symptom["code"]: symptom
            for symptom
            in output["recognised_symptoms"]
        }

        self.assertIn(
            "fever",
            symptoms,
        )

        self.assertIn(
            "headache",
            symptoms,
        )

        self.assertEqual(
            symptoms["headache"]["features"],
            [
                "E_53",
            ],
        )

    def test_fuzzy_typo_matching(self):
        matches = find_symptoms(
            "I have a couhg and feaver"
        )

        codes = {
            match["code"]
            for match in matches
        }

        self.assertEqual(
            codes,
            {
                "cough",
                "fever",
            },
        )

        fuzzy_codes = {
            match["code"]
            for match in matches
            if match["match_type"] == "fuzzy"
        }

        self.assertIn(
            "cough",
            fuzzy_codes,
        )

        self.assertIn(
            "fever",
            fuzzy_codes,
        )

    def test_unmatched_wording(self):
        output = build_confirmation_output(
            "I have fever and a skin rash"
        )

        codes = {
            symptom["code"]
            for symptom
            in output["recognised_symptoms"]
        }

        self.assertEqual(
            codes,
            {
                "fever",
            },
        )

        unmatched = {
            item["unmatched_text"]
            for item
            in output["unmatched_wording"]
        }

        self.assertIn(
            "skin rash",
            unmatched,
        )

    def test_near_match_is_suggestion(self):
        output = build_confirmation_output(
            "I have throt pane"
        )

        self.assertEqual(
            output["recognised_symptoms"],
            [],
        )

        self.assertTrue(
            output["unmatched_wording"]
        )

        suggestions = (
            output[
                "unmatched_wording"
            ][0]["suggestions"]
        )

        suggestion_codes = {
            item["code"]
            for item in suggestions
        }

        self.assertIn(
            "sore_throat",
            suggestion_codes,
        )

    def test_red_flag_detection(self):
        output = build_confirmation_output(
            "I am coughing up blood"
        )

        self.assertTrue(
            output["has_red_flag"]
        )

        self.assertTrue(
            output[
                "requires_confirmation"
            ]
        )

        symptom = (
            output[
                "recognised_symptoms"
            ][0]
        )

        self.assertEqual(
            symptom["code"],
            "coughing_blood",
        )

        self.assertTrue(
            symptom["is_red_flag"]
        )

        self.assertEqual(
            symptom["features"],
            [
                "E_45",
            ],
        )

    def test_safety_only_red_flag(self):
        output = build_confirmation_output(
            "My lips are turning blue"
        )

        codes = {
            symptom["code"]
            for symptom
            in output["recognised_symptoms"]
        }

        self.assertIn(
            "blue_lips",
            codes,
        )

        blue_lips = next(
            symptom
            for symptom
            in output[
                "recognised_symptoms"
            ]
            if symptom["code"]
            == "blue_lips"
        )

        self.assertEqual(
            blue_lips["features"],
            [],
        )

        self.assertTrue(
            blue_lips[
                "is_red_flag"
            ]
        )

        self.assertTrue(
            output["has_red_flag"]
        )

    def test_confirmation_state(self):
        output = build_confirmation_output(
            "I have fever"
        )

        symptom = (
            output[
                "recognised_symptoms"
            ][0]
        )

        self.assertFalse(
            symptom["confirmed"]
        )

        self.assertTrue(
            output[
                "requires_confirmation"
            ]
        )

    def test_unrelated_text_not_matched(self):
        output = build_confirmation_output(
            "I went to the market "
            "and bought food after work"
        )

        self.assertEqual(
            output["recognised_symptoms"],
            [],
        )

        self.assertFalse(
            output["has_red_flag"]
        )


if __name__ == "__main__":
    unittest.main()
