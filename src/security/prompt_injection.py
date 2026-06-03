from __future__ import annotations

SUSPICIOUS_PATTERNS = [
    "ignore previous instructions",
    "ignore all instructions",
    "reveal system prompt",
    "bypass policy",
    "disable guardrails",
    "exfiltrate",
    "override compliance",
    "act as developer",
]


def detect_prompt_injection(text: str) -> dict:
    lower = (text or "").lower()
    hits = [p for p in SUSPICIOUS_PATTERNS if p in lower]
    return {
        "is_suspicious": bool(hits),
        "matched_patterns": hits,
        "recommended_action": "human_review_required" if hits else "continue",
    }
