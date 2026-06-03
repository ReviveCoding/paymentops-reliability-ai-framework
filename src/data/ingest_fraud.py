from __future__ import annotations

from datetime import datetime, timedelta
import random
import numpy as np
import pandas as pd
from src.utils import DATA_DIR, seed_everything


def generate_fraud_sample(n: int = 120, seed: int = 42) -> pd.DataFrame:
    seed_everything(seed)
    rows = []
    base = datetime(2026, 1, 1)
    for i in range(n):
        amount = float(np.random.lognormal(mean=7.8, sigma=1.05))
        merchant_risk = random.random()
        country_risk = random.choice([0.05, 0.15, 0.35, 0.65, 0.90])
        account_age_days = random.randint(1, 2200)
        velocity_1h = np.random.poisson(1.3 + 4.0*merchant_risk)
        card_present = int(random.random() < 0.55)
        new_device = int(random.random() < (0.10 + 0.45*merchant_risk))
        score = (
            0.000035*amount + 1.2*merchant_risk + 0.9*country_risk + 0.11*velocity_1h +
            0.6*new_device - 0.00025*account_age_days - 0.35*card_present
        )
        prob = 1 / (1 + np.exp(-(score - 1.65)))
        is_fraud = int(random.random() < prob)
        rows.append({
            "transaction_id": f"FRD-{i:04d}",
            "source_dataset": "fraud_benchmark_style_sample",
            "event_time": (base + timedelta(minutes=20*i)).isoformat(),
            "amount": round(amount, 2),
            "merchant_risk": round(merchant_risk, 3),
            "country_risk": country_risk,
            "account_age_days": account_age_days,
            "velocity_1h": int(velocity_1h),
            "card_present": card_present,
            "new_device": new_device,
            "risk_label": is_fraud,
            "route_label": "analyst_review" if is_fraud else "auto_resolve",
            "narrative": f"Transaction amount {round(amount,2)} with merchant risk {round(merchant_risk,2)}, country risk {country_risk}, velocity {int(velocity_1h)}.",
        })
    return pd.DataFrame(rows)


def save_fraud_sample(n: int = 120, seed: int = 42) -> None:
    out = DATA_DIR / "sample_public" / "fraud_sample.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    generate_fraud_sample(n=n, seed=seed).to_csv(out, index=False)


if __name__ == "__main__":
    save_fraud_sample()
