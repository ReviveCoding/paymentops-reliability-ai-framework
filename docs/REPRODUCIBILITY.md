# Reproducibility

## Environment Setup

    cd "C:\Users\bjw-0\Downloads\paymentops_reliability_ai_framework"
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install --upgrade pip
    pip install -r requirements.txt

## GitHub-Clean Sample Validation

    python -m src.scripts.run_all
    python -m src.scripts.run_tests
    python -m pytest -q
    Get-Content .\reports\repository_audit.json

Expected:
- 21 passed, 0 failed
- 21 passed
- audit_status: PASS
- large_files: []

## External Public/Proxy Data Validation

    $env:PAYMENTOPS_EXTERNAL_DATA = "C:\Users\bjw-0\Downloads\paymentops_external_data"
    python -m src.scripts.run_score_alignment_blend_experiment --max-ibm-rows 500000 --chunk-size 100000 --max-chunks 80 --max-features 10000 --review-capacity 0.35 --n-thresholds 101

Expected output reports:
- reports/28_score_alignment_blend_experiment.md
- reports/score_alignment_blend_metrics.json
- reports/28_score_alignment_blend_resume_claims.md

## Repository Hygiene Check

    Get-ChildItem -Recurse -File | Where-Object {$_.Length -gt 50MB} | Select-Object FullName, Length
    git status --short

No large dataset or model artifact should be staged for commit.
