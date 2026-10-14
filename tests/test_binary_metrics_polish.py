"""Regression checks compatible with the project's lightweight test runner."""

from src.evaluation.metrics import binary_metrics


def test_f2_uses_reported_precision_and_recall() -> None:
    cases = [
        ([0, 1, 1, 0], [0.1, 0.9, 0.4, 0.3], 1.0, 0.5),
        ([0, 0, 1, 1], [0.8, 0.7, 0.2, 0.1], 0.0, 0.0),
    ]
    for labels, scores, expected_precision, expected_recall in cases:
        result = binary_metrics(labels, scores, threshold=0.5)
        assert abs(result["precision"] - expected_precision) < 1e-12
        assert abs(result["recall"] - expected_recall) < 1e-12
        expected_f2 = (
            5.0 * expected_precision * expected_recall
            / (4.0 * expected_precision + expected_recall + 1e-12)
        )
        assert abs(result["f2"] - expected_f2) < 1e-12
