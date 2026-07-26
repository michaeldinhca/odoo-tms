"""Route handlers called directly, same pattern as test_vehicles_api.py."""

import uuid

import pytest
from fastapi import HTTPException

from app.api.deps import CurrentUser
from app.api.operation_types import (
    delete_operation_type,
    list_operation_types,
    preview_operation_types_refresh,
    refresh_operation_types,
    set_operation_type_active,
    set_operation_type_sync,
)
from app.api.warehouses import set_warehouse_sync
from app.models.synced_picking import SyncedPicking
from app.schemas.sync_config import ArchiveToggle, OperationTypeSyncToggle, WarehouseSyncToggle
from app.services.sync_config import upsert_operation_types, upsert_warehouses

TENANT_ID = uuid.uuid4()
USER = CurrentUser(user_id=uuid.uuid4(), tenant_id=TENANT_ID)


def _operation_type(odoo_id: int, name: str, warehouse_id: int | None = 1) -> dict:
    return {
        "odoo_operation_type_id": odoo_id,
        "name": name,
        "code": "outgoing",
        "warehouse_id": warehouse_id,
    }


def _synced_warehouse(session, odoo_id=1, name="Main WH"):
    """Operation types are scoped to synced warehouses (see DECISIONS.md)
    — most tests in this file need one to exist and be synced before an
    operation type belonging to it is visible at all."""
    rows = upsert_warehouses(
        session,
        TENANT_ID,
        [
            {
                "odoo_warehouse_id": odoo_id,
                "name": name,
                "code": "WH",
                "street": "",
                "street2": "",
                "city": "",
                "state_id": None,
                "state_name": "",
                "country_id": None,
                "country_name": "",
                "zip": "",
            }
        ],
    )
    warehouse = next(w for w in rows if w.odoo_warehouse_id == odoo_id)
    set_warehouse_sync(TENANT_ID, warehouse.id, WarehouseSyncToggle(is_synced=True), session, USER)
    return warehouse


def _new_row(session, warehouse_id=1):
    item = _operation_type(10, "Delivery Orders", warehouse_id)
    rows = upsert_operation_types(session, TENANT_ID, [item])
    return rows[0]


def test_list_excludes_archived_by_default(sync_db_session):
    _synced_warehouse(sync_db_session)
    row = _new_row(sync_db_session)
    set_operation_type_active(TENANT_ID, row.id, ArchiveToggle(active=False), sync_db_session, USER)

    default_list = list_operation_types(TENANT_ID, False, sync_db_session, USER)
    with_archived = list_operation_types(TENANT_ID, True, sync_db_session, USER)

    assert default_list == []
    assert [r["id"] for r in with_archived] == [row.id]
    assert with_archived[0]["active"] is False


def test_archive_toggle_round_trips(sync_db_session):
    _synced_warehouse(sync_db_session)
    row = _new_row(sync_db_session)

    archived = set_operation_type_active(
        TENANT_ID, row.id, ArchiveToggle(active=False), sync_db_session, USER
    )
    assert archived["active"] is False

    restored = set_operation_type_active(
        TENANT_ID, row.id, ArchiveToggle(active=True), sync_db_session, USER
    )
    assert restored["active"] is True


def test_refresh_blocked_when_connection_not_active(sync_db_session):
    with pytest.raises(HTTPException) as exc_info:
        refresh_operation_types(TENANT_ID, sync_db_session, USER)

    assert exc_info.value.status_code == 404  # no credential configured at all


def test_refresh_preview_blocked_when_connection_not_active(sync_db_session):
    with pytest.raises(HTTPException) as exc_info:
        preview_operation_types_refresh(TENANT_ID, sync_db_session, USER)

    assert exc_info.value.status_code == 404


def test_delete_blocked_when_referenced_by_a_synced_picking(sync_db_session):
    _synced_warehouse(sync_db_session)
    row = _new_row(sync_db_session)
    sync_db_session.add(
        SyncedPicking(
            tenant_id=TENANT_ID, odoo_picking_id=99, picking_type_id=row.odoo_operation_type_id
        )
    )
    sync_db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        delete_operation_type(TENANT_ID, row.id, sync_db_session, USER)

    assert exc_info.value.status_code == 400
    assert "archive" in exc_info.value.detail.lower()


def test_delete_succeeds_when_not_referenced(sync_db_session):
    _synced_warehouse(sync_db_session)
    row = _new_row(sync_db_session)

    delete_operation_type(TENANT_ID, row.id, sync_db_session, USER)

    assert list_operation_types(TENANT_ID, True, sync_db_session, USER) == []


# --- warehouse scoping (see DECISIONS.md "sync warehouse first") ---


def test_operation_type_hidden_when_its_warehouse_is_not_synced(sync_db_session):
    # Warehouse exists locally (upserted) but was never marked synced.
    upsert_warehouses(
        sync_db_session,
        TENANT_ID,
        [
            {
                "odoo_warehouse_id": 1,
                "name": "Main WH",
                "code": "WH",
                "street": "",
                "street2": "",
                "city": "",
                "state_id": None,
                "state_name": "",
                "country_id": None,
                "country_name": "",
                "zip": "",
            }
        ],
    )
    _new_row(sync_db_session, warehouse_id=1)

    assert list_operation_types(TENANT_ID, True, sync_db_session, USER) == []


def test_operation_type_with_no_warehouse_is_hidden(sync_db_session):
    _new_row(sync_db_session, warehouse_id=None)

    assert list_operation_types(TENANT_ID, True, sync_db_session, USER) == []


def test_operation_type_reappears_when_warehouse_synced_again(sync_db_session):
    warehouse = _synced_warehouse(sync_db_session)
    row = _new_row(sync_db_session)
    listed = list_operation_types(TENANT_ID, True, sync_db_session, USER)
    assert [r["id"] for r in listed] == [row.id]

    set_warehouse_sync(
        TENANT_ID, warehouse.id, WarehouseSyncToggle(is_synced=False), sync_db_session, USER
    )
    assert list_operation_types(TENANT_ID, True, sync_db_session, USER) == []

    set_warehouse_sync(
        TENANT_ID, warehouse.id, WarehouseSyncToggle(is_synced=True), sync_db_session, USER
    )
    listed = list_operation_types(TENANT_ID, True, sync_db_session, USER)
    assert [r["id"] for r in listed] == [row.id]


def test_warehouse_name_resolved_on_list_and_toggle(sync_db_session):
    _synced_warehouse(sync_db_session, odoo_id=1, name="Main WH")
    row = _new_row(sync_db_session, warehouse_id=1)

    listed = list_operation_types(TENANT_ID, True, sync_db_session, USER)
    assert listed[0]["warehouse_name"] == "Main WH"

    toggled = set_operation_type_sync(
        TENANT_ID, row.id, OperationTypeSyncToggle(is_synced=True), sync_db_session, USER
    )
    assert toggled["warehouse_name"] == "Main WH"


def test_two_warehouses_each_only_show_their_own_operation_types(sync_db_session):
    _synced_warehouse(sync_db_session, odoo_id=1, name="WH A")
    _synced_warehouse(sync_db_session, odoo_id=2, name="WH B")
    upsert_operation_types(
        sync_db_session,
        TENANT_ID,
        [
            _operation_type(10, "A Deliveries", warehouse_id=1),
            _operation_type(11, "B Deliveries", warehouse_id=2),
        ],
    )

    listed = list_operation_types(TENANT_ID, True, sync_db_session, USER)
    by_name = {r["name"]: r["warehouse_name"] for r in listed}
    assert by_name == {"A Deliveries": "WH A", "B Deliveries": "WH B"}
