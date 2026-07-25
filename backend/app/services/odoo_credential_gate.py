"""Shared helpers for fetching a tenant's Odoo credential and enforcing the
connection state machine (see DECISIONS.md "Odoo connection state machine").
Used by every API module that talks to a tenant's Odoo instance."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.odoo_credential import TenantOdooCredential


def get_credential_or_404(db: Session, tenant_id: uuid.UUID) -> TenantOdooCredential:
    credential = (
        db.query(TenantOdooCredential)
        .filter(TenantOdooCredential.tenant_id == tenant_id)
        .first()
    )
    if credential is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No Odoo connection configured"
        )
    return credential


def require_active_instance(db: Session, tenant_id: uuid.UUID) -> TenantOdooCredential:
    """Raises 409 unless the tenant's Odoo connection has completed staged
    setup (state == "active"). Read-only endpoints (get/test/companies)
    don't use this — they're how a connection *reaches* active in the first
    place."""
    credential = get_credential_or_404(db, tenant_id)
    if credential.state != "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Odoo connection is not active yet — finish setup on the Connection page first",
        )
    return credential
