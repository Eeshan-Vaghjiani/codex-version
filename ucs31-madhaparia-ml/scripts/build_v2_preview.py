
"""Build a representative V2 development preview from DDXPlus training only."""

import ast
import csv
import json
import random
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

from prepare_v2_data import make_partial_binary_case

SEED = 42
PER_DISEASE = 50

csv.field_size_limit(2_147_483_647)

with open("data/raw/release_evidences.json", encoding="utf-8") as f:
    metadata = json.load(f)


with open("nlp/canonical_symptoms.json", encoding="utf-8") as f:
    canonical_symptoms = json.load(f)

nlp_features = {
    feature
    for symptom in canonical_symptoms
    for feature in symptom.get("features", [])
}

with open("models/model_features.json", encoding="utf-8") as f:
    features = json.load(f)

with open("data/processed/diseases.json", encoding="utf-8") as f:
    diseases = {d["name"] for d in json.load(f)}


eligible = {
    code for code in features
    if code in nlp_features
    and code in metadata
    and metadata[code].get("data_type") == "B"
    and not metadata[code].get("is_antecedent", False)
}

print("NLP-supported binary features:", len(eligible))

rng = random.Random(SEED)
samples = defaultdict(list)
counts = Counter()

# Reservoir sampling avoids favouring the first records.
with open("data/raw/release_train_patients", encoding="utf-8", newline="") as f:
    for row_number, row in enumerate(csv.DictReader(f), start=1):
        disease = row["PATHOLOGY"]

        if disease not in diseases:
            continue

        original_evidence = set(ast.literal_eval(row["EVIDENCES"]))

        if not (original_evidence & eligible):
            continue

        counts[disease] += 1
        record = (row_number, row)

        selected = samples[disease]

        if len(selected) < PER_DISEASE:
            selected.append(record)
        else:
            index = rng.randrange(counts[disease])
            if index < PER_DISEASE:
                selected[index] = record

output_path = Path(tempfile.gettempdir()) / "ddxplus_v2_stratified_preview.jsonl"

mode_counts = Counter()
disease_counts = Counter()

with output_path.open("w", encoding="utf-8") as output:
    for disease in sorted(diseases):
        for row_number, row in samples[disease]:
            original = ast.literal_eval(row["EVIDENCES"])
            partial = make_partial_binary_case(
                original, metadata, sorted(eligible), rng,
                min_reported=2,
                max_reported=5
            )

            if partial is None:
                # No artificial extra symptoms or negative findings.
                present = sorted(set(original) & eligible)
                partial = {
                    "present": present,
                    "absent": [],
                    "unknown": sorted(eligible - set(present)),
                }
                mode = "original_binary_observation"
            else:
                mode = "partial_binary_scenario"

            example = {
                "source_dataset": "DDXPlus",
                "source_split": "train",
                "source_row": row_number,
                "scenario_type": mode,
                "age": int(float(row["AGE"])),
                "sex": row["SEX"].strip().upper(),
                "pathology": disease,
                **partial
            }

            assert not (set(partial["present"]) & set(partial["unknown"]))
            assert partial["absent"] == []

            output.write(json.dumps(example) + "\n")
            mode_counts[mode] += 1
            disease_counts[disease] += 1

print("\nV2 STRATIFIED PREVIEW")
print("----------------------")
print("Diseases represented:", len(disease_counts))
print("Total examples:", sum(disease_counts.values()))

print("\nScenario types:")
for name, count in sorted(mode_counts.items()):
    print(f"  {name}: {count}")

print("\nExamples by disease:")
for name, count in sorted(disease_counts.items()):
    print(f"  {name}: {count}")

print("\nOutput:", output_path)

assert set(disease_counts) == diseases, "Some diseases are missing."
print("\nPreview validation passed!")
