"""Version-aware Odoo field name resolution.

Tenants connect to Odoo instances that may run different major versions
(13, 15, 16, 17, 18, 19, ...). Native field names are mostly stable across
versions, so each model's FIELD_MAP has a `"default"` block plus an optional
per-major-version block containing *only* entries that genuinely differ —
never a full duplicate of the default (see DECISIONS.md "Version-keyed field
mapping with a default fallback").

This module is pure config + lookup — no XML-RPC, no Odoo client. For
optional fields that may not exist on a given tenant's instance at all (e.g.
`shipping_weight` without the `delivery` module), see
`app.services.odoo_field_resolution.resolve_optional_field`, which layers a
live `fields_get()` existence check on top of this.
"""

from app.odoo_mappings import (
    fleet_vehicle,
    hr_employee,
    res_partner,
    stock_picking,
    stock_picking_type,
    stock_warehouse,
)

_MODEL_MAPS: dict[str, dict] = {
    "stock.picking": stock_picking.FIELD_MAP,
    "stock.warehouse": stock_warehouse.FIELD_MAP,
    "stock.picking.type": stock_picking_type.FIELD_MAP,
    "fleet.vehicle": fleet_vehicle.FIELD_MAP,
    "hr.employee": hr_employee.FIELD_MAP,
    "res.partner": res_partner.FIELD_MAP,
}


def resolve_field(model: str, logical_name: str, version_major: int | None = None) -> str:
    """Returns the Odoo-side field name for `logical_name` on `model`, given
    a tenant's detected `version_major` (or None if undetected — falls back
    to the default mapping). A version-specific override wins when present;
    otherwise falls back to `"default"`. An unknown/future `version_major`
    with no matching block also falls back to `"default"` — it never errors
    just because we haven't seen that version yet.
    """
    try:
        field_map = _MODEL_MAPS[model]
    except KeyError:
        raise KeyError(f"No field mapping registered for Odoo model '{model}'") from None

    version_overrides = field_map.get(version_major, {}) if version_major is not None else {}
    if logical_name in version_overrides:
        return version_overrides[logical_name]

    try:
        return field_map["default"][logical_name]
    except KeyError:
        raise KeyError(f"No default field mapping for '{model}'.'{logical_name}'") from None
