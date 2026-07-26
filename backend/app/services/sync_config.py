"""Operation-type and warehouse sync configuration.

Each "fetch_*" function is Odoo-only (testable against a fake client, no DB).
Each "upsert_*" function is DB-only (testable against a real SQLAlchemy
session, no Odoo) and implements the "new rows default is_synced=False,
existing rows keep whatever sync state the user already set" rule — refresh
must never silently flip a toggle the user set. See DECISIONS.md.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.synced_operation_type import SyncedOperationType
from app.models.synced_warehouse import SyncedWarehouse
from app.services.odoo_client import OdooClient
from app.services.odoo_field_resolution import resolve_required_field
from app.services.odoo_relational import rel_id, rel_name

_OPERATION_TYPE_MODEL = "stock.picking.type"
_WAREHOUSE_MODEL = "stock.warehouse"
_PARTNER_MODEL = "res.partner"


def fetch_operation_types(
    client: OdooClient, company_id: int | None = None, version_major: int | None = None
) -> list[dict]:
    name_f = resolve_required_field(_OPERATION_TYPE_MODEL, "name", version_major)
    code_f = resolve_required_field(_OPERATION_TYPE_MODEL, "code", version_major)
    warehouse_f = resolve_required_field(_OPERATION_TYPE_MODEL, "warehouse_id", version_major)

    records = client.search_read(
        _OPERATION_TYPE_MODEL,
        domain=[],
        fields=["id", name_f, code_f, warehouse_f],
        company_id=company_id,
    )
    return [
        {
            "odoo_operation_type_id": rec["id"],
            "name": rec.get(name_f) or "",
            "code": rec.get(code_f) or "",
            "warehouse_id": rel_id(rec.get(warehouse_f)),
        }
        for rec in records
    ]


def fetch_warehouses(
    client: OdooClient, company_id: int | None = None, version_major: int | None = None
) -> list[dict]:
    name_f = resolve_required_field(_WAREHOUSE_MODEL, "name", version_major)
    code_f = resolve_required_field(_WAREHOUSE_MODEL, "code", version_major)
    partner_f = resolve_required_field(_WAREHOUSE_MODEL, "partner_id", version_major)

    records = client.search_read(
        _WAREHOUSE_MODEL,
        domain=[],
        fields=["id", name_f, code_f, partner_f],
        company_id=company_id,
    )

    street_f = resolve_required_field(_PARTNER_MODEL, "street", version_major)
    street2_f = resolve_required_field(_PARTNER_MODEL, "street2", version_major)
    city_f = resolve_required_field(_PARTNER_MODEL, "city", version_major)
    state_f = resolve_required_field(_PARTNER_MODEL, "state_id", version_major)
    country_f = resolve_required_field(_PARTNER_MODEL, "country_id", version_major)
    zip_f = resolve_required_field(_PARTNER_MODEL, "zip", version_major)

    partner_ids = sorted({rel_id(rec.get(partner_f)) for rec in records if rec.get(partner_f)})
    partner_by_id: dict[int, dict] = {}
    if partner_ids:
        partner_records = client.search_read(
            _PARTNER_MODEL,
            domain=[["id", "in", partner_ids]],
            fields=["id", street_f, street2_f, city_f, state_f, country_f, zip_f],
            company_id=company_id,
        )
        partner_by_id = {p["id"]: p for p in partner_records}

    results = []
    for rec in records:
        partner_id = rel_id(rec.get(partner_f))
        partner = partner_by_id.get(partner_id) if partner_id is not None else None
        results.append(
            {
                "odoo_warehouse_id": rec["id"],
                "name": rec.get(name_f) or "",
                "code": rec.get(code_f) or "",
                "street": (partner or {}).get(street_f) or "",
                "street2": (partner or {}).get(street2_f) or "",
                "city": (partner or {}).get(city_f) or "",
                "state_id": rel_id((partner or {}).get(state_f)),
                "state_name": rel_name((partner or {}).get(state_f)),
                "country_id": rel_id((partner or {}).get(country_f)),
                "country_name": rel_name((partner or {}).get(country_f)),
                "zip": (partner or {}).get(zip_f) or "",
            }
        )
    return results


def upsert_operation_types(
    db: Session, tenant_id: uuid.UUID, fetched: list[dict]
) -> list[SyncedOperationType]:
    now = datetime.now(UTC)
    for item in fetched:
        row = (
            db.query(SyncedOperationType)
            .filter_by(tenant_id=tenant_id, odoo_operation_type_id=item["odoo_operation_type_id"])
            .first()
        )
        if row is None:
            row = SyncedOperationType(
                tenant_id=tenant_id,
                odoo_operation_type_id=item["odoo_operation_type_id"],
                is_synced=False,
            )
            db.add(row)
        # is_synced is intentionally left untouched for existing rows.
        row.name = item["name"]
        row.code = item["code"]
        row.warehouse_id = item["warehouse_id"]
        row.last_seen_at = now
        row.updated_at = now
    db.commit()
    return (
        db.query(SyncedOperationType)
        .filter_by(tenant_id=tenant_id)
        .order_by(SyncedOperationType.name)
        .all()
    )


def upsert_warehouses(
    db: Session, tenant_id: uuid.UUID, fetched: list[dict]
) -> list[SyncedWarehouse]:
    now = datetime.now(UTC)
    for item in fetched:
        row = (
            db.query(SyncedWarehouse)
            .filter_by(tenant_id=tenant_id, odoo_warehouse_id=item["odoo_warehouse_id"])
            .first()
        )
        if row is None:
            row = SyncedWarehouse(
                tenant_id=tenant_id,
                odoo_warehouse_id=item["odoo_warehouse_id"],
                is_synced=False,
            )
            db.add(row)
        # is_synced is intentionally left untouched for existing rows.
        row.name = item["name"]
        row.code = item["code"]
        row.street = item["street"]
        row.street2 = item["street2"]
        row.city = item["city"]
        row.state_id = item["state_id"]
        row.state_name = item["state_name"]
        row.country_id = item["country_id"]
        row.country_name = item["country_name"]
        row.zip = item["zip"]
        row.last_seen_at = now
        row.updated_at = now
    db.commit()
    return (
        db.query(SyncedWarehouse)
        .filter_by(tenant_id=tenant_id)
        .order_by(SyncedWarehouse.name)
        .all()
    )


def preview_operation_types(db: Session, tenant_id: uuid.UUID, fetched: list[dict]) -> dict:
    """Dry-run diff against what's currently stored — writes nothing. Used to
    show "N new, M no longer in Odoo" before a resync is confirmed."""
    existing = db.query(SyncedOperationType).filter_by(tenant_id=tenant_id).all()
    existing_ids = {row.odoo_operation_type_id for row in existing}
    fetched_ids = {item["odoo_operation_type_id"] for item in fetched}

    new_items = [item for item in fetched if item["odoo_operation_type_id"] not in existing_ids]
    removed_items = [
        {
            "odoo_operation_type_id": row.odoo_operation_type_id,
            "name": row.name,
            "code": row.code,
        }
        for row in existing
        if row.odoo_operation_type_id not in fetched_ids
    ]
    return {
        "new": new_items,
        "removed": removed_items,
        "unchanged_count": len(fetched_ids & existing_ids),
    }


def preview_warehouses(db: Session, tenant_id: uuid.UUID, fetched: list[dict]) -> dict:
    """Same idea as preview_operation_types, for warehouses."""
    existing = db.query(SyncedWarehouse).filter_by(tenant_id=tenant_id).all()
    existing_ids = {row.odoo_warehouse_id for row in existing}
    fetched_ids = {item["odoo_warehouse_id"] for item in fetched}

    new_items = [item for item in fetched if item["odoo_warehouse_id"] not in existing_ids]
    removed_items = [
        {"odoo_warehouse_id": row.odoo_warehouse_id, "name": row.name, "code": row.code}
        for row in existing
        if row.odoo_warehouse_id not in fetched_ids
    ]
    return {
        "new": new_items,
        "removed": removed_items,
        "unchanged_count": len(fetched_ids & existing_ids),
    }


def get_synced_operation_type_ids(db: Session, tenant_id: uuid.UUID) -> set[int]:
    """The set of Odoo picking_type ids the tenant has opted into syncing."""
    rows = (
        db.query(SyncedOperationType.odoo_operation_type_id)
        .filter_by(tenant_id=tenant_id, is_synced=True)
        .all()
    )
    return {row[0] for row in rows}


def get_synced_warehouse_odoo_ids(db: Session, tenant_id: uuid.UUID) -> set[int]:
    """The set of Odoo warehouse ids the tenant has opted into syncing —
    operation types are scoped to these (see app.api.operation_types):
    a warehouse must be synced before its operation types are even
    visible to manage, let alone synced themselves."""
    rows = (
        db.query(SyncedWarehouse.odoo_warehouse_id)
        .filter_by(tenant_id=tenant_id, is_synced=True)
        .all()
    )
    return {row[0] for row in rows}


def get_warehouse_by_picking_type(db: Session, tenant_id: uuid.UUID) -> dict[int, dict]:
    """Maps Odoo picking_type id -> {warehouse_id, warehouse_name}, joining
    synced_operation_types.warehouse_id against synced_warehouses locally
    (no extra Odoo round trip)."""
    operation_types = db.query(SyncedOperationType).filter_by(tenant_id=tenant_id).all()
    warehouses = db.query(SyncedWarehouse).filter_by(tenant_id=tenant_id).all()
    warehouse_by_odoo_id = {w.odoo_warehouse_id: w for w in warehouses}

    result: dict[int, dict] = {}
    for operation_type in operation_types:
        if operation_type.warehouse_id is None:
            continue
        warehouse = warehouse_by_odoo_id.get(operation_type.warehouse_id)
        result[operation_type.odoo_operation_type_id] = {
            "warehouse_id": operation_type.warehouse_id,
            "warehouse_name": warehouse.name if warehouse else "",
        }
    return result
