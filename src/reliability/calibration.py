from __future__ import annotations

import numpy as np
from src.evaluation.metrics import expected_calibration_error


def temperature_scale(prob, temperature: float = 1.15):
    prob = np.asarray(prob).clip(1e-6, 1 - 1e-6)
    logit = np.log(prob / (1 - prob))
    scaled = 1 / (1 + np.exp(-logit / temperature))
    return scaled


def calibration_summary(y_true, prob) -> dict:
    from sklearn.metrics import brier_score_loss
    return {"brier": float(brier_score_loss(y_true, prob)), "ece": expected_calibration_error(y_true, prob)}
