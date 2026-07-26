"""Route handlers called directly, same pattern as test_vehicles_api.py."""

import uuid

import pytest
from fastapi import HTTPException

from app.api.deps import CurrentUser
from app.api.warehouses import (
    add_warehouse_destination_location,
    delete_warehouse,
    list_warehouse_destination_locations,
    list_warehouses,
    preview_warehouses_refresh,
    refresh_warehouses,
    remove_warehouse_destination_location,
    set_warehouse_active,
    set_warehouse_coordinates,
)
from app.models.destination_location import DestinationLocation
from app.models.synced_picking import SyncedPicking
from app.models.vehicle import Vehicle
from app.schemas.destination_location import (
    WarehouseCoordinatesUpdate,
    WarehouseDestinationLocationCreate,
)
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


def _second_row(session):
    """upsert_warehouses returns every warehouse for the tenant (ordered by
    name), not just the one just upserted — filter explicitly rather than
    indexing, since "Main WH" sorts before "Second WH" and [0] would
    silently re-select warehouse_a."""
    rows = upsert_warehouses(session, TENANT_ID, [_warehouse(2, "Second WH")])
    return next(row for row in rows if row.odoo_warehouse_id == 2)


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


# --- coordinates + destination-location route set ---


def _destination(session, name="Acme Corp", lat=43.7, lng=-79.4) -> DestinationLocation:
    destination = DestinationLocation(
        tenant_id=TENANT_ID, name=name, lat=lat, lng=lng, street="", street2="", city="", state="",
        country="", zip="",
    )
    session.add(destination)
    session.commit()
    return destination


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


def test_add_destination_to_warehouse_route_set_computes_distance(sync_db_session):
    row = _new_row(sync_db_session)
    set_warehouse_coordinates(
        TENANT_ID,
        row.id,
        WarehouseCoordinatesUpdate(lat=43.6532, lng=-79.3832),
        sync_db_session,
        USER,
    )
    destination = _destination(sync_db_session, lat=43.7764, lng=-79.2318)  # ~18km away

    result = add_warehouse_destination_location(
        TENANT_ID,
        row.id,
        WarehouseDestinationLocationCreate(destination_location_id=destination.id),
        sync_db_session,
        USER,
    )

    assert result["destination"].id == destination.id
    assert result["distance_km"] is not None
    assert 15 < result["distance_km"] < 22


def test_distance_is_null_when_warehouse_has_no_coordinates(sync_db_session):
    row = _new_row(sync_db_session)  # coordinates never set
    destination = _destination(sync_db_session)

    result = add_warehouse_destination_location(
        TENANT_ID,
        row.id,
        WarehouseDestinationLocationCreate(destination_location_id=destination.id),
        sync_db_session,
        USER,
    )

    assert result["distance_km"] is None


def test_cannot_add_the_same_destination_to_a_warehouse_twice(sync_db_session):
    row = _new_row(sync_db_session)
    destination = _destination(sync_db_session)
    add_warehouse_destination_location(
        TENANT_ID,
        row.id,
        WarehouseDestinationLocationCreate(destination_location_id=destination.id),
        sync_db_session,
        USER,
    )

    with pytest.raises(HTTPException) as exc_info:
        add_warehouse_destination_location(
            TENANT_ID,
            row.id,
            WarehouseDestinationLocationCreate(destination_location_id=destination.id),
            sync_db_session,
            USER,
        )

    assert exc_info.value.status_code == 400


def test_same_destination_can_be_added_to_several_warehouses(sync_db_session):
    warehouse_a = _new_row(sync_db_session)
    warehouse_b = _second_row(sync_db_session)
    destination = _destination(sync_db_session)

    add_warehouse_destination_location(
        TENANT_ID,
        warehouse_a.id,
        WarehouseDestinationLocationCreate(destination_location_id=destination.id),
        sync_db_session,
        USER,
    )
    add_warehouse_destination_location(
        TENANT_ID,
        warehouse_b.id,
        WarehouseDestinationLocationCreate(destination_location_id=destination.id),
        sync_db_session,
        USER,
    )

    a_routes = list_warehouse_destination_locations(
        TENANT_ID, warehouse_a.id, sync_db_session, USER
    )
    b_routes = list_warehouse_destination_locations(
        TENANT_ID, warehouse_b.id, sync_db_session, USER
    )
    assert [r["destination"].id for r in a_routes] == [destination.id]
    assert [r["destination"].id for r in b_routes] == [destination.id]


def test_remove_destination_from_warehouse_route_set(sync_db_session):
    row = _new_row(sync_db_session)
    destination = _destination(sync_db_session)
    add_warehouse_destination_location(
        TENANT_ID,
        row.id,
        WarehouseDestinationLocationCreate(destination_location_id=destination.id),
        sync_db_session,
        USER,
    )

    remove_warehouse_destination_location(TENANT_ID, row.id, destination.id, sync_db_session, USER)

    assert list_warehouse_destination_locations(TENANT_ID, row.id, sync_db_session, USER) == []


def test_removing_from_one_warehouse_does_not_affect_another(sync_db_session):
    warehouse_a = _new_row(sync_db_session)
    warehouse_b = _second_row(sync_db_session)
    destination = _destination(sync_db_session)
    for warehouse in (warehouse_a, warehouse_b):
        add_warehouse_destination_location(
            TENANT_ID,
            warehouse.id,
            WarehouseDestinationLocationCreate(destination_location_id=destination.id),
            sync_db_session,
            USER,
        )

    remove_warehouse_destination_location(
        TENANT_ID, warehouse_a.id, destination.id, sync_db_session, USER
    )

    a_routes = list_warehouse_destination_locations(
        TENANT_ID, warehouse_a.id, sync_db_session, USER
    )
    b_routes = list_warehouse_destination_locations(
        TENANT_ID, warehouse_b.id, sync_db_session, USER
    )
    assert a_routes == []
    assert len(b_routes) == 1


def test_deleting_warehouse_cleans_up_its_route_set(sync_db_session):
    row = _new_row(sync_db_session)
    destination = _destination(sync_db_session)
    add_warehouse_destination_location(
        TENANT_ID,
        row.id,
        WarehouseDestinationLocationCreate(destination_location_id=destination.id),
        sync_db_session,
        USER,
    )

    delete_warehouse(TENANT_ID, row.id, sync_db_session, USER)

    # The destination itself survives — only the association is gone.
    from app.api.destination_locations import list_destination_locations

    assert [d.id for d in list_destination_locations(TENANT_ID, sync_db_session, USER)] == [
        destination.id
    ]
