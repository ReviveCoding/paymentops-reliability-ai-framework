"""Regression tests for shared precision/recall calculations."""

import pytest

from src.evaluation.metrics import binary_metrics


@pytest.mark.parametrize(
    ("labels", "scores", "threshold", "expected_precision", "expected_recall"),
    [
        ([0, 1, 1, 0], [0.1, 0.9, 0.4, 0.3], 0.5, 1.0, 0.5),
        ([0, 0, 1, 1], [0.8, 0.7, 0.2, 0.1], 0.5, 0.0, 0.0),
    ],
)
def test_f2_uses_reported_precision_and_recall(
    labels, scores, threshold, expected_precision, expected_recall
) -> None:
    result = binary_metrics(labels, scores, threshold)
    assert result["precision"] == pytest.approx(expected_precision)
    assert result["recall"] == pytest.approx(expected_recall)
    expected_f2 = (
        5 * expected_precision * expected_recall
        / (4 * expected_precision + expected_recall + 1e-12)
    )
    assert result["f2"] == pytest.approx(expected_f2)
