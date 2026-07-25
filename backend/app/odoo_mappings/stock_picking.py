"""Field mapping for stock.picking. Only add a version block below once a
real difference has been confirmed against an actual Odoo instance of that
version — never speculatively (see DECISIONS.md)."""

FIELD_MAP = {
    "default": {
        "partner_id": "partner_id",
        "state": "state",
        "scheduled_date": "scheduled_date",
        "picking_type_id": "picking_type_id",
        "origin": "origin",
        "weight": "weight",
        "shipping_weight": "shipping_weight",  # optional — only with the `delivery` module
        "note": "note",
    },
}
