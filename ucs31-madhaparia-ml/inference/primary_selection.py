"""Portable selective primary-result policy over the unchanged V3 ranking.

This is a simulated-source eligibility rule, not clinical validation. A caller
must apply its clinical scope, mapping ambiguity and emergency pathways first.
No unmentioned feature becomes a negative, and no patient confidence is emitted.
"""
import hashlib
import json
import math
from functools import lru_cache
from pathlib import Path

from .v3_predictor import MODEL_PATH, _evidence, _group, load_v3_bundle, predict_v3

POLICY_PATH = Path(__file__).resolve().parents[1] / "models/v3_primary_selection.json"
SCOPE_POLICY_PATH = POLICY_PATH.with_name("v3_primary_scope.json")
POLICY_VERSION = "v3_selective_primary_v1"
SCOPE_POLICY_VERSION = "v3_respiratory_scope_v1"
# This is the supported respiratory scope, not a list of emergency signs or a
# clinician-validated exclusion test. Generic fever, pain and fatigue alone
# cannot establish that the patient's complaint belongs to these source classes.
RESPIRATORY_ANCHOR_FEATURES = frozenset({
    "E_103", "E_112", "E_166", "E_169", "E_181", "E_182", "E_190", "E_194",
    "E_201", "E_203", "E_212", "E_214", "E_217", "E_220", "E_45", "E_65",
    "E_66", "E_67", "E_77", "E_97",
})


@lru_cache(maxsize=2)
def load_primary_policy(path=None):
    policy = json.loads(Path(path or POLICY_PATH).read_text(encoding="utf8"))
    bundle = load_v3_bundle()
    if policy.get("policy_version") != POLICY_VERSION or policy.get("model_version") != bundle["model_version"]:
        raise ValueError("Unsupported primary-selection policy version")
    if policy.get("model_sha256") != hashlib.sha256(Path(MODEL_PATH).read_bytes()).hexdigest():
        raise ValueError("Primary-selection policy does not match the V3 artifact")
    if policy.get("feature_order") != bundle["features"] or policy.get("class_order") != bundle["classes"]:
        raise ValueError("Primary-selection schema does not match V3")
    if policy.get("clinical_validation") is not False:
        raise ValueError("Source policy cannot claim clinical validation")
    risk, delta = policy.get("target_source_selective_error"), policy.get("familywise_delta")
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 < v < 1 for v in (risk, delta)):
        raise ValueError("Invalid source-validation risk configuration")
    maxima = [policy.get("maximum_present_count"), policy.get("maximum_absent_count")]
    if any(type(v) is not int or not 0 <= v <= len(bundle["features"]) for v in maxima) or maxima[0] == 0:
        raise ValueError("Invalid evidence-count limits")
    expected = {f"{p}:{a}" for p in range(1, maxima[0]+1) for a in range(maxima[1]+1)}
    buckets = policy.get("buckets", {})
    if set(buckets) != expected or policy.get("candidate_bucket_count") != len(expected):
        raise ValueError("Incomplete primary-selection buckets")
    if not math.isclose(policy.get("per_bucket_delta", 0), delta/len(expected), rel_tol=1e-12):
        raise ValueError("Invalid multiple-comparison correction")
    for key, entry in buckets.items():
        if key != f"{entry.get('present_count')}:{entry.get('absent_count')}" or type(entry.get("enabled")) is not bool:
            raise ValueError("Invalid primary-selection bucket")
        if not entry["enabled"]:
            continue
        threshold, bound = entry.get("minimum_relative_score"), entry.get("source_validation_risk_upper_bound")
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in (threshold, bound)):
            raise ValueError("Invalid primary-selection threshold")
        if not 0 <= threshold <= 1 or not 0 <= bound <= risk:
            raise ValueError("Primary-selection bucket did not meet source-validation bound")
        n, errors = entry.get("calibration_accepted"), entry.get("calibration_errors")
        if type(n) is not int or n <= 0 or type(errors) is not int or not 0 <= errors <= n:
            raise ValueError("Invalid independent source-validation counts")
    return policy


@lru_cache(maxsize=2)
def load_primary_scope(path=None):
    scope = json.loads(Path(path or SCOPE_POLICY_PATH).read_text(encoding="utf8"))
    policy = load_primary_policy()
    if scope.get("scope_policy_version") != SCOPE_POLICY_VERSION:
        raise ValueError("Unsupported primary respiratory-scope policy")
    if (scope.get("base_policy_sha256") != hashlib.sha256(Path(POLICY_PATH).read_bytes()).hexdigest()
            or scope.get("model_sha256") != policy["model_sha256"]):
        raise ValueError("Respiratory-scope policy does not match frozen policy/model")
    if scope.get("required_present_anchor_features") != sorted(RESPIRATORY_ANCHOR_FEATURES):
        raise ValueError("Respiratory-scope anchor schema changed")
    if scope.get("clinical_validation") is not False:
        raise ValueError("Source-scope policy cannot claim clinical validation")
    if not isinstance(scope.get("disabled_buckets"), dict):
        raise ValueError("Missing respiratory-scope override configuration")
    for key, override in scope["disabled_buckets"].items():
        if key not in policy["buckets"] or override.get("disabled") is not True:
            raise ValueError("Invalid respiratory-scope override")
        bound = override.get("scoped_source_validation_risk_upper_bound")
        if not isinstance(bound, (int, float)) or not math.isfinite(bound) or not 0 <= bound <= 1:
            raise ValueError("Invalid respiratory-scope source-validation bound")
    return scope


def classify_primary(present_features, absent_features, age, sex):
    """Return at most one possible condition, or an explicit uncertainty state.

    Only lists of unique supported native features are accepted. Explicit
    absent and unmentioned remain distinct. Invalid contradictory evidence and
    demographics raise ValueError for the transport layer to explain.

    `diagnostics` is internal audit data and must not be rendered as a patient
    probability. An eligible result still needs the caller's clinical gates.
    """
    bundle = load_v3_bundle()
    present, absent = _evidence(bundle, present_features, absent_features)
    _group(bundle, age, sex)
    result = {"policy_version": POLICY_VERSION, "scope_policy_version": SCOPE_POLICY_VERSION,
              "model_version": bundle["model_version"],
              "status": "no_information" if not present else "uncertain",
              "primary_prediction": None, "reasons": [], "clinical_validation": False,
              "supported_present_count": len(present), "supported_absent_count": len(absent),
              "supported_unmentioned_count": len(bundle["features"])-len(present)-len(absent),
              "diagnostics": {"evidence_bucket": f"{len(present)}:{len(absent)}"}}
    if not present:
        result["reasons"] = ["insufficient_evidence"]
        return result
    result["diagnostics"]["respiratory_scope_supported"] = bool(present & RESPIRATORY_ANCHOR_FEATURES)
    if not result["diagnostics"]["respiratory_scope_supported"]:
        result["reasons"] = ["non_specific_input"]
        result["diagnostics"]["policy_reason"] = "no_supported_respiratory_anchor"
        return result
    policy, scope = load_primary_policy(), load_primary_scope()
    entry = policy["buckets"].get(result["diagnostics"]["evidence_bucket"])
    if entry is None:
        result["reasons"] = ["unsupported_information"]
        result["diagnostics"]["policy_reason"] = "evidence_count_outside_source_validation"
        return result
    if result["diagnostics"]["evidence_bucket"] in scope["disabled_buckets"]:
        result["reasons"] = ["ambiguous_model_rank"]
        result["diagnostics"]["policy_reason"] = "scoped_source_validation_bound_not_met"
        return result
    ranking = predict_v3(sorted(present), sorted(absent), age, sex, top_k=2)
    first, second = ranking["predictions"]
    result["diagnostics"].update({
        "source_relative_top_score": first["raw_relative_score"],
        "source_relative_top_two_gap": first["raw_relative_score"]-second["raw_relative_score"],
        "supporting_present_count": len(first["supporting_features"]),
        "supporting_absent_count": len(first["supporting_absent_features"]),
        "policy_bucket_enabled": entry["enabled"], "policy_reason": entry["reason"],
    })
    if not entry["enabled"] or first["raw_relative_score"] < entry["minimum_relative_score"]:
        result["reasons"] = ["non_specific_input" if len(present) == 1 else "ambiguous_model_rank"]
        return result
    result["status"] = "eligible"
    result["reasons"] = ["source_validation_selection_rule_met", "not_clinically_validated"]
    # Preserve exact reported evidence, but keep all relative ranking numbers
    # in diagnostics. Patient-facing callers receive no confidence percentage.
    result["primary_prediction"] = {key: value for key, value in first.items() if key not in ("raw_relative_score", "rank")}
    return result
