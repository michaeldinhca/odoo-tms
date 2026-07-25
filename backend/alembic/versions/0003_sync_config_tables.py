"""synced_operation_types, synced_warehouses, synced_pickings

Revision ID: 0003_sync_config
Revises: 0002_add_company
Create Date: 2026-07-25

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_sync_config"
down_revision: str | None = "0002_add_company"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "synced_operation_types",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("odoo_operation_type_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("code", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("warehouse_id", sa.Integer(), nullable=True),
        sa.Column("is_synced", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "tenant_id", "odoo_operation_type_id", name="uq_synced_operation_types_tenant_odoo_id"
        ),
    )
    op.create_index(
        "ix_synced_operation_types_tenant_id", "synced_operation_types", ["tenant_id"]
    )

    op.create_table(
        "synced_warehouses",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("odoo_warehouse_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("code", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("street", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("street2", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("city", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("state_id", sa.Integer(), nullable=True),
        sa.Column("state_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("country_id", sa.Integer(), nullable=True),
        sa.Column("country_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("zip", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("is_synced", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "tenant_id", "odoo_warehouse_id", name="uq_synced_warehouses_tenant_odoo_id"
        ),
    )
    op.create_index("ix_synced_warehouses_tenant_id", "synced_warehouses", ["tenant_id"])

    op.create_table(
        "synced_pickings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("odoo_picking_id", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("customer_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("items_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("street", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("street2", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("city", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("state_id", sa.Integer(), nullable=True),
        sa.Column("state_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("country_id", sa.Integer(), nullable=True),
        sa.Column("country_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("zip", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("scheduled_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("picking_type_id", sa.Integer(), nullable=True),
        sa.Column("warehouse_id", sa.Integer(), nullable=True),
        sa.Column("warehouse_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("origin", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("weight", sa.Float(), nullable=True),
        sa.Column("shipping_weight", sa.Float(), nullable=True),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "tenant_id", "odoo_picking_id", name="uq_synced_pickings_tenant_odoo_id"
        ),
    )
    op.create_index("ix_synced_pickings_tenant_id", "synced_pickings", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_synced_pickings_tenant_id", table_name="synced_pickings")
    op.drop_table("synced_pickings")

    op.drop_index("ix_synced_warehouses_tenant_id", table_name="synced_warehouses")
    op.drop_table("synced_warehouses")

    op.drop_index("ix_synced_operation_types_tenant_id", table_name="synced_operation_types")
    op.drop_table("synced_operation_types")
