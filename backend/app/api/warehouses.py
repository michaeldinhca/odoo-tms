import uuid
import xmlrpc.client

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user, get_db
from app.models.odoo_credential import TenantOdooCredential
from app.models.synced_warehouse import SyncedWarehouse
from app.schemas.sync_config import WarehouseRead, WarehouseSyncToggle
from app.services.odoo_client import OdooAuthError
from app.services.odoo_connection import build_client
from app.services.sync_config import fetch_warehouses, upsert_warehouses

router = APIRouter(prefix="/tenants/{tenant_id}/warehouses", tags=["warehouses"])

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


@router.get("", response_model=list[WarehouseRead])
def list_warehouses(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[SyncedWarehouse]:
    _require_same_tenant(tenant_id, current_user)
    return (
        db.query(SyncedWarehouse)
        .filter_by(tenant_id=tenant_id)
        .order_by(SyncedWarehouse.name)
        .all()
    )


@router.post("/refresh", response_model=list[WarehouseRead])
def refresh_warehouses(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[SyncedWarehouse]:
    _require_same_tenant(tenant_id, current_user)
    credential = _get_credential_or_404(db, tenant_id)
    client = build_client(credential)

    try:
        fetched = fetch_warehouses(
            client, company_id=credential.company_id, version_major=credential.server_version_major
        )
    except ODOO_ERRORS as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not fetch warehouses from Odoo: {exc}",
        ) from exc

    return upsert_warehouses(db, tenant_id, fetched)


@router.put("/{warehouse_id}/sync", response_model=WarehouseRead)
def set_warehouse_sync(
    tenant_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    payload: WarehouseSyncToggle,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> SyncedWarehouse:
    _require_same_tenant(tenant_id, current_user)
    row = db.query(SyncedWarehouse).filter_by(id=warehouse_id, tenant_id=tenant_id).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")

    row.is_synced = payload.is_synced
    db.commit()
    db.refresh(row)
    return row
