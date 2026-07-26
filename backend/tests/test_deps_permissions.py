"""`get_current_user`/`require_admin`/`require_permission` — the
permission-gating infrastructure every other router's `Depends(...)` sits
on. Route handlers are tested elsewhere by calling them as plain
functions (bypassing FastAPI's dependency resolution entirely), which
means the gate itself is never exercised that way — it has to be tested
directly, once, here."""

import uuid

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.api.deps import CurrentUser, get_current_user, require_admin, require_permission
from app.core.security import create_access_token
from app.models.user import User

TENANT_ID = uuid.uuid4()


def _user(**overrides) -> CurrentUser:
    defaults = {
        "user_id": uuid.uuid4(),
        "tenant_id": TENANT_ID,
        "role": "user",
        "can_manage_connection": False,
        "can_manage_warehouses": False,
        "can_manage_operation_types": False,
        "can_manage_fleet": False,
        "can_run_planning": False,
        "can_use_load_planning": False,
    }
    defaults.update(overrides)
    return CurrentUser(**defaults)


def test_current_user_defaults_are_permissive_for_direct_construction():
    """Existing tests across the suite build `CurrentUser(user_id=...,
    tenant_id=...)` with no other args — confirms that keeps working as
    fully-permitted, so the permission system didn't require touching
    every one of those call sites."""
    user = CurrentUser(user_id=uuid.uuid4(), tenant_id=TENANT_ID)

    assert user.is_admin is True
    assert user.can_manage_connection is True
    assert user.can_manage_warehouses is True
    assert user.can_manage_fleet is True


def test_require_permission_allows_when_flag_true():
    checker = require_permission("can_manage_warehouses")
    user = _user(can_manage_warehouses=True)

    assert checker(user) is user


def test_require_permission_blocks_when_flag_false():
    checker = require_permission("can_manage_warehouses")
    user = _user(can_manage_warehouses=False)

    with pytest.raises(HTTPException) as exc_info:
        checker(user)

    assert exc_info.value.status_code == 403


def test_require_permission_is_independent_of_role():
    """An admin with a specific flag turned off is still blocked by that
    flag — `role` isn't a bypass (see DECISIONS.md "Role vs. boolean
    permissions")."""
    checker = require_permission("can_manage_fleet")
    admin_without_flag = _user(role="admin", can_manage_fleet=False)

    with pytest.raises(HTTPException) as exc_info:
        checker(admin_without_flag)

    assert exc_info.value.status_code == 403


def test_require_admin_allows_admin_role():
    user = _user(role="admin")

    assert require_admin(user) is user


def test_require_admin_blocks_user_role():
    user = _user(role="user")

    with pytest.raises(HTTPException) as exc_info:
        require_admin(user)

    assert exc_info.value.status_code == 403


def _credential_for(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_get_current_user_reads_role_and_permissions_from_db_not_the_token(sync_db_session):
    user = User(
        tenant_id=TENANT_ID,
        email="a@example.com",
        password_hash="x",
        role="admin",
        can_manage_connection=True,
        can_manage_warehouses=False,
        can_manage_operation_types=False,
        can_manage_fleet=False,
        can_run_planning=True,
        can_use_load_planning=True,
    )
    sync_db_session.add(user)
    sync_db_session.commit()
    token = create_access_token(subject=str(user.id), tenant_id=str(user.tenant_id))

    result = get_current_user(_credential_for(token), sync_db_session)

    assert result.role == "admin"
    assert result.can_manage_connection is True
    assert result.can_manage_warehouses is False


def test_get_current_user_reflects_a_permission_change_made_after_the_token_was_issued(
    sync_db_session,
):
    """The whole point of looking the user up fresh on every request
    instead of trusting JWT claims: a permission revoked mid-session
    takes effect on the very next call, not just after the (up to
    7-day) token eventually expires."""
    user = User(
        tenant_id=TENANT_ID,
        email="a@example.com",
        password_hash="x",
        role="user",
        can_run_planning=True,
    )
    sync_db_session.add(user)
    sync_db_session.commit()
    token = create_access_token(subject=str(user.id), tenant_id=str(user.tenant_id))

    before = get_current_user(_credential_for(token), sync_db_session)
    assert before.can_run_planning is True

    user.can_run_planning = False
    sync_db_session.commit()

    after = get_current_user(_credential_for(token), sync_db_session)
    assert after.can_run_planning is False


def test_get_current_user_rejects_a_token_for_a_deleted_user(sync_db_session):
    user = User(tenant_id=TENANT_ID, email="a@example.com", password_hash="x")
    sync_db_session.add(user)
    sync_db_session.commit()
    token = create_access_token(subject=str(user.id), tenant_id=str(user.tenant_id))

    sync_db_session.delete(user)
    sync_db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(_credential_for(token), sync_db_session)

    assert exc_info.value.status_code == 401
