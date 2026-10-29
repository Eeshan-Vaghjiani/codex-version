from copy import deepcopy
import json

import numpy as np
import pytest
from inference.primary_selection import load_gap_policy
from scripts.validate_gap_gate import candidate_mask


def test_predeclared_gap_floor_and_one_symptom_rejection():
    scores = np.array([[.52, .48], [.59, .41], [.8, .2], [.8, .2]])
    accepted = candidate_mask(np.ones(4, dtype=bool), scores, np.array([2, 2, 1, 2]))
    assert accepted.tolist() == [False, False, False, True]


def test_missing_gap_artifact_does_not_authorise_naming(tmp_path):
    assert load_gap_policy(str(tmp_path / 'missing.json')) is None


@pytest.mark.parametrize('field,value', [('clinical_validation', True), ('test_used_for_selection', True),
    ('model_sha256', '0'*64), ('base_policy_sha256', '0'*64), ('minimum_relative_gap', float('nan')),
    ('minimum_relative_score', True), ('buckets', {}), ('minimum_present_count', 1)])
def test_gap_artifact_rejects_drift_or_invalid_claims(tmp_path, field, value):
    original = load_gap_policy()
    if original is None:
        pytest.fail('Run the predeclared source-validation check to produce the gap artifact')
    gate = deepcopy(original)
    gate[field] = value
    path = tmp_path / 'invalid.json'
    path.write_text(json.dumps(gate), encoding='utf8')
    with pytest.raises(ValueError):
        load_gap_policy(str(path))
