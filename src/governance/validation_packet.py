from __future__ import annotations

import json
from src.utils import REPORTS_DIR, write_report


def write_validation_packet() -> None:
    metrics_path = REPORTS_DIR / "ablation_metrics.json"
    metrics = json.loads(metrics_path.read_text(encoding="utf-8")) if metrics_path.exists() else {}
    robustness = json.loads((REPORTS_DIR / "robustness_metrics.json").read_text(encoding="utf-8")) if (REPORTS_DIR / "robustness_metrics.json").exists() else {}
    feature_store = json.loads((REPORTS_DIR / "feature_store_validation.json").read_text(encoding="utf-8")) if (REPORTS_DIR / "feature_store_validation.json").exists() else {}
    security = json.loads((REPORTS_DIR / "security_guardrail_metrics.json").read_text(encoding="utf-8")) if (REPORTS_DIR / "security_guardrail_metrics.json").exists() else {"summary": {}}
    body = f"""
## Purpose

Document validation evidence for the local PaymentOps Reliability AI Framework.

## Govern

- Intended use: offline portfolio and model-validation demonstration.
- Prohibited use: real payment decisioning, production use, or regulatory certification.
- Human-review policy: weak evidence, source conflict, high-impact action, or elevated risk must route to review.

## Map

- Data sources: CFPB-style sample, fraud benchmark-style sample, synthetic ISO 20022-inspired payment cases, synthetic policy docs.
- Claim boundary: no proprietary bank data and no production deployment.

## Measure

```json
{json.dumps(metrics, indent=2)[:5000]}
```

## Robustness, feature-store, and guardrail checks

```json
{json.dumps({"robustness": robustness, "feature_store": feature_store, "security": security.get("summary", {})}, indent=2)[:4000]}
```

## Manage

- Permission gates block unsafe actions.
- PII redaction and prompt-injection smoke tests are included.
- Feature-store-style schema/backfill validation is included.
- Worst-slice and stress-test reports surface fragile local slices.
- Release gate returns PASS/REVIEW/BLOCK.
- Audit logs preserve case_id, risk score, evidence document IDs, and final action.

## Known limitations

- Sample data is intentionally small for local reproducibility.
- The RAG layer uses deterministic templates and BM25-style retrieval by default.
- LangGraph and external LLM backends are optional.
- AWS/SageMaker files are compatibility scaffolds only unless actual run logs are added.
- AWS/SageMaker readiness pack, model registry manifests, feature-store-style schema governance, and Transformer fine-tuning scaffold are not evidence of actual cloud execution or fine-tuning.
- Security guardrail tests are local synthetic smoke tests, not a formal penetration test or privacy certification.
"""
    write_report(REPORTS_DIR / "06_model_validation_packet.md", "Model Validation Packet", body)


if __name__ == "__main__":
    write_validation_packet()
