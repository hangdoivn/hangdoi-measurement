# Deployment

Akimitsu Stage-1 measurement runs on the shared Hang Đôi Hostinger VPS.

## Runtime

- Docker project: `hangdoi-measurement`
- Container: `hangdoi_measurement`
- Application port: `3000`
- Published host port: `3105`
- Persistent event volume mounted at `/data`
- Production storage: NDJSON event file
- `NODE_ENV=production`
- `MENU_TRACKING_ONLY=true`
- secure shared cookies scoped to `.akimitsu.store`
- protected performance API token injected at deploy time
- local GeoIP database loaded at container startup

## Public ingress

Nginx terminates TLS and proxies both measurement hosts to `127.0.0.1:3105`.

- `menu.akimitsu.store` — tracked menu entry; records then 302 redirects to Gurutto
- `go.akimitsu.store` — tracked action gateway

The infrastructure definitions live in `hangdoiproduction/06_infra/nginx/` and use the existing controlled VPS deployment SSH path.

## DNS

Hostinger DNS for the measurement layer is managed from the `hangdoi-vps` repository.

Only the measurement subdomains are managed by this setup:

- `menu.akimitsu.store A 72.60.108.22`
- `go.akimitsu.store A 72.60.108.22`

The apex and `www` records are intentionally outside this measurement cutover.

## TLS

Let's Encrypt certificate name: `menu.akimitsu.store`

SANs:

- `menu.akimitsu.store`
- `go.akimitsu.store`

Nginx redirects HTTP to HTTPS.

## Privacy posture

The server transiently uses the client IP for local coarse GeoIP lookup, then stores only available country/region/city/timezone fields. Raw IP is not written to the measurement event store.

## Verification

Production validation confirms:

1. `/healthz` returns `ok=true`, version `0.1.1`, and `geo=ready`.
2. `menu.akimitsu.store` returns 302 to the existing Gurutto menu.
3. `go.akimitsu.store/maps` returns 302 to Google Maps.
4. anonymous visitor identity persists across `menu.*` and `go.*`.
5. source attribution, browser locale, coarse GeoIP and device context are persisted.
6. raw IP is not persisted.
7. synthetic validation events are cleaned after the smoke test.
8. the Docker health state is `healthy`.
