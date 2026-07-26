"""Dev-only bootstrap: creates one tenant + one login user if none exist.

MVP has no self-registration/invite flow (see SPEC.md's endpoint list) — this
script is the only way to get a first user in place. Run with:
    docker compose exec backend python -m app.seed
"""

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models.tenant import Tenant
from app.models.user import User

DEFAULT_TENANT_NAME = "Demo Tenant"
DEFAULT_EMAIL = "admin@example.com"
DEFAULT_PASSWORD = "changeme123"


def seed() -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == DEFAULT_EMAIL).first()
        if user is not None:
            print(f"User {DEFAULT_EMAIL} already exists (tenant_id={user.tenant_id}); skipping.")
            return

        tenant = Tenant(name=DEFAULT_TENANT_NAME)
        db.add(tenant)
        db.flush()

        user = User(
            tenant_id=tenant.id,
            email=DEFAULT_EMAIL,
            password_hash=hash_password(DEFAULT_PASSWORD),
            role="admin",
            can_manage_connection=True,
            can_manage_warehouses=True,
            can_manage_operation_types=True,
            can_manage_fleet=True,
            can_run_planning=True,
            can_use_load_planning=True,
        )
        db.add(user)
        db.commit()

        print(f"Seeded tenant '{DEFAULT_TENANT_NAME}' ({tenant.id})")
        print(f"Seeded user {DEFAULT_EMAIL} / {DEFAULT_PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
