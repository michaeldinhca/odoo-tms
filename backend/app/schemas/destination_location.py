import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DestinationLocationCreate(BaseModel):
    name: str
    street: str = ""
    street2: str = ""
    city: str = ""
    state: str = ""
    country: str = ""
    zip: str = ""
    lat: float
    lng: float


class DestinationLocationUpdate(BaseModel):
    """All fields optional — only the ones provided are applied (partial
    update), matching the VehicleUpdate/DriverUpdate pattern elsewhere."""

    name: str | None = None
    street: str | None = None
    street2: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    zip: str | None = None
    lat: float | None = None
    lng: float | None = None


class DestinationLocationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    street: str
    street2: str
    city: str
    state: str
    country: str
    zip: str
    lat: float
    lng: float
    created_at: datetime
    updated_at: datetime


class WarehouseCoordinatesUpdate(BaseModel):
    """Both nullable so a mistaken coordinate can be explicitly cleared,
    not just overwritten."""

    lat: float | None
    lng: float | None


class WarehouseDestinationLocationCreate(BaseModel):
    destination_location_id: uuid.UUID


class WarehouseDestinationLocationRead(BaseModel):
    """The association row plus the destination it points to and the
    distance from the warehouse being queried — assembled by
    app.services.destination_locations, not a direct `from_attributes`
    read off the join table (distance is computed, not stored; see
    WarehouseDestinationLocation's docstring for why)."""

    id: uuid.UUID
    destination: DestinationLocationRead
    distance_km: float | None
    created_at: datetime
