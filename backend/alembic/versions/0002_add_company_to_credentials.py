"""add company_id/company_name to tenant_odoo_credentials

Revision ID: 0002_add_company
Revises: 0001_initial
Create Date: 2026-07-25

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_add_company"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tenant_odoo_credentials", sa.Column("company_id", sa.Integer(), nullable=True)
    )
    op.add_column(
        "tenant_odoo_credentials",
        sa.Column("company_name", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tenant_odoo_credentials", "company_name")
    op.drop_column("tenant_odoo_credentials", "company_id")
