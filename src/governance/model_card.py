from __future__ import annotations

from src.utils import ARTIFACTS_DIR, write_report


def write_model_card() -> None:
    body = """
## Model purpose

PaymentOps risk scoring, issue routing, evidence retrieval, and agentic review routing on sample/public-style and synthetic workflows.

## Intended use

Offline evaluation, portfolio demonstration, model-risk documentation practice, and local API testing.

## Prohibited use

Do not use for real payment decisions, real customer decisions, automated adverse action, regulatory reporting, or production deployment without independent validation and approved data access.

## Model families

- TF-IDF + Logistic Regression issue routing baseline
- Logistic Regression risk baseline
- Rule-prior residual correction risk model
- BM25-style retrieval and coverage-adaptive evidence expansion
- Deterministic/Fallback agent orchestration with permission gates

## Key risk controls

- claim boundary
- evidence-slot coverage checks
- source conflict checks
- unsupported action blocking
- human-review escalation
- PASS/REVIEW/BLOCK release gate
"""
    write_report(ARTIFACTS_DIR / "model_cards" / "model_card.md", "PaymentOps Reliability AI Model Card", body)


if __name__ == "__main__":
    write_model_card()
