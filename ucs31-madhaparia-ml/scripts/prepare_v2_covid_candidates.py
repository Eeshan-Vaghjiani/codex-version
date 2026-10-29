
"""Prepare COVID-positive candidate records for V2 research.

Does not train a model or modify existing DDXPlus data.
"""

import csv
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

BASE = (
    Path(tempfile.gettempdir())
    / "v2_23class_experiment"
)

SOURCE = BASE / "external_covid"
OUTPUT = BASE / "covid_candidates.jsonl"

SCHEMA = ROOT / "models/v2_feature_schema.json"

SYMPTOM_MAPPING = {
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

    assert set(SYMPTOM_MAPPING.values()).issubset(
        supported
    )

    files = sorted(SOURCE.glob("*.csv"))
    assert len(files) == 29

    seen = set()
    records = []

    total_positive = 0
    duplicates = 0

    for path in files:
        with path.open(
            encoding="utf-8-sig",
            newline=""
        ) as file:

            reader = csv.DictReader(file)

            for row_number, row in enumerate(
                reader, start=1
            ):
                result = (
                    row.get("covid19_test_results") or ""
                ).strip().upper()

                if result != "POSITIVE":
                    continue

                total_positive += 1

                fingerprint = tuple(sorted(
                    (
                        key,
                        str(value or "").strip()
                    )
                    for key, value in row.items()
                    if key != "batch_date"
                ))

                if fingerprint in seen:
                    duplicates += 1
                    continue

                seen.add(fingerprint)

                present = set()
                absent = set()

                for column, code in SYMPTOM_MAPPING.items():
                    value = (
                        row.get(column) or ""
                    ).strip().upper()

                    if value == "TRUE":
                        present.add(code)

                    elif value == "FALSE":
                        absent.add(code)

                    elif value:
                        raise ValueError(
                            f"Unexpected {column}: {value}"
                        )

                unknown = (
                    supported - present - absent
                )

                assert not (present & absent)

                assert (
                    present | absent | unknown
                ) == supported

                age = float(row["age"])
                assert 0 <= age <= 120

                record = {
                    "source_dataset": (
                        "COVID-19 Clinical Data Repository"
                    ),
                    "source_file": path.name,
                    "source_row": row_number,
                    "source_split": "unassigned",
                    "pathology": "COVID-19",
                    "label_evidence": "positive_test",
                    "age": age,
                    "sex": None,
                    "present": sorted(present),
                    "absent": sorted(absent),
                    "unknown": sorted(unknown),
                    "clinically_validated_model": False
                }

                records.append(record)

    assert total_positive == 1313
    assert duplicates == 9
    assert len(records) == 1304

    with OUTPUT.open(
        "w", encoding="utf-8"
    ) as output:
        for record in records:
            output.write(
                json.dumps(record) + "\n"
            )

    with_symptoms = sum(
        bool(record["present"])
        for record in records
    )

    without_symptoms = (
        len(records) - with_symptoms
    )

    print("V2 COVID-19 CANDIDATE PREPARATION")
    print("------------------------------------")
    print("Original positive records:", total_positive)
    print("Repeated occurrences excluded:", duplicates)
    print("Distinct candidate records:", len(records))

    print("\nSYMPTOM COVERAGE")
    print("------------------------------------")
    print("At least 1 supported symptom:", with_symptoms)
    print("No supported positive symptom:", without_symptoms)
    print("Symptom features supported:", len(supported))
    print("COVID symptom fields mapped:", len(SYMPTOM_MAPPING))

    print("\nDATASET STATUS")
    print("------------------------------------")
    print("COVID test labels: PRESERVED")
    print("Explicit negative symptoms: PRESERVED")
    print("Missing sex information: NOT INVENTED")
    print("Train/test split: NOT CREATED")
    print("Existing RF model modified: NO")
    print("Ready for model training: NOT YET")
    print("Output:", OUTPUT)

    print("\nStep 117 PASSED!")


if __name__ == "__main__":
    main()
