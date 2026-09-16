# Deployment

## Runtime

The service supports any Docker host (Railway, Hostinger VPS, Render, etc.). Production should set:

- `NODE_ENV=production`
- `PORT` (usually injected by platform)
- `DATABASE_URL`
- `AUTO_MIGRATE=true` for the first deployment, then optionally false after schema management is formalized
- `COOKIE_SECURE=true`

## Domains

Preferred production hostnames:

- `akimitsu.store` → landing
- `menu.akimitsu.store` → landing
- `go.akimitsu.store` → redirect gateway

All three may point to the same service. Routing is hostname/path aware.

## Hostinger DNS

After the runtime exposes a custom-domain target, configure DNS in Hostinger for the apex/subdomains. Keep TTL low during cutover, then raise after verification. Exact record values depend on the runtime target returned at deploy time.

## Smoke test

1. `GET /healthz` returns `{ok:true}`.
2. Landing sets anonymous cookies and `X-Robots-Tag: noindex, nofollow`.
3. `/r/menu` records `menu_click` then 302s to Gurutto.
4. `/r/order` records `order_click` then 302s to the Mmenu short URL.
5. `/r/maps` records `direction_click` then 302s to Google Maps.
6. `/api/performance?days=1` increments after the above tests.
