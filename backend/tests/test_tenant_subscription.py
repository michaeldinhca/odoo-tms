"""Pure-function tests — Tenant instantiated directly (no DB session), same
as this file needs no Postgres: `Tenant` uses `postgresql.UUID` and isn't
part of the SQLite test fixture (see conftest.py), but these functions
only read plain attributes off the object, never touch the DB."""

from datetime import UTC, datetime, timedelta

from app.models.tenant import Tenant
from app.services.tenant_subscription import (
    DEFAULT_WARNING_PERIOD_DAYS,
    compute_subscription_state,
    compute_warning_date,
)

NOW = datetime(2026, 7, 26, tzinfo=UTC)


def _tenant(**overrides) -> Tenant:
    defaults = {
        "name": "Acme",
        "status": "active",
        "expire_date": None,
        "warning_period_days": None,
    }
    defaults.update(overrides)
    return Tenant(**defaults)


def test_no_expire_date_is_active():
    tenant = _tenant()
    assert compute_warning_date(tenant) is None
    assert compute_subscription_state(tenant, now=NOW) == "active"


def test_far_future_expiry_is_active():
    tenant = _tenant(expire_date=NOW + timedelta(days=60), warning_period_days=14)
    assert compute_subscription_state(tenant, now=NOW) == "active"


def test_within_warning_window_is_warning():
    tenant = _tenant(expire_date=NOW + timedelta(days=5), warning_period_days=14)
    assert compute_subscription_state(tenant, now=NOW) == "warning"


def test_past_expire_date_is_expired():
    tenant = _tenant(expire_date=NOW - timedelta(days=1), warning_period_days=14)
    assert compute_subscription_state(tenant, now=NOW) == "expired"


def test_warning_date_uses_default_period_when_unset():
    tenant = _tenant(expire_date=NOW + timedelta(days=10), warning_period_days=None)
    expected = tenant.expire_date - timedelta(days=DEFAULT_WARNING_PERIOD_DAYS)
    assert compute_warning_date(tenant) == expected
    assert compute_subscription_state(tenant, now=NOW) == "warning"


def test_suspended_status_overrides_future_expiry():
    tenant = _tenant(status="suspended", expire_date=NOW + timedelta(days=365))
    assert compute_subscription_state(tenant, now=NOW) == "suspended"


def test_cancelled_status_overrides_no_expiry():
    tenant = _tenant(status="cancelled", expire_date=None)
    assert compute_subscription_state(tenant, now=NOW) == "cancelled"


def test_expire_date_exactly_now_is_expired():
    tenant = _tenant(expire_date=NOW, warning_period_days=14)
    assert compute_subscription_state(tenant, now=NOW) == "expired"


def test_warning_date_exactly_now_is_warning():
    tenant = _tenant(expire_date=NOW + timedelta(days=14), warning_period_days=14)
    assert compute_subscription_state(tenant, now=NOW) == "warning"
