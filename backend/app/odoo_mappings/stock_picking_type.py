"""Field mapping for stock.picking.type. Only add a version block below once
a real difference has been confirmed against an actual Odoo instance of that
version — never speculatively (see DECISIONS.md)."""

FIELD_MAP = {
    "default": {
        "name": "name",
        "code": "code",
        "warehouse_id": "warehouse_id",
    },
}
