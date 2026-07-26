import uuid
from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.db import get_db  # noqa: F401 - re-exported for use as a route dependency
from app.core.security import decode_access_token
from app.models.user import User

_bearer_scheme = HTTPBearer()


class CurrentUser:
    """Constructor defaults are deliberately permissive (role="admin",
    every permission True) so code that builds one directly — every
    existing test calls routes as plain functions with a hand-built
    `CurrentUser(user_id=..., tenant_id=...)` — doesn't need updating for
    the permission system. Only `get_current_user` (the real,
    HTTP-serving path) ever passes explicit values, always freshly read
    from the database; see its docstring for why."""

    def __init__(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        role: str = "admin",
        can_manage_connection: bool = True,
        can_manage_warehouses: bool = True,
        can_manage_operation_types: bool = True,
        can_manage_fleet: bool = True,
        can_run_planning: bool = True,
        can_use_load_planning: bool = True,
    ):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.role = role
        self.can_manage_connection = can_manage_connection
        self.can_manage_warehouses = can_manage_warehouses
        self.can_manage_operation_types = can_manage_operation_types
        self.can_manage_fleet = can_manage_fleet
        self.can_run_planning = can_run_planning
        self.can_use_load_planning = can_use_load_planning

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> CurrentUser:
    """Looks the user up fresh on every request rather than trusting
    role/permission claims baked into the JWT — with a 7-day token
    lifetime (see DECISIONS.md "Session lifetime extended to 7 days"), a
    permission revoked (or a user deleted) mid-session must take effect
    immediately, not just after the token eventually expires. The JWT
    still carries `sub`/`tenant_id` for identity; everything else is
    read from the `users` row on every call."""
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = uuid.UUID(payload["sub"])
        tenant_id = uuid.UUID(payload["tenant_id"])
    except (ValueError, KeyError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        ) from exc

    user = db.get(User, user_id)
    if user is None or user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    return CurrentUser(
        user_id=user.id,
        tenant_id=user.tenant_id,
        role=user.role,
        can_manage_connection=user.can_manage_connection,
        can_manage_warehouses=user.can_manage_warehouses,
        can_manage_operation_types=user.can_manage_operation_types,
        can_manage_fleet=user.can_manage_fleet,
        can_run_planning=user.can_run_planning,
        can_use_load_planning=user.can_use_load_planning,
    )


def require_admin(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Gate for the user-management endpoints only. Deliberately the one
    place `role` acts as a hard bypass-proof gate rather than a `can_*`
    boolean — see `app.api.users` for the last-admin-standing guards this
    pairs with."""
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


def require_permission(flag_name: str) -> Callable[[CurrentUser], CurrentUser]:
    """Factory for a per-function permission gate, e.g.
    `Depends(require_permission("can_manage_warehouses"))`. Independent of
    `role` on purpose: an admin's everyday access runs through the same
    boolean flags as anyone else's, not a role bypass, so turning a flag
    off actually takes it away — even from an admin (see DECISIONS.md
    "Role vs. boolean permissions")."""

    def _check(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not getattr(current_user, flag_name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to do this",
            )
        return current_user

    return _check
