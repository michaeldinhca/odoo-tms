import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_db, require_permission
from app.models.destination_location import DestinationLocation
from app.models.synced_warehouse import SyncedWarehouse
from app.models.warehouse_route import RouteStop, WarehouseRoute
from app.schemas.warehouse_route import (
    RouteStopRead,
    RouteStopsBulkAdd,
    RouteStopsBulkAddResult,
    RouteStopsReorder,
    WarehouseRouteCreate,
    WarehouseRouteRead,
    WarehouseRouteUpdate,
)
from app.services.destination_locations import distance_km
from app.services.warehouse_routes import assign_route_color

router = APIRouter(
    prefix="/tenants/{tenant_id}/warehouses/{warehouse_id}/routes", tags=["warehouse-routes"]
)


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


def _get_route_or_404(
    db: Session, tenant_id: uuid.UUID, warehouse_id: uuid.UUID, route_id: uuid.UUID
) -> WarehouseRoute:
    row = (
        db.query(WarehouseRoute)
        .filter_by(id=route_id, tenant_id=tenant_id, warehouse_id=warehouse_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")
    return row


def _serialize_route(db: Session, warehouse: SyncedWarehouse, route: WarehouseRoute) -> dict:
    rows = (
        db.query(RouteStop, DestinationLocation)
        .join(DestinationLocation, RouteStop.destination_location_id == DestinationLocation.id)
        .filter(RouteStop.route_id == route.id)
        .order_by(RouteStop.stop_order)
        .all()
    )
    return {
        "id": route.id,
        "tenant_id": route.tenant_id,
        "warehouse_id": route.warehouse_id,
        "name": route.name,
        "color": route.color,
        "stops": [
            {
                "id": stop.id,
                "destination": destination,
                "stop_order": stop.stop_order,
                "distance_km": distance_km(warehouse, destination),
                "created_at": stop.created_at,
            }
            for stop, destination in rows
        ],
        "created_at": route.created_at,
        "updated_at": route.updated_at,
    }


@router.get("", response_model=list[WarehouseRouteRead])
def list_warehouse_routes(
    tenant_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("can_manage_warehouses")),
) -> list[dict]:
    _require_same_tenant(tenant_id, current_user)
    warehouse = _get_warehouse_or_404(db, tenant_id, warehouse_id)

    routes = (
        db.query(WarehouseRoute)
        .filter_by(tenant_id=tenant_id, warehouse_id=warehouse_id)
        .order_by(WarehouseRoute.name)
        .all()
    )
    return [_serialize_route(db, warehouse, route) for route in routes]


@router.post("", response_model=WarehouseRouteRead, status_code=status.HTTP_201_CREATED)
def create_warehouse_route(
    tenant_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    payload: WarehouseRouteCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("can_manage_warehouses")),
) -> dict:
    _require_same_tenant(tenant_id, current_user)
    warehouse = _get_warehouse_or_404(db, tenant_id, warehouse_id)

    color = payload.color
    if not color:
        used_colors = {
            c
            for (c,) in db.query(WarehouseRoute.color)
            .filter_by(tenant_id=tenant_id, warehouse_id=warehouse_id)
            .all()
        }
        color = assign_route_color(used_colors)

    route = WarehouseRoute(
        tenant_id=tenant_id, warehouse_id=warehouse_id, name=payload.name, color=color
    )
    db.add(route)
    db.commit()
    db.refresh(route)
    return _serialize_route(db, warehouse, route)


@router.put("/{route_id}", response_model=WarehouseRouteRead)
def update_warehouse_route(
    tenant_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    route_id: uuid.UUID,
    payload: WarehouseRouteUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("can_manage_warehouses")),
) -> dict:
    _require_same_tenant(tenant_id, current_user)
    warehouse = _get_warehouse_or_404(db, tenant_id, warehouse_id)
    route = _get_route_or_404(db, tenant_id, warehouse_id, route_id)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(route, field, value)
    db.commit()
    db.refresh(route)
    return _serialize_route(db, warehouse, route)


@router.delete("/{route_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_warehouse_route(
    tenant_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    route_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("can_manage_warehouses")),
) -> None:
    _require_same_tenant(tenant_id, current_user)
    route = _get_route_or_404(db, tenant_id, warehouse_id, route_id)

    db.query(RouteStop).filter_by(tenant_id=tenant_id, route_id=route.id).delete()
    db.delete(route)
    db.commit()


@router.post(
    "/{route_id}/stops",
    response_model=RouteStopsBulkAddResult,
    status_code=status.HTTP_201_CREATED,
)
def bulk_add_route_stops(
    tenant_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    route_id: uuid.UUID,
    payload: RouteStopsBulkAdd,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("can_manage_warehouses")),
) -> dict:
    """Adds several destinations to the route in one call. Destinations
    already in the route are silently skipped (not a 400) — this is a
    multi-select bulk action, "give me the ones that aren't already here,"
    not a single explicit add where a duplicate is unexpected — but the
    skipped ids are still reported back, not silently discarded."""
    _require_same_tenant(tenant_id, current_user)
    warehouse = _get_warehouse_or_404(db, tenant_id, warehouse_id)
    route = _get_route_or_404(db, tenant_id, warehouse_id, route_id)

    requested_ids = list(dict.fromkeys(payload.destination_location_ids))  # de-dup, keep order
    destinations = (
        db.query(DestinationLocation)
        .filter(
            DestinationLocation.tenant_id == tenant_id,
            DestinationLocation.id.in_(requested_ids),
        )
        .all()
    )
    found_ids = {d.id for d in destinations}
    missing_ids = [d for d in requested_ids if d not in found_ids]
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Destination(s) not found: {', '.join(str(i) for i in missing_ids)}",
        )

    existing_ids = {
        dest_id
        for (dest_id,) in db.query(RouteStop.destination_location_id)
        .filter_by(route_id=route.id)
        .all()
    }
    current_max = (
        db.query(RouteStop.stop_order)
        .filter_by(route_id=route.id)
        .order_by(RouteStop.stop_order.desc())
        .first()
    )
    next_order = (current_max[0] + 1) if current_max else 0

    skipped_ids = [d for d in requested_ids if d in existing_ids]
    to_add = [d for d in requested_ids if d not in existing_ids]
    for dest_id in to_add:
        db.add(
            RouteStop(
                tenant_id=tenant_id,
                route_id=route.id,
                destination_location_id=dest_id,
                stop_order=next_order,
            )
        )
        next_order += 1
    db.commit()

    serialized = _serialize_route(db, warehouse, route)
    return {"stops": serialized["stops"], "skipped_destination_ids": skipped_ids}


@router.put("/{route_id}/stops/reorder", response_model=list[RouteStopRead])
def reorder_route_stops(
    tenant_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    route_id: uuid.UUID,
    payload: RouteStopsReorder,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("can_manage_warehouses")),
) -> list[dict]:
    _require_same_tenant(tenant_id, current_user)
    warehouse = _get_warehouse_or_404(db, tenant_id, warehouse_id)
    route = _get_route_or_404(db, tenant_id, warehouse_id, route_id)

    stops = db.query(RouteStop).filter_by(route_id=route.id).all()
    stops_by_destination = {stop.destination_location_id: stop for stop in stops}
    given_ids = payload.destination_location_ids

    if len(given_ids) != len(set(given_ids)) or set(given_ids) != set(stops_by_destination.keys()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reorder list must contain exactly the route's current stops, no more, no less",
        )

    for index, dest_id in enumerate(given_ids):
        stops_by_destination[dest_id].stop_order = index
    db.commit()

    return _serialize_route(db, warehouse, route)["stops"]


@router.delete(
    "/{route_id}/stops/{destination_location_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_route_stop(
    tenant_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    route_id: uuid.UUID,
    destination_location_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("can_manage_warehouses")),
) -> None:
    _require_same_tenant(tenant_id, current_user)
    route = _get_route_or_404(db, tenant_id, warehouse_id, route_id)

    stop = (
        db.query(RouteStop)
        .filter_by(route_id=route.id, destination_location_id=destination_location_id)
        .first()
    )
    if stop is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Stop not found in this route"
        )

    db.delete(stop)
    db.commit()
