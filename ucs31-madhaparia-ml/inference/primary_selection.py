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
GAP_POLICY_PATH = POLICY_PATH.with_name('v3_gap_selection.json')
DANGEROUS_ALTERNATIVES = frozenset({"Pneumonia", "Tuberculosis", "Pulmonary neoplasm", "Acute pulmonary edema"})
# Narrow 4:0 family exception (see classify_primary): only for the viral
# upper-respiratory family, only when the disabled 4:0 bucket's top pattern is
# clear on its own. Conservative, unvalidated on a fresh fold - not a
# validated clinical rule.
VIRAL_UPPER_RESPIRATORY_FAMILY = frozenset({
    "URTI", "Influenza", "Viral pharyngitis", "Acute rhinosinusitis",
})
FAMILY_MIN_SCORE = 0.75
FAMILY_MIN_GAP = 0.20

# Specific supporting features that can justify naming a serious condition on
# sparse input: E_162 unintentional weight loss, E_45 coughing blood, E_14
# chest pain at rest, E_66 breathing difficulty, E_50 heavy/night sweats.
# Fever, headache, cough and tiredness alone are NOT specific.
SPARSE_SERIOUS_FEATURES = frozenset({"E_162", "E_45", "E_14", "E_66", "E_50"})
SPARSE_MAX_PRESENT = 3


def sparse_serious_guard(condition, present_features, top_score, gap):
    """True when a serious name must be withheld on sparse, non-specific input.

    Pulmonary neoplasm is never named on <=3 present features without a
    specific supporting feature. Tuberculosis is never named as STRONG (80%+
    with a clear gap) on the same sparse, non-specific input. Does not block
    TB at moderate on a specific pattern such as chronic cough + weight loss.
    """
    if len(present_features) > SPARSE_MAX_PRESENT:
        return False
    if present_features & SPARSE_SERIOUS_FEATURES:
        return False
    if condition == "Pulmonary neoplasm":
        return True
    if condition == "Tuberculosis" and top_score >= 0.80 and gap >= 0.15:
        return True
    return False
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


@lru_cache(maxsize=2)
def load_gap_policy(path=None):
    target = Path(path or GAP_POLICY_PATH)
    if not target.exists():
        return None
    gate = json.loads(target.read_text(encoding='utf8'))
    policy = load_primary_policy()
    if (gate.get('policy_version') != 'v3_relative_gap_v1' or gate.get('clinical_validation') is not False
            or gate.get('model_sha256') != policy['model_sha256']
            or gate.get('base_policy_sha256') != hashlib.sha256(Path(POLICY_PATH).read_bytes()).hexdigest()
            or gate.get('test_used_for_selection') is not False):
        raise ValueError('Gap policy does not match frozen V3 / independent source validation')
    for field in ('minimum_relative_gap', 'minimum_relative_score'):
        value = gate.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError('Invalid relative gap policy threshold')
    if gate.get('minimum_present_count') != 2 or set(gate.get('buckets', {})) != set(policy['buckets']):
        raise ValueError('Incomplete gap-policy evidence buckets')
    for key, entry in gate['buckets'].items():
        if type(entry.get('enabled')) is not bool:
            raise ValueError('Invalid gap bucket state')
        if not entry['enabled']:
            continue
        n, errors, bound = entry.get('accepted'), entry.get('errors'), entry.get('risk_upper_bound')
        if (type(n) is not int or n <= 0 or type(errors) is not int or not 0 <= errors <= n
                or isinstance(bound, bool) or not isinstance(bound, (int, float)) or not math.isfinite(bound)
                or not 0 <= bound <= policy['target_source_selective_error'] or not policy['buckets'][key]['enabled']):
            raise ValueError('Gap bucket did not pass independent source-validation bound')
    return gate


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
    gap = result["diagnostics"]["source_relative_top_two_gap"]
    gate = load_gap_policy()
    # Narrow 4:0 family exception: the 4:0 bucket is gap-disabled because its
    # source-validation risk bound (1.0 accepted here) sits over the target.
    # When the top pattern is nevertheless clear (>=0.75, gap >=0.20),
    # viral-family, and no dangerous alternative is a close second, return a
    # FAMILY answer, not a specific disease name. A 4-symptom close case still
    # withholds below.
    if (result["diagnostics"]["evidence_bucket"].startswith("4:")
            and gate is not None and not gate['buckets']['4:0']['enabled']
            and first["condition"] in VIRAL_UPPER_RESPIRATORY_FAMILY
            and first['raw_relative_score'] >= FAMILY_MIN_SCORE and gap >= FAMILY_MIN_GAP
            and not (second["condition"] in DANGEROUS_ALTERNATIVES and gap < gate['minimum_relative_gap'])):
        result["status"] = "family"
        result["reasons"] = ["family_viral_upper_respiratory", "not_clinically_validated"]
        result["diagnostics"]["policy_reason"] = "family_viral_upper_respiratory_4_0"
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
    if gate is None or gap < gate['minimum_relative_gap']:
        result["reasons"] = ["gap_validation_pending" if gate is None else "close_model_rank"]
        # With no validated separation test, do not hide a potentially serious
        # alternative behind a mild label. This precaution may over-refer.
        if second["condition"] in DANGEROUS_ALTERNATIVES and first["condition"] not in DANGEROUS_ALTERNATIVES:
            result["reasons"].append("dangerous_alternative_requires_review")
        return result
    if (len(present) < gate['minimum_present_count'] or first['raw_relative_score'] < gate['minimum_relative_score']
            or not gate['buckets'][result['diagnostics']['evidence_bucket']]['enabled']):
        result['reasons'] = ['gap_source_validation_bound_not_met']
        return result
    # Sparse-serious guard: never let a peaked score alone name a serious
    # condition on vague input. Sits before eligibility so a high relative
    # score cannot bypass it.
    if sparse_serious_guard(first["condition"], present, first['raw_relative_score'], gap):
        result["reasons"] = ["sparse_serious_guard"]
        result["diagnostics"]["policy_reason"] = "sparse_serious_guard"
        result["diagnostics"]["sparse_serious_guard"] = True
        return result
    if not entry["enabled"] or first["raw_relative_score"] < entry["minimum_relative_score"]:
        result["reasons"] = ["non_specific_input" if len(present) == 1 else "ambiguous_model_rank"]
        return result
    result["status"] = "eligible"
    result["reasons"] = ["source_validation_selection_rule_met", "not_clinically_validated"]
    # Preserve exact reported evidence, but keep all relative ranking numbers
    # in diagnostics. Patient-facing callers receive no confidence percentage.
    result["primary_prediction"] = {key: value for key, value in first.items() if key not in ("raw_relative_score", "rank")}
    return result
