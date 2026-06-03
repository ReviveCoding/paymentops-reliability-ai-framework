# Temporal Drift and Backtest Monitoring

## Purpose

This report adds source-stratified time-split monitoring that complements the static ablation. The stratified design prevents a public/synthetic source-mix shift from being mistaken for within-source model drift.

## Monitoring result

**PASS**

The local smoke-test threshold is intentionally set to PSI < 1.00 because this repository uses tiny mixed public/synthetic samples; stricter production thresholds should be configured before deployment.

| Metric | Value |
|---|---:|
| Reference rows | 201 |
| Current rows | 87 |
| Weighted risk-score PSI | 0.905 |
| Weighted amount PSI | 0.781 |
| Current PR-AUC | 0.748 |
| Current F2 | 0.326 |
| Current ECE | 0.101 |
| False auto-clear | 0.488 |
| Review burden | 0.391 |

## Per-source drift checks

| Source | Reference rows | Current rows | Risk-score PSI | Amount PSI |
|---|---:|---:|---:|---:|
| cfpb_style_public_sample | 67 | 29 | 1.439 | 0.000 |
| fraud_benchmark_style_sample | 84 | 36 | 0.376 | 0.191 |
| synthetic_iso20022 | 50 | 22 | 1.065 | 2.774 |

## Champion/challenger decision

- Champion: `rule_prior_residual_runtime_score`
- Monitoring action: `continue_monitoring`
- Challenger action: `keep_champion`

## Boundary

This is a local offline monitoring simulation on small data. It is not evidence of production model monitoring.
