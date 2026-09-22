from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_LOCK = threading.Lock()


def _path() -> Path:
    return Path(os.getenv("GOOGLE_ADS_AUDIT_LOG_PATH", "/data/audit.jsonl"))


def append_audit_event(event: dict[str, Any]) -> dict[str, Any]:
    row = {
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "actor": os.getenv("GOOGLE_ADS_AUDIT_ACTOR", "chatgpt"),
        **event,
    }
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
    with _LOCK:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    return row


def read_audit_events(
    *,
    limit: int = 50,
    customer_id: str | None = None,
) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit), 500))
    path = _path()
    if not path.exists():
        return []

    with _LOCK:
        lines = path.read_text(encoding="utf-8").splitlines()

    rows: list[dict[str, Any]] = []
    for line in reversed(lines):
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if customer_id and str(row.get("customer_id")) != str(customer_id):
            continue
        rows.append(row)
        if len(rows) >= limit:
            break
    return rows
