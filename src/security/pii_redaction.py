from __future__ import annotations

import re

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}(?!\d)")
SSN_RE = re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)")
ACCOUNT_RE = re.compile(r"(?i)\b(?:acct|account|routing|iban)\s*[:#-]?\s*[A-Z0-9-]{6,24}\b")
CARD_RE = re.compile(r"(?<!\d)(?:\d[ -]*?){13,19}(?!\d)")


def redact_pii(text: str) -> tuple[str, dict]:
    redacted = text or ""
    counts = {"email": 0, "phone": 0, "ssn": 0, "account": 0, "card": 0}
    for key, regex, token in [
        ("email", EMAIL_RE, "[REDACTED_EMAIL]"),
        ("phone", PHONE_RE, "[REDACTED_PHONE]"),
        ("ssn", SSN_RE, "[REDACTED_SSN]"),
        ("account", ACCOUNT_RE, "[REDACTED_ACCOUNT]"),
        ("card", CARD_RE, "[REDACTED_CARD]"),
    ]:
        redacted, n = regex.subn(token, redacted)
        counts[key] += int(n)
    return redacted, counts


def contains_unredacted_pii(text: str) -> bool:
    return any(regex.search(text or "") for regex in [EMAIL_RE, PHONE_RE, SSN_RE, ACCOUNT_RE, CARD_RE])
