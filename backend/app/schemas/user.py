import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

UserRole = Literal["admin", "user"]


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    role: UserRole = "user"
    can_manage_connection: bool = False
    can_manage_warehouses: bool = False
    can_manage_operation_types: bool = False
    can_manage_fleet: bool = False
    can_run_planning: bool = True
    can_use_load_planning: bool = True


class UserUpdate(BaseModel):
    """All fields optional — only the ones provided are applied (partial
    update), matching the VehicleUpdate/DriverUpdate pattern elsewhere.
    Password is deliberately not here — see AdminPasswordReset/
    SelfPasswordChange, kept as separate, explicit actions."""

    email: EmailStr | None = None
    role: UserRole | None = None
    can_manage_connection: bool | None = None
    can_manage_warehouses: bool | None = None
    can_manage_operation_types: bool | None = None
    can_manage_fleet: bool | None = None
    can_run_planning: bool | None = None
    can_use_load_planning: bool | None = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    role: UserRole
    can_manage_connection: bool
    can_manage_warehouses: bool
    can_manage_operation_types: bool
    can_manage_fleet: bool
    can_run_planning: bool
    can_use_load_planning: bool
    created_at: datetime


class AdminPasswordReset(BaseModel):
    """An admin resetting someone else's password — no current-password
    check, admin authority substitutes for it."""

    new_password: str = Field(min_length=8)


class SelfPasswordChange(BaseModel):
    """Any user changing their own password — requires the current one,
    unlike AdminPasswordReset."""

    current_password: str
    new_password: str = Field(min_length=8)
