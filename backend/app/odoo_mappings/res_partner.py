"""Field mapping for res.partner. Only add a version block below once a
real difference has been confirmed against an actual Odoo instance of that
version — never speculatively (see DECISIONS.md)."""

FIELD_MAP = {
    "default": {
        "street": "street",
        "street2": "street2",
        "city": "city",
        "state_id": "state_id",
        "country_id": "country_id",
        "zip": "zip",
    },
}
