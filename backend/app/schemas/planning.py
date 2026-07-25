import uuid
from datetime import datetime

from pydantic import BaseModel


class PlanningRunRequest(BaseModel):
    tenant_id: uuid.UUID


class RouteStop(BaseModel):
    stop_order: int
    picking_id: int
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
