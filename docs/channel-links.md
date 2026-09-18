# Channel link conventions

Production measurement URLs for Akimitsu.

## Owned landing

`https://menu.akimitsu.store/`

Use this when Hang Đôi controls the acquisition link and wants first-party session + attribution measurement.

## Tracked outbound gateway

- Menu → `https://go.akimitsu.store/menu`
- Order → `https://go.akimitsu.store/order`
- Directions → `https://go.akimitsu.store/maps`
- Call → `https://go.akimitsu.store/call`

## Recommended attribution parameters

### Google Ads

Preferred landing:

`https://menu.akimitsu.store/?utm_source=google&utm_medium=cpc&utm_campaign=akimitsu_maps&utm_id={campaignid}`

Google Ads auto-tagging is enabled on the Akimitsu account, so `gclid` is also captured when Google appends it.

### Meta Ads

Preferred landing:

`https://menu.akimitsu.store/?utm_source=meta&utm_medium=paid_social&utm_campaign=akimitsu_social`

Ad-level dynamic parameters may be added in Meta when the live ad setup is updated.

### Organic Instagram

`https://menu.akimitsu.store/?utm_source=instagram&utm_medium=organic_social&utm_campaign=profile`

### Organic Facebook

`https://menu.akimitsu.store/?utm_source=facebook&utm_medium=organic_social&utm_campaign=profile`

## Existing restaurant destinations

These are intentionally unchanged in v0.1:

- Google Business Profile / Maps website may continue to use Gurutto.
- In-store QR may continue to open Mmenu directly.

Direct actions that never touch `menu.akimitsu.store` or `go.akimitsu.store` are not first-party-observed events. They stay reported as platform metrics.

## Future QR option

If the restaurant later allows QR changes, route a table QR through:

`https://go.akimitsu.store/order?utm_source=offline&utm_medium=qr&utm_campaign=table_menu&utm_content=table_XX`

This measures the scan/click-out, not the completed Mmenu order unless Mmenu provides an integration or callback.
