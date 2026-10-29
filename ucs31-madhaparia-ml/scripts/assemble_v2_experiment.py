
"""Assemble the 23-condition V2 research training dataset.

Combines DDXPlus-derived training scenarios with synthetic
COVID-19 and allergic-rhinitis examples.

Does not modify existing models or test datasets.
"""

import csv
import json
import tempfile
from collections import Counter
from itertools import zip_longest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMP = Path(tempfile.gettempdir())

ORIGINAL = TEMP / "ddxplus_v2_encoded"
CANDIDATE = TEMP / "v2_candidate_encoded_66"

OUTPUT = (
    TEMP
    / "v2_23class_experiment"
    / "assembled_66"
)

SCHEMA_PATH = ROOT / "models/v2_feature_schema.json"

NEW_CONDITIONS = {
    "COVID-19",
    "Allergic rhinitis"
}


def append_dataset(
    directory,
    source_name,
    feature_names,
    x_writer,
    y_writer,
    p_writer,
    counts,
    sources
):
    paths = [
        directory / "X_train.csv",
        directory / "y_train.csv",
        directory / "provenance.csv"
    ]

    if source_name == "reference_guided_synthetic":
        paths[0] = directory / "X_candidates.csv"
        paths[1] = directory / "y_candidates.csv"

    for path in paths:
        assert path.is_file(), f"Missing file: {path}"

    with (
        paths[0].open(
            newline="", encoding="utf-8-sig"
        ) as xf,
        paths[1].open(
            newline="", encoding="utf-8-sig"
        ) as yf,
        paths[2].open(
            newline="", encoding="utf-8-sig"
        ) as pf
    ):
        xr = csv.reader(xf)
        yr = csv.reader(yf)
        pr = csv.reader(pf)

        assert next(xr) == feature_names, (
            f"Feature mismatch: {source_name}"
        )

        assert next(yr) == ["PATHOLOGY"]

        provenance_columns = next(pr)

        for features, label, provenance in zip_longest(
            xr, yr, pr
        ):
            if any(
                item is None
                for item in (features, label, provenance)
            ):
                raise ValueError(
                    f"Row count mismatch: {source_name}"
                )

            assert len(features) == 66
            assert len(label) == 1

            assert len(provenance) == len(
                provenance_columns
            )

            disease = label[0]

            if source_name == "reference_guided_synthetic":
                assert disease in NEW_CONDITIONS
            else:
                assert disease not in NEW_CONDITIONS

            x_writer.writerow(features)
            y_writer.writerow(label)

            metadata = dict(
                zip(provenance_columns, provenance)
            )

            p_writer.writerow([
                source_name,
                "yes" if (
                    source_name == "reference_guided_synthetic"
                ) else "no",
                json.dumps(
                    metadata,
                    ensure_ascii=False
                )
            ])

            counts[disease] += 1
            sources[source_name] += 1


def main():
    schema = json.loads(
        SCHEMA_PATH.read_text(encoding="utf-8")
    )

    names = schema["feature_names"]

    assert len(names) == 66
    assert schema["feature_count"] == 66

    OUTPUT.mkdir(
        parents=True,
        exist_ok=True
    )

    counts = Counter()
    sources = Counter()

    with (
        (OUTPUT / "X_experimental.csv").open(
            "w", newline="", encoding="utf-8"
        ) as xf,
        (OUTPUT / "y_experimental.csv").open(
            "w", newline="", encoding="utf-8"
        ) as yf,
        (OUTPUT / "provenance_experimental.csv").open(
            "w", newline="", encoding="utf-8"
        ) as pf
    ):
        x_writer = csv.writer(xf)
        y_writer = csv.writer(yf)
        p_writer = csv.writer(pf)

        x_writer.writerow(names)
        y_writer.writerow(["PATHOLOGY"])

        p_writer.writerow([
            "source_group",
            "reference_guided_candidate",
            "original_provenance_json"
        ])

        # Original 21-condition training set.
        append_dataset(
            ORIGINAL,
            "ddxplus_derived",
            names,
            x_writer,
            y_writer,
            p_writer,
            counts,
            sources
        )

        # Two additional synthetic conditions.
        append_dataset(
            CANDIDATE,
            "reference_guided_synthetic",
            names,
            x_writer,
            y_writer,
            p_writer,
            counts,
            sources
        )

    assert sources["ddxplus_derived"] == 443067

    assert sources["reference_guided_synthetic"] == 800

    assert counts["COVID-19"] == 400
    assert counts["Allergic rhinitis"] == 400

    assert len(counts) == 23

    assert sum(counts.values()) == 443867

    print("STEP 136 - V2 23-CONDITION DATASET ASSEMBLY")
    print("--------------------------------------------")
    print("Total training scenarios:", sum(counts.values()))
    print("Total conditions:", len(counts))
    print("Numerical features:", len(names))

    print("\nDATA SOURCES")
    print("--------------------------------------------")
    print(
        "DDXPlus-derived:",
        sources["ddxplus_derived"]
    )
    print(
        "Reference-guided synthetic:",
        sources["reference_guided_synthetic"]
    )

    print("\nNEW CONDITIONS")
    print("--------------------------------------------")
    print("COVID-19:", counts["COVID-19"])
    print(
        "Allergic rhinitis:",
        counts["Allergic rhinitis"]
    )

    print("\nVALIDATION")
    print("--------------------------------------------")
    print("Original V1 model modified: NO")
    print("Original V2 model modified: NO")
    print("Original training files modified: NO")
    print("Validation/test data included: NO")
    print("Clinical validation performed: NO")
    print("Output:", OUTPUT)

    print("\nStep 136 PASSED!")


if __name__ == "__main__":
    main()
