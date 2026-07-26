import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class DestinationLocation(Base):
    """A reusable, admin-managed delivery destination — a saved place, not
    tied to any one Odoo `stock.picking` (contrast with the Load Planning
    board's `Picking`, which is per-run/per-order and currently fixture
    data only — see design.md). One location can be attached to several
    warehouses' routes (`app.models.warehouse_route.RouteStop`), which is
    the whole point of keeping it a standalone entity instead of
    duplicating a location under every warehouse that delivers to it.

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
