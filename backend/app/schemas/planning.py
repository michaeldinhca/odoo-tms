import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PlanningRunRequest(BaseModel):
    tenant_id: uuid.UUID


class Address(BaseModel):
    street: str = ""
    street2: str = ""
    city: str = ""
    state_id: int | None = None
    state_name: str = ""
    country_id: int | None = None
    country_name: str = ""
    zip: str = ""


class RouteStop(BaseModel):
    stop_order: int
    picking_id: int
    customer_name: str = ""
    items_summary: str = ""
    address: Address = Field(default_factory=Address)
    state: str = ""
    scheduled_date: datetime | None = None
    origin: str = ""
    warehouse_name: str = ""
    eta: datetime | None = None


class VehicleRoute(BaseModel):
    vehicle_id: int
    sequence: list[RouteStop]
    estimated_distance_km: float
    estimated_duration_min: float


class PlanningRunResult(BaseModel):
    run_id: uuid.UUID
    tenant_id: uuid.UUID
    status: str
    routes: list[VehicleRoute] = []
    unassigned_picking_ids: list[int] = []
    created_at: datetime
    completed_at: datetime | None = None
