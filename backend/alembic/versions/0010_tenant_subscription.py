"""add subscription/billing metadata to tenants

Revision ID: 0010_tenant_subscription
Revises: 0009_warehouse_routes
Create Date: 2026-07-26

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0010_tenant_subscription"
down_revision: str | None = "0009_warehouse_routes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
    )
    op.add_column(
        "tenants",
        sa.Column("plan_name", sa.String(length=100), nullable=False, server_default=""),
    )
    op.add_column("tenants", sa.Column("billing_email", sa.String(length=255), nullable=True))
    op.add_column("tenants", sa.Column("expire_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tenants", sa.Column("warning_period_days", sa.Integer(), nullable=True))
    op.add_column(
        "tenants", sa.Column("notes", sa.Text(), nullable=False, server_default="")
    )


def downgrade() -> None:
    op.drop_column("tenants", "notes")
    op.drop_column("tenants", "warning_period_days")
    op.drop_column("tenants", "expire_date")
    op.drop_column("tenants", "billing_email")
    op.drop_column("tenants", "plan_name")
    op.drop_column("tenants", "status")
