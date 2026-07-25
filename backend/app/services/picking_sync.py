"""Persists the Order objects fetched during a planning run into
`synced_pickings` — the local, queryable mirror of a tenant's synced
stock.picking data. Every fetched order is upserted here regardless of
whether FFD assigned it to a vehicle or left it unassigned."""

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.synced_picking import SyncedPicking
from app.services.planning.ffd import Order


def upsert_synced_pickings(db: Session, tenant_id: uuid.UUID, orders: list[Order]) -> None:
    now = datetime.now(UTC)
    for order in orders:
        row = (
            db.query(SyncedPicking)
            .filter_by(tenant_id=tenant_id, odoo_picking_id=order.picking_id)
            .first()
        )
        if row is None:
            row = SyncedPicking(tenant_id=tenant_id, odoo_picking_id=order.picking_id)
            db.add(row)

        row.state = order.state
        row.customer_name = order.customer_name
        row.items_summary = order.items_summary
        row.street = order.address.street
        row.street2 = order.address.street2
        row.city = order.address.city
        row.state_id = order.address.state_id
        row.state_name = order.address.state_name
        row.country_id = order.address.country_id
        row.country_name = order.address.country_name
        row.zip = order.address.zip
        row.scheduled_date = order.scheduled_date
        row.picking_type_id = order.picking_type_id
        row.warehouse_id = order.warehouse_id
        row.warehouse_name = order.warehouse_name
        row.origin = order.origin
        row.weight = order.weight_kg
        row.shipping_weight = order.shipping_weight
        row.note = order.note
        row.last_seen_at = now
        row.updated_at = now
    db.commit()
