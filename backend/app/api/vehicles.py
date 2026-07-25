import uuid
import xmlrpc.client

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user, get_db
from app.models.driver import Driver
from app.models.odoo_credential import TenantOdooCredential
from app.models.vehicle import Vehicle
from app.schemas.fleet import (
    OdooFleetVehicleList,
    VehicleCreate,
    VehicleLinkOdoo,
    VehicleRead,
    VehicleStatus,
    VehicleUpdate,
)
from app.services.fleet_link_sync import sync_link_staleness
from app.services.fleet_lookup import fetch_fleet_vehicles
from app.services.odoo_client import OdooAuthError
from app.services.odoo_connection import build_client

router = APIRouter(prefix="/tenants/{tenant_id}/vehicles", tags=["vehicles"])

ODOO_ERRORS = (OdooAuthError, xmlrpc.client.Fault, OSError)


def _require_same_tenant(tenant_id: uuid.UUID, current_user: CurrentUser) -> None:
    if tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch")


def _get_vehicle_or_404(db: Session, tenant_id: uuid.UUID, vehicle_id: uuid.UUID) -> Vehicle:
    vehicle = db.query(Vehicle).filter_by(id=vehicle_id, tenant_id=tenant_id).first()
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    return vehicle


@router.get("", response_model=list[VehicleRead])
def list_vehicles(
    tenant_id: uuid.UUID,
    status_filter: VehicleStatus | None = None,
    home_warehouse_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[Vehicle]:
    _require_same_tenant(tenant_id, current_user)
    query = db.query(Vehicle).filter_by(tenant_id=tenant_id)
    if status_filter is not None:
        query = query.filter(Vehicle.status == status_filter)
    if home_warehouse_id is not None:
        query = query.filter(Vehicle.home_warehouse_id == home_warehouse_id)
    return query.order_by(Vehicle.name).all()


@router.post("", response_model=VehicleRead, status_code=status.HTTP_201_CREATED)
def create_vehicle(
    tenant_id: uuid.UUID,
    payload: VehicleCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Vehicle:
    _require_same_tenant(tenant_id, current_user)
    vehicle = Vehicle(tenant_id=tenant_id, **payload.model_dump())
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle


@router.get("/odoo-fleet-vehicles", response_model=OdooFleetVehicleList)
def list_odoo_fleet_vehicles(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> OdooFleetVehicleList:
    """Browse-only — never auto-creates local vehicles from this list."""
    _require_same_tenant(tenant_id, current_user)
    credential = (
        db.query(TenantOdooCredential).filter(TenantOdooCredential.tenant_id == tenant_id).first()
    )
    if credential is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No Odoo connection configured"
        )

    client = build_client(credential)
    try:
        available, vehicles = fetch_fleet_vehicles(
            client, company_id=credential.company_id, version_major=credential.server_version_major
        )
    except ODOO_ERRORS as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not fetch fleet vehicles from Odoo: {exc}",
        ) from exc

    if available:
        # Module absent doesn't mean "every link is now stale" — only flag
        # staleness when we can actually see the current Odoo vehicle list.
        sync_link_staleness(
            db, tenant_id, Vehicle, "odoo_fleet_vehicle_id", {v["id"] for v in vehicles}
        )

    return OdooFleetVehicleList(available=available, vehicles=vehicles)


@router.get("/{vehicle_id}", response_model=VehicleRead)
def get_vehicle(
    tenant_id: uuid.UUID,
    vehicle_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Vehicle:
    _require_same_tenant(tenant_id, current_user)
    return _get_vehicle_or_404(db, tenant_id, vehicle_id)


@router.put("/{vehicle_id}", response_model=VehicleRead)
def update_vehicle(
    tenant_id: uuid.UUID,
    vehicle_id: uuid.UUID,
    payload: VehicleUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Vehicle:
    _require_same_tenant(tenant_id, current_user)
    vehicle = _get_vehicle_or_404(db, tenant_id, vehicle_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(vehicle, field, value)
    db.commit()
    db.refresh(vehicle)
    return vehicle


@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vehicle(
    tenant_id: uuid.UUID,
    vehicle_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> None:
    _require_same_tenant(tenant_id, current_user)
    vehicle = _get_vehicle_or_404(db, tenant_id, vehicle_id)

    referencing_driver = db.query(Driver).filter_by(assigned_vehicle_id=vehicle.id).first()
    if referencing_driver is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Vehicle is assigned to driver '{referencing_driver.name}'; unassign it first",
        )

    db.delete(vehicle)
    db.commit()


@router.put("/{vehicle_id}/odoo-link", response_model=VehicleRead)
def link_vehicle_to_odoo(
    tenant_id: uuid.UUID,
    vehicle_id: uuid.UUID,
    payload: VehicleLinkOdoo,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Vehicle:
    """Sets the Odoo cross-reference only — never touches any other field on
    the local vehicle (see DECISIONS.md)."""
    _require_same_tenant(tenant_id, current_user)
    vehicle = _get_vehicle_or_404(db, tenant_id, vehicle_id)
    vehicle.odoo_fleet_vehicle_id = payload.odoo_fleet_vehicle_id
    vehicle.odoo_link_status = "linked"
    db.commit()
    db.refresh(vehicle)
    return vehicle


@router.delete("/{vehicle_id}/odoo-link", response_model=VehicleRead)
def unlink_vehicle_from_odoo(
    tenant_id: uuid.UUID,
    vehicle_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Vehicle:
    _require_same_tenant(tenant_id, current_user)
    vehicle = _get_vehicle_or_404(db, tenant_id, vehicle_id)
    vehicle.odoo_fleet_vehicle_id = None
    vehicle.odoo_link_status = "unlinked"
    db.commit()
    db.refresh(vehicle)
    return vehicle
