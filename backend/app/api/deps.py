import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.db import get_db  # noqa: F401 - re-exported for use as a route dependency
from app.core.security import decode_access_token

_bearer_scheme = HTTPBearer()


class CurrentUser:
    def __init__(self, user_id: uuid.UUID, tenant_id: uuid.UUID):
        self.user_id = user_id
        self.tenant_id = tenant_id


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> CurrentUser:
    try:
        payload = decode_access_token(credentials.credentials)
        return CurrentUser(
            user_id=uuid.UUID(payload["sub"]), tenant_id=uuid.UUID(payload["tenant_id"])
        )
    except (ValueError, KeyError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        ) from exc
