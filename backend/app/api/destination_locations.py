import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_db, require_permission
from app.models.destination_location import DestinationLocation
from app.models.synced_picking import SyncedPicking
from app.models.warehouse_route import RouteStop
from app.schemas.destination_location import (
    DestinationLocationCreate,
    DestinationLocationRead,
    DestinationLocationUpdate,
    PickingAddressOption,
)
from app.services.destination_locations import normalize_address_key

PICKING_ADDRESS_SCAN_LIMIT = 100

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
        db.query(DestinationLocation)
        .filter_by(tenant_id=tenant_id)
        .order_by(DestinationLocation.name)
        .all()
    )


@router.get("/picking-addresses", response_model=list[PickingAddressOption])
def list_picking_address_options(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("can_manage_warehouses")),
) -> list[dict]:
    """Distinct customer/address combos pulled from the tenant's 100 most
    recently seen SyncedPicking rows, to prefill a new destination's
    name/address fields — reuses the delivery address stock.picking sync
    already resolves, rather than a new live Odoo partner-browse call
    (SyncedPicking has no partner id to key a proper link/unlink feature
    on the way Vehicles/Drivers link to Odoo — see DECISIONS.md).

    Deduped in Python, not SQL, using the same `normalize_address_key` the
    auto-create-on-sync path uses (see app.services.picking_sync): Odoo's
    free-text address fields aren't normalized at sync time (case/
    whitespace can drift between pickings for the same customer), and
    this needs to run against both Postgres and the SQLite test fixture,
    so a portable normalize-then-dedupe pass is simpler than a
    dialect-specific DISTINCT ON. Ordered by `last_seen_at` desc and
    capped at the 100 most recent pickings — deliberately a recency
    window, not "however many distinct addresses exist," so this stays a
    quick, small prefill list rather than growing unbounded with tenant
    history."""
    _require_same_tenant(tenant_id, current_user)

    pickings = (
        db.query(SyncedPicking)
        .filter_by(tenant_id=tenant_id)
        .order_by(SyncedPicking.last_seen_at.desc())
        .limit(PICKING_ADDRESS_SCAN_LIMIT)
        .all()
    )

    seen: set[tuple[str, ...]] = set()
    options: list[SyncedPicking] = []
    for picking in pickings:
        key = normalize_address_key(
            picking.customer_name,
            picking.street,
            picking.street2,
            picking.city,
            picking.state_name,
            picking.country_name,
            picking.zip,
        )
        if key in seen:
            continue
        seen.add(key)
        options.append(picking)

    return [
        {
            "customer_name": p.customer_name,
            "street": p.street,
            "street2": p.street2,
            "city": p.city,
            "state_name": p.state_name,
            "country_name": p.country_name,
            "zip": p.zip,
        }
        for p in options
    ]


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
    """Deleting a destination removes it from every route (any warehouse)
    it was a stop on — there's nothing meaningful left for those stop rows
    to point at, so this cleans them up rather than blocking (unlike e.g.
    a warehouse referenced by a vehicle, deleting a shared reference
    location isn't a "someone still depends on this exact record for
    correctness" situation)."""
    _require_same_tenant(tenant_id, current_user)
    location = _get_destination_or_404(db, tenant_id, destination_location_id)

    db.query(RouteStop).filter_by(
        tenant_id=tenant_id, destination_location_id=location.id
    ).delete()
    db.delete(location)
    db.commit()
