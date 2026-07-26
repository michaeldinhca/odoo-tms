"""Route handlers called directly, same pattern as test_vehicles_api.py."""

import uuid

import pytest
from fastapi import HTTPException

from app.api.auth import change_my_password, get_me
from app.api.deps import CurrentUser
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import SelfPasswordChange

TENANT_ID = uuid.uuid4()


def _seed_user(session, **overrides) -> User:
    defaults = {
        "tenant_id": TENANT_ID,
        "email": "a@example.com",
        "password_hash": hash_password("correct-horse-1"),
    }
    defaults.update(overrides)
    user = User(**defaults)
    session.add(user)
    session.commit()
    return user


def _current_user_for(user: User) -> CurrentUser:
    return CurrentUser(user_id=user.id, tenant_id=user.tenant_id, role=user.role)


def test_get_me_returns_own_role_and_permissions(sync_db_session):
    user = _seed_user(sync_db_session, role="admin", can_manage_fleet=True)

    result = get_me(sync_db_session, _current_user_for(user))

    assert result.email == "a@example.com"
    assert result.role == "admin"
    assert result.can_manage_fleet is True


def test_change_my_password_succeeds_with_correct_current_password(sync_db_session):
    user = _seed_user(sync_db_session)

    updated = change_my_password(
        SelfPasswordChange(current_password="correct-horse-1", new_password="new-password-1"),
        sync_db_session,
        _current_user_for(user),
    )

    assert verify_password("new-password-1", updated.password_hash)


def test_change_my_password_rejects_wrong_current_password(sync_db_session):
    user = _seed_user(sync_db_session)

    with pytest.raises(HTTPException) as exc_info:
        change_my_password(
            SelfPasswordChange(current_password="wrong-password", new_password="new-password-1"),
            sync_db_session,
            _current_user_for(user),
        )

    assert exc_info.value.status_code == 400
