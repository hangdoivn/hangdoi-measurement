# Event taxonomy

Core v0.1 events:

- `page_view`: owned landing loaded.
- `menu_click`: user leaves for the current public menu provider (Gurutto).
- `order_click`: user leaves for the restaurant ordering provider (Mmenu).
- `direction_click`: user leaves for Google Maps directions/place view.
- `call_click`: user initiates a phone call.

Every event carries `workspace_id`, `project_id`, anonymous `visitor_id`, `session_id`, timestamp and available attribution parameters. Destination events also include `destination_key` and `destination_provider`.

Platform-reported actions such as Google Ads Local Actions - Directions are **not** merged into first-party `direction_click`; they are different measurement sources and must remain distinguishable in reporting.
