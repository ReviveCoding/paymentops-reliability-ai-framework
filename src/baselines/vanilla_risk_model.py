from __future__ import annotations

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.model_selection import train_test_split
from src.evaluation.metrics import binary_metrics, review_policy_metrics


def prepare_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    X = df[["case_type", "amount", "text", "payment_status", "exception_type"]].copy()
    y = df["risk_label"].astype(int)
    return X, y


def train_vanilla_risk_model(df: pd.DataFrame) -> dict:
    X, y = prepare_features(df)
    strat = y if y.value_counts().min() >= 2 else None
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.35, random_state=42, stratify=strat)
    pre = ColumnTransformer([
        ("num", StandardScaler(), ["amount"]),
        ("cat", OneHotEncoder(handle_unknown="ignore"), ["case_type", "payment_status", "exception_type"]),
        ("txt", TfidfVectorizer(max_features=100, ngram_range=(1, 2)), "text"),
    ])
    model = Pipeline([
        ("pre", pre),
        ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
    ])
    model.fit(X_train, y_train)
    prob = model.predict_proba(X_test)[:, 1]
    metrics = binary_metrics(y_test, prob, threshold=0.5)
    metrics.update(review_policy_metrics(y_test, prob, review_capacity_rate=0.30))
    return {"model": model, "metrics": metrics, "X_test": X_test, "y_test": y_test, "prob": prob}
