from __future__ import annotations

from datetime import datetime, timedelta
import random
import pandas as pd
from src.utils import DATA_DIR, seed_everything

PRODUCTS = ["Credit card", "Checking or savings account", "Money transfer", "Mortgage", "Debt collection"]
ISSUES = {
    "Credit card": ["billing dispute", "fraudulent charge", "late fee", "account closure"],
    "Checking or savings account": ["unauthorized transfer", "deposit hold", "account access", "overdraft fee"],
    "Money transfer": ["delayed transfer", "wrong recipient", "refund not received", "transfer rejected"],
    "Mortgage": ["payment processing", "escrow issue", "loan modification", "foreclosure notice"],
    "Debt collection": ["communication tactics", "debt not owed", "threatened legal action", "credit reporting"],
}


def _severity(issue: str, timely: str, disputed: int) -> int:
    severe_terms = ["fraud", "unauthorized", "rejected", "foreclosure", "threatened", "wrong recipient"]
    return int(any(term in issue for term in severe_terms) or timely == "No" or disputed == 1)


def generate_cfpb_sample(n: int = 96, seed: int = 42) -> pd.DataFrame:
    seed_everything(seed)
    base = datetime(2026, 1, 1)
    rows = []
    for i in range(n):
        product = random.choice(PRODUCTS)
        issue = random.choice(ISSUES[product])
        timely = random.choices(["Yes", "No"], weights=[0.82, 0.18], k=1)[0]
        disputed = int(random.random() < (0.28 if issue in {"fraudulent charge", "unauthorized transfer", "wrong recipient", "debt not owed"} else 0.12))
        narrative = (
            f"Consumer reports {issue} involving {product.lower()}. "
            f"The case mentions customer impact, response status {timely}, and supporting documents."
        )
        risk_label = _severity(issue, timely, disputed)
        issue_group = "payment_or_transfer" if product in {"Money transfer", "Checking or savings account"} else product.lower().replace(" ", "_")
        rows.append({
            "complaint_id": f"CFPB-{i:04d}",
            "source_dataset": "cfpb_style_public_sample",
            "date_received": (base + timedelta(days=i)).date().isoformat(),
            "event_time": (base + timedelta(days=i)).isoformat(),
            "product": product,
            "issue": issue,
            "issue_group": issue_group,
            "consumer_complaint_narrative": narrative,
            "company_response": random.choice(["Closed with explanation", "Closed with monetary relief", "In progress"]),
            "timely_response": timely,
            "consumer_disputed": disputed,
            "state": random.choice(["NJ", "NY", "CA", "OH", "TX"]),
            "submitted_via": random.choice(["Web", "Phone", "Referral"]),
            "risk_label": risk_label,
            "route_label": "analyst_review" if risk_label else "auto_resolve",
        })
    return pd.DataFrame(rows)


def save_cfpb_sample(n: int = 96, seed: int = 42) -> None:
    out = DATA_DIR / "sample_public" / "cfpb_sample.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    generate_cfpb_sample(n=n, seed=seed).to_csv(out, index=False)


if __name__ == "__main__":
    save_cfpb_sample()
