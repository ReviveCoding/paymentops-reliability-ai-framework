# Operating Policy Frontier

## Purpose

The first enhanced implementation improved false auto-clear and evidence reliability but still had a calibration/review-burden tradeoff. This policy frontier explicitly optimizes the operating point instead of hard-coding one threshold.

## Selected policy

| Field | Value |
|---|---|
| Score source | `ml_residual` |
| Temperature | 1.00 |
| Review capacity | 0.45 |
| Prior blend weight | `None` |
| Constraint status | `PASS` |

## Baseline vs selected operating policy

| Metric | Vanilla baseline | Selected enhanced policy |
|---|---:|---:|
| PR-AUC | 0.848 | 0.831 |
| F2 | 0.561 | 0.566 |
| High-risk capture | 0.531 | 0.612 |
| False auto-clear | 0.469 | 0.388 |
| Review burden | 0.297 | 0.446 |
| Brier | 0.178 | 0.154 |
| ECE | 0.128 | 0.073 |

## Top operating-policy candidates

| Rank | Score source | Temp | Review cap | Prior weight | PR-AUC | F2 | Capture | False auto-clear | Burden | ECE | Objective |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | ml_residual | 1.00 | 0.45 | None | 0.831 | 0.566 | 0.612 | 0.388 | 0.446 | 0.073 | 1.157 |
| 2 | blend_rule_prior_ml_residual | 1.00 | 0.45 | 0.0 | 0.831 | 0.566 | 0.612 | 0.388 | 0.446 | 0.073 | 1.157 |
| 3 | blend_rule_prior_ml_residual | 1.00 | 0.45 | 0.1 | 0.829 | 0.566 | 0.612 | 0.388 | 0.446 | 0.074 | 1.153 |
| 4 | ml_residual | 1.10 | 0.45 | None | 0.831 | 0.566 | 0.612 | 0.388 | 0.446 | 0.078 | 1.149 |
| 5 | blend_rule_prior_ml_residual | 1.10 | 0.45 | 0.0 | 0.831 | 0.566 | 0.612 | 0.388 | 0.446 | 0.078 | 1.149 |
| 6 | ml_residual | 0.80 | 0.45 | None | 0.831 | 0.566 | 0.612 | 0.388 | 0.446 | 0.088 | 1.136 |
| 7 | blend_rule_prior_ml_residual | 0.90 | 0.45 | 0.30000000000000004 | 0.829 | 0.566 | 0.612 | 0.388 | 0.446 | 0.087 | 1.131 |
| 8 | ml_residual | 1.00 | 0.40 | None | 0.831 | 0.566 | 0.592 | 0.408 | 0.396 | 0.073 | 1.130 |
| 9 | blend_rule_prior_ml_residual | 1.00 | 0.40 | 0.0 | 0.831 | 0.566 | 0.592 | 0.408 | 0.396 | 0.073 | 1.130 |
| 10 | blend_rule_prior_ml_residual | 1.10 | 0.45 | 0.1 | 0.829 | 0.566 | 0.612 | 0.388 | 0.446 | 0.093 | 1.126 |

## Interpretation

The final project now exposes a review-capacity frontier rather than a single brittle threshold. This is closer to financial-operations deployment review, where risk capture, false auto-clear, calibration, and analyst burden must be jointly managed.
