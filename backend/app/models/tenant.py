import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Tenant(Base):
    """`status`/`plan_name`/`billing_email`/`expire_date`/
    `warning_period_days`/`notes` are subscription/billing metadata, not
    yet enforced anywhere (no billing integration exists — see
    DECISIONS.md). `status` is a manual override channel
    (`active`/`suspended`/`cancelled`) independent of the date math below
    — an operator suspending a tenant for non-payment shouldn't be
    silently overridden by a still-future `expire_date`. There is no
    separate "trial" status: a trial is just a tenant with `expire_date`
    set to the trial's end, which the date-driven warning/expired states
    already cover.

    `warning_date` (when a warning should start) and the overall
    subscription state (active/warning/expired/suspended/cancelled) are
    deliberately NOT stored columns — see
    `app.services.tenant_subscription`, computed at read time from
    `expire_date`/`warning_period_days`/`status` so they can never go
    stale relative to those fields (same reasoning as this project's other
    computed-not-cached values, e.g. destination-to-warehouse distance)."""

    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    plan_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    billing_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expire_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    warning_period_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
