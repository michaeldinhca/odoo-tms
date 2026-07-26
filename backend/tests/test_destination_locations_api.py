"""Route handlers called directly, same pattern as test_vehicles_api.py."""

import uuid

import pytest
from fastapi import HTTPException

from app.api.deps import CurrentUser
from app.api.destination_locations import (
    create_destination_location,
    delete_destination_location,
    list_destination_locations,
    list_picking_address_options,
    update_destination_location,
)
from app.models.synced_picking import SyncedPicking
from app.schemas.destination_location import DestinationLocationCreate, DestinationLocationUpdate

TENANT_ID = uuid.uuid4()
USER = CurrentUser(user_id=uuid.uuid4(), tenant_id=TENANT_ID)


def _new_destination(session, **overrides):
    defaults = {"name": "Acme Corp", "lat": 43.7, "lng": -79.4}
    defaults.update(overrides)
    return create_destination_location(
        TENANT_ID, DestinationLocationCreate(**defaults), session, USER
    )


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


def _new_picking(session, **overrides):
    defaults = {
        "tenant_id": TENANT_ID,
        "odoo_picking_id": overrides.pop("odoo_picking_id", 1),
        "customer_name": "Acme Corp",
        "street": "1 Main St",
        "street2": "",
        "city": "Toronto",
        "state_name": "Ontario",
        "country_name": "Canada",
        "zip": "M1M 1M1",
    }
    defaults.update(overrides)
    picking = SyncedPicking(**defaults)
    session.add(picking)
    session.commit()
    return picking


def test_picking_addresses_dedupes_same_customer_and_address(sync_db_session):
    _new_picking(sync_db_session, odoo_picking_id=1)
    _new_picking(sync_db_session, odoo_picking_id=2)  # same customer/address
    _new_picking(sync_db_session, odoo_picking_id=3, customer_name="Different Co", city="Ottawa")

    options = list_picking_address_options(TENANT_ID, sync_db_session, USER)

    assert len(options) == 2
    names = {o["customer_name"] for o in options}
    assert names == {"Acme Corp", "Different Co"}


def test_picking_addresses_dedupe_ignores_case_and_whitespace(sync_db_session):
    _new_picking(sync_db_session, odoo_picking_id=1, customer_name="Acme Corp", city="Toronto")
    _new_picking(sync_db_session, odoo_picking_id=2, customer_name="  ACME CORP  ", city="TORONTO")

    options = list_picking_address_options(TENANT_ID, sync_db_session, USER)

    assert len(options) == 1


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
