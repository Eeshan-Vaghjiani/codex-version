"""Portable partial-evidence likelihood model; unmentioned is marginalized.

This model is fitted to simulated DDXPlus records. Scores rank the supported
source conditions; they are neither local prevalence nor clinical probability.
The same module can be copied to the backend with only MODEL_PATH changed.
"""
import json
import math
from functools import lru_cache
from pathlib import Path

MODEL_PATH = Path(__file__).resolve().parents[1] / "models/v3_partial_evidence.json"
MODEL_VERSION = "v3_partial_evidence"


@lru_cache(maxsize=2)
def load_v3_bundle(path=None):
    bundle = json.loads(Path(path or MODEL_PATH).read_text(encoding="utf8"))
    classes, features = bundle["classes"], bundle["features"]
    if bundle.get("model_version") != MODEL_VERSION:
        raise ValueError("Unsupported partial-evidence model version")
    if len(classes) < 2 or len(classes) != len(set(classes)):
        raise ValueError("Model classes must be unique")
    if len(features) != len(set(features)) or not features:
        raise ValueError("Model features must be unique")
    if any(not isinstance(v, str) or not v for v in classes + features):
        raise ValueError("Model labels and features must be non-empty strings")
    if bundle.get("demographic_mode") not in ("none", "age", "age_sex"):
        raise ValueError("Unsupported demographic representation")
    if not math.isfinite(bundle["temperature"]) or bundle["temperature"] <= 0:
        raise ValueError("Invalid score temperature")
    if (bundle["age_edges"] != sorted(set(bundle["age_edges"]))
            or any(not 0 < edge < 120 for edge in bundle["age_edges"])):
        raise ValueError("Invalid demographic age boundaries")
    for prior, likelihood in zip(bundle["group_priors"], bundle["group_likelihoods"]):
        if len(prior) != len(classes) or not math.isclose(sum(prior), 1., abs_tol=1e-8):
            raise ValueError("Invalid model prior")
        if any(not math.isfinite(x) or x <= 0 for x in prior):
            raise ValueError("Invalid model prior")
        if len(likelihood) != len(classes) or any(len(row) != len(features) for row in likelihood):
            raise ValueError("Model likelihood dimensions do not match schema")
        if any(not math.isfinite(x) or not 0 < x < 1 for row in likelihood for x in row):
            raise ValueError("Invalid model likelihood")
    if not bundle["group_priors"] or len(bundle["group_priors"]) != len(bundle["group_likelihoods"]):
        raise ValueError("Invalid demographic groups")
    expected_groups = (1 if bundle["demographic_mode"] == "none" else len(bundle["age_edges"])+1)
    if bundle["demographic_mode"] == "age_sex":
        expected_groups *= 2
    if len(bundle["group_priors"]) != expected_groups:
        raise ValueError("Demographic groups do not match schema")
    background = bundle["background_likelihood"]
    if len(background) != len(features) or any(not math.isfinite(v) or not 0 < v < 1 for v in background):
        raise ValueError("Invalid background likelihood")
    conditionals = bundle["pain_location_given_pain"]
    if len(conditionals) != expected_groups:
        raise ValueError("Invalid conditional likelihood groups")
    for group in conditionals:
        if len(group) != len(classes) or any(len(row) != len(features) for row in group):
            raise ValueError("Invalid conditional likelihood dimensions")
        if any(not math.isfinite(v) or not 0 < v < 1 for row in group for v in row):
            raise ValueError("Invalid conditional likelihood")
    return bundle


def _group(bundle, age, sex):
    if isinstance(age, bool) or not isinstance(age, (int, float)) or not math.isfinite(age) or not 0 <= age <= 120:
        raise ValueError("Age must be a finite number between 0 and 120")
    if sex not in ("M", "F"):
        raise ValueError("Sex must be M or F")
    mode = bundle["demographic_mode"]
    if mode == "none":
        return 0
    age_group = sum(age >= edge for edge in bundle["age_edges"])
    return age_group * 2 + int(sex == "M") if mode == "age_sex" else age_group


def _evidence(bundle, present_features, absent_features):
    for values in (present_features, absent_features):
        if not isinstance(values, (list, tuple)) or not all(isinstance(v, str) for v in values):
            raise ValueError("Evidence must be lists of feature strings")
        if len(set(values)) != len(values):
            raise ValueError("Duplicate evidence features")
    present, absent = set(present_features), set(absent_features)
    if present & absent:
        raise ValueError("Evidence cannot be both present and absent")
    unsupported = (present | absent) - set(bundle["features"])
    if unsupported:
        raise ValueError(f"Unsupported model features: {sorted(unsupported)}")
    return present, absent


def _distribution(bundle, present, absent, group):
    names = bundle["features"]
    likelihoods = bundle["group_likelihoods"][group]
    # Related pain-location observations are fitted conditional on pain. When
    # generic pain is known, use the corresponding conditional probability;
    # otherwise use the marginal location likelihood (parent unmentioned).
    conditional = bundle.get("pain_location_given_pain", [])
    logs = []
    for ci, prior in enumerate(bundle["group_priors"][group]):
        value = math.log(prior)
        for fi, name in enumerate(names):
            if name not in present and name not in absent:
                continue
            probability = likelihoods[ci][fi]
            if name.startswith("E_55_@_") and "E_53" in present and conditional:
                probability = conditional[group][ci][fi]
            value += math.log(probability if name in present else 1-probability)
        logs.append(value / bundle["temperature"])
    maximum = max(logs)
    values = [math.exp(v-maximum) for v in logs]
    total = sum(values)
    return [v/total for v in values]


def predict_v3(present_features, absent_features, age, sex, top_k=3):
    bundle = load_v3_bundle()
    present, absent = _evidence(bundle, present_features, absent_features)
    group = _group(bundle, age, sex)
    if not present:
        return {"model_version": MODEL_VERSION, "status": "insufficient_evidence", "predictions": [],
                "uncertain": True, "clinical_validation": False,
                "uncertainty_reasons": ["no_supported_present_symptoms"]}
    if type(top_k) is not int or not 1 <= top_k <= len(bundle["classes"]):
        raise ValueError("top_k is outside supported class count")
    scores = _distribution(bundle, present, absent, group)
    ranked = sorted(range(len(scores)), key=lambda i: (-scores[i], i))[:top_k]
    background = bundle["background_likelihood"]
    predictions = []
    for rank, ci in enumerate(ranked, 1):
        theta = bundle["group_likelihoods"][group][ci]
        support = sorted((f for f in present if theta[bundle["features"].index(f)] > background[bundle["features"].index(f)]),
                         key=lambda f: -math.log(theta[bundle["features"].index(f)] / background[bundle["features"].index(f)]))
        negative_support = sorted(f for f in absent if theta[bundle["features"].index(f)] < background[bundle["features"].index(f)])
        contrary = sorted(f for f in present if theta[bundle["features"].index(f)] < background[bundle["features"].index(f)])
        negative_contrary = sorted(f for f in absent if theta[bundle["features"].index(f)] > background[bundle["features"].index(f)])
        predictions.append({"rank": rank, "condition": bundle["classes"][ci],
                            "raw_relative_score": scores[ci], "supporting_features": support,
                            "supporting_absent_features": negative_support,
                            "contradicting_features": contrary,
                            "contradicting_absent_features": negative_contrary})
    return {"model_version": MODEL_VERSION, "status": "assessment_complete", "predictions": predictions,
            "uncertain": True, "clinical_validation": False, "model_status": "research_partial_evidence",
            "uncertainty_reasons": ["simulated_source_not_clinically_validated", "incomplete_symptom_history"],
            "present_features": sorted(present), "explicitly_absent_features": sorted(absent),
            "unmentioned_features": sorted(set(bundle["features"])-present-absent),
            "score_note": "Dataset-relative model ranking scores, not validated clinical probabilities. "
                          "Unmentioned symptoms were not treated as absent."}


def question_information_gain(present_features, absent_features, age, sex, candidate_features=None):
    """Expected entropy reduction from one known-supported yes/no observation.

    This is a heuristic model utility criterion, not a clinical triage score.
    Hypothetical answers run through the actual temperature-scaled predictor.
    Their mixture weight uses the fitted generative likelihood. Temperature
    scaling means this utility need not equal a coherent Bayesian information
    gain. Emergency questions and clinical context are checked separately.
    """
    bundle = load_v3_bundle()
    present, absent = _evidence(bundle, present_features, absent_features)
    group = _group(bundle, age, sex)
    scores = _distribution(bundle, present, absent, group)
    unknown = set(bundle["features"]) - present - absent
    if candidate_features is not None:
        if not set(candidate_features).issubset(bundle["features"]):
            raise ValueError("Unsupported candidate question feature")
        unknown &= set(candidate_features)
    entropy = lambda values: -sum(p*math.log(p) for p in values if p > 0)
    current = entropy(scores)
    results = []
    for feature in unknown:
        fi = bundle["features"].index(feature)
        q = [row[fi] for row in bundle["group_likelihoods"][group]]
        py = sum(p*v for p, v in zip(scores, q))
        if feature.startswith("E_55_@_") and "E_53" in present:
            q = [row[fi] for row in bundle["pain_location_given_pain"][group]]
            py = sum(p*v for p, v in zip(scores, q))
        yes = _distribution(bundle, present | {feature}, absent, group)
        no = _distribution(bundle, present, absent | {feature}, group)
        gain = max(0., current - py*entropy(yes) - (1-py)*entropy(no))
        results.append({"feature": feature, "information_gain": gain, "yes_probability": py})
    return sorted(results, key=lambda item: (-item["information_gain"], item["feature"]))
