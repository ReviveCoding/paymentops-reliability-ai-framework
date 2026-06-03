from __future__ import annotations

import pandas as pd
import numpy as np


def add_case_health_timestep(df: pd.DataFrame) -> pd.DataFrame:
    """PHT-inspired case maturity signal for financial operations cases.

    Raw elapsed time or event index is not assumed to reflect risk maturity.
    This deterministic, explainable version estimates case maturity from amount,
    text length, status risk, and exception severity.
    """
    out = df.copy()
    status_risk = out.get("payment_status", pd.Series("NA", index=out.index)).isin(["RJCT", "PDNG"]).astype(float)
    exception_text = out.get("exception_type", pd.Series("", index=out.index)).astype(str).str.lower()
    exception_risk = exception_text.str.contains("fraud|unauthorized|duplicate|amount_limit|status_mismatch|rejected|manual|foreclosure|threatened").astype(float)
    text_len = out["text"].fillna("").str.len().clip(0, 350)
    amount_log = np.log1p(out["amount"].astype(float).clip(lower=0))
    raw = 0.35*status_risk + 0.30*exception_risk + 0.20*(text_len/350.0) + 0.15*(amount_log/12.0)
    out["case_health_timestep"] = (100 * raw.clip(0, 1)).round(3)
    return out
