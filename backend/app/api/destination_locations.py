import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_db, require_permission
from app.models.destination_location import DestinationLocation, WarehouseDestinationLocation
from app.schemas.destination_location import (
    DestinationLocationCreate,
    DestinationLocationRead,
    DestinationLocationUpdate,
)

router = APIRouter(
    prefix="/tenants/{tenant_id}/destination-locations", tags=["destination-locations"]
)


def _require_same_tenant(tenant_id: uuid.UUID, current_user: CurrentUser) -> None:
    if tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch")


def _get_destination_or_404(
    db: Session, tenant_id: uuid.UUID, destination_location_id: uuid.UUID
) -> DestinationLocation:
    row = (
        db.query(DestinationLocation)
        .filter_by(id=destination_location_id, tenant_id=tenant_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Destination not found")
    return row


@router.get("", response_model=list[DestinationLocationRead])
def list_destination_locations(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("can_manage_warehouses")),
) -> list[DestinationLocation]:
    _require_same_tenant(tenant_id, current_user)
    return (
        db.query(DestinationLocation).filter_by(tenant_id=tenant_id).order_by(DestinationLocation.name).all()
    )


@router.post("", response_model=DestinationLocationRead, status_code=status.HTTP_201_CREATED)
def create_destination_location(
    tenant_id: uuid.UUID,
    payload: DestinationLocationCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("can_manage_warehouses")),
) -> DestinationLocation:
    _require_same_tenant(tenant_id, current_user)
    location = DestinationLocation(tenant_id=tenant_id, **payload.model_dump())
    db.add(location)
    db.commit()
    db.refresh(location)
    return location


@router.put("/{destination_location_id}", response_model=DestinationLocationRead)
def update_destination_location(
    tenant_id: uuid.UUID,
    destination_location_id: uuid.UUID,
    payload: DestinationLocationUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("can_manage_warehouses")),
) -> DestinationLocation:
    _require_same_tenant(tenant_id, current_user)
    location = _get_destination_or_404(db, tenant_id, destination_location_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(location, field, value)
    db.commit()
    db.refresh(location)
    return location


@router.delete("/{destination_location_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_destination_location(
    tenant_id: uuid.UUID,
    destination_location_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("can_manage_warehouses")),
) -> None:
    """Deleting a destination removes it from every warehouse's route set
    it was attached to — there's nothing meaningful left for those join
    rows to point at, so this cleans them up rather than blocking (unlike
    e.g. a warehouse referenced by a vehicle, deleting a shared reference
    location isn't a "someone still depends on this exact record for
    correctness" situation)."""
    _require_same_tenant(tenant_id, current_user)
    location = _get_destination_or_404(db, tenant_id, destination_location_id)

    db.query(WarehouseDestinationLocation).filter_by(
        tenant_id=tenant_id, destination_location_id=location.id
    ).delete()
    db.delete(location)
    db.commit()
