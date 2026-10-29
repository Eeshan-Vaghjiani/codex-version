
"""Encode synthetic COVID-19 and allergic-rhinitis scenarios.

Uses the existing 66-feature V2 schema.
These are synthetic records, not clinical patient data.
"""

import csv
import json
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SCHEMA_PATH = ROOT / "models/v2_feature_schema.json"

SOURCE_PATH = (
    Path(tempfile.gettempdir())
    / "v2_candidate_scenarios_preview.jsonl"
)

OUTPUT_DIR = (
    Path(tempfile.gettempdir())
    / "v2_candidate_encoded_66"
)


def main():
    schema = json.loads(
        SCHEMA_PATH.read_text(encoding="utf-8")
    )

    codes = schema["symptom_features"]
    names = schema["feature_names"]
    supported = set(codes)

    expected_names = (
        ["AGE", "SEX_M"]
        + [f"{code}__present" for code in codes]
        + [f"{code}__absent" for code in codes]
    )

    assert len(codes) == 32
    assert len(supported) == 32
    assert len(names) == 66
    assert schema["feature_count"] == 66
    assert names == expected_names

    assert SOURCE_PATH.exists(), (
        f"Synthetic data not found: {SOURCE_PATH}"
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    counts = Counter()
    patterns = {
        "COVID-19": set(),
        "Allergic rhinitis": set()
    }

    with (
        SOURCE_PATH.open(encoding="utf-8") as source,
        (OUTPUT_DIR / "X_candidates.csv").open(
            "w", newline="", encoding="utf-8"
        ) as xf,
        (OUTPUT_DIR / "y_candidates.csv").open(
            "w", newline="", encoding="utf-8"
        ) as yf,
        (OUTPUT_DIR / "provenance.csv").open(
            "w", newline="", encoding="utf-8"
        ) as pf
    ):
        x_writer = csv.writer(xf)
        y_writer = csv.writer(yf)
        p_writer = csv.writer(pf)

        x_writer.writerow(names)
        y_writer.writerow(["PATHOLOGY"])

        p_writer.writerow([
            "source_dataset",
            "source_split",
            "scenario_type",
            "scenario_number",
            "validated_patient_record",
            "symptom_pattern"
        ])

        for line in source:
            record = json.loads(line)

            disease = record["pathology"]

            assert disease in patterns
            assert record["source_split"] == "candidate_only"
            assert record["validated_patient_record"] is False

            age = record["AGE"]
            sex_m = record["SEX_M"]

            assert type(age) is int
            assert 0 <= age <= 120

            assert type(sex_m) is int
            assert sex_m in (0, 1)

            present = record["present"]
            absent = record["absent"]
            unknown = record["unknown"]

            present_set = set(present)
            absent_set = set(absent)
            unknown_set = set(unknown)

            assert len(present) == len(present_set)
            assert not absent_set
            assert present_set
            assert present_set.issubset(supported)

            assert present_set.isdisjoint(unknown_set)
            assert present_set | unknown_set == supported

            vector = (
                [age, sex_m]
                + [int(code in present_set) for code in codes]
                + [0 for _ in codes]
            )

            assert len(vector) == 66

            x_writer.writerow(vector)
            y_writer.writerow([disease])

            pattern_key = "|".join(sorted(present_set))

            p_writer.writerow([
                record["source_dataset"],
                record["source_split"],
                record["scenario_type"],
                record["scenario_number"],
                record["validated_patient_record"],
                pattern_key
            ])

            counts[disease] += 1
            patterns[disease].add(pattern_key)

    assert counts == {
        "COVID-19": 400,
        "Allergic rhinitis": 400
    }

    print("STEP 135 - V2 SYNTHETIC DATA ENCODING")
    print("--------------------------------------")
    print("Total scenarios:", sum(counts.values()))
    print("Numerical features:", len(names))

    for disease, count in counts.items():
        print(f"\n{disease}")
        print("Encoded records:", count)
        print(
            "Distinct symptom patterns:",
            len(patterns[disease])
        )

    print("\nENCODING VALIDATION")
    print("--------------------------------------")
    print("AGE included: YES")
    print("SEX_M included: YES")
    print("Present symptom features:", len(codes))
    print("Absent symptom features:", len(codes))
    print("Unknown symptoms encoded as absent: NO")
    print("Real patient records used: NO")
    print("Clinical validation: NOT PERFORMED")
    print("Existing model modified: NO")
    print("Output:", OUTPUT_DIR)

    print("\nStep 135 PASSED!")


if __name__ == "__main__":
    main()
