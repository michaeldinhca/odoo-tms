"""Tenant lifecycle management. There's no self-service signup and the
public tenant-CRUD HTTP endpoints were removed (they were unauthenticated
and unused by the frontend — see DECISIONS.md), so this is the only way
to onboard a new client or update its subscription/billing metadata. Run
via, e.g.:
    docker compose exec backend python -m app.manage_tenants create \
        --name "Acme Co" --admin-email admin@acme.com --admin-password ... \
        --plan pro --expire-date 2027-01-01 --warning-period-days 14
    docker compose exec backend python -m app.manage_tenants list
    docker compose exec backend python -m app.manage_tenants update \
        --name "Acme Co" --status suspended

See TODO.md for the planned future direction (managing the tenant list
from Odoo instead of this script).
"""

import argparse
import sys
import uuid
from datetime import UTC, datetime

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models.tenant import Tenant
from app.models.user import User
from app.services.tenant_subscription import compute_subscription_state, compute_warning_date

ALL_PERMISSIONS = {
    "can_manage_connection": True,
    "can_manage_warehouses": True,
    "can_manage_operation_types": True,
    "can_manage_fleet": True,
    "can_run_planning": True,
    "can_use_load_planning": True,
}

# Returned by _parse_date for "none"/"clear" so `update` can distinguish
# "explicitly clear this field" from "flag not passed at all" (both of
# which would otherwise show up as None).
_CLEAR = object()


def _parse_date(value: str):
    if value.strip().lower() in ("none", "clear", ""):
        return _CLEAR
    try:
        return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=UTC)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"expected YYYY-MM-DD (or 'none' to clear), got {value!r}"
        ) from exc


def cmd_create(args: argparse.Namespace) -> None:
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == args.admin_email).first() is not None:
            print(
                f"A user with email {args.admin_email} already exists — aborting.",
                file=sys.stderr,
            )
            sys.exit(1)

        tenant = Tenant(
            name=args.name,
            plan_name=args.plan or "",
            billing_email=args.billing_email,
            expire_date=None if args.expire_date is _CLEAR else args.expire_date,
            warning_period_days=args.warning_period_days,
            notes=args.notes or "",
        )
        db.add(tenant)
        db.flush()

        user = User(
            tenant_id=tenant.id,
            email=args.admin_email,
            password_hash=hash_password(args.admin_password),
            role="admin",
            **ALL_PERMISSIONS,
        )
        db.add(user)
        db.commit()

        print(f"Created tenant '{tenant.name}' ({tenant.id})")
        print(f"Created admin user {args.admin_email} — share the password out of band.")
    finally:
        db.close()


def cmd_list(args: argparse.Namespace) -> None:
    db = SessionLocal()
    try:
        rows: list[tuple[str, ...]] = []
        for tenant in db.query(Tenant).order_by(Tenant.name).all():
            state = compute_subscription_state(tenant)
            if args.state and state != args.state:
                continue
            user_count = db.query(User).filter(User.tenant_id == tenant.id).count()
            warning_date = compute_warning_date(tenant)
            rows.append(
                (
                    str(tenant.id),
                    tenant.name,
                    state,
                    tenant.plan_name or "-",
                    tenant.expire_date.date().isoformat() if tenant.expire_date else "-",
                    warning_date.date().isoformat() if warning_date else "-",
                    str(user_count),
                )
            )
        _print_table(("ID", "Name", "State", "Plan", "Expires", "Warns", "Users"), rows)
    finally:
        db.close()


def cmd_update(args: argparse.Namespace) -> None:
    db = SessionLocal()
    try:
        tenant = _find_tenant(db, args)
        if tenant is None:
            print("Tenant not found.", file=sys.stderr)
            sys.exit(1)

        if args.status is not None:
            tenant.status = args.status
        if args.plan is not None:
            tenant.plan_name = args.plan
        if args.billing_email is not None:
            tenant.billing_email = args.billing_email
        if args.expire_date is not None:
            tenant.expire_date = None if args.expire_date is _CLEAR else args.expire_date
        if args.warning_period_days is not None:
            tenant.warning_period_days = args.warning_period_days
        if args.notes is not None:
            tenant.notes = args.notes

        db.commit()
        state = compute_subscription_state(tenant)
        print(f"Updated tenant '{tenant.name}' ({tenant.id}) — state is now {state}")
    finally:
        db.close()


def _find_tenant(db, args: argparse.Namespace) -> Tenant | None:
    if args.tenant_id:
        return db.query(Tenant).filter(Tenant.id == uuid.UUID(args.tenant_id)).first()
    return db.query(Tenant).filter(Tenant.name == args.name).first()


def _print_table(headers: tuple[str, ...], rows: list[tuple[str, ...]]) -> None:
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def fmt(row: tuple[str, ...]) -> str:
        return "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row))

    print(fmt(headers))
    print("  ".join("-" * w for w in widths))
    for row in rows:
        print(fmt(row))
    if not rows:
        print("(no matching tenants)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="manage_tenants")
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create", help="Create a new tenant + its first admin user")
    create.add_argument("--name", required=True)
    create.add_argument("--admin-email", required=True)
    create.add_argument("--admin-password", required=True)
    create.add_argument("--plan", default=None)
    create.add_argument("--billing-email", default=None)
    create.add_argument("--expire-date", type=_parse_date, default=None)
    create.add_argument("--warning-period-days", type=int, default=None)
    create.add_argument("--notes", default=None)
    create.set_defaults(func=cmd_create)

    list_cmd = sub.add_parser("list", help="List tenants and their subscription state")
    list_cmd.add_argument(
        "--state", choices=["active", "warning", "expired", "suspended", "cancelled"], default=None
    )
    list_cmd.set_defaults(func=cmd_list)

    update = sub.add_parser("update", help="Update a tenant's subscription/billing fields")
    lookup = update.add_mutually_exclusive_group(required=True)
    lookup.add_argument("--tenant-id")
    lookup.add_argument("--name")
    update.add_argument("--status", choices=["active", "suspended", "cancelled"], default=None)
    update.add_argument("--plan", default=None)
    update.add_argument("--billing-email", default=None)
    update.add_argument("--expire-date", type=_parse_date, default=None)
    update.add_argument("--warning-period-days", type=int, default=None)
    update.add_argument("--notes", default=None)
    update.set_defaults(func=cmd_update)

    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
