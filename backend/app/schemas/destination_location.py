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


class PickingAddressOption(BaseModel):
    """One distinct customer/address combo pulled from the tenant's
    already-synced `SyncedPicking` rows — used to prefill a new
    destination's name/address fields (see
    GET .../destination-locations/picking-addresses). Raw field values
    from the picked row; lat/lng is never included since pickings don't
    have coordinates either — those always stay manual on the destination
    form."""

    customer_name: str
    street: str
    street2: str
    city: str
    state_name: str
    country_name: str
    zip: str
