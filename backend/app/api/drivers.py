import uuid
import xmlrpc.client

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user, get_db
from app.models.driver import Driver
from app.models.odoo_credential import TenantOdooCredential
from app.schemas.fleet import (
    DriverCreate,
    DriverLinkOdoo,
    DriverRead,
    DriverStatus,
    DriverUpdate,
    OdooEmployeeList,
)
from app.services.fleet_link_sync import sync_link_staleness
from app.services.fleet_lookup import fetch_employees
from app.services.odoo_client import OdooAuthError
from app.services.odoo_connection import build_client

router = APIRouter(prefix="/tenants/{tenant_id}/drivers", tags=["drivers"])

ODOO_ERRORS = (OdooAuthError, xmlrpc.client.Fault, OSError)


def _require_same_tenant(tenant_id: uuid.UUID, current_user: CurrentUser) -> None:
    if tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch")


def _get_driver_or_404(db: Session, tenant_id: uuid.UUID, driver_id: uuid.UUID) -> Driver:
    driver = db.query(Driver).filter_by(id=driver_id, tenant_id=tenant_id).first()
    if driver is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")
    return driver


@router.get("", response_model=list[DriverRead])
def list_drivers(
    tenant_id: uuid.UUID,
    status_filter: DriverStatus | None = None,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[Driver]:
    _require_same_tenant(tenant_id, current_user)
    query = db.query(Driver).filter_by(tenant_id=tenant_id)
    if status_filter is not None:
        query = query.filter(Driver.status == status_filter)
    return query.order_by(Driver.name).all()


@router.post("", response_model=DriverRead, status_code=status.HTTP_201_CREATED)
def create_driver(
    tenant_id: uuid.UUID,
    payload: DriverCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Driver:
    _require_same_tenant(tenant_id, current_user)
    driver = Driver(tenant_id=tenant_id, **payload.model_dump())
    db.add(driver)
    db.commit()
    db.refresh(driver)
    return driver


@router.get("/odoo-employees", response_model=OdooEmployeeList)
def list_odoo_employees(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> OdooEmployeeList:
    """Browse-only — never auto-creates local drivers from this list."""
    _require_same_tenant(tenant_id, current_user)
    credential = (
        db.query(TenantOdooCredential).filter(TenantOdooCredential.tenant_id == tenant_id).first()
    )
    if credential is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No Odoo connection configured"
        )

    client = build_client(credential)
    try:
        available, employees = fetch_employees(
            client, company_id=credential.company_id, version_major=credential.server_version_major
        )
    except ODOO_ERRORS as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not fetch employees from Odoo: {exc}",
        ) from exc

    if available:
        # Module absent doesn't mean "every link is now stale" — only flag
        # staleness when we can actually see the current Odoo employee list.
        sync_link_staleness(
            db, tenant_id, Driver, "odoo_employee_id", {e["id"] for e in employees}
        )

    return OdooEmployeeList(available=available, employees=employees)


@router.get("/{driver_id}", response_model=DriverRead)
def get_driver(
    tenant_id: uuid.UUID,
    driver_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Driver:
    _require_same_tenant(tenant_id, current_user)
    return _get_driver_or_404(db, tenant_id, driver_id)


@router.put("/{driver_id}", response_model=DriverRead)
def update_driver(
    tenant_id: uuid.UUID,
    driver_id: uuid.UUID,
    payload: DriverUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Driver:
    _require_same_tenant(tenant_id, current_user)
    driver = _get_driver_or_404(db, tenant_id, driver_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(driver, field, value)
    db.commit()
    db.refresh(driver)
    return driver


@router.delete("/{driver_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_driver(
    tenant_id: uuid.UUID,
    driver_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> None:
    _require_same_tenant(tenant_id, current_user)
    driver = _get_driver_or_404(db, tenant_id, driver_id)

    # No trip/assignment-history table exists yet — the checkable proxy for
    # "has current assignments" is simply an active status. See DECISIONS.md.
    if driver.status == "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete an active driver; set status to inactive first",
        )

    db.delete(driver)
    db.commit()


@router.put("/{driver_id}/odoo-link", response_model=DriverRead)
def link_driver_to_odoo(
    tenant_id: uuid.UUID,
    driver_id: uuid.UUID,
    payload: DriverLinkOdoo,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Driver:
    """Sets the Odoo cross-reference only — never touches any other field on
    the local driver (see DECISIONS.md)."""
    _require_same_tenant(tenant_id, current_user)
    driver = _get_driver_or_404(db, tenant_id, driver_id)
    driver.odoo_employee_id = payload.odoo_employee_id
    driver.odoo_link_status = "linked"
    db.commit()
    db.refresh(driver)
    return driver


@router.delete("/{driver_id}/odoo-link", response_model=DriverRead)
def unlink_driver_from_odoo(
    tenant_id: uuid.UUID,
    driver_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Driver:
    _require_same_tenant(tenant_id, current_user)
    driver = _get_driver_or_404(db, tenant_id, driver_id)
    driver.odoo_employee_id = None
    driver.odoo_link_status = "unlinked"
    db.commit()
    db.refresh(driver)
    return driver
