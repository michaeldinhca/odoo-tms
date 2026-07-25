import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

VehicleType = Literal["van", "truck", "motorbike", "three_wheeler", "other"]
VehicleStatus = Literal["active", "inactive", "maintenance"]
DriverStatus = Literal["active", "locked", "inactive"]
OdooLinkStatus = Literal["unlinked", "linked", "stale"]


class VehicleCreate(BaseModel):
    name: str
    license_plate: str | None = None
    vehicle_type: VehicleType = "van"
    payload_capacity_kg: float | None = None
    volume_capacity_m3: float | None = None
    fuel_consumption_per_100km: float | None = None
    home_warehouse_id: uuid.UUID | None = None
    status: VehicleStatus = "active"


class VehicleUpdate(BaseModel):
    """All fields optional — only the ones provided are applied (partial
    update); omitted fields are left unchanged."""

    name: str | None = None
    license_plate: str | None = None
    vehicle_type: VehicleType | None = None
    payload_capacity_kg: float | None = None
    volume_capacity_m3: float | None = None
    fuel_consumption_per_100km: float | None = None
    home_warehouse_id: uuid.UUID | None = None
    status: VehicleStatus | None = None


class VehicleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    license_plate: str | None
    vehicle_type: str
    payload_capacity_kg: float | None
    volume_capacity_m3: float | None
    fuel_consumption_per_100km: float | None
    home_warehouse_id: uuid.UUID | None
    status: str
    odoo_fleet_vehicle_id: int | None
    odoo_link_status: str
    created_at: datetime
    updated_at: datetime


class VehicleLinkOdoo(BaseModel):
    odoo_fleet_vehicle_id: int


class DriverCreate(BaseModel):
    name: str
    phone: str | None = None
    email: str | None = None
    license_number: str | None = None
    id_passport_number: str | None = None
    status: DriverStatus = "active"
    locked_until: datetime | None = None
    assigned_vehicle_id: uuid.UUID | None = None


class DriverUpdate(BaseModel):
    """All fields optional — only the ones provided are applied (partial
    update); omitted fields are left unchanged."""

    name: str | None = None
    phone: str | None = None
    email: str | None = None
    license_number: str | None = None
    id_passport_number: str | None = None
    status: DriverStatus | None = None
    locked_until: datetime | None = None
    assigned_vehicle_id: uuid.UUID | None = None


class DriverRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    phone: str | None
    email: str | None
    license_number: str | None
    id_passport_number: str | None
    status: str
    locked_until: datetime | None
    assigned_vehicle_id: uuid.UUID | None
    odoo_employee_id: int | None
    odoo_link_status: str
    created_at: datetime
    updated_at: datetime


class DriverLinkOdoo(BaseModel):
    odoo_employee_id: int


class OdooFleetVehicle(BaseModel):
    id: int
    name: str
    license_plate: str


class OdooFleetVehicleList(BaseModel):
    available: bool
    vehicles: list[OdooFleetVehicle] = []


class OdooEmployee(BaseModel):
    id: int
    name: str
    work_phone: str
    mobile_phone: str


class OdooEmployeeList(BaseModel):
    available: bool
    employees: list[OdooEmployee] = []
