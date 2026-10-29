"""
Prepare the DDXPlus respiratory subset for machine learning.

Usage:
    python prepare_data.py <ddxplus_dir> <out_dir>

Example:
    python scripts/prepare_data.py data/raw data/processed

Outputs:
    train.csv
    validate.csv
    test.csv
    features.json
    diseases.json

The respiratory scope is:
    - ICD-10 Chapter J
    - Tuberculosis
    - Pulmonary neoplasm
    - Whooping cough
"""

import ast
import csv
import json
import os
import sys


EXTRA = [
    "Tuberculosis",
    "Pulmonary neoplasm",
    "Whooping cough",
]


# Allow very large CSV fields safely.
csv.field_size_limit(2_147_483_647)


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def respiratory_conditions(conditions):
    """
    Select ICD-10 Chapter J conditions plus the three agreed additions.
    """
    names = [
        name
        for name, info in conditions.items()
        if info["icd10-id"].upper().startswith("J")
    ]

    for name in EXTRA:
        if name not in names:
            names.append(name)

    return sorted(names)


def linked_evidence_codes(conditions, diseases):
    """
    Collect all evidence codes linked to the selected diseases.

    Includes both symptoms and antecedents/history.
    """
    codes = set()

    for disease in diseases:
        info = conditions[disease]

        codes.update(info.get("symptoms", {}).keys())
        codes.update(info.get("antecedents", {}).keys())

    return sorted(
        codes,
        key=lambda x: int(x.split("_")[1])
    )


def is_numeric_values(values):
    """
    Return True when all possible values are numeric.
    """
    if not values:
        return False

    return all(isinstance(v, (int, float)) for v in values)


def build_evidence_features(evidences, evidence_codes):
    """
    Build the ordered evidence feature columns.

    B:
        one binary feature, e.g. E_91

    M:
        one binary feature per possible value,
        e.g. E_55_@_V_89

    C:
        numeric scales remain one numeric feature,
        e.g. E_56

        categorical values are one-hot encoded,
        but the default/reference category is dropped.
    """
    features = []

    for code in evidence_codes:
        ev = evidences[code]

        data_type = ev["data_type"]
        values = ev.get("possible-values", [])

        if data_type == "B":
            features.append(code)

        elif data_type == "M":
            for value in values:
                features.append(f"{code}_@_{value}")

        elif data_type == "C":
            if is_numeric_values(values):
                features.append(code)
            else:
                default = ev.get("default_value")

                for value in values:
                    if value != default:
                        features.append(f"{code}_@_{value}")

        else:
            raise ValueError(
                f"Unsupported evidence type {data_type!r} for {code}"
            )

    return features

def parse_numeric(value):
    """
    Convert a numeric string such as '4' into int/float.
    """
    try:
        number = float(value)

        if number.is_integer():
            return int(number)

        return number

    except ValueError:
        return 0


def encode_evidences(items, evidences, feature_index):
    """
    Encode one patient's DDXPlus evidence list into the model feature vector.
    """
    values = [0] * len(feature_index)

    # Dictionary mapping feature name -> vector position.
    index = feature_index

    for item in items:

        # Example:
        # E_91
        if "_@_" not in item:
            if item in index:
                values[index[item]] = 1
            continue

        # Examples:
        # E_55_@_V_89
        # E_56_@_4
        code, value = item.split("_@_", 1)

        ev = evidences.get(code)

        if ev is None:
            continue

        data_type = ev["data_type"]
        possible_values = ev.get("possible-values", [])

        if data_type == "C" and is_numeric_values(possible_values):

            # Numeric scale such as pain intensity.
            if code in index:
                values[index[code]] = parse_numeric(value)

        else:

            # Multi-choice or categorical one-hot value.
            feature_name = f"{code}_@_{value}"

            if feature_name in index:
                values[index[feature_name]] = 1

    return values


def normalise_ddx(raw_ddx, diseases):
    """
    Keep only diseases inside the respiratory scope and re-normalise
    their probabilities so that the remaining probabilities sum to 1.
    """
    ddx = ast.literal_eval(raw_ddx)

    filtered = [
        (disease, float(probability))
        for disease, probability in ddx
        if disease in diseases
    ]

    total = sum(probability for _, probability in filtered)

    if total <= 0:
        return []

    normalised = [
        [disease, probability / total]
        for disease, probability in filtered
    ]

    normalised.sort(
        key=lambda x: x[1],
        reverse=True
    )

    return normalised


def process_split(
    src,
    out,
    split,
    diseases,
    evidences,
    model_features,
    evidence_features,
):
    """
    Process one official DDXPlus split.
    """

    input_path = os.path.join(
        src,
        f"release_{split}_patients"
    )

    output_path = os.path.join(
        out,
        f"{split}.csv"
    )

    evidence_index = {
        feature: i
        for i, feature in enumerate(evidence_features)
    }

    output_columns = (
        model_features
        + [
            "PATHOLOGY",
            "INITIAL_EVIDENCE",
            "DDX",
        ]
    )

    count = 0

    with open(
        input_path,
        "r",
        encoding="utf-8",
        newline=""
    ) as fin, open(
        output_path,
        "w",
        encoding="utf-8",
        newline=""
    ) as fout:

        reader = csv.DictReader(fin)

        writer = csv.writer(fout)

        writer.writerow(output_columns)

        for row in reader:

            pathology = row["PATHOLOGY"]

            if pathology not in diseases:
                continue

            raw_evidences = ast.literal_eval(
                row["EVIDENCES"]
            )

            encoded = encode_evidences(
                raw_evidences,
                evidences,
                evidence_index,
            )

            age = int(float(row["AGE"]))

            sex_m = (
                1
                if row["SEX"].strip().upper() == "M"
                else 0
            )

            ddx = normalise_ddx(
                row["DIFFERENTIAL_DIAGNOSIS"],
                diseases,
            )

            output_row = (
                [age, sex_m]
                + encoded
                + [
                    pathology,
                    row["INITIAL_EVIDENCE"],
                    json.dumps(ddx),
                ]
            )

            writer.writerow(output_row)

            count += 1

            if count % 50000 == 0:
                print(
                    f"{split}: {count:,} respiratory patients processed..."
                )

    print(
        f"{split}: {count:,} patients written to {output_path}"
    )

    return count


def save_metadata(
    out,
    conditions,
    diseases,
    model_features,
):
    """
    Save feature ordering and disease metadata.
    """

    features_path = os.path.join(
        out,
        "features.json"
    )

    with open(
        features_path,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            model_features,
            f,
            indent=2,
        )

    disease_records = []

    for name in diseases:
        info = conditions[name]

        disease_records.append(
            {
                "name": name,
                "icd10": info["icd10-id"].upper(),
                "severity": info["severity"],
            }
        )

    diseases_path = os.path.join(
        out,
        "diseases.json"
    )

    with open(
        diseases_path,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            disease_records,
            f,
            indent=2,
        )


def main(src, out):

    os.makedirs(
        out,
        exist_ok=True
    )

    conditions = load_json(
        os.path.join(
            src,
            "release_conditions.json"
        )
    )

    evidences = load_json(
        os.path.join(
            src,
            "release_evidences.json"
        )
    )

    diseases = respiratory_conditions(
        conditions
    )

    evidence_codes = linked_evidence_codes(
        conditions,
        diseases
    )

    evidence_features = build_evidence_features(
        evidences,
        evidence_codes
    )

    model_features = (
        ["AGE", "SEX_M"]
        + evidence_features
    )

    print()
    print("DDXPlus respiratory preparation")
    print("--------------------------------")
    print(
        f"Diseases in scope: {len(diseases)}"
    )
    print(
        f"Linked evidence codes: {len(evidence_codes)}"
    )
    print(
        f"Evidence feature columns: {len(evidence_features)}"
    )
    print(
        f"Total model features: {len(model_features)}"
    )
    print()

    # Validation against the current agreed dataset scope.
    if len(diseases) != 21:
        raise ValueError(
            f"Expected 21 diseases, found {len(diseases)}"
        )

    if len(evidence_codes) != 110:
        raise ValueError(
            f"Expected 110 linked evidences, found {len(evidence_codes)}"
        )

    if len(model_features) != 797:
        raise ValueError(
            f"Expected 797 model features, found {len(model_features)}"
        )

    save_metadata(
        out,
        conditions,
        diseases,
        model_features,
    )

    counts = {}

    for split in (
        "train",
        "validate",
        "test",
    ):
        counts[split] = process_split(
            src,
            out,
            split,
            set(diseases),
            evidences,
            model_features,
            evidence_features,
        )

    print()
    print("Finished.")
    print("--------------------------------")
    print(
        f"train:    {counts['train']:,}"
    )
    print(
        f"validate: {counts['validate']:,}"
    )
    print(
        f"test:     {counts['test']:,}"
    )
    print(
        f"{len(diseases)} diseases, "
        f"{len(model_features)} feature columns"
    )


if __name__ == "__main__":

    if len(sys.argv) != 3:
        sys.exit(
            "Usage: python prepare_data.py "
            "<ddxplus_dir> <out_dir>"
        )

    main(
        sys.argv[1],
        sys.argv[2],
    )