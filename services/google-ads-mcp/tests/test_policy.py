from decimal import Decimal

import pytest

from policy import (
    MutationPolicy,
    PolicyError,
    amount_to_micros,
    normalize_customer_id,
    parse_allowlist,
    require_allowed_customer,
)


def test_normalize_customer_id():
    assert normalize_customer_id("868-122-8450") == "8681228450"


def test_allowlist():
    allowed = parse_allowlist("868-122-8450,1234567890")
    assert require_allowed_customer("8681228450", allowed) == "8681228450"
    with pytest.raises(PolicyError):
        require_allowed_customer("1111111111", allowed)


def test_amount_to_micros_vnd():
    assert amount_to_micros(100000) == 100_000_000_000


def test_large_increase_requires_acknowledgement():
    policy = MutationPolicy(
        max_daily_budget=Decimal("5000000"),
        max_increase_ratio=Decimal("0.20"),
    )
    with pytest.raises(PolicyError):
        policy.validate_budget_change(
            current_amount=Decimal("50000"),
            requested_amount=Decimal("100000"),
            acknowledge_large_change=False,
        )
    policy.validate_budget_change(
        current_amount=Decimal("50000"),
        requested_amount=Decimal("100000"),
        acknowledge_large_change=True,
    )


def test_hard_budget_limit():
    policy = MutationPolicy(
        max_daily_budget=Decimal("200000"),
        max_increase_ratio=Decimal("10"),
    )
    with pytest.raises(PolicyError):
        policy.validate_budget_change(
            current_amount=Decimal("100000"),
            requested_amount=Decimal("200001"),
            acknowledge_large_change=True,
        )
