from pathlib import Path

from performance_store import read_campaign_daily, upsert_campaign_daily


def test_campaign_daily_upsert(monkeypatch, tmp_path: Path):
    db = tmp_path / "google_ads.sqlite3"
    monkeypatch.setenv("GOOGLE_ADS_PERFORMANCE_DB", str(db))

    rows = [
        {
            "date": "2026-09-22",
            "campaign_id": "24060570697",
            "campaign_name": "Campaign #1",
            "campaign_status": "ENABLED",
            "advertising_channel_type": "PERFORMANCE_MAX",
            "cost_micros": 100_000_000_000,
            "impressions": 1000,
            "clicks": 50,
            "conversions": 5.0,
            "conversions_value": 0.0,
        }
    ]

    assert upsert_campaign_daily(
        customer_id="8681228450",
        currency_code="VND",
        rows=rows,
    ) == 1

    stored = read_campaign_daily(
        customer_id="8681228450",
        start_date="2026-09-22",
        end_date="2026-09-22",
    )
    assert len(stored) == 1
    assert stored[0]["campaign_id"] == "24060570697"
    assert stored[0]["spend"] == 100000.0

    rows[0]["clicks"] = 60
    upsert_campaign_daily(
        customer_id="8681228450",
        currency_code="VND",
        rows=rows,
    )
    stored = read_campaign_daily(
        customer_id="8681228450",
        start_date="2026-09-22",
        end_date="2026-09-22",
    )
    assert stored[0]["clicks"] == 60
