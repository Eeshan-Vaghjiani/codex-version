"""Evaluate frozen application models without fitting or threshold tuning.

DDXPlus is simulated data. Sparse cases retain source diagnoses solely for
research comparison; they are not independent clinical validation. Added V2
classes have no test ground truth. Run from the ML root with
``python scripts/audit_saved_model_reliability.py``.
"""

import ast
import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix, log_loss

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUTPUT = ROOT / "reports/autonomous_audit"
SEED = 20261027


def fingerprint(age, sex, evidence):
    value = json.dumps([age, sex, sorted(evidence)], separators=(",", ":"))
    return hashlib.sha256(value.encode()).digest()


def reliability_metrics(actual, probabilities, labels, source_labels):
    """Compute multiclass Brier score and 10-bin top-label ECE explicitly."""
    actual = np.asarray(actual)
    labels = np.asarray(labels)
    winners = probabilities.argmax(axis=1)
    predicted = labels[winners]
    confidence = probabilities.max(axis=1)
    correct = predicted == actual
    target = (actual[:, None] == labels[None, :]).astype(float)
    bins = []
    for bin_index in range(10):
        lower, upper = bin_index / 10, (bin_index + 1) / 10
        selected = (confidence >= lower) & (confidence < upper)
        if bin_index == 9:
            selected |= confidence == 1
        if selected.any():
            bins.append({"lower": round(float(lower), 1),
                         "count": int(selected.sum()),
                         "accuracy": float(correct[selected].mean()),
                         "mean_score": float(confidence[selected].mean())})
    report = classification_report(actual, predicted, labels=labels,
                                   output_dict=True, zero_division=0)
    return {
        "cases": len(actual), "source_classes_represented": len(set(actual)),
        "accuracy": float(correct.mean()),
        "macro_f1_all_model_classes": report["macro avg"]["f1-score"],
        "macro_f1_21_source_classes": float(np.mean([
            report[str(label)]["f1-score"] for label in source_labels])),
        "macro_precision_21_source_classes": float(np.mean([
            report[str(label)]["precision"] for label in source_labels])),
        "macro_recall_21_source_classes": float(np.mean([
            report[str(label)]["recall"] for label in source_labels])),
        "log_loss": float(log_loss(actual, probabilities, labels=labels)),
        "multiclass_brier": float(np.square(probabilities-target).sum(axis=1).mean()),
        "top_label_ece_10_bins": float(sum(
            b["count"] / len(actual) * abs(b["accuracy"]-b["mean_score"])
            for b in bins)),
        "score_bins": bins,
        "scores_at_least_0_9": int((confidence >= .9).sum()),
        "errors_at_scores_at_least_0_9": int(((confidence >= .9) & ~correct).sum()),
        "predicted_counts": dict(Counter(predicted)),
    }, report, predicted


def save_evaluation(name, model, frame, actual, source_labels):
    probabilities = model.predict_proba(frame)
    metrics, report, predicted = reliability_metrics(actual, probabilities, model.classes_, source_labels)
    pd.DataFrame(report).T.to_csv(OUTPUT / f"{name}_per_class.csv")
    pd.DataFrame(confusion_matrix(actual, predicted, labels=model.classes_),
                 index=model.classes_, columns=model.classes_).to_csv(
                     OUTPUT / f"{name}_confusion.csv")
    print(name, json.dumps({k: metrics[k] for k in (
        "cases", "accuracy", "macro_f1_21_source_classes", "top_label_ece_10_bins")}), flush=True)
    return metrics


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    csv.field_size_limit(2_147_483_647)
    schema = json.loads((ROOT / "models/v2_feature_schema.json").read_text())
    codes = schema["symptom_features"]
    code_set = set(codes)
    v1_names = json.loads((ROOT / "models/model_features.json").read_text())
    v1 = joblib.load(ROOT / "models/respiratory_random_forest_v1.joblib")
    v2 = joblib.load(ROOT / "models/rf_v2_23class_prototype.joblib")
    assert list(v1.feature_names_in_) == v1_names
    assert list(v2.feature_names_in_) == schema["feature_names"]
    assert set(v1.classes_).issubset(set(v2.classes_))
    source_classes = set(v1.classes_)
    # Read each original source once; label-independent hashes audit exact
    # overlap and conflicting labels without changing a single dataset row.
    train_hashes = defaultdict(set)
    train_count = 0
    train_counts = Counter()
    for row in csv.DictReader((ROOT / "data/raw/release_train_patients").open(encoding="utf8", newline="")):
        if row["PATHOLOGY"] not in source_classes:
            continue
        ev = ast.literal_eval(row["EVIDENCES"])
        key = fingerprint(float(row["AGE"]), row["SEX"].upper(), ev)
        train_hashes[key].add(row["PATHOLOGY"])
        train_count += 1
        train_counts[row["PATHOLOGY"]] += 1
    print("Training signatures loaded", train_count, len(train_hashes), flush=True)
    actual, vectors, positives, overlaps = [], [], [], []
    test_hashes = Counter()
    unknown_counts = Counter()
    test_counts = Counter()
    for row in csv.DictReader((ROOT / "data/raw/release_test_patients").open(encoding="utf8", newline="")):
        if row["PATHOLOGY"] not in source_classes:
            continue
        evidence = ast.literal_eval(row["EVIDENCES"])
        age, sex = float(row["AGE"]), row["SEX"].upper()
        present = code_set & set(evidence)
        key = fingerprint(age, sex, evidence)
        test_hashes[key] += 1
        overlaps.append(key in train_hashes)
        actual.append(row["PATHOLOGY"])
        test_counts[row["PATHOLOGY"]] += 1
        positives.append(sorted(present))
        unknown_counts[len(present)] += 1
        vectors.append([age, float(sex == "M")] + [float(code in present) for code in codes] + [0.] * len(codes))
    full_v2 = pd.DataFrame(vectors, columns=schema["feature_names"], dtype=np.float32)
    full_v1 = pd.read_csv(ROOT / "data/processed/test.csv", usecols=v1_names + ["PATHOLOGY"])
    assert full_v1["PATHOLOGY"].tolist() == actual
    full_v1 = full_v1[v1_names].astype(np.float32)
    result = {
        "methodology": {"source": "frozen DDXPlus test partition", "seed": SEED,
            "no_training_or_threshold_tuning": True,
            "sparse_selection": "Deterministic nested random subsets; eligible source cases have at least k supported positives; all unmentioned evidence remains unknown.",
            "v1_full": "Original 198-feature processed test data",
            "v2_full": "All 32 supported binary positives, no invented absences",
            "calibration": "Uncalibrated scores; 10 equal-width top-label ECE bins and unscaled multiclass Brier",
            "macro_averaging": "Macro metrics use all 21 original source classes even if a sparse subset contains zero examples of one class. All-model macro metrics also include the 2 classes with no independent test labels.",
            "limitations": ["Simulated data only", "Test split has previously been evaluated for V1 and may have been inspected historically; no pristine clinical holdout exists", "Exact overlap removal cannot exclude near-duplicate or generator-pattern leakage", "COVID-19 and allergic rhinitis lack independent test labels", "Synthetic sparse inputs do not measure free-text or clinical accuracy"]},
        "artifacts_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (
            ROOT / "models/respiratory_random_forest_v1.joblib", ROOT / "models/rf_v2_23class_prototype.joblib",
            ROOT / "models/v2_feature_schema.json")},
        "dataset": {"training_records": train_count, "unique_training_raw_inputs": len(train_hashes),
            "duplicate_training_raw_input_records": train_count-len(train_hashes),
            "conflicting_training_raw_input_signatures": sum(len(v)>1 for v in train_hashes.values()),
            "test_records": len(actual), "unique_test_raw_inputs": len(test_hashes),
            "test_records_exactly_matching_training_raw_inputs": sum(overlaps),
            "train_class_counts": dict(train_counts), "test_class_counts": dict(test_counts),
            "supported_positive_symptom_count_distribution_test": dict(sorted(unknown_counts.items()))},
        "evaluations": {},
        "majority_training_class_baseline": {"class": train_counts.most_common(1)[0][0],
            "test_accuracy": test_counts[train_counts.most_common(1)[0][0]] / len(actual)},
    }
    result["evaluations"]["v1_full"] = save_evaluation("v1_full", v1, full_v1, actual, sorted(source_classes))
    result["evaluations"]["v2_full"] = save_evaluation("v2_full", v2, full_v2, actual, sorted(source_classes))
    non_overlap = ~np.array(overlaps)
    actual_array = np.array(actual)
    for name, model, frame in (("v1_full_no_exact_train_overlap", v1, full_v1), ("v2_full_no_exact_train_overlap", v2, full_v2)):
        result["evaluations"][name] = save_evaluation(name, model, frame[non_overlap], actual_array[non_overlap], sorted(source_classes))
    rng = np.random.default_rng(SEED)
    permutations = [rng.permutation(p).tolist() for p in positives]
    for count in (1, 2, 3):
        eligible = np.array([len(p) >= count for p in positives])
        sparse_v2 = full_v2[eligible].copy()
        sparse_v2.iloc[:, 2:] = 0.
        sparse_v1 = full_v1[eligible].copy()
        sparse_v1.iloc[:, 2:] = 0.
        indices = np.flatnonzero(eligible)
        for target, source in enumerate(indices):
            for code in permutations[source][:count]:
                sparse_v2.iat[target, sparse_v2.columns.get_loc(code + "__present")] = 1.
                sparse_v1.iat[target, sparse_v1.columns.get_loc(code)] = 1.
        for name, model, frame in ((f"v1_sparse_{count}", v1, sparse_v1), (f"v2_sparse_{count}", v2, sparse_v2)):
            result["evaluations"][name] = save_evaluation(name, model, frame, actual_array[eligible], sorted(source_classes))
    (OUTPUT / "model_reliability.json").write_text(json.dumps(result, indent=2), encoding="utf8")
    print("Saved", OUTPUT / "model_reliability.json", flush=True)


if __name__ == "__main__":
    main()
