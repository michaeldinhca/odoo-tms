import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class WarehouseRoute(Base):
    """A named, colored delivery route belonging to one warehouse — an
    ordered sequence of `RouteStop`s. Replaces the earlier flat
    `WarehouseDestinationLocation` "route set" (unordered, no grouping),
    which shipped with no real usage and was dropped outright (see
    alembic revision 0009). `color` is a hex string, auto-assigned from a
    fixed palette (see app.services.warehouse_routes) unless the admin
    picks one explicitly."""

    __tablename__ = "warehouse_routes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("synced_warehouses.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    color: Mapped[str] = mapped_column(String(7), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class RouteStop(Base):
    """One destination's position within a `WarehouseRoute`. `stop_order`
    is only meaningful relative to other stops in the same route — it's
    densified to 0..N-1 whenever the route is explicitly reordered, but a
    single-stop delete leaves gaps rather than renumbering (harmless, since
    nothing depends on density, only relative order). A destination can't
    repeat within one route (unique on route_id+destination_location_id)
    but can still appear in any number of other routes/warehouses.
    Distance to the destination is *not* stored here, same reasoning as
    the old join table: computed at read time from both sides' current
    lat/lng (see app.services.destination_locations.distance_km)."""

    __tablename__ = "route_stops"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    route_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("warehouse_routes.id"), nullable=False, index=True
    )
    destination_location_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("destination_locations.id"), nullable=False, index=True
    )
    stop_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("route_id", "destination_location_id", name="uq_route_stop"),
    )
