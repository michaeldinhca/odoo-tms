import uuid
import xmlrpc.client
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_db, require_permission
from app.models.synced_picking import SyncedPicking
from app.models.synced_warehouse import SyncedWarehouse
from app.models.vehicle import Vehicle
from app.models.warehouse_route import RouteStop, WarehouseRoute
from app.schemas.destination_location import WarehouseCoordinatesUpdate
from app.schemas.sync_config import (
    ArchiveToggle,
    WarehouseRead,
    WarehouseRefreshPreview,
    WarehouseSyncToggle,
)
from app.services.odoo_client import OdooAuthError
from app.services.odoo_connection import build_client
from app.services.odoo_credential_gate import require_active_instance
from app.services.sync_config import fetch_warehouses, preview_warehouses, upsert_warehouses

router = APIRouter(prefix="/tenants/{tenant_id}/warehouses", tags=["warehouses"])

ODOO_ERRORS = (OdooAuthError, xmlrpc.client.Fault, OSError)


def _require_same_tenant(tenant_id: uuid.UUID, current_user: CurrentUser) -> None:
    if tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch")


def _get_warehouse_or_404(
    db: Session, tenant_id: uuid.UUID, warehouse_id: uuid.UUID
) -> SyncedWarehouse:
    row = db.query(SyncedWarehouse).filter_by(id=warehouse_id, tenant_id=tenant_id).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")
    return row


def _fetch_from_odoo(credential, db: Session) -> list[dict]:
    client = build_client(credential)
    try:
        return fetch_warehouses(
            client, company_id=credential.company_id, version_major=credential.server_version_major
        )
    except ODOO_ERRORS as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not fetch warehouses from Odoo: {exc}",
        ) from exc


@router.get("", response_model=list[WarehouseRead])
def list_warehouses(
    tenant_id: uuid.UUID,
    include_archived: bool = False,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("can_manage_warehouses")),
) -> list[SyncedWarehouse]:
    _require_same_tenant(tenant_id, current_user)
    query = db.query(SyncedWarehouse).filter_by(tenant_id=tenant_id)
    if not include_archived:
        query = query.filter(SyncedWarehouse.active.is_(True))
    return query.order_by(SyncedWarehouse.name).all()


@router.post("/refresh/preview", response_model=WarehouseRefreshPreview)
def preview_warehouses_refresh(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("can_manage_warehouses")),
) -> dict:
    """Dry-run — fetches from Odoo and diffs against local rows, writes
    nothing. The frontend shows this before letting the user confirm."""
    _require_same_tenant(tenant_id, current_user)
    credential = require_active_instance(db, tenant_id)
    fetched = _fetch_from_odoo(credential, db)
    return preview_warehouses(db, tenant_id, fetched)


@router.post("/refresh", response_model=list[WarehouseRead])
def refresh_warehouses(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("can_manage_warehouses")),
) -> list[SyncedWarehouse]:
    _require_same_tenant(tenant_id, current_user)
    credential = require_active_instance(db, tenant_id)
    fetched = _fetch_from_odoo(credential, db)

    result = upsert_warehouses(db, tenant_id, fetched)
    credential.last_synced_warehouses_at = datetime.now(UTC)
    db.commit()
    return result


@router.put("/{warehouse_id}/sync", response_model=WarehouseRead)
def set_warehouse_sync(
    tenant_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    payload: WarehouseSyncToggle,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("can_manage_warehouses")),
) -> SyncedWarehouse:
    _require_same_tenant(tenant_id, current_user)
    row = _get_warehouse_or_404(db, tenant_id, warehouse_id)

    row.is_synced = payload.is_synced
    db.commit()
    db.refresh(row)
    return row


@router.put("/{warehouse_id}/archive", response_model=WarehouseRead)
def set_warehouse_active(
    tenant_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    payload: ArchiveToggle,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("can_manage_warehouses")),
) -> SyncedWarehouse:
    _require_same_tenant(tenant_id, current_user)
    row = _get_warehouse_or_404(db, tenant_id, warehouse_id)

    row.active = payload.active
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{warehouse_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_warehouse(
    tenant_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("can_manage_warehouses")),
) -> None:
    _require_same_tenant(tenant_id, current_user)
    row = _get_warehouse_or_404(db, tenant_id, warehouse_id)

    referencing_vehicle = db.query(Vehicle).filter_by(home_warehouse_id=row.id).first()
    if referencing_vehicle is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Warehouse is the home warehouse for vehicle '{referencing_vehicle.name}'; "
                "archive it instead of deleting"
            ),
        )

    referencing_picking = (
        db.query(SyncedPicking)
        .filter_by(tenant_id=tenant_id, warehouse_id=row.odoo_warehouse_id)
        .first()
    )
    if referencing_picking is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Warehouse has synced pickings; archive it instead of deleting",
        )

    route_ids = [
        r_id
        for (r_id,) in db.query(WarehouseRoute.id)
        .filter_by(tenant_id=tenant_id, warehouse_id=row.id)
        .all()
    ]
    if route_ids:
        db.query(RouteStop).filter(RouteStop.route_id.in_(route_ids)).delete(
            synchronize_session=False
        )
        db.query(WarehouseRoute).filter(WarehouseRoute.id.in_(route_ids)).delete(
            synchronize_session=False
        )
    db.delete(row)
    db.commit()


@router.put("/{warehouse_id}/coordinates", response_model=WarehouseRead)
def set_warehouse_coordinates(
    tenant_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    payload: WarehouseCoordinatesUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("can_manage_warehouses")),
) -> SyncedWarehouse:
    """Admin-entered, not synced from Odoo (see SyncedWarehouse's
    docstring) — needed for distance-to-destination on this warehouse's
    routes (see app.api.warehouse_routes)."""
    _require_same_tenant(tenant_id, current_user)
    row = _get_warehouse_or_404(db, tenant_id, warehouse_id)

    row.lat = payload.lat
    row.lng = payload.lng
    db.commit()
    db.refresh(row)
    return row
