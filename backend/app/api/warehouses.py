import uuid
import xmlrpc.client
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_db, require_permission
from app.models.destination_location import DestinationLocation, WarehouseDestinationLocation
from app.models.synced_picking import SyncedPicking
from app.models.synced_warehouse import SyncedWarehouse
from app.models.vehicle import Vehicle
from app.schemas.destination_location import (
    WarehouseCoordinatesUpdate,
    WarehouseDestinationLocationCreate,
    WarehouseDestinationLocationRead,
)
from app.schemas.sync_config import (
    ArchiveToggle,
    WarehouseRead,
    WarehouseRefreshPreview,
    WarehouseSyncToggle,
)
from app.services.destination_locations import distance_km
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

    db.query(WarehouseDestinationLocation).filter_by(
        tenant_id=tenant_id, warehouse_id=row.id
    ).delete()
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
    docstring) — needed for distance-to-destination on the route-set
    endpoints below."""
    _require_same_tenant(tenant_id, current_user)
    row = _get_warehouse_or_404(db, tenant_id, warehouse_id)

    row.lat = payload.lat
    row.lng = payload.lng
    db.commit()
    db.refresh(row)
    return row


@router.get(
    "/{warehouse_id}/destination-locations",
    response_model=list[WarehouseDestinationLocationRead],
)
def list_warehouse_destination_locations(
    tenant_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("can_manage_warehouses")),
) -> list[dict]:
    """This warehouse's route set — every destination attached to it,
    each with the distance from this warehouse (null if the warehouse has
    no coordinates set yet — see PUT .../coordinates)."""
    _require_same_tenant(tenant_id, current_user)
    warehouse = _get_warehouse_or_404(db, tenant_id, warehouse_id)

    rows = (
        db.query(WarehouseDestinationLocation, DestinationLocation)
        .join(
            DestinationLocation,
            WarehouseDestinationLocation.destination_location_id == DestinationLocation.id,
        )
        .filter(
            WarehouseDestinationLocation.tenant_id == tenant_id,
            WarehouseDestinationLocation.warehouse_id == warehouse.id,
        )
        .order_by(DestinationLocation.name)
        .all()
    )
    return [
        {
            "id": assoc.id,
            "destination": destination,
            "distance_km": distance_km(warehouse, destination),
            "created_at": assoc.created_at,
        }
        for assoc, destination in rows
    ]


@router.post(
    "/{warehouse_id}/destination-locations",
    response_model=WarehouseDestinationLocationRead,
    status_code=status.HTTP_201_CREATED,
)
def add_warehouse_destination_location(
    tenant_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    payload: WarehouseDestinationLocationCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("can_manage_warehouses")),
) -> dict:
    """Adds a destination to this warehouse's route set. The same
    destination can be added to any number of other warehouses too — this
    only creates one join row, it doesn't move or copy the destination."""
    _require_same_tenant(tenant_id, current_user)
    warehouse = _get_warehouse_or_404(db, tenant_id, warehouse_id)

    destination = (
        db.query(DestinationLocation)
        .filter_by(id=payload.destination_location_id, tenant_id=tenant_id)
        .first()
    )
    if destination is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Destination not found")

    existing = (
        db.query(WarehouseDestinationLocation)
        .filter_by(warehouse_id=warehouse.id, destination_location_id=destination.id)
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This destination is already in the warehouse's route set",
        )

    association = WarehouseDestinationLocation(
        tenant_id=tenant_id, warehouse_id=warehouse.id, destination_location_id=destination.id
    )
    db.add(association)
    db.commit()
    db.refresh(association)

    return {
        "id": association.id,
        "destination": destination,
        "distance_km": distance_km(warehouse, destination),
        "created_at": association.created_at,
    }


@router.delete(
    "/{warehouse_id}/destination-locations/{destination_location_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_warehouse_destination_location(
    tenant_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    destination_location_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("can_manage_warehouses")),
) -> None:
    """Removes the destination from this warehouse's route set only — the
    `DestinationLocation` itself, and its presence in any other
    warehouse's route set, is untouched."""
    _require_same_tenant(tenant_id, current_user)
    warehouse = _get_warehouse_or_404(db, tenant_id, warehouse_id)

    association = (
        db.query(WarehouseDestinationLocation)
        .filter_by(warehouse_id=warehouse.id, destination_location_id=destination_location_id)
        .first()
    )
    if association is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Destination is not in this warehouse's route set",
        )

    db.delete(association)
    db.commit()
