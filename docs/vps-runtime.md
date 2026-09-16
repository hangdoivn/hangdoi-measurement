# Hostinger VPS runtime target

Production target follows Hang Đôi's existing VPS convention:

- runtime user: `deploy`
- app code: `/home/deploy/apps/hangdoi-measurement`
- persistent first-party events: `/home/deploy/data/hangdoi-measurement/events.jsonl`
- process: PM2 (`hangdoi-measurement`)
- reverse proxy: Nginx
- public hosts: `akimitsu.store`, `menu.akimitsu.store`, `go.akimitsu.store`

The deployment workflow must generate and retain `MEASUREMENT_API_TOKEN` only on the VPS. It must never commit or print the token.
