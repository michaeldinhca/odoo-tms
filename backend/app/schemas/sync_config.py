import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OperationTypeRead(BaseModel):
    """`warehouse_name` is assembled by the router (resolved from
    `warehouse_id` against the tenant's synced warehouses at read time),
    not a stored column — same reasoning as every other computed-not-
    cached value in this project (a warehouse can be renamed after an
    operation type was last synced)."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    odoo_operation_type_id: int
    name: str
    code: str
    warehouse_id: int | None
    warehouse_name: str | None
    is_synced: bool
    active: bool
    last_seen_at: datetime | None
    created_at: datetime
    updated_at: datetime


class OperationTypeSyncToggle(BaseModel):
    is_synced: bool


class ArchiveToggle(BaseModel):
    active: bool


class OperationTypeDiffItem(BaseModel):
    odoo_operation_type_id: int
    name: str
    code: str


class OperationTypeRefreshPreview(BaseModel):
    """Result of a dry-run resync — nothing is written to the DB yet."""

    new: list[OperationTypeDiffItem]
    removed: list[OperationTypeDiffItem]
    unchanged_count: int


class WarehouseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    odoo_warehouse_id: int
    name: str
    code: str
    street: str
    street2: str
    city: str
    state_id: int | None
    state_name: str
    country_id: int | None
    country_name: str
    zip: str
    is_synced: bool
    active: bool
    lat: float | None
    lng: float | None
    last_seen_at: datetime | None
    created_at: datetime
    updated_at: datetime


class WarehouseSyncToggle(BaseModel):
    is_synced: bool


class WarehouseDiffItem(BaseModel):
    odoo_warehouse_id: int
    name: str
    code: str


class WarehouseRefreshPreview(BaseModel):
    """Result of a dry-run resync — nothing is written to the DB yet."""

    new: list[WarehouseDiffItem]
    removed: list[WarehouseDiffItem]
    unchanged_count: int
