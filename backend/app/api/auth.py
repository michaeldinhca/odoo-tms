from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user, get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import SelfPasswordChange, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )
    token = create_access_token(subject=str(user.id), tenant_id=str(user.tenant_id))
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserRead)
def get_me(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> User:
    """Any authenticated user can read their own role/permissions — this
    is what the frontend uses to decide what to show/hide. Not a
    user-management action (see app.api.users, which is admin-only)."""
    user = db.get(User, current_user.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.put("/password", response_model=UserRead)
def change_my_password(
    payload: SelfPasswordChange,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> User:
    user = db.get(User, current_user.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect"
        )
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    db.refresh(user)
    return user
