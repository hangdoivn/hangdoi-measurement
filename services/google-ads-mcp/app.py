from __future__ import annotations

import hmac
import os
from decimal import Decimal
from functools import lru_cache
from typing import Any

from fastmcp import FastMCP
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from audit_log import append_audit_event, read_audit_events
from google_ads import GoogleAdsApiError, GoogleAdsRestClient
from policy import (
    MutationPolicy,
    PolicyError,
    amount_to_micros,
    parse_allowlist,
    require_allowed_customer,
)


SERVICE_NAME = "Hang Doi Google Ads MCP"
MCP_BEARER_TOKEN = os.getenv("MCP_BEARER_TOKEN", "").strip()
ALLOWED_CUSTOMERS = parse_allowlist(os.getenv("GOOGLE_ADS_ALLOWED_CUSTOMERS"))
POLICY = MutationPolicy.from_env()


class StaticBearerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/mcp"):
            if not MCP_BEARER_TOKEN:
                return JSONResponse(
                    {"error": "MCP_BEARER_TOKEN is not configured"}, status_code=503
                )
            auth = request.headers.get("authorization", "")
            expected = f"Bearer {MCP_BEARER_TOKEN}"
            if not hmac.compare_digest(auth, expected):
                return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)


@lru_cache(maxsize=1)
def ads_client() -> GoogleAdsRestClient:
    return GoogleAdsRestClient.from_env()


def _customer(customer_id: str) -> str:
    return require_allowed_customer(customer_id, ALLOWED_CUSTOMERS)


def _api_error(exc: Exception) -> RuntimeError:
    if isinstance(exc, (PolicyError, GoogleAdsApiError)):
        return RuntimeError(str(exc))
    return RuntimeError(f"Unexpected Google Ads MCP error: {exc}")


mcp = FastMCP(SERVICE_NAME)


@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(request: Request) -> JSONResponse:
    return JSONResponse(
        {
            "ok": True,
            "service": "hangdoi-google-ads-mcp",
            "version": "0.1.0",
            "api_version": os.getenv("GOOGLE_ADS_API_VERSION", "v25"),
            "allowed_customers": sorted(ALLOWED_CUSTOMERS),
            "credentials_configured": bool(
                os.getenv("GOOGLE_ADS_SERVICE_ACCOUNT_FILE")
                or os.getenv("GOOGLE_ADS_SERVICE_ACCOUNT_JSON_B64")
            ),
            "mcp_auth_configured": bool(MCP_BEARER_TOKEN),
            "audit_log_path": os.getenv("GOOGLE_ADS_AUDIT_LOG_PATH", "/data/audit.jsonl"),
        }
    )


@mcp.tool
def get_account_context(customer_id: str) -> dict[str, Any]:
    """Read Google Ads account name, currency and timezone for an allowlisted account."""
    try:
        customer_id = _customer(customer_id)
        return ads_client().customer_context(customer_id)
    except Exception as exc:
        raise _api_error(exc) from exc


@mcp.tool
def list_campaigns(customer_id: str) -> dict[str, Any]:
    """List non-removed campaigns and their daily budgets for an allowlisted account."""
    try:
        customer_id = _customer(customer_id)
        campaigns = ads_client().list_campaigns(customer_id)
        context = ads_client().customer_context(customer_id)
        currency = context.get("currencyCode") or "UNKNOWN"
        for campaign in campaigns:
            micros = campaign.get("daily_budget_micros", 0)
            campaign["daily_budget"] = micros / 1_000_000
            campaign["currency_code"] = currency
        return {"customer_id": customer_id, "campaigns": campaigns}
    except Exception as exc:
        raise _api_error(exc) from exc


@mcp.tool
def get_campaign(customer_id: str, campaign_id: str) -> dict[str, Any]:
    """Read a campaign's current status and budget before any mutation."""
    try:
        customer_id = _customer(customer_id)
        snap = ads_client().get_campaign_snapshot(customer_id, campaign_id)
        return {
            "customer_id": snap.customer_id,
            "campaign_id": snap.campaign_id,
            "name": snap.name,
            "status": snap.status,
            "advertising_channel_type": snap.advertising_channel_type,
            "daily_budget": float(snap.daily_budget),
            "currency_code": snap.currency_code,
            "budget_shared": snap.budget_shared,
            "budget_resource_name": snap.budget_resource_name,
        }
    except Exception as exc:
        raise _api_error(exc) from exc


@mcp.tool
def get_recent_audit_events(
    limit: int = 50,
    customer_id: str | None = None,
) -> dict[str, Any]:
    """Read recent append-only Google Ads mutation audit events."""
    try:
        normalized = _customer(customer_id) if customer_id else None
        events = read_audit_events(limit=limit, customer_id=normalized)
        return {"count": len(events), "events": events}
    except Exception as exc:
        raise _api_error(exc) from exc


@mcp.tool
def enable_campaign(
    customer_id: str,
    campaign_id: str,
    validate_only: bool = False,
) -> dict[str, Any]:
    """Enable a paused campaign. Never creates or removes campaigns."""
    try:
        customer_id = _customer(customer_id)
        before = ads_client().get_campaign_snapshot(customer_id, campaign_id)
        if before.status == "ENABLED":
            return {
                "changed": False,
                "customer_id": customer_id,
                "campaign_id": before.campaign_id,
                "campaign_name": before.name,
                "status": before.status,
                "message": "Campaign is already enabled",
            }
        ads_client().set_campaign_status(
            customer_id, campaign_id, "ENABLED", validate_only=validate_only
        )
        after = before if validate_only else ads_client().get_campaign_snapshot(customer_id, campaign_id)
        if not validate_only:
            append_audit_event(
                {
                    "customer_id": customer_id,
                    "campaign_id": before.campaign_id,
                    "campaign_name": before.name,
                    "action": "enable_campaign",
                    "before": {"status": before.status},
                    "after": {"status": after.status},
                    "currency": before.currency_code,
                    "validate_only_passed": True,
                    "result": "success",
                    "source": "mcp",
                }
            )
        return {
            "changed": not validate_only,
            "validate_only": validate_only,
            "customer_id": customer_id,
            "campaign_id": before.campaign_id,
            "campaign_name": before.name,
            "before_status": before.status,
            "after_status": "ENABLED" if validate_only else after.status,
        }
    except Exception as exc:
        raise _api_error(exc) from exc


@mcp.tool
def pause_campaign(
    customer_id: str,
    campaign_id: str,
    validate_only: bool = False,
) -> dict[str, Any]:
    """Pause an enabled campaign. Never removes a campaign."""
    try:
        customer_id = _customer(customer_id)
        before = ads_client().get_campaign_snapshot(customer_id, campaign_id)
        if before.status == "PAUSED":
            return {
                "changed": False,
                "customer_id": customer_id,
                "campaign_id": before.campaign_id,
                "campaign_name": before.name,
                "status": before.status,
                "message": "Campaign is already paused",
            }
        ads_client().set_campaign_status(
            customer_id, campaign_id, "PAUSED", validate_only=validate_only
        )
        after = before if validate_only else ads_client().get_campaign_snapshot(customer_id, campaign_id)
        if not validate_only:
            append_audit_event(
                {
                    "customer_id": customer_id,
                    "campaign_id": before.campaign_id,
                    "campaign_name": before.name,
                    "action": "pause_campaign",
                    "before": {"status": before.status},
                    "after": {"status": after.status},
                    "currency": before.currency_code,
                    "validate_only_passed": True,
                    "result": "success",
                    "source": "mcp",
                }
            )
        return {
            "changed": not validate_only,
            "validate_only": validate_only,
            "customer_id": customer_id,
            "campaign_id": before.campaign_id,
            "campaign_name": before.name,
            "before_status": before.status,
            "after_status": "PAUSED" if validate_only else after.status,
        }
    except Exception as exc:
        raise _api_error(exc) from exc


@mcp.tool
def set_daily_budget(
    customer_id: str,
    campaign_id: str,
    daily_budget: float,
    acknowledge_large_change: bool = False,
    allow_shared_budget: bool = False,
    validate_only: bool = False,
) -> dict[str, Any]:
    """Set a campaign daily budget in the account currency.

    Safety:
    - Account must be allowlisted.
    - Hard max is controlled by GOOGLE_ADS_MAX_DAILY_BUDGET.
    - Increases above GOOGLE_ADS_MAX_BUDGET_INCREASE_PCT require
      acknowledge_large_change=true after explicit user approval.
    - Shared budgets are blocked unless allow_shared_budget=true.
    """
    try:
        customer_id = _customer(customer_id)
        before = ads_client().get_campaign_snapshot(customer_id, campaign_id)
        requested = Decimal(str(daily_budget))
        if before.budget_shared and not allow_shared_budget:
            raise PolicyError(
                "Campaign uses an explicitly shared budget. Set allow_shared_budget=true "
                "only after confirming every campaign affected by that budget."
            )
        POLICY.validate_budget_change(
            current_amount=before.daily_budget,
            requested_amount=requested,
            acknowledge_large_change=acknowledge_large_change,
        )
        micros = amount_to_micros(requested)
        ads_client().set_budget(
            customer_id,
            before.budget_resource_name,
            micros,
            validate_only=validate_only,
        )
        after = before if validate_only else ads_client().get_campaign_snapshot(customer_id, campaign_id)
        if not validate_only:
            append_audit_event(
                {
                    "customer_id": customer_id,
                    "campaign_id": before.campaign_id,
                    "campaign_name": before.name,
                    "action": "set_daily_budget",
                    "before": {"daily_budget": float(before.daily_budget)},
                    "after": {"daily_budget": float(after.daily_budget)},
                    "currency": before.currency_code,
                    "validate_only_passed": True,
                    "result": "success",
                    "source": "mcp",
                }
            )
        return {
            "changed": not validate_only,
            "validate_only": validate_only,
            "customer_id": customer_id,
            "campaign_id": before.campaign_id,
            "campaign_name": before.name,
            "currency_code": before.currency_code,
            "before_daily_budget": float(before.daily_budget),
            "requested_daily_budget": float(requested),
            "after_daily_budget": float(requested if validate_only else after.daily_budget),
            "budget_shared": before.budget_shared,
        }
    except Exception as exc:
        raise _api_error(exc) from exc


app = mcp.http_app(
    path="/mcp",
    middleware=[Middleware(StaticBearerMiddleware)],
    host_origin_protection=True,
    allowed_hosts=[
        os.getenv("MCP_PUBLIC_HOST", "mcp-googleads.hangdoistudio.vn"),
        "127.0.0.1",
        "localhost",
    ],
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8010")),
        proxy_headers=True,
        forwarded_allow_ips=os.getenv("FORWARDED_ALLOW_IPS", "127.0.0.1"),
    )
