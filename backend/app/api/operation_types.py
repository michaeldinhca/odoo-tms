import uuid
import xmlrpc.client
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_db, require_permission
from app.models.synced_operation_type import SyncedOperationType
from app.models.synced_picking import SyncedPicking
from app.models.synced_warehouse import SyncedWarehouse
from app.schemas.sync_config import (
    ArchiveToggle,
    OperationTypeRead,
    OperationTypeRefreshPreview,
    OperationTypeSyncToggle,
)
from app.services.odoo_client import OdooAuthError
from app.services.odoo_connection import build_client
from app.services.odoo_credential_gate import require_active_instance
from app.services.sync_config import (
    fetch_operation_types,
    get_synced_warehouse_odoo_ids,
    preview_operation_types,
    upsert_operation_types,
)

router = APIRouter(prefix="/tenants/{tenant_id}/operation-types", tags=["operation-types"])

ODOO_ERRORS = (OdooAuthError, xmlrpc.client.Fault, OSError)


def _require_same_tenant(tenant_id: uuid.UUID, current_user: CurrentUser) -> None:
    if tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch")


def _get_operation_type_or_404(
    db: Session, tenant_id: uuid.UUID, operation_type_id: uuid.UUID
) -> SyncedOperationType:
    row = (
        db.query(SyncedOperationType)
        .filter_by(id=operation_type_id, tenant_id=tenant_id)
        .first()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Operation type not found"
        )
    return row


def _fetch_from_odoo(credential, db: Session) -> list[dict]:
    client = build_client(credential)
    try:
        return fetch_operation_types(
            client, company_id=credential.company_id, version_major=credential.server_version_major
        )
    except ODOO_ERRORS as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not fetch operation types from Odoo: {exc}",
        ) from exc


def _fetch_scoped_to_synced_warehouses(credential, db: Session, tenant_id: uuid.UUID) -> list[dict]:
    """A warehouse must be synced before its operation types are even
    visible to manage — see DECISIONS.md. Filtering happens here, not
    inside fetch_operation_types itself, so that function stays a pure
    Odoo-only fetch with no DB dependency (existing test-separation
    convention — see sync_config.py's module docstring)."""
    fetched = _fetch_from_odoo(credential, db)
    synced_warehouse_ids = get_synced_warehouse_odoo_ids(db, tenant_id)
    return [item for item in fetched if item["warehouse_id"] in synced_warehouse_ids]


def _serialize(row: SyncedOperationType, warehouse_name_by_id: dict[int, str]) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "odoo_operation_type_id": row.odoo_operation_type_id,
        "name": row.name,
        "code": row.code,
        "warehouse_id": row.warehouse_id,
        "warehouse_name": warehouse_name_by_id.get(row.warehouse_id) if row.warehouse_id else None,
        "is_synced": row.is_synced,
        "active": row.active,
        "last_seen_at": row.last_seen_at,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


@router.get("", response_model=list[OperationTypeRead])
def list_operation_types(
    tenant_id: uuid.UUID,
    include_archived: bool = False,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("can_manage_operation_types")),
) -> list[dict]:
    _require_same_tenant(tenant_id, current_user)
    synced_warehouse_ids = get_synced_warehouse_odoo_ids(db, tenant_id)
    warehouse_name_by_id = {
        w.odoo_warehouse_id: w.name
        for w in db.query(SyncedWarehouse).filter_by(tenant_id=tenant_id).all()
    }

    query = db.query(SyncedOperationType).filter_by(tenant_id=tenant_id)
    if not include_archived:
        query = query.filter(SyncedOperationType.active.is_(True))
    rows = query.order_by(SyncedOperationType.name).all()

    # Scoped to currently-synced warehouses, not deleted when a warehouse
    # is un-synced — a row for a since-un-synced warehouse just stops
    # appearing here until that warehouse is synced again (see
    # DECISIONS.md).
    return [
        _serialize(row, warehouse_name_by_id)
        for row in rows
        if row.warehouse_id in synced_warehouse_ids
    ]


@router.post("/refresh/preview", response_model=OperationTypeRefreshPreview)
def preview_operation_types_refresh(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("can_manage_operation_types")),
) -> dict:
    """Dry-run — fetches from Odoo (scoped to synced warehouses) and diffs
    against local rows, writes nothing. The frontend shows this before
    letting the user confirm."""
    _require_same_tenant(tenant_id, current_user)
    credential = require_active_instance(db, tenant_id)
    fetched = _fetch_scoped_to_synced_warehouses(credential, db, tenant_id)
    return preview_operation_types(db, tenant_id, fetched)


@router.post("/refresh", response_model=list[OperationTypeRead])
def refresh_operation_types(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("can_manage_operation_types")),
) -> list[dict]:
    _require_same_tenant(tenant_id, current_user)
    credential = require_active_instance(db, tenant_id)
    fetched = _fetch_scoped_to_synced_warehouses(credential, db, tenant_id)

    result = upsert_operation_types(db, tenant_id, fetched)
    credential.last_synced_operation_types_at = datetime.now(UTC)
    db.commit()

    warehouse_name_by_id = {
        w.odoo_warehouse_id: w.name
        for w in db.query(SyncedWarehouse).filter_by(tenant_id=tenant_id).all()
    }
    return [_serialize(row, warehouse_name_by_id) for row in result]


def _warehouse_name_for(
    db: Session, tenant_id: uuid.UUID, odoo_warehouse_id: int | None
) -> dict[int, str]:
    if odoo_warehouse_id is None:
        return {}
    warehouse = (
        db.query(SyncedWarehouse)
        .filter_by(tenant_id=tenant_id, odoo_warehouse_id=odoo_warehouse_id)
        .first()
    )
    return {odoo_warehouse_id: warehouse.name} if warehouse else {}


@router.put("/{operation_type_id}/sync", response_model=OperationTypeRead)
def set_operation_type_sync(
    tenant_id: uuid.UUID,
    operation_type_id: uuid.UUID,
    payload: OperationTypeSyncToggle,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("can_manage_operation_types")),
) -> dict:
    _require_same_tenant(tenant_id, current_user)
    row = _get_operation_type_or_404(db, tenant_id, operation_type_id)

    row.is_synced = payload.is_synced
    db.commit()
    db.refresh(row)
    return _serialize(row, _warehouse_name_for(db, tenant_id, row.warehouse_id))


@router.put("/{operation_type_id}/archive", response_model=OperationTypeRead)
def set_operation_type_active(
    tenant_id: uuid.UUID,
    operation_type_id: uuid.UUID,
    payload: ArchiveToggle,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("can_manage_operation_types")),
) -> dict:
    _require_same_tenant(tenant_id, current_user)
    row = _get_operation_type_or_404(db, tenant_id, operation_type_id)

    row.active = payload.active
    db.commit()
    db.refresh(row)
    return _serialize(row, _warehouse_name_for(db, tenant_id, row.warehouse_id))


@router.delete("/{operation_type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_operation_type(
    tenant_id: uuid.UUID,
    operation_type_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("can_manage_operation_types")),
) -> None:
    _require_same_tenant(tenant_id, current_user)
    row = _get_operation_type_or_404(db, tenant_id, operation_type_id)

    referencing_picking = (
        db.query(SyncedPicking)
        .filter_by(tenant_id=tenant_id, picking_type_id=row.odoo_operation_type_id)
        .first()
    )
    if referencing_picking is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Operation type has synced pickings; archive it instead of deleting",
        )

    db.delete(row)
    db.commit()
