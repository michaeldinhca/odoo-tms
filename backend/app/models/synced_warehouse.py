import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class SyncedWarehouse(Base):
    """Mirrors a tenant's Odoo `stock.warehouse` records, address split into
    the same street/street2/city/state/country/zip shape used everywhere else
    (see DECISIONS.md "Structured addresses, not concatenated strings") —
    reused as-is, not a second inconsistent address structure.

    `active` is a soft-delete/archive flag, separate from `is_synced` — see
    SyncedOperationType's docstring for the same pattern.

    `lat`/`lng` are admin-entered, not synced from Odoo — Odoo's
    `res.partner` has no confirmed lat/lon field mapping yet (see
    TODO.md's open questions), so rather than block the destination-
    location/route-distance feature on that, warehouse coordinates are a
    plain local override. Nullable: distance-to-destination just reads as
    unavailable until they're set."""

    __tablename__ = "synced_warehouses"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    odoo_warehouse_id: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    code: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    street: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    street2: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    city: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    state_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    state_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    country_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    country_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    zip: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    is_synced: Mapped[bool] = mapped_column(default=False, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    lat: Mapped[float | None] = mapped_column(nullable=True)
    lng: Mapped[float | None] = mapped_column(nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "odoo_warehouse_id", name="uq_synced_warehouses_tenant_odoo_id"
        ),
    )
