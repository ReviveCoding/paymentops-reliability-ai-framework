from __future__ import annotations

import numpy as np
from src.evaluation.metrics import review_policy_metrics


def choose_review_threshold(prob, review_capacity_rate: float = 0.30) -> float:
    prob = np.asarray(prob)
    if len(prob) == 0:
        return 0.5
    k = max(1, int(len(prob) * review_capacity_rate))
    return float(np.sort(prob)[-k])


def apply_threshold(prob, threshold: float) -> list[str]:
    return ["analyst_review" if p >= threshold else "auto_resolve" for p in prob]
