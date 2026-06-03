from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import random
import pandas as pd
from src.utils import DATA_DIR, seed_everything, write_jsonl

STATUSES = ["ACCP", "ACSP", "RJCT", "PDNG"]
REASONS = {
    "ACCP": "accepted for processing",
    "ACSP": "accepted settlement in process",
    "RJCT": "rejected by business validation",
    "PDNG": "pending beneficiary confirmation",
}
EXCEPTIONS = ["none", "duplicate_payment", "future_dated", "amount_limit", "missing_beneficiary", "status_mismatch", "manual_compliance_review"]


def generate_iso20022_cases(n: int = 72, seed: int = 42) -> list[dict]:
    seed_everything(seed)
    rows = []
    base_date = datetime(2026, 1, 1)
    for i in range(n):
        amount = round(random.lognormvariate(8.6, 1.05), 2)
        status = random.choices(STATUSES, weights=[0.35, 0.25, 0.25, 0.15], k=1)[0]
        exception = random.choices(EXCEPTIONS, weights=[0.36, 0.12, 0.10, 0.14, 0.10, 0.09, 0.09], k=1)[0]
        if amount > 20000 and exception == "none":
            exception = "amount_limit"
        if status == "RJCT" and exception == "none":
            exception = random.choice(EXCEPTIONS[1:])
        risk_label = int(status in {"RJCT", "PDNG"} or exception in {"duplicate_payment", "amount_limit", "status_mismatch", "manual_compliance_review"} or amount > 35000)
        event_time = base_date + timedelta(hours=6*i)
        rows.append({
            "case_id": f"ISO-{i:04d}",
            "source_dataset": "synthetic_iso20022",
            "event_time": event_time.isoformat(),
            "pacs008_id": f"PACS008-{100000+i}",
            "pacs002_id": f"PACS002-{100000+i}",
            "amount": amount,
            "currency": "USD",
            "debtor_agent": f"BANKUS{random.randint(10,99)}XXX",
            "creditor_agent": f"RCVRUS{random.randint(10,99)}XXX",
            "payment_status": status,
            "status_reason": REASONS[status],
            "exception_type": exception,
            "narrative": f"Synthetic pacs.008 credit transfer with pacs.002 status {status}; exception={exception}; amount={amount}.",
            "risk_label": risk_label,
            "route_label": "compliance_review" if exception == "manual_compliance_review" else ("analyst_review" if risk_label else "auto_resolve"),
        })
    return rows


def generate_policy_docs() -> list[dict]:
    return [
        {"doc_id": "POL-001", "title": "Payment status handling", "slots": ["payment_status", "required_action"], "content": "If a pacs.002 status is RJCT or PDNG, the case must not be auto-cleared until the rejection or pending reason is reviewed."},
        {"doc_id": "POL-002", "title": "Amount limit review", "slots": ["policy_rule", "risk_reason", "required_action"], "content": "Payments above the configured amount threshold require analyst review when combined with missing beneficiary, duplicate, or status mismatch indicators."},
        {"doc_id": "POL-003", "title": "Duplicate payment control", "slots": ["policy_rule", "risk_reason"], "content": "Duplicate payment signals require evidence of unique payment identifiers before auto-resolution."},
        {"doc_id": "POL-004", "title": "Customer impact handling", "slots": ["customer_impact", "required_action"], "content": "Customer-impacting payment delays should be routed to analyst review when there is weak evidence or conflicting status information."},
        {"doc_id": "POL-005", "title": "Compliance action gate", "slots": ["policy_rule", "required_action"], "content": "Compliance review is required before any block or escalation action if the case contains manual compliance review flags."},
        {"doc_id": "POL-006", "title": "Evidence sufficiency", "slots": ["policy_rule", "required_action"], "content": "If required evidence slots are missing, the assistant must abstain from final resolution and route the case to human review."},
    ]


def save_iso20022(n: int = 72, seed: int = 42) -> None:
    synthetic_dir = DATA_DIR / "synthetic"
    synthetic_dir.mkdir(parents=True, exist_ok=True)
    cases = generate_iso20022_cases(n=n, seed=seed)
    write_jsonl(synthetic_dir / "iso20022_cases.jsonl", cases)
    write_jsonl(synthetic_dir / "payment_policy_docs.jsonl", generate_policy_docs())
    pd.DataFrame(cases).to_csv(synthetic_dir / "iso20022_cases.csv", index=False)


if __name__ == "__main__":
    save_iso20022()
