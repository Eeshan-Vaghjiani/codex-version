
import json
from pathlib import Path


VALID_STATUSES = {"present", "absent", "unknown"}


def load_symptom_codes():
    """Load all supported canonical symptoms."""

    path = Path(__file__).with_name("canonical_symptoms.json")

    with open(path, "r", encoding="utf-8") as file:
        symptoms = json.load(file)

    return {item["code"] for item in symptoms}


def build_symptom_profile(reported_symptoms, durations=None):
    """
    Build a structured patient symptom profile.

    reported_symptoms:
        {"cough": "present", "headache": "absent"}

    durations:
        {"cough": (4, 7)}  # 4 to 7 days
    """

    supported = load_symptom_codes()
    durations = durations or {}

    profile = {
        code: {
            "status": "unknown",
            "duration_min_days": None,
            "duration_max_days": None,
        }
        for code in sorted(supported)
    }

    # Store explicitly reported symptom states
    for code, status in reported_symptoms.items():

        if code not in supported:
            raise ValueError(f"Unsupported symptom: {code}")

        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid symptom status: {status}")

        profile[code]["status"] = status

    # Store duration when available
    for code, duration in durations.items():

        if code not in supported:
            raise ValueError(f"Unsupported symptom: {code}")

        if profile[code]["status"] != "present":
            raise ValueError(
                f"Duration requires a present symptom: {code}"
            )

        if (
            not isinstance(duration, (list, tuple))
            or len(duration) != 2
        ):
            raise ValueError("Duration must contain minimum and maximum days")

        minimum, maximum = duration

        if (
            type(minimum) is not int
            or type(maximum) is not int
            or minimum < 0
            or maximum < minimum
        ):
            raise ValueError("Invalid symptom duration")

        profile[code]["duration_min_days"] = minimum
        profile[code]["duration_max_days"] = maximum

    return profile
