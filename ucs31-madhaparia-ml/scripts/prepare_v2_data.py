
"""Prepare controlled partial-symptom scenarios for Random Forest V2.

The original DDXPlus datasets must remain unchanged.
Only confirmed positive binary symptoms are sampled here.
Unreported symptoms are unknown, not confirmed absent.
"""

import random


def make_partial_binary_case(
    evidence_items,
    evidence_metadata,
    feature_names,
    rng,
    min_reported=2,
    max_reported=5,
):
    """Create one partial-information scenario from existing evidence."""

    if min_reported < 1 or max_reported < min_reported:
        raise ValueError("Invalid symptom count limits")

    eligible = {
        code
        for code in feature_names
        if code in evidence_metadata
        and evidence_metadata[code].get("data_type") == "B"
        and not evidence_metadata[code].get("is_antecedent", False)
    }

    original_present = sorted(
        set(evidence_items) & eligible
    )

    # Require at least one symptom to be hidden.
    if len(original_present) <= min_reported:
        return None

    max_keep = min(max_reported, len(original_present) - 1)
    count = rng.randint(min_reported, max_keep)

    reported = sorted(rng.sample(original_present, count))

    return {
        "present": reported,
        "absent": [],
        "unknown": sorted(eligible - set(reported)),
    }


def create_v2_preview(max_examples=1000, seed=42):
    import ast
    import csv
    import json
    import tempfile
    from collections import Counter
    from pathlib import Path

    csv.field_size_limit(2_147_483_647)

    with open("data/raw/release_evidences.json", encoding="utf-8") as f:
        metadata = json.load(f)

    with open("models/model_features.json", encoding="utf-8") as f:
        features = json.load(f)

    with open("data/processed/diseases.json", encoding="utf-8") as f:
        diseases = {item["name"] for item in json.load(f)}

    rng = random.Random(seed)

    output_path = (
        Path(tempfile.gettempdir())
        / "ddxplus_v2_partial_preview.jsonl"
    )

    generated = 0
    checked = 0
    disease_counts = Counter()

    with open(
        "data/raw/release_train_patients",
        encoding="utf-8",
        newline=""
    ) as source, output_path.open(
        "w",
        encoding="utf-8"
    ) as output:

        for row_number, row in enumerate(csv.DictReader(source), start=1):

            if row["PATHOLOGY"] not in diseases:
                continue

            checked += 1

            original = ast.literal_eval(row["EVIDENCES"])

            partial = make_partial_binary_case(
                evidence_items=original,
                evidence_metadata=metadata,
                feature_names=features,
                rng=rng,
                min_reported=2,
                max_reported=5,
            )

            if partial is None:
                continue

            example = {
                "source_dataset": "DDXPlus",
                "source_split": "train",
                "source_row": row_number,
                "variant": 0,
                "age": int(float(row["AGE"])),
                "sex": row["SEX"].strip().upper(),
                "pathology": row["PATHOLOGY"],
                **partial,
            }

            output.write(json.dumps(example) + "\n")

            disease_counts[row["PATHOLOGY"]] += 1
            generated += 1

            if generated >= max_examples:
                break

    print("\nV2 DATA PREVIEW")
    print("-------------------------")
    print("Original records examined:", checked)
    print("Generated examples:", generated)
    print("Diseases represented:", len(disease_counts))
    print("Random seed:", seed)
    print("Output:", output_path)

    print("\nTop five diagnoses:")
    for disease, count in disease_counts.most_common(5):
        print(f"  {disease}: {count}")

    return output_path


if __name__ == "__main__":
    create_v2_preview()
