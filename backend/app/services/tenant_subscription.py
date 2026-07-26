"""Subscription state, computed at read time — see Tenant's docstring for
why `warning_date` and the overall state aren't stored columns. Nothing
here is enforced yet (no login/API blocking on an expired or suspended
tenant) — this is tracking/reporting only until a real billing flow
exists to dispute/grace against. See DECISIONS.md."""

from datetime import UTC, datetime, timedelta

from app.models.tenant import Tenant

DEFAULT_WARNING_PERIOD_DAYS = 14

_MANUAL_STATES = ("suspended", "cancelled")


def compute_warning_date(tenant: Tenant) -> datetime | None:
    if tenant.expire_date is None:
        return None
    period = (
        tenant.warning_period_days
        if tenant.warning_period_days is not None
        else DEFAULT_WARNING_PERIOD_DAYS
    )
    return tenant.expire_date - timedelta(days=period)


def compute_subscription_state(tenant: Tenant, *, now: datetime | None = None) -> str:
    """One of `active`/`warning`/`expired`/`suspended`/`cancelled`. A
    manual `status` override always wins over date math — see Tenant's
    docstring."""
    if tenant.status in _MANUAL_STATES:
        return tenant.status
    if tenant.expire_date is None:
        return "active"

    now = now or datetime.now(UTC)
    if now >= tenant.expire_date:
        return "expired"

    warning_date = compute_warning_date(tenant)
    if warning_date is not None and now >= warning_date:
        return "warning"
    return "active"
