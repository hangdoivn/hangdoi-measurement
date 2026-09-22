import json
from pathlib import Path

from audit_log import append_audit_event, read_audit_events


def test_append_and_read_audit(monkeypatch, tmp_path: Path):
    path = tmp_path / "audit.jsonl"
    monkeypatch.setenv("GOOGLE_ADS_AUDIT_LOG_PATH", str(path))
    monkeypatch.setenv("GOOGLE_ADS_AUDIT_ACTOR", "test")

    first = append_audit_event(
        {
            "customer_id": "8681228450",
            "campaign_id": "24060570697",
            "action": "set_daily_budget",
            "before": {"daily_budget": 170000},
            "after": {"daily_budget": 100000},
            "result": "success",
        }
    )
    second = append_audit_event(
        {
            "customer_id": "8681228450",
            "campaign_id": "24060570697",
            "action": "enable_campaign",
            "before": {"status": "PAUSED"},
            "after": {"status": "ENABLED"},
            "result": "success",
        }
    )

    assert path.exists()
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert len(rows) == 2
    assert first["actor"] == "test"
    assert second["event_id"] != first["event_id"]

    recent = read_audit_events(limit=1, customer_id="8681228450")
    assert len(recent) == 1
    assert recent[0]["action"] == "enable_campaign"
