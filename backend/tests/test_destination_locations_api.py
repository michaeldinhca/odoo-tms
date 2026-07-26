"""Route handlers called directly, same pattern as test_vehicles_api.py."""

import uuid

import pytest
from fastapi import HTTPException

from app.api.deps import CurrentUser
from app.api.destination_locations import (
    create_destination_location,
    delete_destination_location,
    list_destination_locations,
    update_destination_location,
)
from app.api.warehouses import (
    add_warehouse_destination_location,
    list_warehouse_destination_locations,
)
from app.schemas.destination_location import (
    DestinationLocationCreate,
    DestinationLocationUpdate,
    WarehouseDestinationLocationCreate,
)
from app.services.sync_config import upsert_warehouses

TENANT_ID = uuid.uuid4()
USER = CurrentUser(user_id=uuid.uuid4(), tenant_id=TENANT_ID)


def _new_destination(session, **overrides):
    defaults = {"name": "Acme Corp", "lat": 43.7, "lng": -79.4}
    defaults.update(overrides)
    return create_destination_location(
        TENANT_ID, DestinationLocationCreate(**defaults), session, USER
    )


def _new_warehouse(session, odoo_id=1, name="Main WH"):
    return upsert_warehouses(
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
    )[0]


def test_create_and_list_destination_location(sync_db_session):
    _new_destination(sync_db_session, name="Acme Corp", city="Toronto")

    locations = list_destination_locations(TENANT_ID, sync_db_session, USER)

    assert len(locations) == 1
    assert locations[0].name == "Acme Corp"
    assert locations[0].city == "Toronto"


def test_update_destination_location_partial(sync_db_session):
    destination = _new_destination(sync_db_session, name="Old Name")

    updated = update_destination_location(
        TENANT_ID, destination.id, DestinationLocationUpdate(name="New Name"), sync_db_session, USER
    )

    assert updated.name == "New Name"
    assert updated.lat == destination.lat  # untouched


def test_delete_destination_location(sync_db_session):
    destination = _new_destination(sync_db_session)

    delete_destination_location(TENANT_ID, destination.id, sync_db_session, USER)

    assert list_destination_locations(TENANT_ID, sync_db_session, USER) == []


def test_deleting_destination_location_removes_it_from_every_warehouse_route_set(sync_db_session):
    destination = _new_destination(sync_db_session)
    warehouse = _new_warehouse(sync_db_session)
    add_warehouse_destination_location(
        TENANT_ID,
        warehouse.id,
        WarehouseDestinationLocationCreate(destination_location_id=destination.id),
        sync_db_session,
        USER,
    )

    delete_destination_location(TENANT_ID, destination.id, sync_db_session, USER)

    remaining = list_warehouse_destination_locations(TENANT_ID, warehouse.id, sync_db_session, USER)
    assert remaining == []


def test_destination_location_endpoints_reject_mismatched_tenant(sync_db_session):
    destination = _new_destination(sync_db_session)
    other_tenant_user = CurrentUser(user_id=uuid.uuid4(), tenant_id=uuid.uuid4())

    with pytest.raises(HTTPException) as exc_info:
        update_destination_location(
            TENANT_ID,
            destination.id,
            DestinationLocationUpdate(name="x"),
            sync_db_session,
            other_tenant_user,
        )

    assert exc_info.value.status_code == 403
