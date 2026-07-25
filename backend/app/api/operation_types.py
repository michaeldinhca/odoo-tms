import uuid
import xmlrpc.client

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user, get_db
from app.models.odoo_credential import TenantOdooCredential
from app.models.synced_operation_type import SyncedOperationType
from app.schemas.sync_config import OperationTypeRead, OperationTypeSyncToggle
from app.services.odoo_client import OdooAuthError
from app.services.odoo_connection import build_client
from app.services.sync_config import fetch_operation_types, upsert_operation_types

router = APIRouter(prefix="/tenants/{tenant_id}/operation-types", tags=["operation-types"])

ODOO_ERRORS = (OdooAuthError, xmlrpc.client.Fault, OSError)


def _require_same_tenant(tenant_id: uuid.UUID, current_user: CurrentUser) -> None:
    if tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch")


def _get_credential_or_404(db: Session, tenant_id: uuid.UUID) -> TenantOdooCredential:
    credential = (
        db.query(TenantOdooCredential).filter(TenantOdooCredential.tenant_id == tenant_id).first()
    )
    if credential is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No Odoo connection configured"
        )
    return credential


@router.get("", response_model=list[OperationTypeRead])
def list_operation_types(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[SyncedOperationType]:
    _require_same_tenant(tenant_id, current_user)
    return (
        db.query(SyncedOperationType)
        .filter_by(tenant_id=tenant_id)
        .order_by(SyncedOperationType.name)
        .all()
    )


@router.post("/refresh", response_model=list[OperationTypeRead])
def refresh_operation_types(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[SyncedOperationType]:
    _require_same_tenant(tenant_id, current_user)
    credential = _get_credential_or_404(db, tenant_id)
    client = build_client(credential)

    try:
        fetched = fetch_operation_types(
            client, company_id=credential.company_id, version_major=credential.server_version_major
        )
    except ODOO_ERRORS as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not fetch operation types from Odoo: {exc}",
        ) from exc

    return upsert_operation_types(db, tenant_id, fetched)


@router.put("/{operation_type_id}/sync", response_model=OperationTypeRead)
def set_operation_type_sync(
    tenant_id: uuid.UUID,
    operation_type_id: uuid.UUID,
    payload: OperationTypeSyncToggle,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> SyncedOperationType:
    _require_same_tenant(tenant_id, current_user)
    row = (
        db.query(SyncedOperationType)
        .filter_by(id=operation_type_id, tenant_id=tenant_id)
        .first()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Operation type not found"
        )

    row.is_synced = payload.is_synced
    db.commit()
    db.refresh(row)
    return row
