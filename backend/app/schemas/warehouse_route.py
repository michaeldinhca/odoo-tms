import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.destination_location import DestinationLocationRead


class WarehouseRouteCreate(BaseModel):
    name: str
    color: str | None = None


class WarehouseRouteUpdate(BaseModel):
    """Partial update, matching the DestinationLocationUpdate pattern."""

    name: str | None = None
    color: str | None = None


class RouteStopRead(BaseModel):
    """Assembled by the router (destination joined + distance computed at
    read time), not a direct `from_attributes` read off RouteStop — same
    reasoning as the old WarehouseDestinationLocationRead."""

    id: uuid.UUID
    destination: DestinationLocationRead
    stop_order: int
    distance_km: float | None
    created_at: datetime


class WarehouseRouteRead(BaseModel):
    """Assembled by the router: the route's own fields plus its ordered
    stops in one response, so the frontend can render both the route list
    and the map from a single list call."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    warehouse_id: uuid.UUID
    name: str
    color: str
    stops: list[RouteStopRead]
    created_at: datetime
    updated_at: datetime


class RouteStopsBulkAdd(BaseModel):
    destination_location_ids: list[uuid.UUID]


class RouteStopsBulkAddResult(BaseModel):
    """`skipped_destination_ids` are ones already in the route — bulk-add
    silently skips duplicates rather than 400ing the whole batch (a
    different UX contract than the single-add case), but still reports
    what was skipped instead of discarding that information."""

    stops: list[RouteStopRead]
    skipped_destination_ids: list[uuid.UUID]


class RouteStopsReorder(BaseModel):
    """Must be exactly the route's current stop set — the router 400s on
    any missing/extra id rather than guessing at a partial reorder."""

    destination_location_ids: list[uuid.UUID]
