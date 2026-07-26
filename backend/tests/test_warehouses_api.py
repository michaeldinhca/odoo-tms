"""Route handlers called directly, same pattern as test_vehicles_api.py."""

import uuid

import pytest
from fastapi import HTTPException

from app.api.deps import CurrentUser
from app.api.warehouses import (
    delete_warehouse,
    list_warehouses,
    preview_warehouses_refresh,
    refresh_warehouses,
    set_warehouse_active,
    set_warehouse_coordinates,
)
from app.models.synced_picking import SyncedPicking
from app.models.vehicle import Vehicle
from app.schemas.destination_location import WarehouseCoordinatesUpdate
from app.schemas.sync_config import ArchiveToggle
from app.services.sync_config import upsert_warehouses

TENANT_ID = uuid.uuid4()
USER = CurrentUser(user_id=uuid.uuid4(), tenant_id=TENANT_ID)


def _warehouse(odoo_id: int, name: str) -> dict:
    return {
        "odoo_warehouse_id": odoo_id,
        "name": name,
        "code": "WH",
        "street": "1 Depot Rd",
        "street2": "",
        "city": "Toronto",
        "state_id": None,
        "state_name": "",
        "country_id": None,
        "country_name": "",
        "zip": "",
    }


def _new_row(session):
    rows = upsert_warehouses(session, TENANT_ID, [_warehouse(1, "Main WH")])
    return rows[0]


def test_list_excludes_archived_by_default(sync_db_session):
    row = _new_row(sync_db_session)
    set_warehouse_active(TENANT_ID, row.id, ArchiveToggle(active=False), sync_db_session, USER)

    default_list = list_warehouses(TENANT_ID, False, sync_db_session, USER)
    with_archived = list_warehouses(TENANT_ID, True, sync_db_session, USER)

    assert default_list == []
    assert [r.id for r in with_archived] == [row.id]
    assert with_archived[0].active is False


def test_archive_toggle_round_trips(sync_db_session):
    row = _new_row(sync_db_session)

    archived = set_warehouse_active(
        TENANT_ID, row.id, ArchiveToggle(active=False), sync_db_session, USER
    )
    assert archived.active is False

    restored = set_warehouse_active(
        TENANT_ID, row.id, ArchiveToggle(active=True), sync_db_session, USER
    )
    assert restored.active is True


def test_refresh_blocked_when_connection_not_active(sync_db_session):
    with pytest.raises(HTTPException) as exc_info:
        refresh_warehouses(TENANT_ID, sync_db_session, USER)

    assert exc_info.value.status_code == 404  # no credential configured at all


def test_refresh_preview_blocked_when_connection_not_active(sync_db_session):
    with pytest.raises(HTTPException) as exc_info:
        preview_warehouses_refresh(TENANT_ID, sync_db_session, USER)

    assert exc_info.value.status_code == 404


def test_delete_blocked_when_a_vehicle_has_it_as_home_warehouse(sync_db_session):
    row = _new_row(sync_db_session)
    sync_db_session.add(Vehicle(tenant_id=TENANT_ID, name="Truck 1", home_warehouse_id=row.id))
    sync_db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        delete_warehouse(TENANT_ID, row.id, sync_db_session, USER)

    assert exc_info.value.status_code == 400
    assert "archive" in exc_info.value.detail.lower()


def test_delete_blocked_when_referenced_by_a_synced_picking(sync_db_session):
    row = _new_row(sync_db_session)
    sync_db_session.add(
        SyncedPicking(tenant_id=TENANT_ID, odoo_picking_id=99, warehouse_id=row.odoo_warehouse_id)
    )
    sync_db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        delete_warehouse(TENANT_ID, row.id, sync_db_session, USER)

    assert exc_info.value.status_code == 400


def test_delete_succeeds_when_not_referenced(sync_db_session):
    row = _new_row(sync_db_session)

    delete_warehouse(TENANT_ID, row.id, sync_db_session, USER)

    assert list_warehouses(TENANT_ID, True, sync_db_session, USER) == []


# --- coordinates ---


def test_set_warehouse_coordinates(sync_db_session):
    row = _new_row(sync_db_session)

    updated = set_warehouse_coordinates(
        TENANT_ID,
        row.id,
        WarehouseCoordinatesUpdate(lat=43.6532, lng=-79.3832),
        sync_db_session,
        USER,
    )

    assert updated.lat == 43.6532
    assert updated.lng == -79.3832


def test_warehouse_coordinates_can_be_cleared(sync_db_session):
    row = _new_row(sync_db_session)
    set_warehouse_coordinates(
        TENANT_ID, row.id, WarehouseCoordinatesUpdate(lat=1.0, lng=2.0), sync_db_session, USER
    )

    cleared = set_warehouse_coordinates(
        TENANT_ID, row.id, WarehouseCoordinatesUpdate(lat=None, lng=None), sync_db_session, USER
    )

    assert cleared.lat is None
    assert cleared.lng is None
