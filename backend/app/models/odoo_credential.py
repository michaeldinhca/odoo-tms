import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class TenantOdooCredential(Base):
    """Odoo XML-RPC connection details for a tenant.

    `encrypted_key` is Fernet-encrypted at rest (see app.core.crypto) and must
    never be logged, returned in API responses, or stored in plaintext.

    `state` is the connection's staged-onboarding state machine (see
    DECISIONS.md "Odoo connection state machine"): `draft` (credentials saved
    but not yet activated), `active` (company selection completed at least
    once — Odoo-dependent screens are gated on this), `error` (reserved for
    future use, not yet set anywhere). `activated_at` is set the first time
    the connection transitions to `active`. `last_synced_operation_types_at`/
    `last_synced_warehouses_at` record the last successful "confirm and
    apply" resync (not preview) for each.

    `company_id`/`company_name` cache the tenant's selected Odoo res.company
    (see DECISIONS.md "Multi-company handled as one selectable default
    company per tenant credential"). NULL means unfiltered — all companies
    the API user can see.

    `server_version`/`server_version_major`/`server_serie`/`protocol_version`
    are captured from Odoo's `common.version()` every time the connection is
    tested (see DECISIONS.md "Odoo version detection"), and drive the
    version-aware field mapping in app.odoo_mappings. `version_change_detected`
    is set when a test-connection re-check finds a different
    `server_version_major` than what was previously stored.
    """

    __tablename__ = "tenant_odoo_credentials"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False, unique=True, index=True
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    db: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_key: Mapped[str] = mapped_column(String(1000), nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_synced_operation_types_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_synced_warehouses_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    company_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    server_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    server_version_major: Mapped[int | None] = mapped_column(Integer, nullable=True)
    server_serie: Mapped[str | None] = mapped_column(String(50), nullable=True)
    protocol_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    version_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    version_change_detected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
