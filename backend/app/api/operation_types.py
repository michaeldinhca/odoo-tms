import uuid
import xmlrpc.client
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user, get_db
from app.models.synced_operation_type import SyncedOperationType
from app.models.synced_picking import SyncedPicking
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


@router.get("", response_model=list[OperationTypeRead])
def list_operation_types(
    tenant_id: uuid.UUID,
    include_archived: bool = False,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[SyncedOperationType]:
    _require_same_tenant(tenant_id, current_user)
    query = db.query(SyncedOperationType).filter_by(tenant_id=tenant_id)
    if not include_archived:
        query = query.filter(SyncedOperationType.active.is_(True))
    return query.order_by(SyncedOperationType.name).all()


@router.post("/refresh/preview", response_model=OperationTypeRefreshPreview)
def preview_operation_types_refresh(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Dry-run — fetches from Odoo and diffs against local rows, writes
    nothing. The frontend shows this before letting the user confirm."""
    _require_same_tenant(tenant_id, current_user)
    credential = require_active_instance(db, tenant_id)
    fetched = _fetch_from_odoo(credential, db)
    return preview_operation_types(db, tenant_id, fetched)


@router.post("/refresh", response_model=list[OperationTypeRead])
def refresh_operation_types(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[SyncedOperationType]:
    _require_same_tenant(tenant_id, current_user)
    credential = require_active_instance(db, tenant_id)
    fetched = _fetch_from_odoo(credential, db)

    result = upsert_operation_types(db, tenant_id, fetched)
    credential.last_synced_operation_types_at = datetime.now(UTC)
    db.commit()
    return result


@router.put("/{operation_type_id}/sync", response_model=OperationTypeRead)
def set_operation_type_sync(
    tenant_id: uuid.UUID,
    operation_type_id: uuid.UUID,
    payload: OperationTypeSyncToggle,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> SyncedOperationType:
    _require_same_tenant(tenant_id, current_user)
    row = _get_operation_type_or_404(db, tenant_id, operation_type_id)

    row.is_synced = payload.is_synced
    db.commit()
    db.refresh(row)
    return row


@router.put("/{operation_type_id}/archive", response_model=OperationTypeRead)
def set_operation_type_active(
    tenant_id: uuid.UUID,
    operation_type_id: uuid.UUID,
    payload: ArchiveToggle,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> SyncedOperationType:
    _require_same_tenant(tenant_id, current_user)
    row = _get_operation_type_or_404(db, tenant_id, operation_type_id)

    row.active = payload.active
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{operation_type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_operation_type(
    tenant_id: uuid.UUID,
    operation_type_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
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
