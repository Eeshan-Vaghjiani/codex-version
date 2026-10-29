
"""Audit COVID-positive records before V2 dataset integration."""

import csv
import json
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SOURCE = (
    Path(tempfile.gettempdir())
    / "v2_23class_experiment"
    / "external_covid"
)

SCHEMA = ROOT / "models/v2_feature_schema.json"

SYMPTOMS = {
    "cough": "E_201",
    "fever": "E_91",
    "fatigue": "E_89",
    "loss_of_smell": "E_103",
    "runny_nose": "E_181",
    "muscle_sore": "E_144",
    "sore_throat": "E_97",
}


def main():
    schema = json.loads(
        SCHEMA.read_text(encoding="utf-8")
    )

    supported = set(schema["symptom_features"])

    assert set(SYMPTOMS.values()).issubset(supported)

    files = sorted(SOURCE.glob("*.csv"))
    assert len(files) == 29

    positive_count = 0
    positive_symptom_counts = Counter()
    symptom_values = {
        name: Counter() for name in SYMPTOMS
    }

    valid_age = 0
    missing_age = 0

    for path in files:
        with path.open(
            encoding="utf-8-sig",
            newline=""
        ) as file:

            reader = csv.DictReader(file)

            assert set(SYMPTOMS).issubset(
                set(reader.fieldnames or [])
            )

            for row in reader:
                result = (
                    row.get("covid19_test_results") or ""
                ).strip().upper()

                if result != "POSITIVE":
                    continue

                positive_count += 1
                present_count = 0

                for symptom in SYMPTOMS:
                    value = (
                        row.get(symptom) or ""
                    ).strip().upper()

                    if value not in {
                        "TRUE", "FALSE", ""
                    }:
                        raise ValueError(
                            f"Unexpected {symptom}: {value}"
                        )

                    symptom_values[symptom][
                        value or "MISSING"
                    ] += 1

                    if value == "TRUE":
                        present_count += 1

                positive_symptom_counts[
                    present_count
                ] += 1

                try:
                    age = float(row["age"])

                    if 0 <= age <= 120:
                        valid_age += 1
                    else:
                        missing_age += 1

                except (ValueError, TypeError):
                    missing_age += 1

    assert positive_count == 1313

    print("COVID-19 POSITIVE RECORD AUDIT")
    print("--------------------------------")
    print("Files inspected:", len(files))
    print("COVID-positive records:", positive_count)

    print("\nPOSITIVE SYMPTOMS PER RECORD")
    print("--------------------------------")

    for count in range(len(SYMPTOMS) + 1):
        print(
            f"{count} symptoms:",
            positive_symptom_counts[count]
        )

    at_least_one = sum(
        count for n, count in positive_symptom_counts.items()
        if n >= 1
    )

    at_least_two = sum(
        count for n, count in positive_symptom_counts.items()
        if n >= 2
    )

    print("\nRECORD USABILITY")
    print("--------------------------------")
    print("At least 1 positive symptom:", at_least_one)
    print("At least 2 positive symptoms:", at_least_two)
    print("Age within 0-120:", valid_age)
    print("Age missing or unsupported:", missing_age)

    print("\nSYMPTOM VALUE COUNTS")
    print("--------------------------------")

    for symptom, counts in symptom_values.items():
        print(
            f"{symptom}:",
            f"TRUE={counts['TRUE']}",
            f"FALSE={counts['FALSE']}",
            f"MISSING={counts['MISSING']}"
        )

    print("\nTraining data modified: NO")
    print("Step 114 PASSED!")


if __name__ == "__main__":
    main()
