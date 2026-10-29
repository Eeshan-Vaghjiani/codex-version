"""Behavioral guarantees for the fitted partial-evidence model.

Synthetic feature tests verify software/state behavior, not expected diagnoses.
"""
import json
from copy import deepcopy
from unittest.mock import patch

import numpy as np
import pytest

from inference.v3_predictor import (
    MODEL_PATH, _distribution, _group, load_v3_bundle, predict_v3, question_information_gain,
)
from scripts.train_v3_partial_evidence import FEATURES, masks, score


def test_artifact_contains_only_authentic_source_classes_and_features():
    bundle = load_v3_bundle()
    assert len(bundle["classes"]) == 21
    assert "COVID-19" not in bundle["classes"]
    assert "Allergic rhinitis" not in bundle["classes"]
    assert bundle["features"] == FEATURES
    assert all(f in bundle["feature_definitions"] for f in FEATURES)


def test_all_ranking_scores_are_normalized_and_deterministic():
    first = predict_v3(["E_201", "E_91"], [], 21, "M", top_k=21)
    second = predict_v3(["E_91", "E_201"], [], 21, "M", top_k=21)
    assert first == second
    scores = [p["raw_relative_score"] for p in first["predictions"]]
    assert sum(scores) == pytest.approx(1)
    assert scores == sorted(scores, reverse=True)
    assert first["clinical_validation"] is False
    assert first["uncertain"] is True
    assert len(first["unmentioned_features"]) == len(FEATURES)-2


def test_explicit_negative_differs_from_unmentioned():
    unknown = predict_v3(["E_201"], [], 21, "M", top_k=21)
    negative = predict_v3(["E_201"], ["E_91"], 21, "M", top_k=21)
    assert unknown["predictions"] != negative["predictions"]
    assert "E_91" in unknown["unmentioned_features"]
    assert "E_91" not in negative["unmentioned_features"]
    assert negative["explicitly_absent_features"] == ["E_91"]


@pytest.mark.parametrize("feature", FEATURES)
def test_each_native_feature_has_a_learned_yes_no_effect(feature):
    bundle = load_v3_bundle()
    group = _group(bundle, 21, "M")
    yes = _distribution(bundle, {feature}, set(), group)
    no = _distribution(bundle, set(), {feature}, group)
    assert not np.allclose(yes, no), feature


def test_no_positive_evidence_requests_clarification():
    result = predict_v3([], ["E_91"], 21, "M")
    assert result["predictions"] == []
    assert result["status"] == "insufficient_evidence"


@pytest.mark.parametrize("present,absent", [(["E_91"],["E_91"]), (["fake"],[]), (["E_91","E_91"],[]), (None,[])])
def test_invalid_or_contradictory_evidence_rejected(present, absent):
    with pytest.raises(ValueError):
        predict_v3(present, absent, 21, "M")


@pytest.mark.parametrize("age,sex", [(True,"M"), (-1,"M"), (121,"M"), (float("nan"),"M"), (21,"X")])
def test_invalid_demographics_rejected(age, sex):
    with pytest.raises(ValueError):
        predict_v3(["E_91"], [], age, sex)


def test_sex_exclusion_is_explicit_and_invariant():
    # Validation-selected artifact excludes sex; it must not covertly affect
    # scores when the request still carries the demographic field.
    assert load_v3_bundle()["demographic_mode"] == "age"
    assert predict_v3(["E_91"], [], 21, "M") == predict_v3(["E_91"], [], 21, "F")


def test_supporting_features_never_invent_evidence():
    result = predict_v3(["E_201","E_91"], ["E_181"], 21, "M")
    for p in result["predictions"]:
        assert set(p["supporting_features"]) <= {"E_201","E_91"}
        assert set(p["supporting_absent_features"]) <= {"E_181"}
        assert set(p["contradicting_features"]) <= {"E_201","E_91"}
        assert set(p["contradicting_absent_features"]) <= {"E_181"}
        assert not set(p["supporting_features"]) & set(p["contradicting_features"])


def test_information_gain_excludes_answered_and_respects_candidates():
    questions = question_information_gain(["E_201"], ["E_91"], 21, "M", ["E_201","E_91","E_181","E_77"])
    assert {q["feature"] for q in questions} == {"E_181","E_77"}
    assert all(q["information_gain"] >= 0 and 0 < q["yes_probability"] < 1 for q in questions)
    assert questions == sorted(questions, key=lambda q: (-q["information_gain"],q["feature"]))
    assert questions == question_information_gain(["E_201"], ["E_91"], 21, "M", ["E_201","E_91","E_181","E_77"])


def test_vectorized_evaluation_matches_portable_runtime():
    bundle = load_v3_bundle()
    present, absent = np.zeros((2,len(FEATURES))), np.zeros((2,len(FEATURES)))
    for i, code in ((0,"E_91"),(0,"E_201"),(1,"E_53"),(1,"E_55_@_V_89")):
        present[i, FEATURES.index(code)] = 1
    absent[1, FEATURES.index("E_55_@_V_101")] = 1
    data = {"age": np.array([21,65]), "sex": np.array([1,0])}
    vectorized = score(bundle,present,absent,data)
    for i in range(2):
        p = {FEATURES[j] for j in np.flatnonzero(present[i])}
        a = {FEATURES[j] for j in np.flatnonzero(absent[i])}
        portable = _distribution(bundle,p,a,_group(bundle,int(data["age"][i]),"M" if data["sex"][i] else "F"))
        assert np.allclose(vectorized[i], portable, atol=1e-12)


@pytest.mark.parametrize("field,value", [("temperature",0), ("demographic_mode","invented"),
    ("age_edges",[40,18]), ("background_likelihood",[.5]),
    ("pain_location_given_pain",[]), ("group_priors",[])])
def test_corrupt_artifact_is_rejected(tmp_path,field,value):
    bundle=deepcopy(load_v3_bundle())
    bundle[field]=value
    artifact=tmp_path/"invalid.json"
    artifact.write_text(json.dumps(bundle),encoding="utf8")
    with pytest.raises(ValueError):
        load_v3_bundle(str(artifact))


def test_masked_positive_reports_are_nested_and_unchanged_by_negative_questions():
    x=np.zeros((10,len(FEATURES)))
    x[:,:8]=1
    data={"x":x}
    one,_=masks(data,1)
    three,no= masks(data,3)
    three_with_negatives,negative=masks(data,3,3)
    assert np.array_equal(three,three_with_negatives)
    assert np.all(one <= three)
    assert np.all(negative.sum(axis=1)==3)
    assert not (negative*x).any()
