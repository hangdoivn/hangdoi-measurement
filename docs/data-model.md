# Data model

## Event source of truth

Each first-party event stores:

- workspace/project IDs
- anonymous visitor/session IDs
- event name and destination provider
- current (last-touch) campaign fields for convenient reporting
- immutable `firstTouch` attribution
- current `lastTouch` attribution
- device category, language, referrer/path, timestamp

## Platform metrics

Google Ads, Meta and GBP metrics belong in `platform_daily_metrics`, never in the first-party event log. Reporting joins them by project/date/campaign where appropriate while preserving source provenance.

This prevents double counting between, for example, Google Ads `Local actions - Directions` and owned `direction_click` events.
