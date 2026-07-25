"""Read-only lookups against Odoo's `fleet.vehicle` / `hr.employee` — used
only to let the user browse and link a local Vehicle/Driver to an Odoo
record for cross-reference. Never auto-creates local records from this data,
and both modules are optional on a tenant's Odoo instance, so every call
checks the model exists first rather than assuming it (see DECISIONS.md)."""

from app.services.odoo_client import OdooClient
from app.services.odoo_field_resolution import resolve_required_field

_FLEET_VEHICLE_MODEL = "fleet.vehicle"
_HR_EMPLOYEE_MODEL = "hr.employee"


def fetch_fleet_vehicles(
    client: OdooClient, company_id: int | None = None, version_major: int | None = None
) -> tuple[bool, list[dict]]:
    """Returns (available, vehicles). `available=False` means the Fleet
    module isn't installed on this Odoo instance — not an error."""
    if not client.model_exists(_FLEET_VEHICLE_MODEL):
        return False, []

    name_f = resolve_required_field(_FLEET_VEHICLE_MODEL, "name", version_major)
    license_plate_f = resolve_required_field(_FLEET_VEHICLE_MODEL, "license_plate", version_major)

    records = client.search_read(
        _FLEET_VEHICLE_MODEL,
        domain=[],
        fields=["id", name_f, license_plate_f],
        company_id=company_id,
    )
    return True, [
        {
            "id": rec["id"],
            "name": rec.get(name_f) or "",
            "license_plate": rec.get(license_plate_f) or "",
        }
        for rec in records
    ]


def fetch_employees(
    client: OdooClient, company_id: int | None = None, version_major: int | None = None
) -> tuple[bool, list[dict]]:
    """Returns (available, employees). `available=False` means `hr.employee`
    isn't accessible on this Odoo instance (HR module absent or no access)
    — not an error."""
    if not client.model_exists(_HR_EMPLOYEE_MODEL):
        return False, []

    name_f = resolve_required_field(_HR_EMPLOYEE_MODEL, "name", version_major)
    work_phone_f = resolve_required_field(_HR_EMPLOYEE_MODEL, "work_phone", version_major)
    mobile_phone_f = resolve_required_field(_HR_EMPLOYEE_MODEL, "mobile_phone", version_major)

    records = client.search_read(
        _HR_EMPLOYEE_MODEL,
        domain=[],
        fields=["id", name_f, work_phone_f, mobile_phone_f],
        company_id=company_id,
    )
    return True, [
        {
            "id": rec["id"],
            "name": rec.get(name_f) or "",
            "work_phone": rec.get(work_phone_f) or "",
            "mobile_phone": rec.get(mobile_phone_f) or "",
        }
        for rec in records
    ]
