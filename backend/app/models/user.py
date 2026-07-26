import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class User(Base):
    """A dispatcher/operator login. `role` is `"admin"` or `"user"` — it
    only gates access to the user-management endpoints themselves (see
    `app.api.deps.require_admin`), so demoting/deleting the last admin is
    blocked (see `app.api.users`) to avoid locking a tenant out of its own
    user management. Day-to-day feature access for *everyone*, admins
    included, is driven purely by the `can_*` booleans below — `role`
    deliberately does not bypass them (see DECISIONS.md "Role vs. boolean
    permissions")."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user")
    can_manage_connection: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    can_manage_warehouses: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    can_manage_operation_types: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    can_manage_fleet: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    can_run_planning: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    can_use_load_planning: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
