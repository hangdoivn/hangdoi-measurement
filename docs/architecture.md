# Architecture v0.1

```text
Meta / Google / Social
        |
        v
akimitsu.store / menu.akimitsu.store
        |
        +--> page_view + attribution --> Event Store
        |
        +--> go.akimitsu.store/{menu|order|maps|call}
                       |
                       +--> event --> Event Store
                       +--> 302 --> Gurutto / Mmenu / Maps / tel

Platform APIs (next phase)
Meta Ads / Google Ads / GBP
        |
        v
platform_daily_metrics
        |
        v
Performance API --> Marcom App / ChatGPT / Client Report
```

## Boundary

Measurement infrastructure owns event capture and normalized metrics. The Marcom App is a consumer and must not write directly to the measurement database.
