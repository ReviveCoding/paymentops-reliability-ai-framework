from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
from src.utils import ARTIFACTS_DIR


def append_audit_log(record: dict) -> None:
    path = ARTIFACTS_DIR / "sample_audit_logs" / "agent_audit_log.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    rec = {"timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), **record}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
