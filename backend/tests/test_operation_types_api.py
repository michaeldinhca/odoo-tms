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
)
from app.models.synced_picking import SyncedPicking
from app.schemas.sync_config import ArchiveToggle
from app.services.sync_config import upsert_operation_types

TENANT_ID = uuid.uuid4()
USER = CurrentUser(user_id=uuid.uuid4(), tenant_id=TENANT_ID)


def _operation_type(odoo_id: int, name: str) -> dict:
    return {
        "odoo_operation_type_id": odoo_id,
        "name": name,
        "code": "outgoing",
        "warehouse_id": None,
    }


def _new_row(session):
    rows = upsert_operation_types(session, TENANT_ID, [_operation_type(10, "Delivery Orders")])
    return rows[0]


def test_list_excludes_archived_by_default(sync_db_session):
    row = _new_row(sync_db_session)
    set_operation_type_active(TENANT_ID, row.id, ArchiveToggle(active=False), sync_db_session, USER)

    default_list = list_operation_types(TENANT_ID, False, sync_db_session, USER)
    with_archived = list_operation_types(TENANT_ID, True, sync_db_session, USER)

    assert default_list == []
    assert [r.id for r in with_archived] == [row.id]
    assert with_archived[0].active is False


def test_archive_toggle_round_trips(sync_db_session):
    row = _new_row(sync_db_session)

    archived = set_operation_type_active(
        TENANT_ID, row.id, ArchiveToggle(active=False), sync_db_session, USER
    )
    assert archived.active is False

    restored = set_operation_type_active(
        TENANT_ID, row.id, ArchiveToggle(active=True), sync_db_session, USER
    )
    assert restored.active is True


def test_refresh_blocked_when_connection_not_active(sync_db_session):
    with pytest.raises(HTTPException) as exc_info:
        refresh_operation_types(TENANT_ID, sync_db_session, USER)

    assert exc_info.value.status_code == 404  # no credential configured at all


def test_refresh_preview_blocked_when_connection_not_active(sync_db_session):
    with pytest.raises(HTTPException) as exc_info:
        preview_operation_types_refresh(TENANT_ID, sync_db_session, USER)

    assert exc_info.value.status_code == 404


def test_delete_blocked_when_referenced_by_a_synced_picking(sync_db_session):
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
    row = _new_row(sync_db_session)

    delete_operation_type(TENANT_ID, row.id, sync_db_session, USER)

    assert list_operation_types(TENANT_ID, True, sync_db_session, USER) == []
