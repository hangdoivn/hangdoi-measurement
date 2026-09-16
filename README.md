# Hang Đôi Measurement

Shared first-party measurement infrastructure for Hang Đôi projects. **Akimitsu** is the first production implementation.

## v0.1 scope

- `akimitsu.store` / `menu.akimitsu.store`: minimal measurement landing surface.
- `go.akimitsu.store`: tracked outbound redirect gateway.
- First-party anonymous events: page view, menu click, order click, direction click, call click.
- Attribution capture: UTM + Google/Meta click IDs.
- PostgreSQL persistence with memory fallback for local/staging smoke tests.
- `/api/performance?days=30`: first-party event summary.
- Tables reserved for normalized platform metrics and sync runs.

The restaurant's current downstream systems remain unchanged:

- Menu → Gurutto
- Table order → Mmenu
- Directions → Google Maps
- Phone → restaurant phone

## Run locally

```bash
npm install
npm run dev
```

With Postgres:

```bash
docker compose up --build
```

Open `http://localhost:3000`.

## Privacy posture

The MVP stores anonymous visitor/session IDs and campaign attribution. It does **not** store raw IP addresses or customer names/emails/phone numbers.

## Deployment

The app is Docker-ready and includes `railway.json`. See `docs/deployment.md`.
