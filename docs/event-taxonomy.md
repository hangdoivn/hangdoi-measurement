# Event taxonomy

Core v0.1.1 events:

- `page_view`: owned landing loaded. Reserved for future/owned landing surfaces.
- `menu_click`: visitor enters the tracked menu route and is redirected to Gurutto.
- `order_click`: visitor is redirected to Mmenu.
- `direction_click`: visitor is redirected to Google Maps.
- `call_click`: visitor initiates the phone route.

## Stage-1 tracking model

`menu.akimitsu.store` is tracking-only in the current phase. The root URL records `menu_click` and returns a 302 redirect to the existing Gurutto menu. It does not insert a landing page into the customer journey.

`go.akimitsu.store/<action>` is the action gateway:

- `/menu`
- `/order`
- `/maps`
- `/call`

Every first-party event carries:

- anonymous visitor + session ids
- source / medium / campaign attribution
- Google / Meta / TikTok click ids when present
- browser locale
- device category
- coarse GeoIP: country, region, city, timezone when available
- entry host and tracking entrypoint

Raw client IP addresses are used only transiently for local GeoIP lookup and are not written to the event store.

The protected performance API returns breakdowns for source, medium, platform, language, country, region, city, device and a source-by-action matrix.

Platform-reported actions such as Google Ads Local Actions - Directions are **not** merged into first-party `direction_click`; they remain separate measurement sources.
