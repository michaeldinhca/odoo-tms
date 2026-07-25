import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class TenantOdooCredential(Base):
    """Odoo XML-RPC connection details for a tenant.

    `encrypted_key` is Fernet-encrypted at rest (see app.core.crypto) and must
    never be logged, returned in API responses, or stored in plaintext.

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

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, unique=True, index=True
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    db: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_key: Mapped[str] = mapped_column(String(1000), nullable=False)
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
