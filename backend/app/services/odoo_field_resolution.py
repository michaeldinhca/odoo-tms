"""Bridges the pure field-name mapping registry (app.odoo_mappings) with
live Odoo introspection (OdooClient.has_field) — the one place that knows
how to turn a logical field name into "the real Odoo field name for this
tenant's version, or None if it doesn't exist on this Odoo instance at all"
for optional fields. Consolidates what was previously an ad-hoc
has_field()-then-maybe-skip check scattered per call site (see
DECISIONS.md)."""

from app.odoo_mappings import resolve_field
from app.services.odoo_client import OdooClient


def resolve_required_field(model: str, logical_name: str, version_major: int | None) -> str:
    """For fields assumed always present (core, non-optional-module fields)
    — a pure mapping lookup, no Odoo round trip."""
    return resolve_field(model, logical_name, version_major)


def resolve_optional_field(
    client: OdooClient, model: str, logical_name: str, version_major: int | None
) -> str | None:
    """For fields that may not exist on a given tenant's Odoo (e.g. an
    optional module's field, or a field renamed/removed in some version).
    Checks existence via `fields_get()` and returns None instead of the
    field name when absent — callers should skip requesting/populating that
    logical field entirely rather than treating it as an error."""
    odoo_field = resolve_field(model, logical_name, version_major)
    return odoo_field if client.has_field(model, odoo_field) else None
