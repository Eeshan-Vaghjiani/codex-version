"""Freeze a V3 baseline, fit a separate selective policy, and report matched cases.

No model fitting occurs here. The simulated source validation bound is not a
clinical certification. All threshold selection precedes test-policy scoring.
Run --baseline first; then run without arguments. Cached cohorts avoid repeated
reads of the 804 MB source-training CSV.
"""
import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
import numpy as np
import pandas as pd
from scipy.stats import beta
from sklearn.metrics import classification_report, confusion_matrix, log_loss

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from inference.v3_predictor import MODEL_PATH, load_v3_bundle, predict_v3
from inference.primary_selection import RESPIRATORY_ANCHOR_FEATURES, SCOPE_POLICY_PATH, SCOPE_POLICY_VERSION, load_primary_scope
from scripts.train_v3_partial_evidence import CLASSES, FEATURES, SOURCE_FEATURES, masks, read_source, score, subset

OUT = ROOT / "reports/kenya_patient_experience"
CACHE = ROOT / "data/processed/primary_selection_cache"
POLICY = ROOT / "models/v3_primary_selection.json"
SCENARIOS = [(1, 0), (2, 0), (3, 0), (3, 3), (8, 0), (8, 5)]
RISK = .10  # Declared engineering experiment; not a clinical risk standard.
DELTA = .05
MAX_POSITIVE, MAX_NEGATIVE = 8, 5


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf8")


def unique_profiles(data):
    # Select first row per full label-independent profile, without examining y.
    indices = np.sort(np.unique(data["signature"], return_index=True)[1])
    return subset(data, indices)


def cohorts():
    CACHE.mkdir(parents=True, exist_ok=True)
    paths = [ROOT / f"data/processed/{name}.csv" for name in ("train", "validate", "test")]
    manifest = {str(p.name): {"bytes": p.stat().st_size, "mtime_ns": p.stat().st_mtime_ns} for p in paths}
    manifest["signature_features"] = SOURCE_FEATURES
    cached = CACHE / "cohorts.npz"
    manifest_path = CACHE / "manifest.json"
    if cached.exists() and manifest_path.exists() and json.loads(manifest_path.read_text()) == manifest:
        with np.load(cached) as stored:
            result = {name: {key: stored[f"{name}_{key}"] for key in ("x", "age", "sex", "y", "signature")}
                      for name in ("tuning", "calibration", "validation", "test")}
        return result, json.loads((CACHE / "split_summary.json").read_text())
    signatures = []
    for frame in pd.read_csv(paths[0], usecols=SOURCE_FEATURES, dtype={f: "float32" for f in SOURCE_FEATURES}, chunksize=50000):
        signatures.append(pd.util.hash_pandas_object(frame[SOURCE_FEATURES], index=False).to_numpy())
    train_signatures = np.concatenate(signatures)
    print("Loaded source-training signatures", len(train_signatures), flush=True)
    val = read_source("validate")
    clean = subset(val, ~np.isin(val["signature"], train_signatures))
    tuning = unique_profiles(subset(clean, clean["signature"] % 2 == 0))
    calibration = unique_profiles(subset(clean, clean["signature"] % 4 == 1))
    validation = unique_profiles(subset(clean, clean["signature"] % 4 == 3))
    test_raw = read_source("test")
    test = subset(test_raw, ~np.isin(test_raw["signature"], np.concatenate([train_signatures, val["signature"]])))
    result = dict(tuning=tuning, calibration=calibration, validation=validation, test=test)
    summary = {
        "training_records": len(train_signatures),
        "original_tuning_records": int((clean["signature"] % 2 == 0).sum()),
        "original_reporting_validation_records": int((clean["signature"] % 2 == 1).sum()),
        "independent_profile_counts": {name: len(value["y"]) for name, value in result.items()},
        "unique_source_profiles": {name: len(np.unique(value["signature"])) for name, value in result.items()},
        "source_training_overlap_removed_from_validation": len(val["y"]) - len(clean["y"]),
        "source_train_or_validation_overlap_removed_from_test": len(test_raw["y"]) - len(test["y"]),
        "policy": "V3 retained unchanged. Original signature-even tuning selects thresholds. Previously reporting-only signature%4==1 source profiles validate selected risk bounds; signature%4==3 profiles report validation. Test excludes every source training/validation signature. Tuning/calibration/reporting-validation use first label-blind row per complete-198-feature signature. The 53,387 retained test records include one without supported positive evidence; the same 53,386 eligible cases as prior V3 are used for disease-ranking metrics.",
        "source_hash_fingerprint": manifest,
    }
    np.savez_compressed(cached, **{f"{name}_{key}": values for name, data in result.items() for key, values in data.items()})
    dump(manifest_path, manifest)
    dump(CACHE / "split_summary.json", summary)
    return result, summary


def summarize(y, probabilities, accepted=None):
    n = len(y)
    predicted = probabilities.argmax(axis=1)
    selected = np.ones(n, dtype=bool) if accepted is None else np.asarray(accepted, dtype=bool)
    all_report = classification_report(y, predicted, labels=range(len(CLASSES)), target_names=CLASSES, output_dict=True, zero_division=0)
    shown = predicted.copy()
    shown[~selected] = len(CLASSES)
    # Abstention is a false negative for its true class; it cannot become a true
    # negative for another class. Specificity below is defined only on accepted.
    full_report = classification_report(y, shown, labels=range(len(CLASSES)), target_names=CLASSES, output_dict=True, zero_division=0)
    confusion = confusion_matrix(y, shown, labels=range(len(CLASSES)+1))[:len(CLASSES)]
    report = classification_report(y[selected], predicted[selected], labels=range(len(CLASSES)), target_names=CLASSES, output_dict=True, zero_division=0) if selected.any() else None
    confidence = probabilities.max(axis=1)
    correct = predicted == y
    bins = []
    ece = 0.
    for i in range(10):
        lo = i/10
        mask = (confidence >= lo) & (confidence < (i+1)/10 if i < 9 else confidence <= 1)
        count = int(mask.sum())
        accuracy = float(correct[mask].mean()) if count else None
        average = float(confidence[mask].mean()) if count else None
        bins.append(dict(lower=float(lo), count=count, accuracy=accuracy, mean_score=average))
        if count:
            ece += count/n*abs(average-accuracy)
    cm_selected = (confusion_matrix(y[selected], predicted[selected], labels=range(len(CLASSES)))
                   if selected.any() else np.zeros((len(CLASSES), len(CLASSES)), dtype=int))
    total = cm_selected.sum()
    tp = np.diag(cm_selected)
    fp = cm_selected.sum(axis=0)-tp
    fn = cm_selected.sum(axis=1)-tp
    tn = total-tp-fp-fn
    specificity = np.divide(tn, tn+fp, out=np.zeros(len(CLASSES), dtype=float), where=(tn+fp)>0)
    for i, label in enumerate(CLASSES):
        full_report[label]["accepted_true_class_count"] = int(((y == i) & selected).sum())
        full_report[label]["abstentions"] = int(((y == i) & ~selected).sum())
        full_report[label]["coverage"] = float(selected[y == i].mean()) if (y == i).any() else None
        full_report[label]["specificity_on_accepted"] = float(specificity[i]) if total else None
    result = {
        "cases": n, "accepted_cases": int(selected.sum()),
        "underlying_top1_accuracy": float(correct.mean()),
        "underlying_top3_accuracy": float(np.any(np.argsort(-probabilities, axis=1)[:, :3] == y[:, None], axis=1).mean()),
        "underlying_macro_precision": all_report["macro avg"]["precision"],
        "underlying_macro_recall": all_report["macro avg"]["recall"],
        "underlying_macro_f1": all_report["macro avg"]["f1-score"],
        "coverage": float(selected.mean()), "abstention_rate": float((~selected).mean()),
        "selective_accuracy": float(correct[selected].mean()) if selected.any() else None,
        "correct_primary_per_all_cases": float((correct & selected).mean()),
        "macro_precision_including_abstention": full_report["macro avg"]["precision"],
        "macro_recall_including_abstention": full_report["macro avg"]["recall"],
        "macro_f1_including_abstention": full_report["macro avg"]["f1-score"],
        "macro_specificity_on_accepted": float(specificity.mean()) if total else None,
        "accepted_macro_precision": report["macro avg"]["precision"] if report else None,
        "accepted_macro_recall": report["macro avg"]["recall"] if report else None,
        "accepted_macro_f1": report["macro avg"]["f1-score"] if report else None,
        "underlying_log_loss": float(log_loss(y, probabilities, labels=range(len(CLASSES)))),
        "underlying_multiclass_brier": float(((probabilities-np.eye(len(CLASSES))[y])**2).sum(axis=1).mean()),
        "underlying_top_label_ece_10_equal_width_bins": float(ece),
        "reliability_bins": bins,
        "probability_note": "All probability metrics describe the unchanged source-relative V3 distribution on simulated data; no clinical or Kenyan-population probability interpretation.",
    }
    return result, full_report, confusion


def save_evaluation(prefix, data, bundle, policy=None, include_scope=True):
    result = {}
    for count, negatives in SCENARIOS:
        p, a = masks(data, count, negatives)
        eligible = p.sum(axis=1) > 0
        x = subset(data, eligible)
        p, a = p[eligible], a[eligible]
        probabilities = score(bundle, p, a, x)
        accepted = None if policy is None else accept_vectorized(policy, probabilities, p.sum(axis=1), a.sum(axis=1), p, include_scope)
        name = f"{count}_positive_{negatives}_negative"
        metrics, report, confusion = summarize(x["y"], probabilities, accepted)
        result[name] = metrics
        pd.DataFrame(report).T.to_csv(OUT / f"{prefix}_{name}_per_class.csv")
        pd.DataFrame(confusion, index=CLASSES, columns=CLASSES+["ABSTAIN"]).to_csv(OUT / f"{prefix}_{name}_confusion.csv")
        print(prefix, name, "accuracy", round(metrics["underlying_top1_accuracy"], 4), "coverage", round(metrics["coverage"], 4), "selected_accuracy", metrics["selective_accuracy"], flush=True)
    return result


def upper_risk(errors, n, delta):
    if not n or errors == n:
        return 1.
    return float(beta.ppf(1-delta, errors+1, n-errors))


def choose_threshold(probabilities, y):
    confidence = probabilities.max(axis=1)
    errors = probabilities.argmax(axis=1) != y
    # Evaluate complete tie groups. The independent source-validation check,
    # rather than this adaptive tuning bound, is the reported bound.
    order = np.argsort(-confidence, kind="stable")
    conf, cumulative = confidence[order], errors[order].cumsum()
    ends = np.flatnonzero(np.r_[conf[1:] != conf[:-1], True])
    counts = ends+1
    upper = beta.ppf(1-DELTA, cumulative[ends]+1, counts-cumulative[ends])
    upper[cumulative[ends] == counts] = 1.
    feasible = np.flatnonzero(upper <= RISK)
    if not len(feasible):
        return None
    end = ends[feasible[-1]]
    return {"minimum_relative_score": float(conf[end]), "tuning_accepted": int(end+1),
            "tuning_errors": int(cumulative[end]), "tuning_cases": len(y),
            "tuning_accuracy": float(1-cumulative[end]/(end+1)),
            "tuning_risk_upper_bound_exploratory": float(upper[feasible[-1]])}


def fit_policy(data, bundle):
    tuning, calibration = data["tuning"], data["calibration"]
    policies = {}
    comparisons = MAX_POSITIVE * (MAX_NEGATIVE+1)
    for count in range(1, MAX_POSITIVE+1):
        for negatives in range(MAX_NEGATIVE+1):
            key = f"{count}:{negatives}"
            p, a = masks(tuning, count, negatives)
            eligible = (p.sum(axis=1) == count) & (a.sum(axis=1) == negatives)
            probabilities = score(bundle, p[eligible], a[eligible], subset(tuning, eligible))
            chosen = choose_threshold(probabilities, tuning["y"][eligible])
            entry = {"enabled": False, "reason": "no_threshold_met_tuning_risk_target", "present_count": count, "absent_count": negatives}
            if chosen:
                entry.update(chosen)
                p, a = masks(calibration, count, negatives)
                eligible = (p.sum(axis=1) == count) & (a.sum(axis=1) == negatives)
                probabilities = score(bundle, p[eligible], a[eligible], subset(calibration, eligible))
                accepted = probabilities.max(axis=1) >= chosen["minimum_relative_score"]
                errors = int((probabilities.argmax(axis=1)[accepted] != calibration["y"][eligible][accepted]).sum())
                n = int(accepted.sum())
                upper = upper_risk(errors, n, DELTA/comparisons)
                entry.update({"calibration_cases": int(eligible.sum()), "calibration_accepted": n,
                              "calibration_errors": errors, "source_validation_risk_upper_bound": upper,
                              "source_validation_accuracy": float(1-errors/n) if n else None,
                              "enabled": upper <= RISK,
                              "reason": "source_validation_bound_met" if upper <= RISK else "source_validation_bound_not_met"})
            policies[key] = entry
        print("Policy candidates frozen for", count, "reported positives", flush=True)
    policy = {"policy_version": "v3_selective_primary_v1", "model_version": "v3_partial_evidence",
              "model_sha256": digest(MODEL_PATH), "feature_order": FEATURES, "class_order": CLASSES,
              "selection_method": "Tuning maximum coverage under exploratory exact-binomial bound; one frozen threshold per exact evidence-count bucket independently checked on unique source-validation profiles. Disabled on failure, no retuning.",
              "target_source_selective_error": RISK, "familywise_delta": DELTA,
              "candidate_bucket_count": comparisons, "per_bucket_delta": DELTA/comparisons,
              "maximum_present_count": MAX_POSITIVE, "maximum_absent_count": MAX_NEGATIVE,
              "clinical_validation": False,
              "limitations": ["90% target is a predeclared research engineering risk budget, not a medical standard or patient probability.",
                  "Clopper-Pearson bounds assume independent exchangeable source profiles and the same randomized sparse-evidence reporting scheme.",
                  "Source grouping, label ambiguity, nonrandom real reporting, Kenyan prevalence, missing classes and distribution shift preclude a clinical guarantee.",
                  "Same source can appear in different buckets; within each calibration bucket there is one masked view per unique complete source profile. Bonferroni does not require independence across buckets.",
                  "Prior reporting validation was used to inspect V3 but never fit it; a new deterministic source split isolates policy-bound checks and reporting validation.",
                  "Primary eligibility must be combined with clinical scope, free-text mapping ambiguity and warning-sign gates; uncertainty never rules out illness."],
              "buckets": policies}
    dump(POLICY, policy)
    return policy


def accept_vectorized(policy, probabilities, present_count, absent_count, present, include_scope=True, apply_scope_overrides=True):
    accepted = np.zeros(len(probabilities), dtype=bool)
    for entry in policy["buckets"].values():
        if entry["enabled"]:
            accepted |= ((present_count == entry["present_count"]) & (absent_count == entry["absent_count"]) &
                         (probabilities.max(axis=1) >= entry["minimum_relative_score"]))
    if include_scope:
        indices = [FEATURES.index(f) for f in RESPIRATORY_ANCHOR_FEATURES]
        accepted &= present[:, indices].sum(axis=1) > 0
        if apply_scope_overrides:
            for key in load_primary_scope()["disabled_buckets"]:
                p, a = map(int, key.split(":"))
                accepted &= ~((present_count == p) & (absent_count == a))
    return accepted


def scoped_source_diagnostics(policy, calibration, bundle):
    """Descriptive post-scope checks; do not refit or re-enable any bucket."""
    result = {}
    for key, entry in policy["buckets"].items():
        if not entry["enabled"]:
            continue
        count, negatives = entry["present_count"], entry["absent_count"]
        p, a = masks(calibration, count, negatives)
        eligible = (p.sum(axis=1) == count) & (a.sum(axis=1) == negatives)
        p, a = p[eligible], a[eligible]
        data = subset(calibration, eligible)
        probabilities = score(bundle, p, a, data)
        accepted = accept_vectorized(policy, probabilities, p.sum(axis=1), a.sum(axis=1), p, apply_scope_overrides=False)
        n = int(accepted.sum())
        errors = int((probabilities.argmax(axis=1)[accepted] != data["y"][accepted]).sum())
        result[key] = {"accepted_source_profiles": n, "errors": errors,
                       "accuracy": float(1-errors/n) if n else None,
                       "descriptive_risk_upper_bound": upper_risk(errors, n, DELTA/policy["candidate_bucket_count"])}
    return result


def freeze_scope_override(policy, diagnostics):
    scope = {"scope_policy_version": SCOPE_POLICY_VERSION,
             "base_policy_sha256": digest(POLICY), "model_sha256": policy["model_sha256"],
             "required_present_anchor_features": sorted(RESPIRATORY_ANCHOR_FEATURES),
             "clinical_validation": False, "thresholds_changed": False,
             "decision_source": "Only the independent unique-source-profile calibration partition; no reporting-validation/test labels used. Respiratory anchors fixed from supported complaint domain before scoped calibration review.",
             "disabled_buckets": {},
             "note": "Additional rejection only. Existing score thresholds and original enabled/disabled policy retained. Bound interpretation remains simulated-source and reporting-mechanism dependent; application mapping, severity and emergency gates need separate validation."}
    for key, row in diagnostics.items():
        if row["descriptive_risk_upper_bound"] > policy["target_source_selective_error"]:
            scope["disabled_buckets"][key] = {"disabled": True,
                "reason": "scoped_source_validation_bound_not_met",
                "scoped_source_validation_risk_upper_bound": row["descriptive_risk_upper_bound"],
                "accepted_source_profiles_before_override": row["accepted_source_profiles"],
                "errors_before_override": row["errors"]}
    dump(SCOPE_POLICY_PATH, scope)
    load_primary_scope.cache_clear()
    return scope


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", action="store_true", help="Record frozen V3 before any selection policy")
    parser.add_argument("--evaluate-only", action="store_true", help="Reuse frozen policy; never refit from test")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    data, split_summary = cohorts()
    bundle = load_v3_bundle()
    if args.baseline:
        baseline = {"baseline": "Current V3 before this request; not V1/V2", "model_sha256": digest(MODEL_PATH),
                    "splits": split_summary, "test": save_evaluation("baseline_test", data["test"], bundle),
                    "validation": save_evaluation("baseline_validation", data["validation"], bundle),
                    "clinical_validation": False}
        dump(OUT / "baseline_frozen.json", baseline)
        return
    baseline = json.loads((OUT / "baseline_frozen.json").read_text())
    if baseline["model_sha256"] != digest(MODEL_PATH):
        raise ValueError("V3 changed after baseline freeze")
    policy = json.loads(POLICY.read_text()) if args.evaluate_only else fit_policy(data, bundle)
    diagnostics = scoped_source_diagnostics(policy, data["calibration"], bundle)
    if args.evaluate_only and SCOPE_POLICY_PATH.exists():
        scope = load_primary_scope()
    else:
        scope = freeze_scope_override(policy, diagnostics)
    # Separate report-validation and test are read for metrics after the policy
    # artifact is frozen; they never change its parameters or enabled buckets.
    report = {"model_unchanged": True, "model_sha256": digest(MODEL_PATH), "policy_sha256": digest(POLICY),
              "splits": split_summary, "policy": policy,
              "respiratory_scope": {"required_present_anchor_features": sorted(RESPIRATORY_ANCHOR_FEATURES),
                  "note": "Fixed complaint-domain filter added independently of test outcomes; not triage or a disease exclusion rule. The original per-bucket bound checks concern pre-scope selection, not automatically the filtered subset. Scoped results below are empirical observations; no clinical or inherited selected-risk guarantee is claimed."},
              "baseline": baseline,
              "scope_policy": scope, "scope_policy_sha256": digest(SCOPE_POLICY_PATH),
              "scoped_calibration_diagnostics": diagnostics,
              "model_only_improved_test": save_evaluation("model_only_improved_test", data["test"], bundle, policy, include_scope=False),
              "improved_validation": save_evaluation("improved_validation", data["validation"], bundle, policy),
              "improved_test": save_evaluation("improved_test", data["test"], bundle, policy),
              "clinical_validation": False}
    dump(OUT / "evaluation.json", report)


if __name__ == "__main__":
    main()
