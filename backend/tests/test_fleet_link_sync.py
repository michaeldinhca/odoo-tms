import uuid

from app.models.vehicle import Vehicle
from app.services.fleet_link_sync import sync_link_staleness

TENANT_ID = uuid.uuid4()


def _linked_vehicle(session, odoo_id, link_status="linked"):
    vehicle = Vehicle(
        tenant_id=TENANT_ID,
        name="Truck 1",
        odoo_fleet_vehicle_id=odoo_id,
        odoo_link_status=link_status,
    )
    session.add(vehicle)
    session.commit()
    session.refresh(vehicle)
    return vehicle


def test_linked_vehicle_missing_from_odoo_becomes_stale(fleet_db_session):
    vehicle = _linked_vehicle(fleet_db_session, odoo_id=42)

    sync_link_staleness(fleet_db_session, TENANT_ID, Vehicle, "odoo_fleet_vehicle_id", set())

    fleet_db_session.refresh(vehicle)
    assert vehicle.odoo_link_status == "stale"
    assert vehicle.odoo_fleet_vehicle_id == 42  # reference kept, not cleared


def test_stale_vehicle_reappearing_in_odoo_self_heals_to_linked(fleet_db_session):
    vehicle = _linked_vehicle(fleet_db_session, odoo_id=42, link_status="stale")

    sync_link_staleness(fleet_db_session, TENANT_ID, Vehicle, "odoo_fleet_vehicle_id", {42})

    fleet_db_session.refresh(vehicle)
    assert vehicle.odoo_link_status == "linked"


def test_linked_vehicle_present_in_odoo_stays_linked(fleet_db_session):
    vehicle = _linked_vehicle(fleet_db_session, odoo_id=42)

    sync_link_staleness(fleet_db_session, TENANT_ID, Vehicle, "odoo_fleet_vehicle_id", {42, 99})

    fleet_db_session.refresh(vehicle)
    assert vehicle.odoo_link_status == "linked"


def test_unlinked_vehicle_is_never_touched(fleet_db_session):
    vehicle = Vehicle(tenant_id=TENANT_ID, name="Truck 2", odoo_link_status="unlinked")
    fleet_db_session.add(vehicle)
    fleet_db_session.commit()
    fleet_db_session.refresh(vehicle)

    sync_link_staleness(fleet_db_session, TENANT_ID, Vehicle, "odoo_fleet_vehicle_id", set())

    fleet_db_session.refresh(vehicle)
    assert vehicle.odoo_link_status == "unlinked"
