import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OperationTypeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    odoo_operation_type_id: int
    name: str
    code: str
    warehouse_id: int | None
    is_synced: bool
    last_seen_at: datetime | None
    created_at: datetime
    updated_at: datetime


class OperationTypeSyncToggle(BaseModel):
    is_synced: bool


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
    last_seen_at: datetime | None
    created_at: datetime
    updated_at: datetime


class WarehouseSyncToggle(BaseModel):
    is_synced: bool
