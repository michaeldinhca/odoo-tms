import uuid

import pytest
from fastapi import HTTPException

from app.api.deps import CurrentUser
from app.api.drivers import (
    create_driver,
    delete_driver,
    link_driver_to_odoo,
    list_drivers,
    unlink_driver_from_odoo,
    update_driver,
)
from app.models.odoo_credential import TenantOdooCredential
from app.schemas.fleet import DriverCreate, DriverLinkOdoo, DriverUpdate

TENANT_ID = uuid.uuid4()
USER = CurrentUser(user_id=uuid.uuid4(), tenant_id=TENANT_ID)


def _new_driver(session, **kwargs):
    kwargs.setdefault("name", "Alice")
    return create_driver(TENANT_ID, DriverCreate(**kwargs), session, USER)


def _active_credential(session):
    credential = TenantOdooCredential(
        tenant_id=TENANT_ID, url="https://x.odoo.com", db="x", username="u",
        encrypted_key="k", state="active",
    )
    session.add(credential)
    session.commit()
    return credential


def test_create_and_list_driver(fleet_db_session):
    _new_driver(fleet_db_session, phone="555-1234")

    drivers = list_drivers(TENANT_ID, None, False, fleet_db_session, USER)

    assert len(drivers) == 1
    assert drivers[0].name == "Alice"
    assert drivers[0].status == "active"  # default
    assert drivers[0].odoo_link_status == "unlinked"  # default


def test_list_drivers_filters_by_status(fleet_db_session):
    _new_driver(fleet_db_session, name="Alice", status="active")
    _new_driver(fleet_db_session, name="Bob", status="locked")

    locked_only = list_drivers(TENANT_ID, "locked", False, fleet_db_session, USER)

    assert [d.name for d in locked_only] == ["Bob"]


def test_update_driver_only_changes_provided_fields(fleet_db_session):
    driver = _new_driver(fleet_db_session, phone="555-1234")

    updated = update_driver(
        TENANT_ID, driver.id, DriverUpdate(phone="555-9999"), fleet_db_session, USER
    )

    assert updated.phone == "555-9999"
    assert updated.name == "Alice"  # untouched


def test_delete_driver_blocked_when_active(fleet_db_session):
    driver = _new_driver(fleet_db_session, status="active")

    with pytest.raises(HTTPException) as exc_info:
        delete_driver(TENANT_ID, driver.id, fleet_db_session, USER)

    assert exc_info.value.status_code == 400


def test_delete_driver_succeeds_when_inactive(fleet_db_session):
    driver = _new_driver(fleet_db_session, status="inactive")

    delete_driver(TENANT_ID, driver.id, fleet_db_session, USER)

    assert list_drivers(TENANT_ID, None, False, fleet_db_session, USER) == []


def test_link_driver_to_odoo_sets_link_fields_without_mutating_others(fleet_db_session):
    _active_credential(fleet_db_session)
    driver = _new_driver(fleet_db_session, phone="555-1234")
    link_payload = DriverLinkOdoo(odoo_employee_id=7)

    linked = link_driver_to_odoo(TENANT_ID, driver.id, link_payload, fleet_db_session, USER)

    assert linked.odoo_employee_id == 7
    assert linked.odoo_link_status == "linked"
    assert linked.name == "Alice"  # not overwritten
    assert linked.phone == "555-1234"  # not overwritten


def test_link_driver_to_odoo_blocked_when_connection_not_active(fleet_db_session):
    driver = _new_driver(fleet_db_session)
    link_payload = DriverLinkOdoo(odoo_employee_id=7)

    with pytest.raises(HTTPException) as exc_info:
        link_driver_to_odoo(TENANT_ID, driver.id, link_payload, fleet_db_session, USER)

    assert exc_info.value.status_code in (404, 409)  # no connection at all -> 404; draft -> 409


def test_unlink_driver_from_odoo_clears_link_fields_only(fleet_db_session):
    _active_credential(fleet_db_session)
    driver = _new_driver(fleet_db_session)
    link_payload = DriverLinkOdoo(odoo_employee_id=7)
    link_driver_to_odoo(TENANT_ID, driver.id, link_payload, fleet_db_session, USER)

    unlinked = unlink_driver_from_odoo(TENANT_ID, driver.id, fleet_db_session, USER)

    assert unlinked.odoo_employee_id is None
    assert unlinked.odoo_link_status == "unlinked"
    assert unlinked.name == "Alice"  # not overwritten


def test_archived_driver_hidden_from_default_list_but_visible_with_include_archived(
    fleet_db_session,
):
    driver = _new_driver(fleet_db_session)
    update_driver(TENANT_ID, driver.id, DriverUpdate(active=False), fleet_db_session, USER)

    default_list = list_drivers(TENANT_ID, None, False, fleet_db_session, USER)
    with_archived = list_drivers(TENANT_ID, None, True, fleet_db_session, USER)

    assert default_list == []
    assert [d.id for d in with_archived] == [driver.id]
    assert with_archived[0].active is False


def test_driver_endpoints_reject_mismatched_tenant(fleet_db_session):
    driver = _new_driver(fleet_db_session)
    other_tenant_user = CurrentUser(user_id=uuid.uuid4(), tenant_id=uuid.uuid4())
    rename_payload = DriverUpdate(name="Hijacked")

    with pytest.raises(HTTPException) as exc_info:
        update_driver(
            driver.tenant_id, driver.id, rename_payload, fleet_db_session, other_tenant_user
        )

    assert exc_info.value.status_code == 403
