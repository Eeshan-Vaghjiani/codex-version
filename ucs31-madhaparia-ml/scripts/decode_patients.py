"""Decode DDXPlus patients into plain English, for the respiratory scope.

Companion to prepare_data.py. That script produces the numeric CSVs the model
trains on; this one produces a readable version of the same patients, for
understanding the data, writing the report, and picking demo cases.

Usage:
    python decode_patients.py <ddxplus_dir> <out_dir> [--limit N] [--splits train,test]

Writes, per split:
    <out_dir>/<split>_readable.csv   one row per patient, codes replaced by text
    <out_dir>/<split>_sample.txt     the first 20 patients, one line each
"""
import ast
import csv
import json
import os
import sys

EXTRA = ["Tuberculosis", "Pulmonary neoplasm", "Whooping cough"]


def load(src):
    with open(os.path.join(src, "release_conditions.json")) as f:
        conditions = json.load(f)
    with open(os.path.join(src, "release_evidences.json")) as f:
        evidences = json.load(f)
    return conditions, evidences


def respiratory(conditions):
    """Same selection rule as prepare_data.py: ICD-10 chapter J, plus EXTRA."""
    names = [k for k, v in conditions.items() if v["icd10-id"].upper().startswith("J")]
    return sorted(names + EXTRA)


def question_text(ev):
    """Short readable label for one evidence."""
    return ev.get("question_en") or ev.get("name") or "?"


def value_text(ev, value):
    """Readable text for a V_xx code, or the number itself for a scale."""
    meanings = ev.get("value_meaning") or {}
    entry = meanings.get(value)
    if isinstance(entry, dict):
        return entry.get("en") or entry.get("fr") or value
    if isinstance(entry, str):
        return entry
    return value


def decode_evidence(item, evidences):
    """'E_55_@_V_89' -> ('Where is the pain?: forehead', is_antecedent)."""
    if "_@_" in item:
        code, value = item.split("_@_", 1)
    else:
        code, value = item, None
    ev = evidences.get(code)
    if ev is None:
        return item, False
    label = question_text(ev)
    if value is not None:
        label = f"{label}: {value_text(ev, value)}"
    return label, bool(ev.get("is_antecedent"))


def decode_row(row, conditions, evidences, diseases):
    items = [decode_evidence(i, evidences) for i in ast.literal_eval(row["EVIDENCES"])]
    symptoms = [t for t, is_hist in items if not is_hist]
    history = [t for t, is_hist in items if is_hist]

    initial, _ = decode_evidence(row["INITIAL_EVIDENCE"], evidences)

    ddx = [(d, p) for d, p in ast.literal_eval(row["DIFFERENTIAL_DIAGNOSIS"]) if d in diseases]
    total = sum(p for _, p in ddx) or 1
    ddx = sorted(((d, p / total) for d, p in ddx), key=lambda x: -x[1])[:5]

    cond = conditions[row["PATHOLOGY"]]
    return {
        "PATHOLOGY": row["PATHOLOGY"],
        "ICD10": cond["icd10-id"].upper(),
        "SEVERITY": cond["severity"],
        "AGE": row["AGE"],
        "SEX": row["SEX"],
        "INITIAL_COMPLAINT": initial,
        "N_EVIDENCES": len(items),
        "SYMPTOMS": "; ".join(symptoms),
        "HISTORY": "; ".join(history),
        "TOP_DIFFERENTIAL": "; ".join(f"{d} {p:.0%}" for d, p in ddx),
    }


FIELDS = ["PATHOLOGY", "ICD10", "SEVERITY", "AGE", "SEX", "INITIAL_COMPLAINT",
          "N_EVIDENCES", "SYMPTOMS", "HISTORY", "TOP_DIFFERENTIAL"]


def one_line(d):
    parts = [f"{d['PATHOLOGY']}, {d['SEX']}, {d['AGE']}: {d['SYMPTOMS']}"]
    if d["HISTORY"]:
        parts.append(f"  history: {d['HISTORY']}")
    return "\n".join(parts)


def main(src, out, limit=None, splits=("train", "validate", "test")):
    os.makedirs(out, exist_ok=True)
    conditions, evidences = load(src)
    diseases = set(respiratory(conditions))

    for split in splits:
        path = os.path.join(src, f"release_{split}_patients")
        if not os.path.exists(path):
            print(f"{split}: no file at {path}, skipped")
            continue
        n = 0
        sample = []
        with open(path) as fin, \
                open(os.path.join(out, f"{split}_readable.csv"), "w", newline="") as fout:
            w = csv.DictWriter(fout, fieldnames=FIELDS)
            w.writeheader()
            for r in csv.DictReader(fin):
                if r["PATHOLOGY"] not in diseases:
                    continue
                d = decode_row(r, conditions, evidences, diseases)
                w.writerow(d)
                if len(sample) < 20:
                    sample.append(one_line(d))
                n += 1
                if limit and n >= limit:
                    break
        with open(os.path.join(out, f"{split}_sample.txt"), "w") as f:
            f.write("\n\n".join(sample) + "\n")
        print(f"{split}: {n} patients decoded")

    print(f"{len(diseases)} diseases in scope")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = dict(a.lstrip("-").split("=", 1) for a in sys.argv[1:] if a.startswith("--"))
    if len(args) < 2:
        sys.exit(__doc__)
    main(args[0], args[1],
         limit=int(flags["limit"]) if "limit" in flags else None,
         splits=tuple(flags["splits"].split(",")) if "splits" in flags
         else ("train", "validate", "test"))
