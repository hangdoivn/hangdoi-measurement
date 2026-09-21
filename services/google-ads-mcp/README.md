# Hang Đôi Google Ads MCP v0.1

Private control plane for Google Ads. This service is deliberately separate from the public measurement app and exposes only a small allowlisted MCP surface.

## Why this exists

Ad operations must not depend on a third-party connector quota. The MCP calls the Google Ads API directly using a Google Cloud service account.

As of **2026-09-09**, Google sunset developer tokens for normal Google Ads API access. API access level is associated with the Google Cloud project that owns the service-account/OAuth credentials, so this service intentionally sends **no developer-token header**.

## v0.1 tools

Read:
- get_account_context
- list_campaigns
- get_campaign

Write:
- enable_campaign
- pause_campaign
- set_daily_budget

There is no remove/delete tool, campaign creation, conversion-goal mutation, bidding mutation, or targeting mutation in v0.1.

## Safety model

1. GOOGLE_ADS_ALLOWED_CUSTOMERS is a hard account allowlist.
2. Every write reads the campaign first.
3. Large budget increases require acknowledge_large_change=true.
4. A hard maximum daily budget is enforced server-side.
5. Explicitly shared campaign budgets are blocked unless the caller deliberately opts in.
6. The remote MCP endpoint requires a separate static bearer token.
7. Service-account JSON never enters Git.

## Akimitsu

First allowlisted production account:
- Google Ads customer: 8681228450
- Account currency is read from Google Ads before showing/changing budget.

The intended first production mutation is to set the selected Akimitsu campaign to **100,000 VND/day** and enable it, after the API connection passes a read plus validate_only check.

## Google Cloud prerequisites

1. Use the Google Cloud project that will own Hang Đôi Google Ads API access.
2. Enable Google Ads API.
3. On Google Ads API Overview for that Cloud project, obtain Explorer or higher access for production accounts.
4. Create or reuse a service account in that same project.
5. In Google Ads account 8681228450, add the service-account email under Admin → Access and security with sufficient access to modify campaigns.
6. Put the service-account JSON only on the VPS, for example /srv/secrets/google-ads/service-account.json.

OAuth scope: https://www.googleapis.com/auth/adwords

## Local test

    python -m venv .venv
    . .venv/bin/activate
    pip install -e '.[dev]'
    pytest

## Runtime

Health endpoint: GET /healthz

MCP endpoint: POST /mcp with Authorization: Bearer <MCP_BEARER_TOKEN>.

Recommended public endpoint:
https://mcp-googleads.hangdoistudio.vn/mcp

Bind the service only to localhost or a private Docker network. Nginx terminates TLS, forwards Authorization unchanged, and disables proxy buffering for streaming responses.
