from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


class PolicyError(ValueError):
    """Raised when a requested Ads mutation violates Hang Doi policy."""


def normalize_customer_id(customer_id: str) -> str:
    value = "".join(ch for ch in str(customer_id) if ch.isdigit())
    if len(value) != 10:
        raise PolicyError("customer_id must contain exactly 10 digits")
    return value


def parse_allowlist(raw: str | None) -> set[str]:
    if not raw:
        return set()
    return {
        normalize_customer_id(item)
        for item in raw.replace(";", ",").split(",")
        if item.strip()
    }


def require_allowed_customer(customer_id: str, allowlist: set[str]) -> str:
    normalized = normalize_customer_id(customer_id)
    if not allowlist:
        raise PolicyError("No Google Ads customer allowlist is configured")
    if normalized not in allowlist:
        raise PolicyError(f"Google Ads customer {normalized} is not allowlisted")
    return normalized


def amount_to_micros(amount: float | int | str) -> int:
    try:
        decimal_amount = Decimal(str(amount))
    except InvalidOperation as exc:
        raise PolicyError("daily_budget must be numeric") from exc
    if decimal_amount <= 0:
        raise PolicyError("daily_budget must be greater than zero")
    micros = decimal_amount * Decimal(1_000_000)
    if micros != micros.to_integral_value():
        raise PolicyError("daily_budget has more precision than Google Ads supports")
    return int(micros)


@dataclass(frozen=True)
class MutationPolicy:
    max_daily_budget: Decimal
    max_increase_ratio: Decimal

    @classmethod
    def from_env(cls) -> "MutationPolicy":
        max_daily = Decimal(os.getenv("GOOGLE_ADS_MAX_DAILY_BUDGET", "5000000"))
        max_increase_pct = Decimal(os.getenv("GOOGLE_ADS_MAX_BUDGET_INCREASE_PCT", "20"))
        return cls(
            max_daily_budget=max_daily,
            max_increase_ratio=max_increase_pct / Decimal(100),
        )

    def validate_budget_change(
        self,
        *,
        current_amount: Decimal,
        requested_amount: Decimal,
        acknowledge_large_change: bool,
    ) -> None:
        if requested_amount <= 0:
            raise PolicyError("daily_budget must be greater than zero")
        if requested_amount > self.max_daily_budget:
            raise PolicyError(
                f"daily_budget exceeds MCP hard limit {self.max_daily_budget}"
            )
        if current_amount > 0:
            increase_ratio = (requested_amount - current_amount) / current_amount
            if increase_ratio > self.max_increase_ratio and not acknowledge_large_change:
                pct = (increase_ratio * Decimal(100)).quantize(Decimal("0.1"))
                raise PolicyError(
                    "Budget increase is "
                    f"{pct}% and exceeds the confirmation threshold. "
                    "Call again with acknowledge_large_change=true after explicit user approval."
                )
