# Reliability Ablation Results

## Purpose

This report compares vanilla ML/RAG baselines against reliability-enhanced modules. The enhanced path adds calibrated risk scoring, rule-prior residual correction, PHT-inspired Case Health Timestep features, evidence coverage expansion, and ABC-style evidence/action correction.

## Issue routing baseline

| Metric | Value |
|---|---:|
| Macro-F1 | 1.000 |
| Weighted-F1 | 1.000 |

## Risk model ablation

| Version | PR-AUC | F2 | High-risk capture | False auto-clear | Brier | ECE |
|---|---:|---:|---:|---:|---:|---:|
| V0 Vanilla risk model | 0.848 | 0.561 | 0.531 | 0.469 | 0.178 | 0.128 |
| V3 Rule-prior residual + CHT | 0.831 | 0.566 | 0.612 | 0.388 | 0.154 | 0.073 |

## Calibration note

Temperature-scaled enhanced score:

| Metric | Value |
|---|---:|
| Brier | 0.154 |
| ECE | 0.078 |

## RAG/evidence ablation

| Metric | Vanilla BM25 Top-1 | Evidence Coverage + ABC Correction |
|---|---:|---:|
| Evidence-slot Recall | 0.400 | 1.000 |
| Evidence-slot Precision | 1.000 | 1.000 |
| Evidence-slot F1 | 0.571 | 1.000 |

## Interpretation

- Vanilla ML/RAG establishes a fair baseline.
- Rule-prior residual correction anchors learned risk in interpretable payment/complaint risk cues.
- Case Health Timestep adds a case-maturity feature rather than assuming raw event age is sufficient.
- Evidence coverage expansion improves missing-evidence recovery, while ABC correction removes unsupported or duplicated evidence.
