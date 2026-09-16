# Decision log

## 2026-09-16 — keep restaurant systems downstream
Gurutto remains the public menu link and Mmenu remains the table-order system. Hang Đôi adds an owned measurement layer in front of controlled campaign traffic rather than replacing restaurant operations.

## 2026-09-16 — Maps remains Google-hosted measurement
Google Ads/GBP Directions and Calls remain platform-reported local actions. Owned `direction_click`/`call_click` are separate first-party observations and are not summed automatically.

## 2026-09-16 — VPS-first persistence
v0.1 supports an append-only VPS file store so production does not depend on a new database credential. PostgreSQL remains supported as a later scale path.
