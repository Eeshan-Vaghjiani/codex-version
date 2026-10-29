"""Serving/research fail-closed parity; no numeric threshold is validated here."""
import numpy as np
import pytest

from inference.primary_selection import classify_primary, load_primary_policy
from nlp.symptom_mapper import detect_safety_signs
from scripts.evaluate_primary_selection import accept_vectorized


def test_pending_gap_abstains_in_runtime_and_vectorized_evaluation(monkeypatch):
    import inference.primary_selection as selection
    monkeypatch.setattr(selection, 'load_gap_policy', lambda: None)
    result = classify_primary(['E_203', 'E_166'], [], 24, 'F')
    assert result['primary_prediction'] is None and 'gap_validation_pending' in result['reasons']
    accepted = accept_vectorized(load_primary_policy(), np.array([[.99, .01]]),
        np.array([2]), np.array([0]), np.ones((1, 34)))
    assert not accepted.any()


@pytest.mark.parametrize('text,tier', [("I can't breathe", 'emergency'), ('Siwezi kupumua', 'emergency'),
    ('Napumua kwa shida', 'severity_check'), ('Kifua kinabana', 'severity_check'),
    ('I have difficulty breathing when I walk, but I can speak fine', 'urgent_same_day')])
def test_breathing_safety_tiers(text, tier):
    flags = detect_safety_signs(text)
    assert flags and flags[0]['breathing_tier'] == tier


def test_breathing_denial_does_not_become_warning():
    assert detect_safety_signs('I can breathe fine') == []
