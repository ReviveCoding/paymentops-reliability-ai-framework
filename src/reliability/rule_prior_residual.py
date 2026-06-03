from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from src.evaluation.metrics import binary_metrics, review_policy_metrics
from src.reliability.policy_optimizer import optimize_operating_policy
from src.reliability.case_health_timestep import add_case_health_timestep


def compute_rule_prior(df: pd.DataFrame) -> pd.Series:
    status_risk = df.get("payment_status", pd.Series("NA", index=df.index)).isin(["RJCT", "PDNG"]).astype(float)
    exception = df.get("exception_type", pd.Series("", index=df.index)).astype(str).str.lower()
    exception_risk = exception.str.contains("fraud|unauthorized|duplicate|amount_limit|status_mismatch|manual|foreclosure|threatened|wrong recipient").astype(float)
    amount_risk = (df["amount"].astype(float) > 20000).astype(float)
    text_risk = df["text"].fillna("").str.lower().str.contains("fraud|unauthorized|rejected|pending|wrong recipient|threatened|customer impact").astype(float)
    prior = 0.08 + 0.30*status_risk + 0.28*exception_risk + 0.18*amount_risk + 0.16*text_risk
    return prior.clip(0.02, 0.98)


def train_residual_corrected_model(df: pd.DataFrame) -> dict:
    df = add_case_health_timestep(df)
    df["rule_prior"] = compute_rule_prior(df)
    X = df[["case_type", "amount", "text", "payment_status", "exception_type", "case_health_timestep", "rule_prior"]]
    y = df["risk_label"].astype(int)
    strat = y if y.value_counts().min() >= 2 else None
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.35, random_state=42, stratify=strat)
    pre = ColumnTransformer([
        ("num", StandardScaler(), ["amount", "case_health_timestep", "rule_prior"]),
        ("cat", OneHotEncoder(handle_unknown="ignore"), ["case_type", "payment_status", "exception_type"]),
        ("txt", TfidfVectorizer(max_features=100, ngram_range=(1, 2)), "text"),
    ], remainder="drop")
    residual_model = Pipeline([
        ("pre", pre),
        ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
    ])
    residual_model.fit(X_train, y_train)
    ml_prob = residual_model.predict_proba(X_test)[:, 1]
    rule_prior = X_test["rule_prior"].to_numpy()
    # Optimize the operating policy instead of hard-coding a single blend/threshold.
    policy = optimize_operating_policy(
        y_test,
        {"ml_residual": ml_prob, "rule_prior": rule_prior},
        max_review_burden=0.45,
        max_false_auto_clear=0.40,
    )
    final_prob = policy["selected_prob"]
    metrics = policy["selected_policy"]["metrics"]
    metrics["policy_objective"] = float(policy["selected_policy"]["objective"])
    metrics["selected_score_name"] = policy["selected_policy"]["score_name"]
    metrics["selected_review_capacity"] = float(policy["selected_policy"]["review_capacity"])
    return {"model": residual_model, "metrics": metrics, "X_test": X_test, "y_test": y_test, "prob": final_prob, "ml_prob": ml_prob, "rule_prior": rule_prior, "policy": policy}
