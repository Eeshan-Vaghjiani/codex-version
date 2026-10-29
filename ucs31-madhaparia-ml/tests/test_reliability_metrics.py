"""Research metric calculations must preserve class scope and bin boundaries."""
import numpy as np
import pytest

from scripts.audit_saved_model_reliability import reliability_metrics


def test_perfect_scores_have_zero_brier_and_calibration_error():
    metrics, _, _ = reliability_metrics(["A", "B"], np.array([[1., 0.], [0., 1.]]), ["A", "B"], ["A", "B"])
    assert metrics["multiclass_brier"] == 0
    assert metrics["top_label_ece_10_bins"] == 0
    assert sum(b["count"] for b in metrics["score_bins"]) == 2


def test_incorrect_certain_score_is_not_good_calibration():
    metrics, _, _ = reliability_metrics(["A", "B"], np.array([[0., 1.], [1., 0.]]), ["A", "B"], ["A", "B"])
    assert metrics["multiclass_brier"] == 2
    assert metrics["top_label_ece_10_bins"] == 1
    assert metrics["errors_at_scores_at_least_0_9"] == 2


def test_sparse_metrics_retain_original_class_scope():
    metrics, _, _ = reliability_metrics(["A", "B"], np.array([[1., 0., 0.], [0., 1., 0.]]), ["A", "B", "C"], ["A", "B", "C"])
    assert metrics["macro_f1_21_source_classes"] == pytest.approx(2/3)
    assert metrics["source_classes_represented"] == 2


def test_exact_bin_boundaries_are_counted_once_in_upper_bin():
    probabilities = np.array([[.3, .25, .25, .2], [.6, .2, .1, .1], [.7, .1, .1, .1]])
    metrics, _, _ = reliability_metrics(["A", "B", "C"], probabilities, ["A", "B", "C", "D"], ["A", "B", "C", "D"])
    assert [b["lower"] for b in metrics["score_bins"]] == [.3, .6, .7]
    assert sum(b["count"] for b in metrics["score_bins"]) == 3
