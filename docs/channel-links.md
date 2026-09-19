# Channel link conventions

Production Stage-1 tracking URLs for Akimitsu.

## Tracked menu entry

`https://menu.akimitsu.store/`

This is not a landing page in the current phase. It records the incoming source/campaign context and a `menu_click`, then redirects to the existing Gurutto menu.

Example:

`https://menu.akimitsu.store/?utm_source=instagram&utm_medium=organic_social&utm_campaign=profile`

## Action gateway

- Menu → `https://go.akimitsu.store/menu`
- Order → `https://go.akimitsu.store/order`
- Directions → `https://go.akimitsu.store/maps`
- Call → `https://go.akimitsu.store/call`

Add source/campaign parameters when the distribution channel allows them.

## Recommended attribution parameters

### Google-controlled link

`https://menu.akimitsu.store/?utm_source=google&utm_medium=cpc&utm_campaign=<campaign>&utm_id=<campaign_id>`

Google Ads auto-tagging can additionally supply `gclid` / `gbraid` / `wbraid` when the platform sends traffic through an owned tracking URL. Do not change a live Google Ads final URL solely from this convention without reviewing the campaign destination and policy behavior.

### Meta paid

`https://menu.akimitsu.store/?utm_source=meta&utm_medium=paid_social&utm_campaign=<campaign>`

### Organic Instagram

`https://menu.akimitsu.store/?utm_source=instagram&utm_medium=organic_social&utm_campaign=profile`

### Organic Facebook

`https://menu.akimitsu.store/?utm_source=facebook&utm_medium=organic_social&utm_campaign=profile`

### Offline / QR

`https://go.akimitsu.store/order?utm_source=offline&utm_medium=qr&utm_campaign=table_menu&utm_content=table_XX`

## Existing Akimitsu destinations

The Stage-1 measurement layer does not replace the existing downstream systems:

- Menu → Gurutto
- Order → Mmenu
- Directions → Google Maps
- Call → phone route

Direct platform-native actions that do not touch `menu.akimitsu.store` or `go.akimitsu.store` remain platform-reported metrics.

## Interpretation

A tracked route identifies the action represented by the link that was clicked. If a channel exposes only one fixed CTA and that CTA always points to the menu route, the resulting `menu_click` reflects the configured path as well as user intent. To compare user preferences between menu, directions, call and order, expose distinct action links or combine first-party data with the platform's native action metrics.
