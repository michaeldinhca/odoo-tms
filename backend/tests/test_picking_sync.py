import uuid

from app.models.synced_picking import SyncedPicking
from app.services.picking_sync import upsert_synced_pickings
from app.services.planning.ffd import Address, Order

TENANT_ID = uuid.uuid4()


def _order(picking_id: int, **overrides) -> Order:
    defaults = dict(
        picking_id=picking_id,
        weight_kg=10.0,
        volume_m3=0.0,
        lat=0.0,
        lon=0.0,
        customer_name="Acme Corp",
        items_summary="Widget x1",
        address=Address(street="1 Main St", city="Toronto"),
        state="assigned",
        origin="SO0001",
        shipping_weight=11.0,
        note="fragile",
    )
    defaults.update(overrides)
    return Order(**defaults)


def test_upsert_synced_pickings_creates_new_rows(sync_db_session):
    upsert_synced_pickings(sync_db_session, TENANT_ID, [_order(101)])

    rows = sync_db_session.query(SyncedPicking).filter_by(tenant_id=TENANT_ID).all()
    assert len(rows) == 1
    assert rows[0].odoo_picking_id == 101
    assert rows[0].customer_name == "Acme Corp"
    assert rows[0].street == "1 Main St"
    assert rows[0].origin == "SO0001"
    assert rows[0].shipping_weight == 11.0


def test_upsert_synced_pickings_updates_existing_row_in_place(sync_db_session):
    upsert_synced_pickings(sync_db_session, TENANT_ID, [_order(101, customer_name="Old Name")])
    upsert_synced_pickings(sync_db_session, TENANT_ID, [_order(101, customer_name="New Name")])

    rows = sync_db_session.query(SyncedPicking).filter_by(tenant_id=TENANT_ID).all()
    assert len(rows) == 1  # no duplicate row
    assert rows[0].customer_name == "New Name"


def test_upsert_synced_pickings_stores_unassigned_orders_too(sync_db_session):
    # picking_sync doesn't know/care whether FFD assigned an order to a
    # vehicle — every fetched order gets persisted locally.
    upsert_synced_pickings(sync_db_session, TENANT_ID, [_order(101), _order(102)])

    rows = sync_db_session.query(SyncedPicking).filter_by(tenant_id=TENANT_ID).all()
    assert {r.odoo_picking_id for r in rows} == {101, 102}
