"""add Odoo version tracking fields to tenant_odoo_credentials

Revision ID: 0005_odoo_version
Revises: 0004_vehicles_drivers
Create Date: 2026-07-25

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005_odoo_version"
down_revision: str | None = "0004_vehicles_drivers"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tenant_odoo_credentials", sa.Column("server_version", sa.String(length=50), nullable=True)
    )
    op.add_column(
        "tenant_odoo_credentials", sa.Column("server_version_major", sa.Integer(), nullable=True)
    )
    op.add_column(
        "tenant_odoo_credentials", sa.Column("server_serie", sa.String(length=50), nullable=True)
    )
    op.add_column(
        "tenant_odoo_credentials", sa.Column("protocol_version", sa.Integer(), nullable=True)
    )
    op.add_column(
        "tenant_odoo_credentials",
        sa.Column("version_checked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "tenant_odoo_credentials",
        sa.Column(
            "version_change_detected", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )


def downgrade() -> None:
    op.drop_column("tenant_odoo_credentials", "version_change_detected")
    op.drop_column("tenant_odoo_credentials", "version_checked_at")
    op.drop_column("tenant_odoo_credentials", "protocol_version")
    op.drop_column("tenant_odoo_credentials", "server_serie")
    op.drop_column("tenant_odoo_credentials", "server_version_major")
    op.drop_column("tenant_odoo_credentials", "server_version")
