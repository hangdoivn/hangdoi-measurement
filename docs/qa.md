# v0.1 QA evidence

Local smoke test passed in file-store mode:

1. `/healthz` returned `200` and `db=file`.
2. First touch Meta/Instagram was retained.
3. A later Google/CPC touch replaced only last-touch attribution.
4. `/r/menu` returned `302` to Gurutto and recorded `menu_click`.
5. `/r/order` returned `302` to the stable Mmenu short URL.
6. `/r/maps` returned `302` to the verified Google Place ID.
7. `/api/performance` returned `401` without token in production mode and succeeded with the configured bearer token.
8. No raw IP is written to the event payload.
