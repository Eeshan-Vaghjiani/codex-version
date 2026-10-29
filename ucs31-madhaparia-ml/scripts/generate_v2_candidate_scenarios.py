
"""Generate synthetic scenarios for two additional V2 conditions.

Research prototype only. Sampling weights are design choices,
NOT clinical prevalence estimates or real patient statistics.
"""

import json
import random
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PROFILE_PATH = ROOT / "docs/v2_candidate_condition_profiles.json"
SCHEMA_PATH = ROOT / "models/v2_feature_schema.json"

OUTPUT_PATH = (
    Path(tempfile.gettempdir())
    / "v2_candidate_scenarios_preview.jsonl"
)

SEED = 42
RECORDS_PER_CONDITION = 400

# Illustrative sampling weights, NOT measured disease frequencies.
WEIGHTS = {
    "COVID-19": {
        "E_91": 0.65,
        "E_94": 0.30,
        "E_97": 0.40,
        "E_201": 0.75,
        "E_181": 0.30,
        "E_103": 0.22,
        "E_89": 0.65,
        "E_144": 0.42,
        "E_66": 0.20,
    },
    "Allergic rhinitis": {
        "E_181": 0.80,
        "E_169": 0.72,
        "E_170": 0.35,
        "E_201": 0.23,
    },
}


def main():
    rng = random.Random(SEED)

    profiles = json.loads(
        PROFILE_PATH.read_text(encoding="utf-8")
    )

    schema = json.loads(
        SCHEMA_PATH.read_text(encoding="utf-8")
    )

    supported = set(schema["symptom_features"])

    assert len(supported) == 32
    assert schema["feature_count"] == 66

    conditions = profiles["conditions"]

    assert {c["name"] for c in conditions} == set(WEIGHTS)

    records = []

    for condition in conditions:
        name = condition["name"]
        weights = WEIGHTS[name]

        assert set(weights) == set(
            condition["possible_features"]
        )

        assert set(weights).issubset(supported)

        seen = set()
        created = 0
        attempts = 0

        while created < RECORDS_PER_CONDITION:
            attempts += 1

            if attempts > 100000:
                raise RuntimeError(
                    f"Cannot generate enough distinct scenarios: {name}"
                )

            # Include one deliberately ambiguous pattern in both
            # conditions to reflect overlapping symptoms.
            if created == 0:
                present = ["E_181", "E_201"]
                age = 30
                sex_m = 0
            else:
                present = sorted(
                    code
                    for code, weight in weights.items()
                    if rng.random() < weight
                )

                if not present:
                    continue

                # Allergy examples must have a relevant
                # nasal or eye symptom.
                if name == "Allergic rhinitis":
                    if not set(present).intersection(
                        {"E_181", "E_169", "E_170"}
                    ):
                        continue

                age = rng.randint(5, 85)
                sex_m = rng.randint(0, 1)

            key = (
                tuple(sorted(present)),
                age,
                sex_m
            )

            if key in seen:
                continue

            seen.add(key)
            created += 1

            record = {
                "source_dataset": "reference_guided_synthetic",
                "source_split": "candidate_only",
                "scenario_type": "synthetic_symptom_scenario",
                "scenario_number": created,
                "pathology": name,
                "AGE": age,
                "SEX_M": sex_m,
                "present": sorted(present),
                "absent": [],
                "unknown": sorted(
                    supported - set(present)
                ),
                "validated_patient_record": False,
                "sampling_assumptions": (
                    "illustrative_not_clinical_prevalence"
                ),
            }

            records.append(record)

    assert len(records) == RECORDS_PER_CONDITION * 2

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8"
    ) as f:
        for record in records:
            f.write(json.dumps(record) + "\n")

    print("STEP 133 - SYNTHETIC SCENARIO GENERATION")
    print("-----------------------------------------")

    print("Total scenarios:", len(records))

    for name in WEIGHTS:
        selected = [
            record for record in records
            if record["pathology"] == name
        ]

        patterns = {
            tuple(record["present"])
            for record in selected
        }

        print(f"\n{name}")
        print("Scenarios:", len(selected))
        print("Distinct symptom patterns:", len(patterns))

    print("\nDATA VALIDATION")
    print("-----------------------------------------")
    print("DDXPlus symptom features:", len(supported))
    print("Confirmed absent evidence invented: NO")
    print("Synthetic demographics labelled: YES")
    print("Real patient records used: NO")
    print("Clinically validated: NO")
    print("Ready for training: NOT YET")
    print("Existing model modified: NO")
    print("Output:", OUTPUT_PATH)

    print("\nStep 133 PASSED!")


if __name__ == "__main__":
    main()
