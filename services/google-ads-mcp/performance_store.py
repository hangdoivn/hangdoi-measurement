from __future__ import annotations

import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_LOCK = threading.Lock()


def _db_path() -> Path:
    return Path(os.getenv("GOOGLE_ADS_PERFORMANCE_DB", "/data/google_ads.sqlite3"))


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_db() -> None:
    with _LOCK, _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS campaign_daily (
                date TEXT NOT NULL,
                customer_id TEXT NOT NULL,
                campaign_id TEXT NOT NULL,
                campaign_name TEXT,
                campaign_status TEXT,
                advertising_channel_type TEXT,
                currency_code TEXT,
                cost_micros INTEGER NOT NULL DEFAULT 0,
                impressions INTEGER NOT NULL DEFAULT 0,
                clicks INTEGER NOT NULL DEFAULT 0,
                conversions REAL NOT NULL DEFAULT 0,
                conversions_value REAL NOT NULL DEFAULT 0,
                collected_at TEXT NOT NULL,
                PRIMARY KEY (date, customer_id, campaign_id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_campaign_daily_customer_date "
            "ON campaign_daily(customer_id, date)"
        )


def upsert_campaign_daily(
    *,
    customer_id: str,
    currency_code: str,
    rows: list[dict[str, Any]],
) -> int:
    init_db()
    collected_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    payload = []
    for row in rows:
        payload.append(
            (
                str(row["date"]),
                str(customer_id),
                str(row["campaign_id"]),
                row.get("campaign_name"),
                row.get("campaign_status"),
                row.get("advertising_channel_type"),
                currency_code,
                int(row.get("cost_micros", 0) or 0),
                int(row.get("impressions", 0) or 0),
                int(row.get("clicks", 0) or 0),
                float(row.get("conversions", 0) or 0),
                float(row.get("conversions_value", 0) or 0),
                collected_at,
            )
        )
    if not payload:
        return 0

    with _LOCK, _connect() as conn:
        conn.executemany(
            """
            INSERT INTO campaign_daily (
                date, customer_id, campaign_id, campaign_name, campaign_status,
                advertising_channel_type, currency_code, cost_micros, impressions,
                clicks, conversions, conversions_value, collected_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(date, customer_id, campaign_id) DO UPDATE SET
                campaign_name=excluded.campaign_name,
                campaign_status=excluded.campaign_status,
                advertising_channel_type=excluded.advertising_channel_type,
                currency_code=excluded.currency_code,
                cost_micros=excluded.cost_micros,
                impressions=excluded.impressions,
                clicks=excluded.clicks,
                conversions=excluded.conversions,
                conversions_value=excluded.conversions_value,
                collected_at=excluded.collected_at
            """,
            payload,
        )
    return len(payload)


def read_campaign_daily(
    *,
    customer_id: str,
    start_date: str,
    end_date: str,
    campaign_id: str | None = None,
) -> list[dict[str, Any]]:
    init_db()
    sql = (
        "SELECT date, customer_id, campaign_id, campaign_name, campaign_status, "
        "advertising_channel_type, currency_code, cost_micros, impressions, clicks, "
        "conversions, conversions_value, collected_at "
        "FROM campaign_daily WHERE customer_id=? AND date BETWEEN ? AND ?"
    )
    params: list[Any] = [customer_id, start_date, end_date]
    if campaign_id:
        sql += " AND campaign_id=?"
        params.append(str(campaign_id))
    sql += " ORDER BY date, campaign_id"

    with _LOCK, _connect() as conn:
        rows = [dict(row) for row in conn.execute(sql, params).fetchall()]

    for row in rows:
        row["spend"] = row["cost_micros"] / 1_000_000
    return rows
