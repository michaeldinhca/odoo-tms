import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Vehicle(Base):
    """Vehicles are first-class, locally-owned entities — a vehicle can exist
    here with no Odoo link at all (e.g. a subcontracted truck not in Odoo).
    `odoo_fleet_vehicle_id` is an optional cross-reference to Odoo's
    `fleet.vehicle`, never a data source we depend on (see DECISIONS.md)."""

    __tablename__ = "vehicles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    license_plate: Mapped[str | None] = mapped_column(String(50), nullable=True)
    vehicle_type: Mapped[str] = mapped_column(String(20), nullable=False, default="van")
    payload_capacity_kg: Mapped[float | None] = mapped_column(nullable=True)
    volume_capacity_m3: Mapped[float | None] = mapped_column(nullable=True)
    fuel_consumption_per_100km: Mapped[float | None] = mapped_column(nullable=True)
    home_warehouse_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("synced_warehouses.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    odoo_fleet_vehicle_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    odoo_link_status: Mapped[str] = mapped_column(String(20), nullable=False, default="unlinked")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
