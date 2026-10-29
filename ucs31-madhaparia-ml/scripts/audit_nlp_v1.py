
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nlp.symptom_mapper import build_confirmation_output

# Expected NLP behaviour, not medical diagnoses.
# Format: name, input, expected symptom states, red flag.

CASES = [
    ("English basic", "I have fever and cough",
     {"fever": "present", "cough": "present"}, False),

    ("English negation", "I have cough but not headache",
     {"cough": "present", "headache": "absent"}, False),

    ("English no/or", "I have no fever or cough",
     {"fever": "absent", "cough": "absent"}, False),

    ("English without", "I have cough without fever",
     {"cough": "present", "fever": "absent"}, False),

    ("Uncertainty", "I have cough but I am not sure about fever",
     {"cough": "present", "fever": "unknown"}, False),

    ("English clauses", "I do not have fever but I have cough",
     {"fever": "absent", "cough": "present"}, False),

    ("Swahili basic", "Nina homa na kikohozi",
     {"fever": "present", "cough": "present"}, False),

    ("Swahili negation", "Nina kikohozi lakini sina homa",
     {"cough": "present", "fever": "absent"}, False),

    ("Swahili no symptoms", "Sina homa wala kikohozi",
     {"fever": "absent", "cough": "absent"}, False),

    ("Mixed language", "I have kikohozi but sina homa",
     {"cough": "present", "fever": "absent"}, False),

    ("Misspellings", "I have couhg and feaver",
     {"cough": "present", "fever": "present"}, False),

    ("Sneezing", "I have a runny nose, sneezing and a mild cough",
     {"runny_blocked_nose": "present",
     "cough": "present"}, False),

    ("Weight loss", "I have had cough and been losing weight",
     {"cough": "present", "weight_loss": "present"}, False),

    ("Blood positive", "I am coughing up blood",
     {"coughing_blood": "present"}, True),

    ("Blood negated", "I am not coughing up blood",
     {"coughing_blood": "absent"}, False),

    ("Blue lips negated", "No blue lips",
     {"blue_lips": "absent"}, False),

    ("Breathing emergency", "I am struggling to breathe",
     {"shortness_of_breath": "present"}, True),

    ("Breathing negated", "I do not have shortness of breath",
     {"shortness_of_breath": "absent"}, False),

    ("Breathing variation", "I can't catch my breath",
     {"shortness_of_breath": "present"}, True),

    ("Blood in sputum", "I have blood in my sputum",
     {"coughing_blood": "present"}, True),

    ("Swahili breathing", "Ninashindwa kupumua",
     {"shortness_of_breath": "present"}, True),

    ("Other person's symptoms", "My sister has a cough, not me",
     {"cough": "absent"}, False),

    ("Past symptoms", "I had fever last week but not now",
     {"fever": "absent"}, False),

    ("Vague description", "I feel unwell",
     {}, False),
]

passed = 0

for number, (name, text, expected, red_flag) in enumerate(CASES, 1):
    result = build_confirmation_output(text)

    actual = {
        symptom["code"]: symptom.get(
            "status", "not_implemented"
        )
        for symptom in result["recognised_symptoms"]
    }

    problems = []

    for code, status in expected.items():
        if actual.get(code) != status:
            problems.append(
                f"{code}: expected {status}, got {actual.get(code, 'missing')}"
            )

    if result["has_red_flag"] != red_flag:
        problems.append(
            f"red flag: expected {red_flag}, got {result['has_red_flag']}"
        )

    if not expected and actual:
        problems.append(f"Unexpected symptoms: {list(actual)}")


    if name == "Sneezing":
        sneezing_entry = next(
            (
                item for item in result["unmatched_wording"]
                if item["unmatched_text"] == "sneezing"
            ),
            None
        )

        if sneezing_entry is None:
            problems.append("Sneezing not preserved")

        elif any(
            suggestion["code"] == "wheezing"
            for suggestion in sneezing_entry["suggestions"]
        ):
            problems.append("Sneezing incorrectly suggests wheezing")

        if "wheezing" in actual:
            problems.append("Sneezing incorrectly recognised as wheezing")


    if problems:
        print(f"{number:02d}. NEEDS FIX - {name}")
        for problem in problems:
            print("   ", problem)
    else:
        passed += 1
        print(f"{number:02d}. PASS - {name}")

print(f"\nScenario checks: {passed}/{len(CASES)} passed")

# Test one English alias for every canonical symptom.
with open(
    ROOT / "nlp" / "canonical_symptoms.json",
    encoding="utf-8"
) as file:
    concepts = json.load(file)

coverage_passed = 0

for concept in concepts:
    alias = concept["aliases"]["en"][0]
    result = build_confirmation_output("I have " + alias)

    codes = {
        symptom["code"]
        for symptom in result["recognised_symptoms"]
    }

    if concept["code"] in codes:
        coverage_passed += 1
    else:
        print(f"Alias needs review: {concept['code']} - {alias}")

print(f"Canonical symptom checks: {coverage_passed}/{len(concepts)}")

# Duration checks.
duration_cases = [
    ("I have had a cough for two days", 2),
    ("I have had a cough for three weeks", 21),
]

duration_passed = 0

for text, expected_days in duration_cases:
    result = build_confirmation_output(text)

    cough = next(
        (s for s in result["recognised_symptoms"]
         if s["code"] == "cough"),
        None
    )

    if cough and (
        cough.get("duration_min_days") == expected_days
        and cough.get("duration_max_days") == expected_days
    ):
        duration_passed += 1
    else:
        print(f"Duration needs review: {text}")

print(f"Duration checks: {duration_passed}/{len(duration_cases)}")

total = len(CASES) + len(concepts) + len(duration_cases)
successful = passed + coverage_passed + duration_passed

print(f"\nTOTAL: {successful}/{total} checks passed")
print("NLP audit complete. No model files modified.")
