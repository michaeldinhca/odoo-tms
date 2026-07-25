import uuid
import xmlrpc.client
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user, get_db
from app.models.odoo_credential import TenantOdooCredential
from app.models.planning_run import PlanningRun
from app.schemas.planning import PlanningRunRequest, PlanningRunResult
from app.services.odoo_client import OdooAuthError
from app.services.odoo_connection import build_client
from app.services.picking_sync import upsert_synced_pickings
from app.services.planning.runner import run_planning_sync
from app.services.sync_config import get_synced_operation_type_ids, get_warehouse_by_picking_type

# Anything raised while talking to a customer's Odoo instance — bad
# credentials, DNS/network failures, malformed XML-RPC responses — is an
# upstream problem, not ours; surface it as 502 rather than a raw 500.
ODOO_ERRORS = (OdooAuthError, xmlrpc.client.Fault, OSError)

router = APIRouter(prefix="/planning", tags=["planning"])


def _to_result_schema(run: PlanningRun) -> PlanningRunResult:
    result_json = run.result_json or {}
    return PlanningRunResult(
        run_id=run.id,
        tenant_id=run.tenant_id,
        status=run.status,
        routes=result_json.get("routes", []),
        unassigned_picking_ids=result_json.get("unassigned_picking_ids", []),
        created_at=run.created_at,
        completed_at=run.completed_at,
    )


@router.post("/run", response_model=PlanningRunResult)
def run_planning(
    payload: PlanningRunRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> PlanningRunResult:
    if payload.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch")

    credential = (
        db.query(TenantOdooCredential)
        .filter(TenantOdooCredential.tenant_id == payload.tenant_id)
        .first()
    )
    if credential is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No Odoo connection configured"
        )

    run = PlanningRun(tenant_id=payload.tenant_id, status="running")
    db.add(run)
    db.commit()
    db.refresh(run)

    client = build_client(credential)
    synced_operation_type_ids = get_synced_operation_type_ids(db, payload.tenant_id)
    warehouse_by_picking_type = get_warehouse_by_picking_type(db, payload.tenant_id)

    try:
        result = run_planning_sync(
            client,
            company_id=credential.company_id,
            synced_operation_type_ids=synced_operation_type_ids,
            warehouse_by_picking_type=warehouse_by_picking_type,
        )
    except ODOO_ERRORS as exc:
        run.status = "failed"
        run.result_json = {"error": str(exc)}
        run.completed_at = datetime.now(UTC)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not complete planning run against Odoo: {exc}",
        ) from exc

    orders = result.pop("orders", [])
    upsert_synced_pickings(db, payload.tenant_id, orders)

    run.status = "done"
    run.result_json = result
    run.completed_at = datetime.now(UTC)
    db.commit()
    db.refresh(run)
    return _to_result_schema(run)


@router.get("/results/{run_id}", response_model=PlanningRunResult)
def get_planning_result(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> PlanningRunResult:
    run = db.get(PlanningRun, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Planning run not found")
    if run.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch")
    return _to_result_schema(run)
