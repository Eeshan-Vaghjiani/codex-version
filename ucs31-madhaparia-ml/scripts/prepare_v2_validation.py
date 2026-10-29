
"""Prepare held-out DDXPlus validation data for V2 evaluation.

Uses the official validation split, never the training split.
No synthetic disease extension is added to validation.
"""

import ast
import csv
import json
import tempfile
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SOURCE = ROOT / "data/raw/release_validate_patients"
SCHEMA = ROOT / "docs/v2_experimental_feature_schema.json"
DISEASES = ROOT / "data/processed/diseases.json"

OUTPUT = (
    Path(tempfile.gettempdir())
    / "v2_23class_experiment"
    / "validation"
)


def main():
    schema = json.loads(
        SCHEMA.read_text(encoding="utf-8")
    )

    codes = schema["symptom_features"]
    feature_names = schema["feature_names"]

    diseases = {
        item["name"]
        for item in json.loads(
            DISEASES.read_text(encoding="utf-8")
        )
    }

    assert len(codes) == 32
    assert len(feature_names) == 64
    assert len(diseases) == 21

    assert feature_names == (
        [f"{code}__present" for code in codes]
        + [f"{code}__absent" for code in codes]
    )

    OUTPUT.mkdir(parents=True, exist_ok=True)

    counts = Counter()
    skipped = 0

    with (
        SOURCE.open(
            newline="", encoding="utf-8"
        ) as source,
        (OUTPUT / "X_validate.csv").open(
            "w", newline="", encoding="utf-8"
        ) as xf,
        (OUTPUT / "y_validate.csv").open(
            "w", newline="", encoding="utf-8"
        ) as yf,
        (OUTPUT / "provenance_validate.csv").open(
            "w", newline="", encoding="utf-8"
        ) as pf
    ):
        reader = csv.DictReader(source)

        x_writer = csv.writer(xf)
        y_writer = csv.writer(yf)
        p_writer = csv.writer(pf)

        x_writer.writerow(feature_names)
        y_writer.writerow(["PATHOLOGY"])

        p_writer.writerow([
            "source_dataset",
            "source_split",
            "source_row",
            "scenario_type"
        ])

        for row_number, row in enumerate(reader, start=1):
            disease = row["PATHOLOGY"]

            if disease not in diseases:
                continue

            evidences = set(
                ast.literal_eval(row["EVIDENCES"])
            )

            present = evidences & set(codes)

            if not present:
                skipped += 1
                continue

            # Raw observed positive symptoms.
            # Unreported symptoms remain unknown,
            # not confirmed absent.
            vector = (
                [int(code in present) for code in codes]
                + [0] * len(codes)
            )

            assert len(vector) == 64

            x_writer.writerow(vector)
            y_writer.writerow([disease])

            p_writer.writerow([
                "DDXPlus",
                "validate",
                row_number,
                "original_binary_observation"
            ])

            counts[disease] += 1

    assert sum(counts.values()) > 0
    assert len(counts) == 21

    print("V2 HELD-OUT VALIDATION PREPARATION")
    print("-------------------------------------")
    print("Validation scenarios:", sum(counts.values()))
    print("Conditions represented:", len(counts))
    print("Numerical features:", len(feature_names))
    print("Skipped without supported symptoms:", skipped)
    print("Source split: validate")
    print("Synthetic COVID-19 cases added: NO")
    print("Synthetic allergic rhinitis cases added: NO")
    print("Output:", OUTPUT)
    print("\nValidation preparation PASSED!")


if __name__ == "__main__":
    main()
