# PaymentOps Reliability AI Framework

A GitHub-clean, local-runnable financial AI reliability framework for PaymentOps-style risk routing, AML transaction behavior modeling, source-wise score calibration, review-capacity evaluation, retraining simulation, and governance-ready model validation.

This project uses external public/proxy CFPB and IBM AML-style datasets only. It does not use proprietary bank data, production payment logs, real customer account data, JPMC data, or regulatory certification artifacts.

## Repository Description

Reliability-oriented PaymentOps risk-routing framework with source-wise calibration, AML behavior modeling, and review-capacity evaluation.

## Key Results

On a 130,982-row future test split, the selected source-aligned router improved over a combined text baseline:

| Metric | Combined Text Baseline | Source-Aligned Router | Change |
|---|---:|---:|---:|
| PR-AUC | 0.1828 | 0.2103 | +15.0% |
| ROC-AUC | 0.8904 | 0.9045 | +1.6% |
| F2 | 0.4371 | 0.4526 | +3.5% |
| Brier Score | 0.0972 | 0.0224 | -76.9% |
| ECE | 0.1810 | 0.0064 | -96.5% |
| High-Risk Capture | 0.9223 | 0.9417 | +1.94 pts |
| False Auto-Clear | 0.0777 | 0.0583 | -25.0% |

## What This Project Demonstrates

- Source-specific adapters for CFPB complaint narratives and IBM AML-style transaction data
- Temporal train/validation/test splits for future-test evaluation
- Text baselines, AML behavior features, and source-specific routing
- Source-wise score normalization, percentile alignment, sigmoid calibration, and isotonic calibration
- Review-capacity evaluation and false auto-clear analysis
- Brier score and ECE calibration diagnostics
- Operational backtesting and retraining-policy simulation
- Governance-ready reports and claim boundaries
- GitHub-clean local reproducibility with tests and repository audit

## Project Positioning

This is not a single classifier notebook. It is a reliability-oriented financial AI evaluation framework that tests how PaymentOps-style risk scores behave under source shift, class imbalance, review-capacity limits, calibration error, retraining policy, and governance constraints.

## Main Workflow

1. Build a combined public/proxy case schema.
2. Train baseline text risk-routing models.
3. Engineer IBM AML raw transaction behavior features.
4. Train source-specific CFPB and IBM AML models.
5. Align score scales using source-wise normalization and calibration.
6. Select operating policies using validation data.
7. Evaluate final metrics on a held-out future test split.
8. Generate governance-ready reports and claim boundaries.

## Claim Boundary

Supported wording:
- external public/proxy data
- PaymentOps-style risk routing
- AML-style transaction behavior modeling
- source-wise score calibration
- review-capacity evaluation
- governance-ready reporting
- local-runnable / GitHub-clean prototype

Unsupported wording:
- production-deployed payment risk model
- real bank transaction model
- certified regulatory model
- JPMC internal data or systems
- proprietary bank data or production payment logs

See docs/CLAIM_BOUNDARY.md for details.

## Local Setup

Run:

    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install --upgrade pip
    pip install -r requirements.txt

## GitHub-Clean Sample Run

Run:

    python -m src.scripts.run_all
    python -m src.scripts.run_tests
    python -m pytest -q
    Get-Content .\reports\repository_audit.json

Expected:
- 21 passed, 0 failed
- 21 passed
- audit_status: PASS
- large_files: []

## External Public/Proxy Data Run

Run:

    $env:PAYMENTOPS_EXTERNAL_DATA = "C:\Users\bjw-0\Downloads\paymentops_external_data"
    python -m src.scripts.run_score_alignment_blend_experiment --max-ibm-rows 500000 --chunk-size 100000 --max-chunks 80 --max-features 10000 --review-capacity 0.35 --n-thresholds 101

Primary reports:
- reports/28_score_alignment_blend_experiment.md
- reports/score_alignment_blend_metrics.json
- reports/28_score_alignment_blend_resume_claims.md

## Resume-Safe Summary

Built a GitHub-clean PaymentOps reliability AI framework using external public/proxy CFPB and IBM AML datasets, with temporal validation, source-wise score calibration, review-capacity evaluation, operational backtesting, retraining simulation, and governance-ready reports.

Improved a combined text risk-routing baseline with source-wise isotonic score calibration and aligned routing on 523,927 rows, increasing PR-AUC by 15.0%, reducing Brier score by 76.9%, and lowering false auto-clear by 25.0% on a 130,982-row future test split.

## Author

Jinwoo Bae  
GitHub: ReviveCoding
