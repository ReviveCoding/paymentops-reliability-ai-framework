from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    f1_score, precision_score, recall_score, roc_auc_score, average_precision_score,
    brier_score_loss, classification_report
)


def safe_auc(y_true, y_score, kind="roc") -> float:
    try:
        if len(set(y_true)) < 2:
            return 0.5
        return float(roc_auc_score(y_true, y_score) if kind == "roc" else average_precision_score(y_true, y_score))
    except Exception:
        return 0.5


def expected_calibration_error(y_true, y_prob, n_bins: int = 10) -> float:
    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob)
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    for lo, hi in zip(bins[:-1], bins[1:]):
        mask = (y_prob >= lo) & (y_prob < hi if hi < 1.0 else y_prob <= hi)
        if mask.sum() == 0:
            continue
        acc = y_true[mask].mean()
        conf = y_prob[mask].mean()
        ece += (mask.sum() / len(y_prob)) * abs(acc - conf)
    return float(ece)


def binary_metrics(y_true, y_prob, threshold: float = 0.5) -> dict:
    y_pred = (np.asarray(y_prob) >= threshold).astype(int)
    return {
        "roc_auc": safe_auc(y_true, y_prob, "roc"),
        "pr_auc": safe_auc(y_true, y_prob, "pr"),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "f2": float((5 * precision_score(y_true, y_pred, zero_division=0) * recall_score(y_true, y_pred, zero_division=0)) / (4 * precision_score(y_true, y_pred, zero_division=0) + recall_score(y_true, y_pred, zero_division=0) + 1e-12)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "brier": float(brier_score_loss(y_true, y_prob)),
        "ece": expected_calibration_error(y_true, y_prob),
    }


def review_policy_metrics(y_true, y_prob, review_capacity_rate: float = 0.30) -> dict:
    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob)
    k = max(1, int(len(y_prob) * review_capacity_rate))
    order = np.argsort(-y_prob)
    review = np.zeros(len(y_prob), dtype=bool)
    review[order[:k]] = True
    positives = max(1, int(y_true.sum()))
    high_risk_capture = float(y_true[review].sum() / positives)
    false_auto_clear = float(((y_true == 1) & (~review)).sum() / positives)
    review_burden = float(review.mean())
    return {
        "high_risk_capture": high_risk_capture,
        "false_auto_clear_rate": false_auto_clear,
        "review_burden": review_burden,
    }


def evidence_slot_metrics(required: set[str], predicted: set[str]) -> dict:
    tp = len(required & predicted)
    fp = len(predicted - required)
    fn = len(required - predicted)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2*precision*recall/(precision+recall) if (precision + recall) else 0.0
    return {"evidence_slot_precision": precision, "evidence_slot_recall": recall, "evidence_slot_f1": f1}
