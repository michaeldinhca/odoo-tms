"""add connection state machine fields and archive (active) flags

Revision ID: 0006_state_archive
Revises: 0005_odoo_version
Create Date: 2026-07-25

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006_state_archive"
down_revision: str | None = "0005_odoo_version"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tenant_odoo_credentials",
        sa.Column("state", sa.String(length=20), nullable=False, server_default="draft"),
    )
    op.add_column(
        "tenant_odoo_credentials",
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "tenant_odoo_credentials",
        sa.Column("last_synced_operation_types_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "tenant_odoo_credentials",
        sa.Column("last_synced_warehouses_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Existing rows already have a company_id (or were explicitly scoped to
    # "all companies") from before this state machine existed — treat them
    # as already active rather than forcing every existing tenant back
    # through onboarding.
    op.execute(
        "UPDATE tenant_odoo_credentials SET state = 'active', activated_at = created_at"
    )

    for table, model_name in (
        ("synced_operation_types", "operation type"),
        ("synced_warehouses", "warehouse"),
        ("vehicles", "vehicle"),
        ("drivers", "driver"),
    ):
        op.add_column(
            table,
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        )


def downgrade() -> None:
    for table in ("drivers", "vehicles", "synced_warehouses", "synced_operation_types"):
        op.drop_column(table, "active")

    op.drop_column("tenant_odoo_credentials", "last_synced_warehouses_at")
    op.drop_column("tenant_odoo_credentials", "last_synced_operation_types_at")
    op.drop_column("tenant_odoo_credentials", "activated_at")
    op.drop_column("tenant_odoo_credentials", "state")
