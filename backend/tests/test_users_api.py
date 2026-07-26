"""Route handlers called directly, same pattern as test_vehicles_api.py.
Note: calling them this way bypasses `Depends(require_admin)` entirely —
that gate is tested separately in test_deps_permissions.py. These tests
cover what's actually inside the route bodies: CRUD, uniqueness, and the
last-admin-standing guards."""

import uuid

import pytest
from fastapi import HTTPException

from app.api.deps import CurrentUser
from app.api.users import (
    create_user,
    delete_user,
    list_users,
    reset_user_password,
    update_user,
)
from app.core.security import verify_password
from app.models.user import User
from app.schemas.user import AdminPasswordReset, UserCreate, UserUpdate

TENANT_ID = uuid.uuid4()
ADMIN = CurrentUser(user_id=uuid.uuid4(), tenant_id=TENANT_ID, role="admin")


def _new_user(session, **kwargs):
    kwargs.setdefault("email", "new@example.com")
    kwargs.setdefault("password", "correct-horse-1")
    return create_user(TENANT_ID, UserCreate(**kwargs), session, ADMIN)


def _seed_admin(session) -> User:
    """A second, already-existing admin row — distinct from the `ADMIN`
    `CurrentUser` making the calls, since the last-admin guards count
    rows in the database, not who's asking."""
    user = User(
        tenant_id=TENANT_ID, email="seed-admin@example.com", password_hash="x", role="admin"
    )
    session.add(user)
    session.commit()
    return user


def test_create_and_list_user(sync_db_session):
    _new_user(sync_db_session, role="user", can_run_planning=True)

    users = list_users(TENANT_ID, sync_db_session, ADMIN)

    assert len(users) == 1
    assert users[0].email == "new@example.com"
    assert users[0].role == "user"
    assert users[0].can_run_planning is True
    assert users[0].can_manage_connection is False  # default


def test_create_user_defaults_match_role_free_choice():
    """Defaults live on the schema, not hardcoded per role — admin's
    higher default (all False except run/load-planning, same as "user")
    is a caller choice, not automatic. Confirms UserCreate's own
    defaults rather than asserting behavior the endpoint doesn't have."""
    payload = UserCreate(email="x@example.com", password="correct-horse-1")

    assert payload.role == "user"
    assert payload.can_run_planning is True
    assert payload.can_use_load_planning is True
    assert payload.can_manage_connection is False


def test_create_user_rejects_duplicate_email(sync_db_session):
    _new_user(sync_db_session, email="dup@example.com")

    with pytest.raises(HTTPException) as exc_info:
        _new_user(sync_db_session, email="dup@example.com")

    assert exc_info.value.status_code == 400


def test_create_user_hashes_the_password(sync_db_session):
    created = _new_user(sync_db_session, password="correct-horse-1")

    assert created.password_hash != "correct-horse-1"
    assert verify_password("correct-horse-1", created.password_hash)


def test_update_user_permissions_partial(sync_db_session):
    user = _new_user(sync_db_session, can_manage_warehouses=False)

    updated = update_user(
        TENANT_ID, user.id, UserUpdate(can_manage_warehouses=True), sync_db_session, ADMIN
    )

    assert updated.can_manage_warehouses is True
    assert updated.email == user.email  # untouched


def test_update_user_rejects_duplicate_email(sync_db_session):
    _new_user(sync_db_session, email="taken@example.com")
    other = _new_user(sync_db_session, email="other@example.com")

    with pytest.raises(HTTPException) as exc_info:
        update_user(
            TENANT_ID, other.id, UserUpdate(email="taken@example.com"), sync_db_session, ADMIN
        )

    assert exc_info.value.status_code == 400


def test_cannot_demote_the_last_admin(sync_db_session):
    only_admin = _new_user(sync_db_session, role="admin")

    with pytest.raises(HTTPException) as exc_info:
        update_user(TENANT_ID, only_admin.id, UserUpdate(role="user"), sync_db_session, ADMIN)

    assert exc_info.value.status_code == 400


def test_can_demote_an_admin_when_another_admin_exists(sync_db_session):
    _seed_admin(sync_db_session)
    second_admin = _new_user(sync_db_session, role="admin")

    demoted = update_user(
        TENANT_ID, second_admin.id, UserUpdate(role="user"), sync_db_session, ADMIN
    )

    assert demoted.role == "user"


def test_cannot_delete_the_last_admin(sync_db_session):
    only_admin = _new_user(sync_db_session, role="admin")

    with pytest.raises(HTTPException) as exc_info:
        delete_user(TENANT_ID, only_admin.id, sync_db_session, ADMIN)

    assert exc_info.value.status_code == 400


def test_can_delete_an_admin_when_another_admin_exists(sync_db_session):
    _seed_admin(sync_db_session)
    second_admin = _new_user(sync_db_session, role="admin")

    delete_user(TENANT_ID, second_admin.id, sync_db_session, ADMIN)

    assert [u.email for u in list_users(TENANT_ID, sync_db_session, ADMIN)] == [
        "seed-admin@example.com"
    ]


def test_delete_non_admin_user_always_succeeds(sync_db_session):
    user = _new_user(sync_db_session, role="user")

    delete_user(TENANT_ID, user.id, sync_db_session, ADMIN)

    assert list_users(TENANT_ID, sync_db_session, ADMIN) == []


def test_reset_user_password(sync_db_session):
    user = _new_user(sync_db_session, password="old-password-1")

    updated = reset_user_password(
        TENANT_ID,
        user.id,
        AdminPasswordReset(new_password="new-password-1"),
        sync_db_session,
        ADMIN,
    )

    assert verify_password("new-password-1", updated.password_hash)
    assert not verify_password("old-password-1", updated.password_hash)


def test_users_endpoints_reject_mismatched_tenant(sync_db_session):
    user = _new_user(sync_db_session)
    other_tenant_admin = CurrentUser(user_id=uuid.uuid4(), tenant_id=uuid.uuid4(), role="admin")

    with pytest.raises(HTTPException) as exc_info:
        update_user(
            TENANT_ID,
            user.id,
            UserUpdate(email="x@example.com"),
            sync_db_session,
            other_tenant_admin,
        )

    assert exc_info.value.status_code == 403
