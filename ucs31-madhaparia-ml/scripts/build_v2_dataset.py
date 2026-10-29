
"""Build reproducible V2 symptom scenarios from DDXPlus training data."""

import argparse
import ast
import csv
import json
import random
import tempfile
from collections import Counter
from pathlib import Path

from prepare_v2_data import make_partial_binary_case

ROOT = Path(__file__).resolve().parents[1]
csv.field_size_limit(2_147_483_647)


def load_json(path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def build_dataset(output_path, max_examples=None, seed=42):
    if max_examples is not None and max_examples < 1:
        raise ValueError("max_examples must be positive")

    metadata = load_json(ROOT / "data/raw/release_evidences.json")
    features = load_json(ROOT / "models/model_features.json")
    diseases = {
        item["name"]
        for item in load_json(ROOT / "data/processed/diseases.json")
    }
    canonical = load_json(ROOT / "nlp/canonical_symptoms.json")

    nlp_features = {
        feature
        for symptom in canonical
        for feature in symptom.get("features", [])
    }

    eligible = sorted(
        code for code in features
        if code in nlp_features
        and code in metadata
        and metadata[code].get("data_type") == "B"
        and not metadata[code].get("is_antecedent", False)
    )

    if not eligible:
        raise ValueError("No NLP-supported binary features found")

    eligible_set = set(eligible)
    counts = Counter()
    modes = Counter()
    skipped = 0
    generated = 0

    source_path = ROOT / "data/raw/release_train_patients"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with source_path.open(
        encoding="utf-8", newline=""
    ) as source, output_path.open(
        "w", encoding="utf-8"
    ) as output:

        for row_number, row in enumerate(csv.DictReader(source), start=1):
            disease = row["PATHOLOGY"]

            if disease not in diseases:
                continue

            original = ast.literal_eval(row["EVIDENCES"])
            present = sorted(set(original) & eligible_set)

            if not present:
                skipped += 1
                continue

            # Per-source-row seed makes generation reproducible.
            rng = random.Random(f"{seed}:{row_number}")

            partial = make_partial_binary_case(
                original,
                metadata,
                eligible,
                rng,
                min_reported=2,
                max_reported=5,
            )

            if partial is None:
                partial = {
                    "present": present,
                    "absent": [],
                    "unknown": sorted(eligible_set - set(present)),
                }
                scenario_type = "original_binary_observation"
            else:
                scenario_type = "partial_binary_scenario"

            assert set(partial["present"]).issubset(set(original))
            assert partial["absent"] == []
            assert (
                set(partial["present"]) |
                set(partial["unknown"])
            ) == eligible_set
            assert not (
                set(partial["present"]) & set(partial["unknown"])
            )

            example = {
                "source_dataset": "DDXPlus",
                "source_split": "train",
                "source_row": row_number,
                "scenario_type": scenario_type,
                "age": int(float(row["AGE"])),
                "sex": row["SEX"].strip().upper(),
                "pathology": disease,
                **partial,
            }

            output.write(json.dumps(example) + "\n")

            generated += 1
            counts[disease] += 1
            modes[scenario_type] += 1

            if max_examples is not None and generated >= max_examples:
                break

    print("\nV2 DATASET BUILD")
    print("----------------------")
    print("NLP-supported features:", len(eligible))
    print("Generated examples:", generated)
    print("Diseases represented:", len(counts))
    print("Skipped (no supported symptoms):", skipped)
    print("Partial scenarios:", modes["partial_binary_scenario"])
    print("Original binary observations:",
          modes["original_binary_observation"])
    print("Seed:", seed)
    print("Output:", output_path)

    return counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-examples", type=int, default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(tempfile.gettempdir()) / "ddxplus_v2_training.jsonl",
    )

    args = parser.parse_args()

    build_dataset(
        output_path=args.output,
        max_examples=args.max_examples,
        seed=args.seed,
    )
