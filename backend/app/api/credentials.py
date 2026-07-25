import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user, get_db
from app.core.crypto import decrypt_secret, encrypt_secret
from app.models.odoo_credential import TenantOdooCredential
from app.schemas.credentials import (
    OdooCredentialRead,
    OdooCredentialTestResult,
    OdooCredentialUpsert,
)
from app.services.odoo_client import OdooClient

router = APIRouter(prefix="/tenants/{tenant_id}/credentials", tags=["credentials"])


def _require_same_tenant(tenant_id: uuid.UUID, current_user: CurrentUser) -> None:
    if tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch")


def _get_credential_or_404(db: Session, tenant_id: uuid.UUID) -> TenantOdooCredential:
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


@router.get("", response_model=OdooCredentialRead)
def get_credential(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> TenantOdooCredential:
    _require_same_tenant(tenant_id, current_user)
    return _get_credential_or_404(db, tenant_id)


@router.put("", response_model=OdooCredentialRead)
def upsert_credential(
    tenant_id: uuid.UUID,
    payload: OdooCredentialUpsert,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> TenantOdooCredential:
    _require_same_tenant(tenant_id, current_user)
    credential = (
        db.query(TenantOdooCredential)
        .filter(TenantOdooCredential.tenant_id == tenant_id)
        .first()
    )
    if credential is None:
        credential = TenantOdooCredential(tenant_id=tenant_id)
        db.add(credential)

    credential.url = payload.url
    credential.db = payload.db
    credential.username = payload.username
    credential.encrypted_key = encrypt_secret(payload.api_key)

    db.commit()
    db.refresh(credential)
    return credential


@router.post("/test", response_model=OdooCredentialTestResult)
def test_credential(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> OdooCredentialTestResult:
    _require_same_tenant(tenant_id, current_user)
    credential = _get_credential_or_404(db, tenant_id)

    client = OdooClient(
        url=credential.url,
        db=credential.db,
        username=credential.username,
        api_key=decrypt_secret(credential.encrypted_key),
    )
    success, detail = client.test_connection()
    return OdooCredentialTestResult(success=success, detail=detail)
