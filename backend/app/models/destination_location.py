import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class DestinationLocation(Base):
    """A reusable, admin-managed delivery destination — a saved place, not
    tied to any one Odoo `stock.picking` (contrast with the Load Planning
    board's `Picking`, which is per-run/per-order and currently fixture
    data only — see design.md). One location can be attached to several
    warehouses' route sets (`WarehouseDestinationLocation`), which is the
    whole point of keeping it a standalone entity instead of duplicating a
    location under every warehouse that delivers to it.

    Locally created, so no Odoo `res.country`/`res.country.state` ids to
    reference — `state`/`country` are plain text, unlike the synced
    entities' split id+cached-name address shape."""

    __tablename__ = "destination_locations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    street: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    street2: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    city: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    state: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    country: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    zip: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    lat: Mapped[float] = mapped_column(nullable=False)
    lng: Mapped[float] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class WarehouseDestinationLocation(Base):
    """Many-to-many: which destinations are in a given warehouse's route
    set. A destination may appear under several warehouses at once — this
    join row is what "add this destination to warehouse X" actually
    creates, and deleting it is what "remove from warehouse" means (the
    `DestinationLocation` itself is untouched, and may still be attached
    elsewhere). Distance to the destination is *not* stored here — it's
    computed at read time from both sides' lat/lng (see
    app.services.destination_locations), since either coordinate can be
    edited after the association is created."""

    __tablename__ = "warehouse_destination_locations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("synced_warehouses.id"), nullable=False, index=True
    )
    destination_location_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("destination_locations.id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "warehouse_id",
            "destination_location_id",
            name="uq_warehouse_destination_location",
        ),
    )
