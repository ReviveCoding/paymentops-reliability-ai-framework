from __future__ import annotations

import json
import os
from pathlib import Path
from src.utils import ROOT, REPORTS_DIR, write_json, write_report

EXCLUDE_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache"}


def run_repository_audit() -> dict:
    files = []
    for path in ROOT.rglob("*"):
        if any(part in EXCLUDE_DIRS for part in path.parts):
            continue
        if path.is_file():
            rel = path.relative_to(ROOT).as_posix()
            size = path.stat().st_size
            files.append({"path": rel, "size_bytes": size})
    total_size = sum(f["size_bytes"] for f in files)
    large_files = [f for f in files if f["size_bytes"] > 2_000_000]
    py_files = [f for f in files if f["path"].endswith(".py")]
    report_files = [f for f in files if f["path"].startswith("reports/")]
    # Keep this audit independent of the release gate to avoid a circular dependency:
    # release_gate reads repository_audit.json, while release_gate itself generates
    # reports/09_release_decision.md. Therefore, 09_release_decision.md is verified
    # by the release-gate check, not by the pre-release repository audit.
    required = [
        "README.md", "CLAIM_BOUNDARY.md", "Makefile", "Dockerfile", "requirements.txt",
        "reports/02_baseline_results.md", "reports/03_reliability_ablation.md",
        "RUN_VERIFICATION.md",
    ]
    missing = [p for p in required if not (ROOT / p).exists()]
    result = {
        "audit_status": "PASS" if not missing and not large_files else "REVIEW",
        "num_files": len(files),
        "num_python_files": len(py_files),
        "num_report_files": len(report_files),
        "total_size_mb": total_size / 1_000_000,
        "large_files": large_files,
        "missing_required_files": missing,
        "local_runnable_commands": ["make all", "make test", "make serve"],
    }
    write_json(REPORTS_DIR / "repository_audit.json", result)
    rows = "\n".join([f"| {k} | `{v}` |" for k, v in result.items() if k not in {"large_files", "missing_required_files", "local_runnable_commands"}])
    body = f"""
## Purpose

This audit checks whether the repository remains lightweight, local/GitHub runnable, and portfolio-safe after the hardening loop.

## Summary

| Field | Value |
|---|---|
{rows}

## Large files

`{large_files}`

## Missing required files

`{missing}`

## Runnable commands

- `make all`
- `make test`
- `make serve`

## Optimization decision

No generated raw public datasets or large binaries are committed. The repository keeps sample/synthetic data for portability and keeps full-dataset adapters as code rather than cached data.
"""
    write_report(REPORTS_DIR / "19_repository_runnability_audit.md", "Repository Runnability and Efficiency Audit", body)
    return result


if __name__ == "__main__":
    print(json.dumps(run_repository_audit(), indent=2))
