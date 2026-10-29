"""Portable selective primary-result policy over the unchanged V3 ranking.

This is a simulated-source eligibility rule, not clinical validation. A caller
must apply its clinical scope, mapping ambiguity and emergency pathways first.
No unmentioned feature becomes a negative. The only patient-facing number
is a rounded whole-percent match band (see patient_match): it is a display
mapping of the relative ranking score, not a probability, not a diagnosis,
and not overall accuracy. Raw relative scores stay in diagnostics only.
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

# Patient-facing match band. Thresholds are conservative and deliberately
# NOT claimed as validated on a fresh fold: the gap gate (0.10) is the
# checklist's 10-point minimum, and the dangerous-second margin (0.20) is a
# safety margin, not a measured clinical threshold. Do not tune these on
# the test set. Raw scores are relative ranking shares (they sum to 1
# across the 21 classes), so a whole-percent display is a share of the
# model's ranking, not a probability that the patient has the condition.
MIN_CLOSE_GAP = 0.10
DANGEROUS_CLOSE_GAP = 0.20
DANGEROUS_CONDITIONS = frozenset({
    "Pneumonia", "Tuberculosis", "Pulmonary neoplasm", "Acute pulmonary edema",
    "Spontaneous pneumothorax", "Epiglottitis",
})

# Narrow 4:0 family exception (see classify_primary). Only for the viral
# upper-respiratory family, only when the disabled bucket's top pattern is
# clear on its own. Thresholds are conservative and unvalidated on a fresh
# fold; they are not a validated clinical rule.
VIRAL_UPPER_RESPIRATORY_FAMILY = frozenset({
    "URTI", "Influenza", "Viral pharyngitis", "Acute rhinosinusitis",
})
FAMILY_MIN_SCORE = 0.75
FAMILY_MIN_GAP = 0.20

# Specific supporting features that can justify naming a serious condition
# on sparse input. Feature codes: E_162 unintentional weight loss,
# E_45 coughing blood, E_14 chest pain at rest, E_66 breathing difficulty,
# E_50 heavy/night sweats. Fever, headache, cough and tiredness alone are
# NOT specific: they occur in common viral illnesses too.
SPARSE_SERIOUS_FEATURES = frozenset({"E_162", "E_45", "E_14", "E_66", "E_50"})
SPARSE_MAX_PRESENT = 3


def sparse_serious_guard(condition, present_features, top_score, gap):
    """True when a serious name must be withheld on sparse, non-specific input.

    Pulmonary neoplasm is never named on <=3 present features without a
    specific supporting feature, whatever the model score. Tuberculosis is
    never named as STRONG (80%+ with a clear gap) on the same sparse,
    non-specific input. This is the guard against the original tumour-on-
    vague-symptoms failure; it does not block TB at moderate on a specific
    pattern such as chronic cough + weight loss (E_162 is specific).
    """
    if len(present_features) > SPARSE_MAX_PRESENT:
        return False
    if present_features & SPARSE_SERIOUS_FEATURES:
        return False
    if condition == "Pulmonary neoplasm":
        return True
    if condition == "Tuberculosis" and top_score >= 0.80 and gap >= MIN_CLOSE_GAP:
        return True
    return False


def match_band_for(percent_rounded, gap):
    """Band for an already-eligible result. Strong needs 80+ AND a clear gap."""
    if percent_rounded >= 80 and gap >= MIN_CLOSE_GAP:
        return "strong"
    if percent_rounded >= 60:
        return "moderate"
    return "low"


def patient_match(top_score, gap):
    """Patient-safe match dict. Never include a raw score here."""
    percent_rounded = int(round(top_score * 100))
    return {
        "percent_rounded": percent_rounded,
        "band": match_band_for(percent_rounded, gap),
        "gap_points_rounded": int(round(gap * 100)),
        "label": "Model match, not a probability.",
        "label_detail": "This whole percent is how strongly the reported pattern matched this condition in the simulated model. It is not the probability that you have this condition, not a diagnosis, and not overall accuracy.",
    }



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
    top_score = first["raw_relative_score"]
    gap = first["raw_relative_score"] - second["raw_relative_score"]
    result["diagnostics"]["second_condition"] = second["condition"]
    # Narrow 4:0 family exception, chosen route (not a general 4:0 enablement):
    # the 4:0 bucket is disabled only because its source-validation risk
    # bound (0.1025) sits just over the 0.10 target. When the top pattern is
    # nevertheless clear (>=0.75, gap >=0.20), viral-family, and no dangerous
    # condition is a close second, return a FAMILY answer, not a specific
    # disease name. A 4-symptom close case still withholds below.
    if not entry["enabled"] and result["diagnostics"]["evidence_bucket"] == "4:0":
        if (first["condition"] in VIRAL_UPPER_RESPIRATORY_FAMILY
                and top_score >= FAMILY_MIN_SCORE and gap >= FAMILY_MIN_GAP
                and not (second["condition"] in DANGEROUS_CONDITIONS and gap < DANGEROUS_CLOSE_GAP)):
            result["status"] = "family"
            result["reasons"] = ["family_viral_upper_respiratory", "not_clinically_validated"]
            result["match"] = patient_match(top_score, gap)
            result["primary_prediction"] = {
                "condition": "Flu-like illness / common cold",
                "is_family_answer": True,
                "family_top_condition": first["condition"],
                "supporting_features": first["supporting_features"],
                "supporting_absent_features": first.get("supporting_absent_features", []),
                "contradicting_features": first.get("contradicting_features", []),
                "contradicting_absent_features": first.get("contradicting_absent_features", []),
            }
            return result
        result["reasons"] = ["non_specific_input" if len(present) == 1 else "ambiguous_model_rank"]
        return result
    if not entry["enabled"] or first["raw_relative_score"] < entry["minimum_relative_score"]:
        result["reasons"] = ["non_specific_input" if len(present) == 1 else "ambiguous_model_rank"]
        return result
    # Sparse-serious guard: never let a peaked score alone name a serious
    # condition on vague input. This check sits before eligibility, so the
    # guard cannot be bypassed by a high relative score.
    if sparse_serious_guard(first["condition"], present, top_score, gap):
        result["reasons"] = ["sparse_serious_guard"]
        result["diagnostics"]["policy_reason"] = "sparse_serious_guard"
        result["diagnostics"]["sparse_serious_guard"] = True
        return result
    if second["condition"] in DANGEROUS_CONDITIONS and gap < DANGEROUS_CLOSE_GAP:
        result["reasons"] = ["dangerous_close_second"]
        result["diagnostics"]["policy_reason"] = "dangerous_close_second_below_margin"
        return result
    if gap < MIN_CLOSE_GAP:
        result["reasons"] = ["close_alternative"]
        result["diagnostics"]["policy_reason"] = "top_two_gap_below_minimum"
        return result
    result["status"] = "eligible"
    result["reasons"] = ["source_validation_selection_rule_met", "not_clinically_validated"]
    result["match"] = patient_match(top_score, gap)
    # Preserve exact reported evidence. Raw relative scores stay in
    # diagnostics (audit only); the patient object carries only the
    # rounded match band in result["match"].
    result["primary_prediction"] = {key: value for key, value in first.items() if key not in ("raw_relative_score", "rank")}
    return result
