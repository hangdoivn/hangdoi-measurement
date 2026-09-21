# Google Ads MCP control plane

Status: implementation ready on feature branch; production credentials and ingress still required.

## Architecture

ChatGPT / Marcom App
→ mcp-googleads.hangdoistudio.vn
→ Hang Đôi Google Ads MCP
→ Google Ads REST API v25
→ allowlisted Google Ads customers

The MCP is a separate control plane from the Akimitsu first-party measurement service. Measurement reads user/channel behavior. This service changes Google Ads state.

## Authentication

Two independent trust boundaries are used:

1. MCP client → MCP server: static bearer token in v0.1.
2. MCP server → Google Ads: Google Cloud service account with the adwords OAuth scope.

The legacy Google Ads developer-token header is intentionally omitted. From 2026-09-09, Google Ads API access level is attached to the Google Cloud project that owns the OAuth/service-account credentials.

## Production account allowlist

Initial allowlist:
- Akimitsu: 8681228450

No other customer can be read or mutated unless added to GOOGLE_ADS_ALLOWED_CUSTOMERS on the server.

## Write policy v0.1

Allowed:
- enable campaign
- pause campaign
- set daily campaign budget

Blocked by omission:
- campaign deletion/removal
- campaign creation
- conversion-goal mutation
- bid-strategy mutation
- targeting mutation
- asset removal

Budget safeguards:
- server-side hard maximum
- large-increase acknowledgement
- shared-budget detection
- pre-read before mutation
- validate_only support

## First production run

For Akimitsu:
1. read account context
2. list campaigns and identify the PMax/Maps campaign
3. read campaign snapshot
4. validate budget mutation to 100000 VND/day
5. validate enable mutation
6. execute budget mutation
7. execute enable mutation
8. read campaign again and confirm budget/status

Do not execute steps 6-7 until Google Cloud project production API access and service-account permissions are confirmed.
