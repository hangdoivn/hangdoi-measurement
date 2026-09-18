# Deployment

Akimitsu measurement runs on the shared Hang Đôi VPS.

## Runtime

- Hostinger VPS
- Docker project: `hangdoi-measurement`
- Container: `hangdoi_measurement`
- Application port: `3000`
- Published host port: `3105`
- Persistent event volume mounted at `/data`
- Production storage for v0.1: NDJSON event file
- `NODE_ENV=production`
- secure cookies enabled
- protected performance API token injected at deploy time

## Public ingress

Nginx terminates TLS and proxies both measurement hosts to `127.0.0.1:3105`.

- `menu.akimitsu.store` — real landing surface
- `go.akimitsu.store` — tracked redirect gateway

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

## Verification

Production launch validation must confirm:

1. `/healthz` returns `ok=true` on both domains.
2. landing HTML contains AKIMITSU.
3. `go.akimitsu.store/maps` returns a 302 redirect.
4. smoke-test UTM values are persisted in the event store.
5. the Docker health state is `healthy`.
