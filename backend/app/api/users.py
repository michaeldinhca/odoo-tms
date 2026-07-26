import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_db, require_admin
from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import AdminPasswordReset, UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/tenants/{tenant_id}/users", tags=["users"])


def _require_same_tenant(tenant_id: uuid.UUID, current_user: CurrentUser) -> None:
    if tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch")


def _get_user_or_404(db: Session, tenant_id: uuid.UUID, user_id: uuid.UUID) -> User:
    user = db.query(User).filter_by(id=user_id, tenant_id=tenant_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def _admin_count(
    db: Session, tenant_id: uuid.UUID, exclude_user_id: uuid.UUID | None = None
) -> int:
    query = db.query(User).filter_by(tenant_id=tenant_id, role="admin")
    if exclude_user_id is not None:
        query = query.filter(User.id != exclude_user_id)
    return query.count()


@router.get("", response_model=list[UserRead])
def list_users(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
) -> list[User]:
    _require_same_tenant(tenant_id, current_user)
    return db.query(User).filter_by(tenant_id=tenant_id).order_by(User.email).all()


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    tenant_id: uuid.UUID,
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
) -> User:
    """No invite-email flow — nothing in this project sends email yet, so
    an admin sets the initial password directly here and communicates it
    out of band (see TODO.md)."""
    _require_same_tenant(tenant_id, current_user)

    existing = db.query(User).filter(User.email == payload.email).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="A user with this email already exists"
        )

    user = User(
        tenant_id=tenant_id,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        can_manage_connection=payload.can_manage_connection,
        can_manage_warehouses=payload.can_manage_warehouses,
        can_manage_operation_types=payload.can_manage_operation_types,
        can_manage_fleet=payload.can_manage_fleet,
        can_run_planning=payload.can_run_planning,
        can_use_load_planning=payload.can_use_load_planning,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.put("/{user_id}", response_model=UserRead)
def update_user(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
) -> User:
    _require_same_tenant(tenant_id, current_user)
    user = _get_user_or_404(db, tenant_id, user_id)
    updates = payload.model_dump(exclude_unset=True)

    if "email" in updates and updates["email"] != user.email:
        existing = db.query(User).filter(User.email == updates["email"]).first()
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email already exists",
            )

    # Demoting the last remaining admin would lock the tenant out of its
    # own user management — same reasoning as the delete guard below.
    if "role" in updates and updates["role"] != "admin" and user.role == "admin":
        if _admin_count(db, tenant_id, exclude_user_id=user.id) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote the last admin — promote another user first",
            )

    for field, value in updates.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
) -> None:
    _require_same_tenant(tenant_id, current_user)
    user = _get_user_or_404(db, tenant_id, user_id)

    if user.role == "admin" and _admin_count(db, tenant_id, exclude_user_id=user.id) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the last admin — promote another user first",
        )

    db.delete(user)
    db.commit()


@router.put("/{user_id}/password", response_model=UserRead)
def reset_user_password(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: AdminPasswordReset,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
) -> User:
    _require_same_tenant(tenant_id, current_user)
    user = _get_user_or_404(db, tenant_id, user_id)
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    db.refresh(user)
    return user
