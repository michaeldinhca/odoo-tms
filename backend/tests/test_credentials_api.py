"""State-machine behavior for the tenant's Odoo connection (see DECISIONS.md
"Odoo connection state machine"). Route handlers are called directly, same
pattern as test_vehicles_api.py — no HTTP/JWT plumbing needed."""

import uuid

import pytest
from fastapi import HTTPException

from app.api.credentials import reauthenticate_credential, select_company, upsert_credential
from app.api.deps import CurrentUser
from app.schemas.credentials import OdooCredentialCompanySelect, OdooCredentialUpsert
from app.services.odoo_credential_gate import get_credential_or_404, require_active_instance

TENANT_ID = uuid.uuid4()
USER = CurrentUser(user_id=uuid.uuid4(), tenant_id=TENANT_ID)


def _upsert(session, **overrides):
    defaults = {"url": "https://x.odoo.com", "db": "x", "username": "u", "api_key": "k"}
    defaults.update(overrides)
    return upsert_credential(TENANT_ID, OdooCredentialUpsert(**defaults), session, USER)


def test_first_save_creates_a_draft_credential(sync_db_session):
    credential = _upsert(sync_db_session)

    assert credential.state == "draft"
    assert credential.activated_at is None


def test_resaving_credentials_does_not_touch_state(sync_db_session):
    _upsert(sync_db_session)
    select_company(
        TENANT_ID,
        OdooCredentialCompanySelect(company_id=1, company_name="Co"),
        sync_db_session,
        USER,
    )

    updated = _upsert(sync_db_session, url="https://y.odoo.com")

    assert updated.url == "https://y.odoo.com"
    assert updated.state == "active"  # untouched by a plain re-save


def test_select_company_activates_a_draft_connection(sync_db_session):
    _upsert(sync_db_session)

    activated = select_company(
        TENANT_ID,
        OdooCredentialCompanySelect(company_id=5, company_name="Co"),
        sync_db_session,
        USER,
    )

    assert activated.state == "active"
    assert activated.activated_at is not None
    assert activated.company_id == 5


def test_select_company_with_no_company_still_activates(sync_db_session):
    """Explicitly choosing "All companies" (both fields None) is still a
    valid completion of onboarding — activation isn't gated on picking a
    specific company."""
    _upsert(sync_db_session)

    activated = select_company(
        TENANT_ID,
        OdooCredentialCompanySelect(company_id=None, company_name=None),
        sync_db_session,
        USER,
    )

    assert activated.state == "active"


def test_reselecting_company_while_active_does_not_reset_activated_at(sync_db_session):
    _upsert(sync_db_session)
    first = select_company(
        TENANT_ID,
        OdooCredentialCompanySelect(company_id=1, company_name="A"),
        sync_db_session,
        USER,
    )
    first_activated_at = first.activated_at

    rescoped = select_company(
        TENANT_ID,
        OdooCredentialCompanySelect(company_id=2, company_name="B"),
        sync_db_session,
        USER,
    )

    assert rescoped.activated_at == first_activated_at
    assert rescoped.company_id == 2


def test_reauthenticate_blocked_while_draft(sync_db_session):
    _upsert(sync_db_session)
    payload = OdooCredentialUpsert(
        url="https://x.odoo.com", db="x", username="u", api_key="new-key"
    )

    with pytest.raises(HTTPException) as exc_info:
        reauthenticate_credential(TENANT_ID, payload, sync_db_session, USER)

    assert exc_info.value.status_code == 409


def test_reauthenticate_succeeds_once_active(sync_db_session):
    _upsert(sync_db_session)
    select_company(
        TENANT_ID,
        OdooCredentialCompanySelect(company_id=1, company_name="Co"),
        sync_db_session,
        USER,
    )
    payload = OdooCredentialUpsert(
        url="https://x.odoo.com", db="x", username="u", api_key="rotated-key"
    )

    result = reauthenticate_credential(TENANT_ID, payload, sync_db_session, USER)

    assert result.state == "active"  # unchanged
    assert result.company_id == 1  # untouched by reauthenticate


def test_require_active_instance_raises_404_with_no_credential(sync_db_session):
    with pytest.raises(HTTPException) as exc_info:
        require_active_instance(sync_db_session, TENANT_ID)

    assert exc_info.value.status_code == 404


def test_require_active_instance_raises_409_while_draft(sync_db_session):
    _upsert(sync_db_session)

    with pytest.raises(HTTPException) as exc_info:
        require_active_instance(sync_db_session, TENANT_ID)

    assert exc_info.value.status_code == 409


def test_require_active_instance_returns_credential_once_active(sync_db_session):
    _upsert(sync_db_session)
    select_company(
        TENANT_ID,
        OdooCredentialCompanySelect(company_id=1, company_name="Co"),
        sync_db_session,
        USER,
    )

    credential = require_active_instance(sync_db_session, TENANT_ID)

    assert credential.state == "active"
    assert credential == get_credential_or_404(sync_db_session, TENANT_ID)
