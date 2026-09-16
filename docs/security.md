# Security and privacy posture

- No raw IP address is stored.
- Visitors and sessions use anonymous first-party IDs.
- Campaign attribution is stored as first-touch and last-touch metadata.
- The public landing/gateway is marked `noindex, nofollow`.
- `/api/performance` requires `MEASUREMENT_API_TOKEN` in production.
- Secrets must never be committed; production values live in runtime environment or VPS-local `.env`.
- First-party `direction_click` remains separate from Google Ads/GBP-reported Directions to avoid double counting.
