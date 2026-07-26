import uuid
import xmlrpc.client
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_db, require_permission
from app.core.crypto import encrypt_secret
from app.models.odoo_credential import TenantOdooCredential
from app.schemas.credentials import (
    OdooCompany,
    OdooCredentialCompanySelect,
    OdooCredentialRead,
    OdooCredentialTestResult,
    OdooCredentialUpsert,
)
from app.services.odoo_client import OdooAuthError
from app.services.odoo_connection import build_client
from app.services.odoo_credential_gate import get_credential_or_404
from app.services.odoo_version import detect_and_store_version

router = APIRouter(prefix="/tenants/{tenant_id}/credentials", tags=["credentials"])


def _require_same_tenant(tenant_id: uuid.UUID, current_user: CurrentUser) -> None:
    if tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch")


def _apply_credential_fields(
    credential: TenantOdooCredential, payload: OdooCredentialUpsert
) -> None:
    credential.url = payload.url
    credential.db = payload.db
    credential.username = payload.username
    credential.encrypted_key = encrypt_secret(payload.api_key)


@router.get("", response_model=OdooCredentialRead)
def get_credential(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("can_manage_connection")),
) -> TenantOdooCredential:
    _require_same_tenant(tenant_id, current_user)
    return get_credential_or_404(db, tenant_id)


@router.put("", response_model=OdooCredentialRead)
def upsert_credential(
    tenant_id: uuid.UUID,
    payload: OdooCredentialUpsert,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("can_manage_connection")),
) -> TenantOdooCredential:
    """The initial/setup save — always usable regardless of current state,
    so a broken draft connection can always be corrected. Never touches
    `state`/`company_id` (see `select_company` for activation and
    `reauthenticate_credential` for the equivalent action once active)."""
    _require_same_tenant(tenant_id, current_user)
    credential = (
        db.query(TenantOdooCredential)
        .filter(TenantOdooCredential.tenant_id == tenant_id)
        .first()
    )
    if credential is None:
        credential = TenantOdooCredential(tenant_id=tenant_id, state="draft")
        db.add(credential)

    _apply_credential_fields(credential, payload)

    db.commit()
    db.refresh(credential)
    return credential


@router.post("/reauthenticate", response_model=OdooCredentialRead)
def reauthenticate_credential(
    tenant_id: uuid.UUID,
    payload: OdooCredentialUpsert,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("can_manage_connection")),
) -> TenantOdooCredential:
    """Distinct from the initial setup PUT above: only usable once the
    connection is already active, so re-authenticating (e.g. after an API
    key rotation) can never be mistaken for restarting onboarding on an
    unconfigured connection."""
    _require_same_tenant(tenant_id, current_user)
    credential = get_credential_or_404(db, tenant_id)
    if credential.state != "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Connection is not active yet; use the initial setup form instead",
        )

    _apply_credential_fields(credential, payload)

    db.commit()
    db.refresh(credential)
    return credential


@router.post("/test", response_model=OdooCredentialTestResult)
def test_credential(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("can_manage_connection")),
) -> OdooCredentialTestResult:
    _require_same_tenant(tenant_id, current_user)
    credential = get_credential_or_404(db, tenant_id)

    client = build_client(credential)
    success, detail = client.test_connection()

    if success:
        try:
            detect_and_store_version(db, credential, client)
        except (OdooAuthError, xmlrpc.client.Fault, OSError):
            # The auth/data connection is fine (that's what `success` means)
            # — a hiccup fetching version info specifically shouldn't fail
            # the whole test. Version fields just stay whatever they were.
            pass

    return OdooCredentialTestResult(
        success=success,
        detail=detail,
        server_version=credential.server_version,
        server_version_major=credential.server_version_major,
        version_change_detected=credential.version_change_detected,
    )


@router.get("/companies", response_model=list[OdooCompany])
def list_companies(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("can_manage_connection")),
) -> list[dict]:
    """Live-fetches the Odoo instance's companies so the dispatcher can pick
    which one to scope planning runs to (see DECISIONS.md multi-company
    entry). Read-only — nothing is persisted here."""
    _require_same_tenant(tenant_id, current_user)
    credential = get_credential_or_404(db, tenant_id)

    client = build_client(credential)
    try:
        return client.list_companies()
    except (OdooAuthError, xmlrpc.client.Fault, OSError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not list companies from Odoo: {exc}",
        ) from exc


@router.put("/company", response_model=OdooCredentialRead)
def select_company(
    tenant_id: uuid.UUID,
    payload: OdooCredentialCompanySelect,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("can_manage_connection")),
) -> TenantOdooCredential:
    """Confirming a company selection (even "All companies", i.e. both
    fields None) is the explicit "Activate" step that completes staged
    onboarding — see DECISIONS.md "Odoo connection state machine". Calling
    this again later just rescopes an already-active connection."""
    _require_same_tenant(tenant_id, current_user)
    credential = get_credential_or_404(db, tenant_id)

    credential.company_id = payload.company_id
    credential.company_name = payload.company_name
    if credential.state != "active":
        credential.state = "active"
        credential.activated_at = datetime.now(UTC)
    db.commit()
    db.refresh(credential)
    return credential
