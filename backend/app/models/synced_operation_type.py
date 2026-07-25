import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class SyncedOperationType(Base):
    """Mirrors a tenant's Odoo `stock.picking.type` records (Receipts,
    Delivery Orders, Manufacturing, ...). Only pickings whose
    `picking_type_id` is marked `is_synced=True` here are pulled by the
    stock.picking sync (see app.services.planning.runner.fetch_open_orders).

    `active` is a soft-delete/archive flag (Odoo-style convention), separate
    from `is_synced` (planning opt-in) — an archived row is hidden from the
    default list and can't be re-referenced, but isn't hard-deleted (see
    DECISIONS.md "Archive instead of delete for referenced sync/fleet rows").
    """

    __tablename__ = "synced_operation_types"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    odoo_operation_type_id: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    code: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    warehouse_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_synced: Mapped[bool] = mapped_column(default=False, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "odoo_operation_type_id", name="uq_synced_operation_types_tenant_odoo_id"
        ),
    )
