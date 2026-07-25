"""Shared helpers for Odoo's XML-RPC value shapes: many2one fields come back
as `[id, display_name]` when set, `False` when unset; datetimes come back as
naive UTC strings, `False` when unset. Used by any sync/pull logic that reads
these (stock.picking.partner_id, res.partner.country_id, scheduled_date...)."""

from datetime import UTC, datetime
from typing import Any

ODOO_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def rel_id(value: Any) -> int | None:
    return value[0] if value else None


def rel_name(value: Any, default: str = "") -> str:
    return value[1] if value else default


def parse_odoo_datetime(value: Any) -> datetime | None:
    """Odoo returns naive UTC datetime strings (or `False` when unset)."""
    if not value:
        return None
    try:
        return datetime.strptime(value, ODOO_DATETIME_FORMAT).replace(tzinfo=UTC)
    except (TypeError, ValueError):
        return None
