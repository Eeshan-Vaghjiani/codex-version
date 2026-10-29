
"""Export V2 training features, labels and provenance separately."""

import argparse
import csv
import json
import tempfile
from contextlib import ExitStack
from pathlib import Path

from v2_feature_encoder import (
    load_v2_symptom_features,
    get_v2_feature_names,
    encode_v2_record,
)


def main(max_examples, output_dir):
    if max_examples is not None and max_examples < 1:
        raise ValueError("max_examples must be positive")

    source = (
        Path(tempfile.gettempdir())
        / "ddxplus_v2_training.jsonl"
    )

    if not source.is_file():
        raise FileNotFoundError(
            "Run build_v2_dataset.py first."
        )

    output_dir.mkdir(parents=True, exist_ok=True)

    symptom_features = load_v2_symptom_features()
    feature_names = get_v2_feature_names(symptom_features)

    with ExitStack() as stack:
        data_file = stack.enter_context(
            (output_dir / "X_train.csv").open(
                "w", newline="", encoding="utf-8"
            )
        )
        label_file = stack.enter_context(
            (output_dir / "y_train.csv").open(
                "w", newline="", encoding="utf-8"
            )
        )
        provenance_file = stack.enter_context(
            (output_dir / "provenance.csv").open(
                "w", newline="", encoding="utf-8"
            )
        )
        input_file = stack.enter_context(
            source.open(encoding="utf-8")
        )

        data_writer = csv.writer(data_file)
        label_writer = csv.writer(label_file)
        provenance_writer = csv.writer(provenance_file)

        data_writer.writerow(feature_names)
        label_writer.writerow(["PATHOLOGY"])
        provenance_writer.writerow([
            "source_dataset",
            "source_split",
            "source_row",
            "scenario_type",
        ])

        count = 0

        for line in input_file:
            record = json.loads(line)

            if (
                record["source_dataset"] != "DDXPlus"
                or record["source_split"] != "train"
            ):
                raise ValueError("Non-training source detected")

            if record["absent"]:
                raise ValueError(
                    "Unverified negative symptoms in training data"
                )

            vector = encode_v2_record(
                record, symptom_features
            )

            data_writer.writerow(vector)
            label_writer.writerow([record["pathology"]])

            provenance_writer.writerow([
                record["source_dataset"],
                record["source_split"],
                record["source_row"],
                record["scenario_type"],
            ])

            count += 1

            if max_examples is not None and count >= max_examples:
                break

    schema = {
        "version": "V2",
        "symptom_features": symptom_features,
        "feature_names": feature_names,
        "feature_count": len(feature_names),
        "negative_evidence_training_supported": False,
    }

    with (output_dir / "feature_schema.json").open(
        "w", encoding="utf-8"
    ) as f:
        json.dump(schema, f, indent=2)

    print("\nV2 NUMERICAL FEATURE EXPORT")
    print("-----------------------------")
    print("Records exported:", count)
    print("Numerical features:", len(feature_names))
    print("Symptom codes:", len(symptom_features))
    print("Negative evidence training: NOT SUPPORTED")
    print("Output directory:", output_dir)

    for name in (
        "X_train.csv",
        "y_train.csv",
        "provenance.csv",
        "feature_schema.json",
    ):
        print("  ", name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--max-examples", type=int, default=None
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=(
            Path(tempfile.gettempdir())
            / "ddxplus_v2_encoded"
        ),
    )

    args = parser.parse_args()

    main(args.max_examples, args.output_dir)
