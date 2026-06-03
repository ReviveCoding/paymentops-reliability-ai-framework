from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
import pandas as pd
from src.utils import DATA_DIR, REPORTS_DIR, ARTIFACTS_DIR, write_json, write_report


@dataclass
class ExpectationResult:
    expectation: str
    passed: bool
    observed: object
    details: str


def _json_safe(value):
    try:
        import numpy as np
        if isinstance(value, (np.integer,)):
            return int(value)
        if isinstance(value, (np.floating,)):
            return float(value)
        if isinstance(value, (np.bool_,)):
            return bool(value)
    except Exception:
        pass
    if isinstance(value, set):
        return sorted(value)
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    return value


def _result(expectation: str, passed: bool, observed: object, details: str) -> dict:
    return ExpectationResult(expectation, bool(passed), _json_safe(observed), details).__dict__


COMMON_EXPECTATIONS = {
    "case_id": "non_null_unique_string",
    "source_dataset": "non_null_string",
    "event_time": "parseable_datetime",
    "case_type": "allowed_domain",
    "amount": "non_negative_numeric",
    "text": "non_empty_string",
    "risk_label": "binary_0_1",
    "route_label": "allowed_domain",
    "payment_status": "non_null_string",
    "exception_type": "non_null_string",
    "issue_group": "non_null_string",
}

ALLOWED_CASE_TYPES = {"customer_complaint", "fraud_transaction", "iso20022_payment_case"}
ALLOWED_ROUTES = {"auto_resolve", "analyst_review", "compliance_review", "compliance_escalation", "human_review_required"}


def validate_common_case_contract(df: pd.DataFrame) -> list[dict]:
    results: list[dict] = []
    required = list(COMMON_EXPECTATIONS)
    missing = [c for c in required if c not in df.columns]
    results.append(_result("all_required_columns_present", not missing, missing, "Common case schema must contain all required columns."))
    if missing:
        return results

    results.extend([
        _result("case_id_non_null", df["case_id"].notna().all(), int(df["case_id"].isna().sum()), "No case_id should be null."),
        _result("case_id_unique", df["case_id"].is_unique, int(df["case_id"].duplicated().sum()), "case_id should uniquely identify a case."),
        _result("event_time_parseable", pd.to_datetime(df["event_time"], errors="coerce").notna().all(), int(pd.to_datetime(df["event_time"], errors="coerce").isna().sum()), "All event_time values should parse as datetimes."),
        _result("case_type_allowed", set(df["case_type"].dropna().unique()).issubset(ALLOWED_CASE_TYPES), sorted(set(df["case_type"].dropna().unique())), "case_type must stay inside the documented ontology."),
        _result("amount_non_negative", (pd.to_numeric(df["amount"], errors="coerce") >= 0).all(), float(pd.to_numeric(df["amount"], errors="coerce").min()), "amount should be non-negative."),
        _result("text_non_empty", df["text"].fillna("").astype(str).str.len().gt(0).all(), int(df["text"].fillna("").astype(str).str.len().eq(0).sum()), "All cases should have text/narrative for routing and RAG."),
        _result("risk_label_binary", set(df["risk_label"].dropna().astype(int).unique()).issubset({0, 1}), sorted(set(df["risk_label"].dropna().astype(int).unique())), "risk_label must be binary for this benchmark."),
        _result("route_label_allowed", set(df["route_label"].dropna().unique()).issubset(ALLOWED_ROUTES), sorted(set(df["route_label"].dropna().unique())), "route_label must be an allowed route."),
    ])
    for col in ["source_dataset", "payment_status", "exception_type", "issue_group"]:
        results.append(_result(f"{col}_non_null", df[col].notna().all(), int(df[col].isna().sum()), f"{col} should not be null."))
    return results


def run_data_contract_validation() -> dict:
    path = DATA_DIR / "processed" / "common_case_schema_sample.csv"
    df = pd.read_csv(path, keep_default_na=False)
    results = validate_common_case_contract(df)
    passed = all(r["passed"] for r in results)
    summary = {
        "passed": passed,
        "num_expectations": len(results),
        "num_failed": sum(not r["passed"] for r in results),
        "results": results,
    }
    ARTIFACTS_DIR.joinpath("data_contracts").mkdir(parents=True, exist_ok=True)
    write_json(ARTIFACTS_DIR / "data_contracts" / "common_case_expectation_suite.json", {
        "suite_name": "common_case_schema_expectations",
        "expectations": COMMON_EXPECTATIONS,
        "allowed_case_types": sorted(ALLOWED_CASE_TYPES),
        "allowed_routes": sorted(ALLOWED_ROUTES),
    })
    write_json(REPORTS_DIR / "data_contract_validation.json", summary)
    rows = "\n".join([f"| {r['expectation']} | {'PASS' if r['passed'] else 'FAIL'} | `{r['observed']}` | {r['details']} |" for r in results])
    body = f"""
## Purpose

This report implements a lightweight Great-Expectations-style data contract for the common case schema. It is dependency-light so the project remains local/GitHub runnable, but it preserves the production pattern of explicit expectations, validation results, and human-readable documentation.

## Result

**{'PASS' if passed else 'FAIL'}**

| Expectation | Result | Observed | Details |
|---|---|---|---|
{rows}

## Artifact

The expectation suite is saved at `artifacts/data_contracts/common_case_expectation_suite.json`.
"""
    write_report(REPORTS_DIR / "15_data_contract_validation.md", "Data Contract Validation", body)
    return summary


if __name__ == "__main__":
    print(json.dumps(run_data_contract_validation(), indent=2))
