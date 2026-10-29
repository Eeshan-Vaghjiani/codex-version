"""Fit and evaluate a missing-evidence likelihood model from authentic DDXPlus.

Original files/artifacts are read-only. Selection uses only source validation;
the separate test split is evaluated after the artifact is frozen. Complete
198-feature source signatures stay grouped, including across masked scenarios.
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix, log_loss

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUTPUT = ROOT / "reports/consultation_v3"
FEATURES = json.loads((ROOT / "models/v2_feature_schema.json").read_text())["symptom_features"] + ["E_55_@_V_89", "E_55_@_V_101"]
SOURCE_FEATURES = json.loads((ROOT / "models/model_features.json").read_text())
CLASSES = json.loads((ROOT / "models/disease_classes.json").read_text())
AGE_EDGES = [1, 5, 12, 18, 40, 65]
SEED = 20261027


def read_source(split):
    print("Reading", split, flush=True)
    frame = pd.read_csv(ROOT / f"data/processed/{split}.csv", usecols=SOURCE_FEATURES + ["PATHOLOGY"],
                        dtype={f: "float32" for f in SOURCE_FEATURES})
    signatures = pd.util.hash_pandas_object(frame[SOURCE_FEATURES], index=False).to_numpy()
    return {"x": frame[FEATURES].to_numpy(dtype=np.float32), "age": frame.AGE.to_numpy(),
            "sex": frame.SEX_M.to_numpy(dtype=int), "y": pd.Categorical(frame.PATHOLOGY, categories=CLASSES).codes,
            "signature": signatures}


def subset(data, mask):
    return {k: v[mask] for k, v in data.items()}


def groups(data, mode):
    age = np.digitize(data["age"], AGE_EDGES)
    return np.zeros(len(age), dtype=int) if mode == "none" else age if mode == "age" else age*2 + data["sex"]


def fit(data, mode, strength=100.):
    x, y = data["x"], data["y"]
    counts = np.bincount(y, minlength=len(CLASSES)).astype(float)
    prior = (counts+1)/(counts.sum()+len(CLASSES))
    yes = np.array([x[y==ci].sum(axis=0) for ci in range(len(CLASSES))], dtype=float)
    theta = (yes+1)/(counts[:, None]+2)
    group = groups(data, mode)
    group_count = 1 if mode == "none" else len(AGE_EDGES)+1 if mode == "age" else (len(AGE_EDGES)+1)*2
    priors, likelihoods, pain_conditionals = [], [], []
    pain = FEATURES.index("E_53")
    for gi in range(group_count):
        mask = group == gi
        gc = np.bincount(y[mask], minlength=len(CLASSES)).astype(float)
        gy = np.array([x[mask & (y==ci)].sum(axis=0) for ci in range(len(CLASSES))], dtype=float)
        gp = prior if mode == "none" else (gc + strength*prior)/(gc.sum()+strength)
        gt = theta if mode == "none" else (gy + strength*theta)/(gc[:, None]+strength)
        cond = gt.copy()
        for fi, feature in enumerate(FEATURES):
            if feature.startswith("E_55_@_"):
                global_cond = (yes[:, fi]+1)/(yes[:, pain]+2)
                cond[:, fi] = (gy[:, fi] + strength*global_cond)/(gy[:, pain]+strength)
        priors.append(gp.tolist()); likelihoods.append(gt.tolist()); pain_conditionals.append(cond.tolist())
    return {"model_version": "v3_partial_evidence", "model_type": "missing_evidence_likelihood",
            "classes": CLASSES, "features": FEATURES, "demographic_mode": mode,
            "age_edges": AGE_EDGES, "demographic_shrinkage": strength, "temperature": 1.,
            "group_priors": priors, "group_likelihoods": likelihoods,
            "pain_location_given_pain": pain_conditionals,
            "background_likelihood": ((x.sum(axis=0)+1)/(len(x)+2)).tolist(),
            "training_class_counts": {c: int(counts[i]) for i,c in enumerate(CLASSES)}}


def score(bundle, present, absent, data):
    result = np.zeros((len(present), len(CLASSES)))
    gi = groups(data, bundle["demographic_mode"])
    loc = [i for i, f in enumerate(FEATURES) if f.startswith("E_55_@_")]
    pain = FEATURES.index("E_53")
    for group in np.unique(gi):
        selected = gi == group
        theta = np.array(bundle["group_likelihoods"][int(group)])
        logs = np.log(np.array(bundle["group_priors"][int(group)]))[None, :]
        values = logs + present[selected] @ np.log(theta).T + absent[selected] @ np.log1p(-theta).T
        for fi in loc:
            conditional = np.array(bundle["pain_location_given_pain"][int(group)])[:, fi]
            p = present[selected, pain] * present[selected, fi]
            a = present[selected, pain] * absent[selected, fi]
            values += p[:, None]*(np.log(conditional)-np.log(theta[:, fi]))
            values += a[:, None]*(np.log1p(-conditional)-np.log1p(-theta[:, fi]))
        result[selected] = values / bundle["temperature"]
    result -= result.max(axis=1, keepdims=True)
    result = np.exp(result)
    return result/result.sum(axis=1, keepdims=True)


def masks(data, count, negatives=0, seed=SEED):
    # One deterministic mask per source; all variants stay in its source split.
    x = data["x"]
    rng = np.random.default_rng(seed)
    negative_rng = np.random.default_rng(seed+1)
    present, absent = np.zeros_like(x), np.zeros_like(x)
    for i in range(len(x)):
        positive = np.flatnonzero(x[i] == 1)
        # Always permute the complete source-positive list, so the first k
        # reports are nested for all k and unaffected by negative questions.
        keep = rng.permutation(positive)[:count]
        present[i, keep] = 1
        if negatives:
            negative = np.flatnonzero(x[i] == 0)
            absent[i, negative_rng.permutation(negative)[:negatives]] = 1
    return present, absent


def metrics(actual, probabilities):
    predicted = probabilities.argmax(axis=1)
    ranked = np.argsort(-probabilities, axis=1)
    confidence = probabilities.max(axis=1)
    correct = predicted == actual
    report = classification_report(actual, predicted, labels=list(range(len(CLASSES))),
                                    target_names=CLASSES, output_dict=True, zero_division=0)
    ece = 0.
    for i in range(10):
        mask = (confidence >= i/10) & (confidence < (i+1)/10 if i < 9 else confidence <= 1)
        if mask.any():
            ece += mask.mean()*abs(confidence[mask].mean()-correct[mask].mean())
    return {"cases": len(actual), "accuracy": float(correct.mean()),
            "top3_recall": float(np.any(ranked[:, :3] == actual[:, None], axis=1).mean()),
            "macro_f1_21_classes": report["macro avg"]["f1-score"],
            "log_loss": float(log_loss(actual, probabilities, labels=list(range(len(CLASSES))))),
            "top_label_ece": float(ece)}, report, predicted


def evaluate(bundle, data, prefix, save=True):
    result = {}
    for count, negatives in ((1,0), (2,0), (3,0), (3,3), (8,0)):
        present, absent = masks(data, count, negatives)
        eligible = present.sum(axis=1) > 0
        probabilities = score(bundle, present[eligible], absent[eligible], subset(data, eligible))
        name = f"{count}_positive_{negatives}_negative"
        result[name], report, predicted = metrics(data["y"][eligible], probabilities)
        if save:
            pd.DataFrame(report).T.to_csv(OUTPUT / f"{prefix}_{name}_per_class.csv")
            pd.DataFrame(confusion_matrix(data["y"][eligible], predicted, labels=list(range(len(CLASSES)))),
                         index=CLASSES, columns=CLASSES).to_csv(OUTPUT / f"{prefix}_{name}_confusion.csv")
    return result


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    train = read_source("train")
    validation = read_source("validate")
    # The signature is label-independent and uses every V1 source feature,
    # never just the selected mask. Repeated source profiles cannot cross the
    # training, model-selection, validation-report or final-test partitions.
    seen = set(train["signature"].tolist())
    validation_clean = ~np.isin(validation["signature"], list(seen))
    val = subset(validation, validation_clean)
    choice = val["signature"] % 2 == 0
    tuning, validation_report = subset(val, choice), subset(val, ~choice)
    print("Train/tune/validation", len(train["y"]), len(tuning["y"]), len(validation_report["y"]), flush=True)
    # Fit only source training; compare a small declared family on tuning NLL.
    candidates = []
    tuning_masks = [masks(tuning, n, neg) for n,neg in ((1,0),(2,0),(3,0),(3,3),(8,0))]
    for mode, strength in (("none",100), ("age",100), ("age",1000), ("age_sex",100), ("age_sex",1000)):
        bundle = fit(train, mode, strength)
        unscaled = []
        for p,a in tuning_masks:
            probabilities = score(bundle, p, a, tuning)
            unscaled.append(probabilities)
        for temperature in (0.75, 1., 1.25, 1.5, 2.):
            loss = 0.
            for probabilities in unscaled:
                adjusted = np.maximum(probabilities, 1e-300)**(1/temperature)
                adjusted /= adjusted.sum(axis=1, keepdims=True)
                loss += log_loss(tuning["y"], adjusted, labels=list(range(len(CLASSES)))) / len(unscaled)
            candidates.append({"demographic_mode": mode, "shrinkage": strength,
                               "temperature": temperature, "selection_log_loss": float(loss)})
        print("Candidate fitted", mode, strength, flush=True)
    selected = min(candidates, key=lambda c: c["selection_log_loss"])
    bundle = fit(train, selected["demographic_mode"], selected["shrinkage"])
    bundle["temperature"] = selected["temperature"]
    metadata = json.loads((ROOT / "data/raw/release_evidences.json").read_text())
    bundle["feature_definitions"] = {
        f: {"question": metadata[f.split("_@_")[0]]["question_en"],
            "value": metadata[f.split("_@_")[0]].get("value_meaning", {}).get(f.split("_@_")[-1], {}).get("en")}
        for f in FEATURES}
    bundle["research_limitations"] = ["Simulated DDXPlus source; not clinically validated",
        "21 authentic source conditions; no independent COVID-19 or allergic-rhinitis labels",
        "Dataset priors are generator-altered and are not Kenyan prevalence",
        "Conditional independence approximation; symptom-reporting selection may differ from real users",
        "Duration/severity not learned; they inform guidance and follow-up only"]
    bundle["negative_evidence_provenance"] = {
        "source": "Full synthetic source records only; never unmentioned user input",
        "paper": "https://papers.nips.cc/paper/2022/file/cae73a974390c0edd95ae7aeae09139c-Paper-Datasets_and_Benchmarks.pdf",
        "section": "3.2 generates all experienced evidence; 3.3 supplies all positives then answers no to additional questions",
        "readme": "https://github.com/mila-iqia/ddxplus/blob/main/README.md"}
    artifact = ROOT / "models/v3_partial_evidence.json"
    # Freeze selection BEFORE opening the final test split.
    artifact.write_text(json.dumps(bundle, indent=2), encoding="utf8")
    report = {"seed": SEED, "selected": selected, "candidate_selection": candidates,
        "split_policy": "Original source train, validation split by label-independent full-198-feature signature parity after removing train overlap; final test after frozen selection; all masks grouped by source.",
        "source_training_records": len(train["y"]), "source_tuning_records": len(tuning["y"]),
        "source_validation_report_records": len(validation_report["y"]),
        "validation_train_overlap_removed": int((~validation_clean).sum()),
        "validation": evaluate(bundle, validation_report, "validation")}
    test = read_source("test")
    previous = np.concatenate([train["signature"], validation["signature"]])
    test_clean = ~np.isin(test["signature"], previous)
    final_test = subset(test, test_clean)
    report["test_train_or_validation_overlap_removed"] = int((~test_clean).sum())
    report["test"] = evaluate(bundle, final_test, "test")
    # Append evaluation metadata only; the fitted parameters and selection
    # remain frozen before the final test was opened.
    bundle["metadata"] = {
        "clinical_validation": False, "training_source": "DDXPlus source train",
        "training_count": len(train["y"]), "tuning_count": len(tuning["y"]),
        "validation_count": len(validation_report["y"]), "test_count": len(final_test["y"]),
        "validation_metrics": report["validation"], "test_metrics": report["test"],
        "selection": selected, "source_groups": "198-feature complete source input signatures",
        "final_test_used_for_selection": False,
    }
    artifact.write_text(json.dumps(bundle, indent=2), encoding="utf8")
    report["artifact_sha256"] = hashlib.sha256(artifact.read_bytes()).hexdigest()
    report["clinical_validation"] = False
    (OUTPUT / "evaluation.json").write_text(json.dumps(report, indent=2), encoding="utf8")
    print(json.dumps({"selected": selected, "validation": report["validation"], "test": report["test"]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
