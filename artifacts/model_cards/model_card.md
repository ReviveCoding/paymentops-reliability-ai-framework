# PaymentOps Reliability AI Model Card

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
