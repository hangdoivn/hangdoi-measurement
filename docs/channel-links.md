# Channel link conventions

Production Stage-1 tracking URLs for Akimitsu.

## Canonical stable links

Use stable channel links whenever the channel lets Hang Đôi control the destination. Source/medium defaults are applied server-side; campaign-specific parameters may still be appended.

| Channel | Menu | Maps | Call | Order |
| --- | --- | --- | --- | --- |
| Instagram organic | `https://menu.akimitsu.store/c/instagram` | `https://go.akimitsu.store/c/instagram/maps` | `https://go.akimitsu.store/c/instagram/call` | `https://go.akimitsu.store/c/instagram/order` |
| Facebook organic | `https://menu.akimitsu.store/c/facebook` | `https://go.akimitsu.store/c/facebook/maps` | `https://go.akimitsu.store/c/facebook/call` | `https://go.akimitsu.store/c/facebook/order` |
| Meta paid | `https://menu.akimitsu.store/c/meta?utm_campaign=<campaign>&utm_id=<campaign_id>` | `https://go.akimitsu.store/c/meta/maps?utm_campaign=<campaign>&utm_id=<campaign_id>` | `https://go.akimitsu.store/c/meta/call?utm_campaign=<campaign>&utm_id=<campaign_id>` | `https://go.akimitsu.store/c/meta/order?utm_campaign=<campaign>&utm_id=<campaign_id>` |
| Google paid | `https://menu.akimitsu.store/c/google?utm_campaign=<campaign>&utm_id=<campaign_id>` | `https://go.akimitsu.store/c/google/maps?utm_campaign=<campaign>&utm_id=<campaign_id>` | `https://go.akimitsu.store/c/google/call?utm_campaign=<campaign>&utm_id=<campaign_id>` | `https://go.akimitsu.store/c/google/order?utm_campaign=<campaign>&utm_id=<campaign_id>` |
| Google Business Profile | `https://menu.akimitsu.store/c/gbp` | `https://go.akimitsu.store/c/gbp/maps` | `https://go.akimitsu.store/c/gbp/call` | `https://go.akimitsu.store/c/gbp/order` |
| Offline / QR | `https://menu.akimitsu.store/c/qr` | `https://go.akimitsu.store/c/qr/maps` | `https://go.akimitsu.store/c/qr/call` | `https://go.akimitsu.store/c/qr/order` |

The server defaults are:

- Instagram → `utm_source=instagram&utm_medium=organic_social&utm_campaign=profile`
- Facebook → `utm_source=facebook&utm_medium=organic_social&utm_campaign=page`
- Meta paid → `utm_source=meta&utm_medium=paid_social&utm_campaign=paid`
- Google paid → `utm_source=google&utm_medium=cpc&utm_campaign=paid`
- GBP → `utm_source=google_business_profile&utm_medium=organic_local&utm_campaign=profile`
- QR → `utm_source=offline&utm_medium=qr&utm_campaign=restaurant`

Explicit query parameters override these defaults.

## Tracking-only behavior

`menu.akimitsu.store` does not render a landing page in Stage 1. It records the menu action and available attribution/audience signals, then returns HTTP 302 to the existing Gurutto menu.

`go.akimitsu.store` tracks explicit outbound action routes and returns HTTP 302 to the existing destination.

## Existing downstream systems

- Menu → Gurutto
- Order → Mmenu
- Directions → Google Maps
- Call → phone route

The measurement layer does not replace the existing Akimitsu systems.

## Platform-native behavior

Do not force native platform actions through the tracking gateway merely to increase measured counts.

Examples that remain platform-reported:

- Google Ads Local Actions — Directions / Calls / Menu views / Website visits
- Google Maps / GBP native Directions / Calls / Website / Menu actions
- Meta messaging conversations and native engagement

These platform metrics remain separate from first-party events to avoid double counting.

## Interpretation

A tracked route identifies the configured action represented by the clicked link. It does not prove a completed order, answered call, store visit, nationality, or customer identity.
