import numpy as np
from src.reliability.policy_optimizer import optimize_operating_policy


def test_policy_optimizer_selects_policy():
    y = np.array([0, 1, 1, 0, 1, 0])
    result = optimize_operating_policy(y, {"ml_residual": np.array([0.1, 0.8, 0.7, 0.2, 0.9, 0.3]), "rule_prior": np.array([0.2, 0.6, 0.5, 0.1, 0.8, 0.2])})
    assert "selected_policy" in result
    assert len(result["selected_prob"]) == len(y)
    assert result["selected_policy"]["metrics"]["high_risk_capture"] >= 0
