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
from app.services.odoo_relational import rel_id, rel_name


def fetch_operation_types(client: OdooClient, company_id: int | None = None) -> list[dict]:
    records = client.search_read(
        "stock.picking.type",
        domain=[],
        fields=["id", "name", "code", "warehouse_id"],
        company_id=company_id,
    )
    return [
        {
            "odoo_operation_type_id": rec["id"],
            "name": rec.get("name") or "",
            "code": rec.get("code") or "",
            "warehouse_id": rel_id(rec.get("warehouse_id")),
        }
        for rec in records
    ]


def fetch_warehouses(client: OdooClient, company_id: int | None = None) -> list[dict]:
    records = client.search_read(
        "stock.warehouse",
        domain=[],
        fields=["id", "name", "code", "partner_id"],
        company_id=company_id,
    )

    partner_ids = sorted(
        {rel_id(rec.get("partner_id")) for rec in records if rec.get("partner_id")}
    )
    partner_by_id: dict[int, dict] = {}
    if partner_ids:
        partner_records = client.search_read(
            "res.partner",
            domain=[["id", "in", partner_ids]],
            fields=["id", "street", "street2", "city", "state_id", "country_id", "zip"],
            company_id=company_id,
        )
        partner_by_id = {p["id"]: p for p in partner_records}

    results = []
    for rec in records:
        partner_id = rel_id(rec.get("partner_id"))
        partner = partner_by_id.get(partner_id) if partner_id is not None else None
        results.append(
            {
                "odoo_warehouse_id": rec["id"],
                "name": rec.get("name") or "",
                "code": rec.get("code") or "",
                "street": (partner or {}).get("street") or "",
                "street2": (partner or {}).get("street2") or "",
                "city": (partner or {}).get("city") or "",
                "state_id": rel_id((partner or {}).get("state_id")),
                "state_name": rel_name((partner or {}).get("state_id")),
                "country_id": rel_id((partner or {}).get("country_id")),
                "country_name": rel_name((partner or {}).get("country_id")),
                "zip": (partner or {}).get("zip") or "",
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


def get_synced_operation_type_ids(db: Session, tenant_id: uuid.UUID) -> set[int]:
    """The set of Odoo picking_type ids the tenant has opted into syncing."""
    rows = (
        db.query(SyncedOperationType.odoo_operation_type_id)
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
