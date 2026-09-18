# Status

Current release: `v0.1.0` Akimitsu first-party measurement MVP.

Production is live on the Hang Đôi VPS.

## Live endpoints

- Landing: `https://menu.akimitsu.store/`
- Tracked gateway: `https://go.akimitsu.store/<destination>`
- Health: `https://menu.akimitsu.store/healthz`
- Protected performance API: `/api/performance?days=30`

## Production state

- Docker service `hangdoi_measurement`: healthy
- Persistent event store: Docker volume `/data/events.ndjson`
- Nginx reverse proxy: enabled
- DNS: `menu.akimitsu.store` and `go.akimitsu.store` point to the VPS
- TLS: Let's Encrypt certificate covers both measurement subdomains
- Smoke test verified persisted `page_view` and `direction_click` events with UTM attribution

## Current boundary

v0.1 measures first-party traffic that passes through Hang Đôi-owned measurement URLs. Direct Google Maps / GBP actions that do not touch the owned layer remain platform-reported metrics and are not deterministically joined to an owned visitor.

Next release: v0.2 platform sync for Google Ads, Meta Ads and GBP where API access permits.
