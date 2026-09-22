from __future__ import annotations

import base64
import json
import os
import threading
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import requests
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import service_account

from policy import PolicyError, normalize_customer_id


ADWORDS_SCOPE = "https://www.googleapis.com/auth/adwords"
DEFAULT_API_VERSION = "v25"


class GoogleAdsApiError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None, payload: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


@dataclass(frozen=True)
class CampaignSnapshot:
    customer_id: str
    currency_code: str
    campaign_id: str
    name: str
    status: str
    advertising_channel_type: str
    budget_resource_name: str
    daily_budget: Decimal
    budget_shared: bool


class GoogleAdsRestClient:
    """Small token-less Google Ads REST client using a service account.

    Since 2026-09-09, Google Ads API access level is attached to the Google
    Cloud project that owns these credentials. The legacy developer-token
    header is intentionally not sent.
    """

    def __init__(
        self,
        *,
        credentials_file: str | None = None,
        credentials_info: dict[str, Any] | None = None,
        api_version: str = DEFAULT_API_VERSION,
        login_customer_id: str | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        if bool(credentials_file) == bool(credentials_info):
            raise RuntimeError(
                "Provide exactly one of credentials_file or credentials_info"
            )
        self.credentials_file = None
        self.api_version = api_version
        self.login_customer_id = (
            normalize_customer_id(login_customer_id) if login_customer_id else None
        )
        self.timeout_seconds = timeout_seconds
        if credentials_info is not None:
            self._credentials = service_account.Credentials.from_service_account_info(
                credentials_info,
                scopes=[ADWORDS_SCOPE],
            )
        else:
            path = Path(str(credentials_file))
            if not path.exists():
                raise RuntimeError(f"Google service account credentials not found: {path}")
            self.credentials_file = str(path)
            self._credentials = service_account.Credentials.from_service_account_file(
                self.credentials_file,
                scopes=[ADWORDS_SCOPE],
            )
        self._credential_lock = threading.Lock()
        self._session = requests.Session()

    @classmethod
    def from_env(cls) -> "GoogleAdsRestClient":
        credentials_b64 = os.environ.get(
            "GOOGLE_ADS_SERVICE_ACCOUNT_JSON_B64", ""
        ).strip()
        credentials_file = os.environ.get(
            "GOOGLE_ADS_SERVICE_ACCOUNT_FILE", ""
        ).strip()
        credentials_info = None
        if credentials_b64:
            try:
                normalized_b64 = "".join(credentials_b64.split())
                decoded = base64.b64decode(normalized_b64, validate=True).decode("utf-8")
                credentials_info = json.loads(decoded)
            except Exception as exc:
                raise RuntimeError(
                    "GOOGLE_ADS_SERVICE_ACCOUNT_JSON_B64 is not valid base64 JSON"
                ) from exc
        if not credentials_info and not credentials_file:
            raise RuntimeError(
                "Configure GOOGLE_ADS_SERVICE_ACCOUNT_JSON_B64 or "
                "GOOGLE_ADS_SERVICE_ACCOUNT_FILE"
            )
        return cls(
            credentials_file=credentials_file or None,
            credentials_info=credentials_info,
            api_version=os.getenv("GOOGLE_ADS_API_VERSION", DEFAULT_API_VERSION),
            login_customer_id=os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID") or None,
            timeout_seconds=float(os.getenv("GOOGLE_ADS_HTTP_TIMEOUT_SECONDS", "30")),
        )

    def _access_token(self, *, force_refresh: bool = False) -> str:
        with self._credential_lock:
            if force_refresh or not self._credentials.valid:
                self._credentials.refresh(GoogleAuthRequest())
            token = self._credentials.token
            if not token:
                raise RuntimeError("Unable to obtain Google OAuth access token")
            return token

    def _headers(self, *, force_refresh: bool = False) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self._access_token(force_refresh=force_refresh)}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "hangdoi-google-ads-mcp/0.1",
        }
        if self.login_customer_id:
            headers["login-customer-id"] = self.login_customer_id
        return headers

    def _post(self, url: str, payload: dict[str, Any]) -> Any:
        response = self._session.post(
            url,
            headers=self._headers(),
            json=payload,
            timeout=self.timeout_seconds,
        )
        if response.status_code == 401:
            response = self._session.post(
                url,
                headers=self._headers(force_refresh=True),
                json=payload,
                timeout=self.timeout_seconds,
            )
        if not response.ok:
            try:
                body = response.json()
            except ValueError:
                body = response.text
            raise GoogleAdsApiError(
                self._extract_error_message(body, response.status_code),
                status_code=response.status_code,
                payload=body,
            )
        if not response.content:
            return {}
        return response.json()

    @staticmethod
    def _extract_error_message(body: Any, status_code: int) -> str:
        if isinstance(body, dict):
            error = body.get("error")
            if isinstance(error, dict):
                message = error.get("message")
                status = error.get("status")
                details = error.get("details")
                suffix = ""
                if details:
                    suffix = f" details={json.dumps(details, ensure_ascii=False)[:2000]}"
                return f"Google Ads API {status_code} {status or ''}: {message or error}{suffix}"
        return f"Google Ads API {status_code}: {str(body)[:2000]}"

    def search(self, customer_id: str, query: str) -> list[dict[str, Any]]:
        customer_id = normalize_customer_id(customer_id)
        url = (
            f"https://googleads.googleapis.com/{self.api_version}/customers/"
            f"{customer_id}/googleAds:searchStream"
        )
        chunks = self._post(url, {"query": query})
        if not isinstance(chunks, list):
            raise GoogleAdsApiError("Unexpected Google Ads searchStream response")
        rows: list[dict[str, Any]] = []
        for chunk in chunks:
            if isinstance(chunk, dict):
                results = chunk.get("results") or []
                if isinstance(results, list):
                    rows.extend(row for row in results if isinstance(row, dict))
        return rows

    def customer_context(self, customer_id: str) -> dict[str, Any]:
        rows = self.search(
            customer_id,
            "SELECT customer.id, customer.descriptive_name, customer.currency_code, "
            "customer.time_zone FROM customer LIMIT 1",
        )
        if not rows:
            raise GoogleAdsApiError("Google Ads customer was not returned by the API")
        return rows[0].get("customer", {})

    def list_campaigns(self, customer_id: str) -> list[dict[str, Any]]:
        rows = self.search(
            customer_id,
            "SELECT campaign.id, campaign.name, campaign.status, "
            "campaign.advertising_channel_type, campaign.bidding_strategy_type, "
            "campaign.campaign_budget, campaign_budget.id, campaign_budget.name, "
            "campaign_budget.amount_micros, campaign_budget.explicitly_shared "
            "FROM campaign WHERE campaign.status != 'REMOVED' ORDER BY campaign.id",
        )
        result: list[dict[str, Any]] = []
        for row in rows:
            campaign = row.get("campaign", {})
            budget = row.get("campaignBudget", {})
            result.append(
                {
                    "id": str(campaign.get("id", "")),
                    "name": campaign.get("name"),
                    "status": campaign.get("status"),
                    "advertising_channel_type": campaign.get("advertisingChannelType"),
                    "bidding_strategy_type": campaign.get("biddingStrategyType"),
                    "campaign_budget": campaign.get("campaignBudget"),
                    "daily_budget_micros": int(budget.get("amountMicros", 0) or 0),
                    "budget_name": budget.get("name"),
                    "budget_shared": bool(budget.get("explicitlyShared", False)),
                }
            )
        return result

    def campaign_performance(
        self,
        customer_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        customer_id = normalize_customer_id(customer_id)
        try:
            start = date.fromisoformat(start_date)
            end = date.fromisoformat(end_date)
        except ValueError as exc:
            raise PolicyError("start_date and end_date must be YYYY-MM-DD") from exc
        if end < start:
            raise PolicyError("end_date must be on or after start_date")
        if (end - start).days > 92:
            raise PolicyError("performance query range cannot exceed 93 days")

        rows = self.search(
            customer_id,
            "SELECT segments.date, campaign.id, campaign.name, campaign.status, "
            "campaign.advertising_channel_type, metrics.cost_micros, "
            "metrics.impressions, metrics.clicks, metrics.conversions, "
            "metrics.conversions_value "
            "FROM campaign "
            f"WHERE segments.date BETWEEN '{start.isoformat()}' AND '{end.isoformat()}' "
            "AND campaign.status != 'REMOVED' "
            "ORDER BY segments.date, campaign.id",
        )
        result: list[dict[str, Any]] = []
        for row in rows:
            segments = row.get("segments", {})
            campaign = row.get("campaign", {})
            metrics = row.get("metrics", {})
            result.append(
                {
                    "date": segments.get("date"),
                    "campaign_id": str(campaign.get("id", "")),
                    "campaign_name": campaign.get("name"),
                    "campaign_status": campaign.get("status"),
                    "advertising_channel_type": campaign.get("advertisingChannelType"),
                    "cost_micros": int(metrics.get("costMicros", 0) or 0),
                    "impressions": int(metrics.get("impressions", 0) or 0),
                    "clicks": int(metrics.get("clicks", 0) or 0),
                    "conversions": float(metrics.get("conversions", 0) or 0),
                    "conversions_value": float(metrics.get("conversionsValue", 0) or 0),
                }
            )
        return result

    def conversion_action_performance(
        self,
        customer_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        customer_id = normalize_customer_id(customer_id)
        try:
            start = date.fromisoformat(start_date)
            end = date.fromisoformat(end_date)
        except ValueError as exc:
            raise PolicyError("start_date and end_date must be YYYY-MM-DD") from exc
        if end < start:
            raise PolicyError("end_date must be on or after start_date")
        if (end - start).days > 92:
            raise PolicyError("performance query range cannot exceed 93 days")

        rows = self.search(
            customer_id,
            "SELECT segments.date, segments.conversion_action_name, "
            "segments.conversion_action_category, metrics.conversions, "
            "metrics.all_conversions "
            "FROM customer "
            f"WHERE segments.date BETWEEN '{start.isoformat()}' AND '{end.isoformat()}' "
            "ORDER BY segments.date",
        )
        result: list[dict[str, Any]] = []
        for row in rows:
            segments = row.get("segments", {})
            metrics = row.get("metrics", {})
            name = segments.get("conversionActionName")
            if not name:
                continue
            result.append(
                {
                    "date": segments.get("date"),
                    "conversion_action_name": name,
                    "conversion_action_category": segments.get("conversionActionCategory"),
                    "conversions": float(metrics.get("conversions", 0) or 0),
                    "all_conversions": float(metrics.get("allConversions", 0) or 0),
                }
            )
        return result

    def device_performance(
        self,
        customer_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        customer_id = normalize_customer_id(customer_id)
        try:
            start = date.fromisoformat(start_date)
            end = date.fromisoformat(end_date)
        except ValueError as exc:
            raise PolicyError("start_date and end_date must be YYYY-MM-DD") from exc
        if end < start:
            raise PolicyError("end_date must be on or after start_date")
        if (end - start).days > 92:
            raise PolicyError("performance query range cannot exceed 93 days")

        rows = self.search(
            customer_id,
            "SELECT segments.date, segments.device, metrics.impressions, "
            "metrics.clicks, metrics.cost_micros, metrics.conversions "
            "FROM campaign "
            f"WHERE segments.date BETWEEN '{start.isoformat()}' AND '{end.isoformat()}' "
            "AND campaign.status != 'REMOVED' "
            "ORDER BY segments.date, segments.device",
        )
        result: list[dict[str, Any]] = []
        for row in rows:
            segments = row.get("segments", {})
            metrics = row.get("metrics", {})
            result.append(
                {
                    "date": segments.get("date"),
                    "device": segments.get("device") or "UNKNOWN",
                    "cost_micros": int(metrics.get("costMicros", 0) or 0),
                    "impressions": int(metrics.get("impressions", 0) or 0),
                    "clicks": int(metrics.get("clicks", 0) or 0),
                    "conversions": float(metrics.get("conversions", 0) or 0),
                }
            )
        return result

    def get_campaign_snapshot(self, customer_id: str, campaign_id: str) -> CampaignSnapshot:
        customer_id = normalize_customer_id(customer_id)
        if not str(campaign_id).isdigit():
            raise PolicyError("campaign_id must be numeric")
        rows = self.search(
            customer_id,
            "SELECT customer.currency_code, campaign.id, campaign.name, campaign.status, "
            "campaign.advertising_channel_type, campaign.campaign_budget, "
            "campaign_budget.amount_micros, campaign_budget.explicitly_shared "
            f"FROM campaign WHERE campaign.id = {int(campaign_id)} LIMIT 1",
        )
        if not rows:
            raise GoogleAdsApiError(f"Campaign {campaign_id} not found")
        row = rows[0]
        customer = row.get("customer", {})
        campaign = row.get("campaign", {})
        budget = row.get("campaignBudget", {})
        amount_micros = int(budget.get("amountMicros", 0) or 0)
        resource_name = campaign.get("campaignBudget")
        if not resource_name:
            raise GoogleAdsApiError("Campaign has no campaign budget resource")
        return CampaignSnapshot(
            customer_id=customer_id,
            currency_code=customer.get("currencyCode") or "UNKNOWN",
            campaign_id=str(campaign.get("id", campaign_id)),
            name=campaign.get("name") or "",
            status=campaign.get("status") or "UNKNOWN",
            advertising_channel_type=campaign.get("advertisingChannelType") or "UNKNOWN",
            budget_resource_name=resource_name,
            daily_budget=Decimal(amount_micros) / Decimal(1_000_000),
            budget_shared=bool(budget.get("explicitlyShared", False)),
        )

    def set_campaign_status(
        self,
        customer_id: str,
        campaign_id: str,
        status: str,
        *,
        validate_only: bool = False,
    ) -> dict[str, Any]:
        customer_id = normalize_customer_id(customer_id)
        status = status.upper()
        if status not in {"ENABLED", "PAUSED"}:
            raise PolicyError("status must be ENABLED or PAUSED")
        if not str(campaign_id).isdigit():
            raise PolicyError("campaign_id must be numeric")
        url = (
            f"https://googleads.googleapis.com/{self.api_version}/customers/"
            f"{customer_id}/campaigns:mutate"
        )
        payload = {
            "operations": [
                {
                    "update": {
                        "resourceName": f"customers/{customer_id}/campaigns/{int(campaign_id)}",
                        "status": status,
                    },
                    "updateMask": "status",
                }
            ],
            "responseContentType": "MUTABLE_RESOURCE",
            "validateOnly": validate_only,
        }
        return self._post(url, payload)

    def set_budget(
        self,
        customer_id: str,
        budget_resource_name: str,
        amount_micros: int,
        *,
        validate_only: bool = False,
    ) -> dict[str, Any]:
        customer_id = normalize_customer_id(customer_id)
        expected_prefix = f"customers/{customer_id}/campaignBudgets/"
        if not budget_resource_name.startswith(expected_prefix):
            raise PolicyError("budget resource does not belong to the requested customer")
        if amount_micros <= 0:
            raise PolicyError("amount_micros must be positive")
        url = (
            f"https://googleads.googleapis.com/{self.api_version}/customers/"
            f"{customer_id}/campaignBudgets:mutate"
        )
        payload = {
            "operations": [
                {
                    "update": {
                        "resourceName": budget_resource_name,
                        "amountMicros": str(amount_micros),
                    },
                    "updateMask": "amount_micros",
                }
            ],
            "responseContentType": "MUTABLE_RESOURCE",
            "validateOnly": validate_only,
        }
        return self._post(url, payload)
