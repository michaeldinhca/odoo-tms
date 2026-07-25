"""Read-only lookups against Odoo's `fleet.vehicle` / `hr.employee` — used
only to let the user browse and link a local Vehicle/Driver to an Odoo
record for cross-reference. Never auto-creates local records from this data,
and both modules are optional on a tenant's Odoo instance, so every call
checks the model exists first rather than assuming it (see DECISIONS.md)."""

from app.services.odoo_client import OdooClient


def fetch_fleet_vehicles(
    client: OdooClient, company_id: int | None = None
) -> tuple[bool, list[dict]]:
    """Returns (available, vehicles). `available=False` means the Fleet
    module isn't installed on this Odoo instance — not an error."""
    if not client.model_exists("fleet.vehicle"):
        return False, []

    records = client.search_read(
        "fleet.vehicle",
        domain=[],
        fields=["id", "name", "license_plate"],
        company_id=company_id,
    )
    return True, [
        {
            "id": rec["id"],
            "name": rec.get("name") or "",
            "license_plate": rec.get("license_plate") or "",
        }
        for rec in records
    ]


def fetch_employees(client: OdooClient, company_id: int | None = None) -> tuple[bool, list[dict]]:
    """Returns (available, employees). `available=False` means `hr.employee`
    isn't accessible on this Odoo instance (HR module absent or no access)
    — not an error."""
    if not client.model_exists("hr.employee"):
        return False, []

    records = client.search_read(
        "hr.employee",
        domain=[],
        fields=["id", "name", "work_phone", "mobile_phone"],
        company_id=company_id,
    )
    return True, [
        {
            "id": rec["id"],
            "name": rec.get("name") or "",
            "work_phone": rec.get("work_phone") or "",
            "mobile_phone": rec.get("mobile_phone") or "",
        }
        for rec in records
    ]
