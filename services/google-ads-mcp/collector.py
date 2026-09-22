from __future__ import annotations

import os
import time
from datetime import date, timedelta

from google_ads import GoogleAdsRestClient
from performance_store import upsert_campaign_daily


def collect_once() -> dict:
    customer_id = "".join(
        ch for ch in os.getenv("GOOGLE_ADS_COLLECTOR_CUSTOMER_ID", "8681228450")
        if ch.isdigit()
    )
    lookback_days = max(1, min(int(os.getenv("GOOGLE_ADS_COLLECTOR_LOOKBACK_DAYS", "7")), 90))
    end = date.today()
    start = end - timedelta(days=lookback_days - 1)

    client = GoogleAdsRestClient.from_env()
    context = client.customer_context(customer_id)
    currency = context.get("currencyCode") or "UNKNOWN"
    rows = client.campaign_performance(customer_id, start.isoformat(), end.isoformat())
    count = upsert_campaign_daily(
        customer_id=customer_id,
        currency_code=currency,
        rows=rows,
    )
    return {
        "customer_id": customer_id,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "rows_upserted": count,
    }


def main() -> None:
    interval = max(900, int(os.getenv("GOOGLE_ADS_COLLECTOR_INTERVAL_SECONDS", "3600")))
    while True:
        try:
            result = collect_once()
            print(f"collector_ok {result}", flush=True)
        except Exception as exc:
            print(f"collector_error {type(exc).__name__}: {exc}", flush=True)
        time.sleep(interval)


if __name__ == "__main__":
    main()
