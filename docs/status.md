# Status

Current production release: `v0.1.1` Akimitsu Stage-1 first-party measurement.

Production is live on the Hang Đôi VPS.

## Live endpoints

- Tracked menu entry: `https://menu.akimitsu.store/`
- Action gateway: `https://go.akimitsu.store/<destination>`
- Health: `https://menu.akimitsu.store/healthz`
- Protected performance API: `/api/performance?days=30`

## Current behavior

`menu.akimitsu.store` is tracking-only in Stage 1. It records a `menu_click` with available source/campaign, click ids, browser locale, coarse GeoIP, device and anonymous visitor/session context, then returns HTTP 302 to the existing Gurutto menu. It does not render a landing page.

`go.akimitsu.store` tracks explicit outbound actions:

- `/menu` → Gurutto
- `/order` → Mmenu
- `/maps` → Google Maps
- `/call` → phone route

Anonymous visitor/session cookies are scoped to `.akimitsu.store`, allowing continuity between `menu.*` and `go.*`.

## Production state

- Docker service `hangdoi_measurement`: healthy
- Runtime version: `0.1.1`
- GeoIP enrichment: ready
- Persistent event store: Docker volume `/data/events.ndjson`
- Nginx reverse proxy: enabled
- DNS: `menu.akimitsu.store` and `go.akimitsu.store` point to the VPS
- TLS: Let's Encrypt certificate covers both measurement subdomains
- Raw client IP is not stored
- Protected performance reporting includes source, medium, platform, language, country, region, city, device and source-by-action breakdowns

## Production validation

Stage-1 validation confirmed:

- `menu.akimitsu.store` records then redirects to Gurutto with HTTP 302
- `go.akimitsu.store/maps` records then redirects to Google Maps with HTTP 302
- visitor identity and attribution persist across the two subdomains
- browser locale and coarse GeoIP are recorded
- raw IP is absent from stored events
- synthetic QA events are removed after the validation run

## Measurement boundary

The Stage-1 model is:

`platform/source → language + coarse geo + device → first-party action`

Location fields represent coarse IP-based network location, not nationality or precise physical location. Browser language is a locale signal, not nationality.

Direct Google Ads / Google Maps / GBP actions that never touch the Hang Đôi-owned measurement URLs remain platform-reported metrics. They are not deterministically joined to an owned visitor.

Google Ads campaign destinations are not changed by this release.
