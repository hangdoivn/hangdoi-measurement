from __future__ import annotations

import hmac
import os
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from typing import Any

from fastmcp import FastMCP
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from audit_log import append_audit_event, read_audit_events
from google_ads import GoogleAdsApiError, GoogleAdsRestClient
from performance_store import read_campaign_daily, upsert_campaign_daily
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
        if request.url.path.startswith("/mcp") or request.url.path.startswith("/api/"):
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


@mcp.custom_route("/api/v1/customers/{customer_id}/report", methods=["GET"])
async def api_customer_report(request: Request) -> JSONResponse:
    """Bearer-protected JSON report for Marcom ingestion."""
    try:
        customer_id = _customer(request.path_params["customer_id"])
        start_date = request.query_params.get("start_date", "")
        end_date = request.query_params.get("end_date", "")
        if not start_date or not end_date:
            return JSONResponse(
                {"error": "start_date and end_date are required"}, status_code=400
            )
        context = ads_client().customer_context(customer_id)
        campaigns = ads_client().campaign_performance(
            customer_id, start_date, end_date
        )
        conversions = ads_client().conversion_action_performance(
            customer_id, start_date, end_date
        )
        devices = ads_client().device_performance(customer_id, start_date, end_date)
        currency = context.get("currencyCode") or "UNKNOWN"
        for row in campaigns:
            row["spend"] = row["cost_micros"] / 1_000_000
        for row in devices:
            row["spend"] = row["cost_micros"] / 1_000_000
        return JSONResponse(
            {
                "customer_id": customer_id,
                "account": context,
                "currency_code": currency,
                "start_date": start_date,
                "end_date": end_date,
                "campaigns": campaigns,
                "conversion_actions": conversions,
                "devices": devices,
            }
        )
    except PolicyError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    except GoogleAdsApiError as exc:
        return JSONResponse({"error": str(exc)}, status_code=502)
    except Exception as exc:
        return JSONResponse({"error": f"unexpected: {exc}"}, status_code=500)


@mcp.custom_route("/api/v1/customers/{customer_id}/campaigns", methods=["GET"])
async def api_campaigns(request: Request) -> JSONResponse:
    """Bearer-protected campaign snapshot endpoint."""
    try:
        customer_id = _customer(request.path_params["customer_id"])
        campaigns = ads_client().list_campaigns(customer_id)
        context = ads_client().customer_context(customer_id)
        currency = context.get("currencyCode") or "UNKNOWN"
        for campaign in campaigns:
            campaign["daily_budget"] = (
                campaign.get("daily_budget_micros", 0) / 1_000_000
            )
            campaign["currency_code"] = currency
        return JSONResponse(
            {"customer_id": customer_id, "account": context, "campaigns": campaigns}
        )
    except PolicyError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    except GoogleAdsApiError as exc:
        return JSONResponse({"error": str(exc)}, status_code=502)
    except Exception as exc:
        return JSONResponse({"error": f"unexpected: {exc}"}, status_code=500)


@mcp.custom_route("/api/v1/audit", methods=["GET"])
async def api_audit(request: Request) -> JSONResponse:
    """Bearer-protected append-only mutation history endpoint."""
    try:
        raw_limit = request.query_params.get("limit", "50")
        limit = int(raw_limit)
        raw_customer = request.query_params.get("customer_id")
        customer_id = _customer(raw_customer) if raw_customer else None
        events = read_audit_events(limit=limit, customer_id=customer_id)
        return JSONResponse({"count": len(events), "events": events})
    except (ValueError, PolicyError) as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    except Exception as exc:
        return JSONResponse({"error": f"unexpected: {exc}"}, status_code=500)


@mcp.custom_route("/api/v1/customers/{customer_id}/campaigns/{campaign_id}/status", methods=["POST"])
async def api_campaign_status(request: Request) -> JSONResponse:
    """Bearer-protected guarded campaign enable/pause endpoint for Marcom."""
    try:
        customer_id = _customer(request.path_params["customer_id"])
        campaign_id = request.path_params["campaign_id"]
        payload = await request.json()
        if not isinstance(payload, dict):
            return JSONResponse({"error": "JSON object body required"}, status_code=400)
        status = str(payload.get("status", "")).strip().upper()
        if status not in {"ENABLED", "PAUSED"}:
            return JSONResponse({"error": "status must be ENABLED or PAUSED"}, status_code=400)
        actor = str(payload.get("actor") or "marcom").strip()[:191] or "marcom"

        before = ads_client().get_campaign_snapshot(customer_id, campaign_id)
        if before.status == status:
            return JSONResponse(
                {
                    "changed": False,
                    "customer_id": customer_id,
                    "campaign_id": before.campaign_id,
                    "campaign_name": before.name,
                    "before_status": before.status,
                    "after_status": before.status,
                    "message": f"Campaign is already {status.lower()}",
                }
            )

        ads_client().set_campaign_status(customer_id, campaign_id, status, validate_only=True)
        ads_client().set_campaign_status(customer_id, campaign_id, status, validate_only=False)
        after = ads_client().get_campaign_snapshot(customer_id, campaign_id)
        event = append_audit_event(
            {
                "actor": actor,
                "customer_id": customer_id,
                "campaign_id": before.campaign_id,
                "campaign_name": before.name,
                "action": "enable_campaign" if status == "ENABLED" else "pause_campaign",
                "before": {"status": before.status},
                "after": {"status": after.status},
                "currency": before.currency_code,
                "validate_only_passed": True,
                "result": "success",
                "source": "marcom_rest",
            }
        )
        return JSONResponse(
            {
                "changed": True,
                "customer_id": customer_id,
                "campaign_id": before.campaign_id,
                "campaign_name": before.name,
                "before_status": before.status,
                "after_status": after.status,
                "audit_event_id": event["event_id"],
            }
        )
    except PolicyError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    except GoogleAdsApiError as exc:
        return JSONResponse({"error": str(exc)}, status_code=502)
    except Exception as exc:
        return JSONResponse({"error": f"unexpected: {exc}"}, status_code=500)


@mcp.custom_route("/api/v1/customers/{customer_id}/campaigns/{campaign_id}/budget", methods=["POST"])
async def api_campaign_budget(request: Request) -> JSONResponse:
    """Bearer-protected guarded daily-budget mutation endpoint for Marcom."""
    try:
        customer_id = _customer(request.path_params["customer_id"])
        campaign_id = request.path_params["campaign_id"]
        payload = await request.json()
        if not isinstance(payload, dict):
            return JSONResponse({"error": "JSON object body required"}, status_code=400)

        try:
            requested = Decimal(str(payload.get("daily_budget")))
        except (InvalidOperation, ValueError, TypeError):
            return JSONResponse({"error": "daily_budget must be numeric"}, status_code=400)

        acknowledge = bool(payload.get("acknowledge_large_change", False))
        allow_shared = bool(payload.get("allow_shared_budget", False))
        actor = str(payload.get("actor") or "marcom").strip()[:191] or "marcom"

        before = ads_client().get_campaign_snapshot(customer_id, campaign_id)
        if before.budget_shared and not allow_shared:
            raise PolicyError(
                "Campaign uses an explicitly shared budget. "
                "Set allow_shared_budget=true only after confirming every affected campaign."
            )
        POLICY.validate_budget_change(
            current_amount=before.daily_budget,
            requested_amount=requested,
            acknowledge_large_change=acknowledge,
        )
        micros = amount_to_micros(requested)

        ads_client().set_budget(
            customer_id,
            before.budget_resource_name,
            micros,
            validate_only=True,
        )
        ads_client().set_budget(
            customer_id,
            before.budget_resource_name,
            micros,
            validate_only=False,
        )
        after = ads_client().get_campaign_snapshot(customer_id, campaign_id)
        event = append_audit_event(
            {
                "actor": actor,
                "customer_id": customer_id,
                "campaign_id": before.campaign_id,
                "campaign_name": before.name,
                "action": "set_daily_budget",
                "before": {"daily_budget": float(before.daily_budget)},
                "after": {"daily_budget": float(after.daily_budget)},
                "currency": before.currency_code,
                "validate_only_passed": True,
                "result": "success",
                "source": "marcom_rest",
            }
        )
        return JSONResponse(
            {
                "changed": True,
                "customer_id": customer_id,
                "campaign_id": before.campaign_id,
                "campaign_name": before.name,
                "currency_code": before.currency_code,
                "before_daily_budget": float(before.daily_budget),
                "after_daily_budget": float(after.daily_budget),
                "budget_shared": before.budget_shared,
                "audit_event_id": event["event_id"],
            }
        )
    except PolicyError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    except GoogleAdsApiError as exc:
        return JSONResponse({"error": str(exc)}, status_code=502)
    except Exception as exc:
        return JSONResponse({"error": f"unexpected: {exc}"}, status_code=500)


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
def get_live_campaign_performance(
    customer_id: str,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """Read live daily campaign performance from Google Ads for up to 93 days."""
    try:
        customer_id = _customer(customer_id)
        context = ads_client().customer_context(customer_id)
        rows = ads_client().campaign_performance(customer_id, start_date, end_date)
        currency = context.get("currencyCode") or "UNKNOWN"
        for row in rows:
            row["spend"] = row["cost_micros"] / 1_000_000
            row["currency_code"] = currency
        return {
            "customer_id": customer_id,
            "currency_code": currency,
            "start_date": start_date,
            "end_date": end_date,
            "rows": rows,
        }
    except Exception as exc:
        raise _api_error(exc) from exc


@mcp.tool
def refresh_campaign_performance(
    customer_id: str,
    lookback_days: int = 7,
) -> dict[str, Any]:
    """Read Google Ads and upsert the recent daily campaign snapshot into local storage."""
    try:
        customer_id = _customer(customer_id)
        days = max(1, min(int(lookback_days), 90))
        end = date.today()
        start = end - timedelta(days=days - 1)
        context = ads_client().customer_context(customer_id)
        currency = context.get("currencyCode") or "UNKNOWN"
        rows = ads_client().campaign_performance(
            customer_id, start.isoformat(), end.isoformat()
        )
        count = upsert_campaign_daily(
            customer_id=customer_id,
            currency_code=currency,
            rows=rows,
        )
        return {
            "customer_id": customer_id,
            "currency_code": currency,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "rows_upserted": count,
        }
    except Exception as exc:
        raise _api_error(exc) from exc


@mcp.tool
def get_collected_campaign_performance(
    customer_id: str,
    start_date: str,
    end_date: str,
    campaign_id: str | None = None,
) -> dict[str, Any]:
    """Read persisted daily campaign performance collected on the VPS."""
    try:
        customer_id = _customer(customer_id)
        rows = read_campaign_daily(
            customer_id=customer_id,
            start_date=start_date,
            end_date=end_date,
            campaign_id=campaign_id,
        )
        return {
            "customer_id": customer_id,
            "start_date": start_date,
            "end_date": end_date,
            "campaign_id": campaign_id,
            "rows": rows,
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
