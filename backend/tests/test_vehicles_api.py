"""Route handlers are plain functions — Depends() only matters when FastAPI
itself resolves them for a real HTTP request. Calling them directly with a
real (SQLite-backed) session and a constructed CurrentUser exercises the
actual CRUD/delete-guard/link logic without needing JWT/HTTP plumbing."""

import uuid

import pytest
from fastapi import HTTPException

from app.api.deps import CurrentUser
from app.api.vehicles import (
    create_vehicle,
    delete_vehicle,
    link_vehicle_to_odoo,
    list_vehicles,
    unlink_vehicle_from_odoo,
    update_vehicle,
)
from app.models.driver import Driver
from app.schemas.fleet import VehicleCreate, VehicleLinkOdoo, VehicleUpdate

TENANT_ID = uuid.uuid4()
USER = CurrentUser(user_id=uuid.uuid4(), tenant_id=TENANT_ID)


def _new_vehicle(session, **kwargs):
    kwargs.setdefault("name", "Truck 1")
    return create_vehicle(TENANT_ID, VehicleCreate(**kwargs), session, USER)


def test_create_and_list_vehicle(fleet_db_session):
    _new_vehicle(fleet_db_session, vehicle_type="truck")

    vehicles = list_vehicles(TENANT_ID, None, None, fleet_db_session, USER)

    assert len(vehicles) == 1
    assert vehicles[0].name == "Truck 1"
    assert vehicles[0].status == "active"  # default
    assert vehicles[0].odoo_link_status == "unlinked"  # default


def test_list_vehicles_filters_by_status(fleet_db_session):
    _new_vehicle(fleet_db_session, name="Active Van", status="active")
    _new_vehicle(fleet_db_session, name="Retired Van", status="inactive")

    active_only = list_vehicles(TENANT_ID, "active", None, fleet_db_session, USER)

    assert [v.name for v in active_only] == ["Active Van"]


def test_update_vehicle_only_changes_provided_fields(fleet_db_session):
    vehicle = _new_vehicle(fleet_db_session, vehicle_type="truck", payload_capacity_kg=1000.0)

    updated = update_vehicle(
        TENANT_ID, vehicle.id, VehicleUpdate(payload_capacity_kg=1500.0), fleet_db_session, USER
    )

    assert updated.payload_capacity_kg == 1500.0
    assert updated.name == "Truck 1"  # untouched
    assert updated.vehicle_type == "truck"  # untouched


def test_delete_vehicle_blocked_when_assigned_to_a_driver(fleet_db_session):
    vehicle = _new_vehicle(fleet_db_session)
    fleet_db_session.add(
        Driver(tenant_id=TENANT_ID, name="Alice", status="active", assigned_vehicle_id=vehicle.id)
    )
    fleet_db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        delete_vehicle(TENANT_ID, vehicle.id, fleet_db_session, USER)

    assert exc_info.value.status_code == 400


def test_delete_vehicle_succeeds_when_not_referenced(fleet_db_session):
    vehicle = _new_vehicle(fleet_db_session)

    delete_vehicle(TENANT_ID, vehicle.id, fleet_db_session, USER)

    assert list_vehicles(TENANT_ID, None, None, fleet_db_session, USER) == []


def test_link_vehicle_to_odoo_sets_link_fields_without_mutating_others(fleet_db_session):
    vehicle = _new_vehicle(fleet_db_session, vehicle_type="truck", payload_capacity_kg=1000.0)
    link_payload = VehicleLinkOdoo(odoo_fleet_vehicle_id=42)

    linked = link_vehicle_to_odoo(TENANT_ID, vehicle.id, link_payload, fleet_db_session, USER)

    assert linked.odoo_fleet_vehicle_id == 42
    assert linked.odoo_link_status == "linked"
    assert linked.name == "Truck 1"  # not overwritten
    assert linked.payload_capacity_kg == 1000.0  # not overwritten


def test_unlink_vehicle_from_odoo_clears_link_fields_only(fleet_db_session):
    vehicle = _new_vehicle(fleet_db_session)
    link_payload = VehicleLinkOdoo(odoo_fleet_vehicle_id=42)
    link_vehicle_to_odoo(TENANT_ID, vehicle.id, link_payload, fleet_db_session, USER)

    unlinked = unlink_vehicle_from_odoo(TENANT_ID, vehicle.id, fleet_db_session, USER)

    assert unlinked.odoo_fleet_vehicle_id is None
    assert unlinked.odoo_link_status == "unlinked"
    assert unlinked.name == "Truck 1"  # not overwritten


def test_vehicle_endpoints_reject_mismatched_tenant(fleet_db_session):
    vehicle = _new_vehicle(fleet_db_session)
    other_tenant_user = CurrentUser(user_id=uuid.uuid4(), tenant_id=uuid.uuid4())
    rename_payload = VehicleUpdate(name="Hijacked")

    with pytest.raises(HTTPException) as exc_info:
        update_vehicle(
            vehicle.tenant_id, vehicle.id, rename_payload, fleet_db_session, other_tenant_user
        )

    assert exc_info.value.status_code == 403
