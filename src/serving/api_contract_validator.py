from __future__ import annotations

import json
from src.serving.app import app
from src.serving.schemas import CaseRequest, CaseResponse
from src.utils import REPORTS_DIR, ARTIFACTS_DIR, write_json, write_report


def validate_api_contract() -> dict:
    spec = app.openapi()
    paths = spec.get("paths", {})
    required_paths = {"/health": "get", "/investigate": "post"}
    checks = {}
    for path, method in required_paths.items():
        checks[f"{method.upper()} {path}"] = path in paths and method in paths.get(path, {})
    sample_request = {
        "case_id": "API-SMOKE-001",
        "text": "Payment is pending and customer reports wrong recipient.",
        "amount": 12500.0,
        "payment_status": "PDNG",
        "exception_type": "wrong_recipient",
    }
    req = CaseRequest(**sample_request)
    resp = CaseResponse(case_id=req.case_id, risk_score=0.42, final_action="analyst_review", summary="Example summary.")
    checks["request_schema_validation"] = req.case_id == sample_request["case_id"]
    checks["response_schema_validation"] = resp.final_action == "analyst_review"
    checks["openapi_has_components"] = "components" in spec and "schemas" in spec.get("components", {})
    passed = all(checks.values())
    result = {"api_contract_status": "PASS" if passed else "REVIEW", "checks": checks, "openapi_title": spec.get("info", {}).get("title"), "openapi_version": spec.get("info", {}).get("version")}
    out_dir = ARTIFACTS_DIR / "api_contract"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "openapi.json", spec)
    write_json(REPORTS_DIR / "api_contract_validation.json", result)
    rows = "\n".join([f"| {k} | {'PASS' if v else 'FAIL'} |" for k, v in checks.items()])
    body = f"""
## Purpose

This report validates the FastAPI service contract without requiring a running server. It confirms the OpenAPI schema, request/response schemas, and required health/investigation endpoints.

## Result

**{result['api_contract_status']}**

| Check | Result |
|---|---|
{rows}

## Artifact

- `artifacts/api_contract/openapi.json`

## Boundary

This is a local API contract smoke test, not a production API gateway, authentication, or load-testing certification.
"""
    write_report(REPORTS_DIR / "20_api_contract_validation.md", "API Contract Validation", body)
    return result


if __name__ == "__main__":
    print(json.dumps(validate_api_contract(), indent=2))
