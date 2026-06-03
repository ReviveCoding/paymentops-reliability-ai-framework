# LangGraph PaymentOps Agentic Review Wrapper

## Claim boundary

Local LangGraph wrapper for PaymentOps-style review routing only. No production payment decisioning, proprietary bank data, or JPMC systems.

## Graph nodes

1. intake
2. evidence_retrieval
3. risk_triage
4. compliance_gate
5. reviewer_decision

## Outputs

- Cases: `5`
- Human review count: `1`
- Auto-clear candidate count: `4`
- JSONL decisions: `reports\langgraph_paymentops_outputs\langgraph_decisions.jsonl`

## Resume-safe wording

Added a LangGraph-based local agentic review wrapper with intake, evidence retrieval, risk triage, compliance gating, and human-review routing under non-production claim boundaries.
