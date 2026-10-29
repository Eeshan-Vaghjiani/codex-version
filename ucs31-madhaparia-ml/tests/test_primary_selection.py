"""Selection contracts, source partition integrity, and denominator semantics."""
import json
from copy import deepcopy

import numpy as np
import pytest

from inference.primary_selection import RESPIRATORY_ANCHOR_FEATURES, classify_primary, load_primary_policy, load_primary_scope
from inference.v3_predictor import load_v3_bundle
from scripts.evaluate_primary_selection import accept_vectorized, cohorts, summarize, upper_risk
from scripts.train_v3_partial_evidence import CLASSES, FEATURES, masks, score, subset


def test_no_information_does_not_infer_from_demographics_or_negatives():
    result = classify_primary([], ["E_91"], 25, "F")
    assert result["status"] == "no_information"
    assert result["primary_prediction"] is None
    assert result["reasons"] == ["insufficient_evidence"]
    assert result["supported_absent_count"] == 1


@pytest.mark.parametrize("features", [["E_91"], ["E_89"], ["E_201"], ["E_53", "E_55_@_V_89", "E_89"], ["E_91", "E_201", "E_97"]])
def test_named_vague_inputs_do_not_force_a_primary(features):
    # Software behavior only: no disease ground truth is invented for a vague
    # symptom description, and this test makes no clinical-safety claim.
    result = classify_primary(features, [], 25, "F")
    assert result["status"] == "uncertain"
    assert result["primary_prediction"] is None


@pytest.mark.parametrize('absent', [[], ['E_66', 'E_91', 'E_214']])
def test_common_cluster_can_name_only_a_family_without_a_score(absent):
    result = classify_primary(['E_201', 'E_97', 'E_181', 'E_53'], absent, 24, 'M')
    assert result['status'] == 'family'
    assert result['clinical_validation'] is False
    assert result['primary_prediction']['condition'] == 'Flu-like illness / common cold'
    assert result['primary_prediction']['is_family_answer'] is True
    assert 'raw_relative_score' not in result['primary_prediction']
    assert 'model_match_percent' not in result['primary_prediction']


@pytest.mark.parametrize('condition,score,second_score', [
    ('URTI', .74, .10), ('URTI', .78, .59), ('Pneumonia', .90, .05),
])
def test_family_exception_does_not_bypass_weak_close_or_serious_patterns(monkeypatch, condition, score, second_score):
    import inference.primary_selection as service
    first = {'condition': condition, 'raw_relative_score': score,
             'supporting_features': [], 'supporting_absent_features': []}
    second = {'condition': 'Tuberculosis', 'raw_relative_score': second_score}
    monkeypatch.setattr(service, 'predict_v3', lambda *args, **kwargs: {'predictions': [first, second]})
    result = service.classify_primary(['E_201', 'E_97', 'E_181', 'E_53'], [], 24, 'M')
    assert result['status'] == 'uncertain'
    assert result['primary_prediction'] is None


@pytest.mark.parametrize("present,absent", [(["E_91"], ["E_91"]), (["fake"], []), (["E_91", "E_91"], []), ("E_91", [])])
def test_invalid_or_contradictory_native_evidence_fails_closed(present, absent):
    with pytest.raises(ValueError):
        classify_primary(present, absent, 25, "F")


def test_unvalidated_evidence_count_cannot_extrapolate_selection():
    result = classify_primary(["E_201"]+[f for f in FEATURES if f != "E_201"][:8], [], 25, "F")
    assert result["status"] == "uncertain"
    assert result["reasons"] == ["unsupported_information"]


def test_generic_symptoms_cannot_establish_respiratory_scope():
    result = classify_primary(["E_91", "E_144", "E_89"], [], 25, "F")
    assert result["status"] == "uncertain"
    assert result["reasons"] == ["non_specific_input"]
    assert result["diagnostics"]["respiratory_scope_supported"] is False
    assert "E_201" in RESPIRATORY_ANCHOR_FEATURES
    assert "E_91" not in RESPIRATORY_ANCHOR_FEATURES


def test_failed_scoped_source_bound_is_an_explicit_extra_abstention():
    scope = load_primary_scope()
    assert "1:4" in scope["disabled_buckets"]
    assert scope["thresholds_changed"] is False
    result = classify_primary(["E_203"], ["E_91", "E_97", "E_181", "E_169"], 25, "F")
    assert result["status"] == "uncertain"
    assert result["primary_prediction"] is None
    assert result["diagnostics"]["policy_reason"] == "scoped_source_validation_bound_not_met"


@pytest.mark.parametrize("field,value", [("model_sha256", "0"*64), ("base_policy_sha256", "0"*64),
    ("required_present_anchor_features", []), ("disabled_buckets", None)])
def test_scope_override_cannot_drift_from_model_or_policy(tmp_path, field, value):
    scope = deepcopy(load_primary_scope())
    scope[field] = value
    path = tmp_path / "scope.json"
    path.write_text(json.dumps(scope), encoding="utf8")
    with pytest.raises(ValueError):
        load_primary_scope(str(path))


@pytest.mark.parametrize("field,value", [("model_sha256", "0"*64), ("clinical_validation", True),
    ("class_order", ["invented"]), ("policy_version", "invented"), ("buckets", {}),
    ("familywise_delta", float("nan")), ("per_bucket_delta", .05)])
def test_policy_rejects_stale_or_corrupt_configuration(tmp_path, field, value):
    policy = deepcopy(load_primary_policy())
    policy[field] = value
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(policy), encoding="utf8")
    with pytest.raises(ValueError):
        load_primary_policy(str(path))


def test_enabled_bucket_must_have_independent_bound_within_target(tmp_path):
    policy = deepcopy(load_primary_policy())
    entry = next(v for v in policy["buckets"].values() if v["enabled"])
    entry["source_validation_risk_upper_bound"] = .2
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(policy), encoding="utf8")
    with pytest.raises(ValueError):
        load_primary_policy(str(path))


def test_abstention_does_not_improve_full_population_recall():
    probabilities = np.zeros((2, len(CLASSES)))
    probabilities[0, 0], probabilities[0, 1] = .9, .1
    probabilities[1, 0], probabilities[1, 1] = .6, .4
    y = np.array([0, 1])
    baseline, _, _ = summarize(y, probabilities)
    selected, _, confusion = summarize(y, probabilities, np.array([True, False]))
    assert selected["coverage"] == .5
    assert selected["selective_accuracy"] == 1
    assert selected["underlying_top1_accuracy"] == baseline["underlying_top1_accuracy"] == .5
    assert selected["correct_primary_per_all_cases"] == .5
    assert selected["macro_recall_including_abstention"] == baseline["macro_recall_including_abstention"]
    assert confusion[1, -1] == 1


def test_empty_selected_subset_is_reported_as_unavailable_not_perfect():
    probabilities = np.ones((2, len(CLASSES)))/len(CLASSES)
    result, _, _ = summarize(np.array([0, 1]), probabilities, np.array([False, False]))
    assert result["coverage"] == 0
    assert result["selective_accuracy"] is None
    assert result["macro_specificity_on_accepted"] is None


def test_score_bin_edges_count_every_record_once():
    probabilities = np.zeros((3, len(CLASSES)))
    probabilities[:, 0] = [.3, .6, .7]
    probabilities[:, 1:5] = (1-probabilities[:, 0, None])/4
    result, _, _ = summarize(np.array([0, 1, 2]), probabilities)
    occupied = [i for i, row in enumerate(result["reliability_bins"]) if row["count"]]
    assert occupied == [3, 6, 7]
    assert sum(row["count"] for row in result["reliability_bins"]) == 3


def test_bound_is_one_sided_and_penalizes_small_sample():
    assert upper_risk(0, 0, .05) == 1
    assert upper_risk(10, 10, .05) == 1
    assert upper_risk(0, 10, .05) > upper_risk(0, 100, .05) > 0
    assert upper_risk(0, 100, .001) > upper_risk(0, 100, .05)


def test_source_partition_and_vectorized_runtime_agree():
    data, _ = cohorts()
    sets = {k: set(v["signature"].tolist()) for k, v in data.items()}
    for i, name in enumerate(sets):
        for other in list(sets)[i+1:]:
            assert not sets[name] & sets[other]
    for name in ("tuning", "calibration", "validation"):
        assert len(data[name]["y"]) == len(sets[name])
    sample = subset(data["validation"], np.arange(200))
    bundle, policy = load_v3_bundle(), load_primary_policy()
    for count, negatives in ((1, 0), (2, 0), (3, 0), (3, 3), (8, 5)):
        present, absent = masks(sample, count, negatives)
        probabilities = score(bundle, present, absent, sample)
        accepted = accept_vectorized(policy, probabilities, present.sum(axis=1), absent.sum(axis=1), present)
        for i in range(len(present)):
            p = [FEATURES[j] for j in np.flatnonzero(present[i])]
            a = [FEATURES[j] for j in np.flatnonzero(absent[i])]
            result = classify_primary(p, a, int(sample["age"][i]), "M" if sample["sex"][i] else "F")
            assert (result["status"] == "eligible") == bool(accepted[i])
            assert result["clinical_validation"] is False
            if accepted[i]:
                assert result["primary_prediction"]["condition"] == CLASSES[probabilities[i].argmax()]
                assert "raw_relative_score" not in result["primary_prediction"]
                assert "confidence" not in result["primary_prediction"]
                assert set(result["primary_prediction"]["supporting_features"]) <= set(p)
