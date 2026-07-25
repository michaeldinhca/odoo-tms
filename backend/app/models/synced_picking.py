import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class SyncedPicking(Base):
    """Local mirror of a tenant's synced stock.picking records — only ones
    whose operation type is marked `is_synced` on SyncedOperationType get
    pulled/stored here (see app.services.planning.runner.fetch_open_orders).
    Upserted as a side effect of `/planning/run`; see app.services.picking_sync.
    """

    __tablename__ = "synced_pickings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    odoo_picking_id: Mapped[int] = mapped_column(Integer, nullable=False)

    state: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    items_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")

    street: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    street2: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    city: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    state_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    state_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    country_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    country_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    zip: Mapped[str] = mapped_column(String(20), nullable=False, default="")

    scheduled_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    picking_type_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    warehouse_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    warehouse_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    origin: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    weight: Mapped[float | None] = mapped_column(nullable=True)
    shipping_weight: Mapped[float | None] = mapped_column(nullable=True)
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")

    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "odoo_picking_id", name="uq_synced_pickings_tenant_odoo_id"),
    )
