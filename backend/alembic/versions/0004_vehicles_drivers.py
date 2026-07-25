"""vehicles, drivers

Revision ID: 0004_vehicles_drivers
Revises: 0003_sync_config
Create Date: 2026-07-25

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_vehicles_drivers"
down_revision: str | None = "0003_sync_config"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "vehicles",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("license_plate", sa.String(length=50), nullable=True),
        sa.Column("vehicle_type", sa.String(length=20), nullable=False, server_default="van"),
        sa.Column("payload_capacity_kg", sa.Float(), nullable=True),
        sa.Column("volume_capacity_m3", sa.Float(), nullable=True),
        sa.Column("fuel_consumption_per_100km", sa.Float(), nullable=True),
        sa.Column(
            "home_warehouse_id", sa.Uuid(), sa.ForeignKey("synced_warehouses.id"), nullable=True
        ),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("odoo_fleet_vehicle_id", sa.Integer(), nullable=True),
        sa.Column(
            "odoo_link_status", sa.String(length=20), nullable=False, server_default="unlinked"
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_vehicles_tenant_id", "vehicles", ["tenant_id"])

    op.create_table(
        "drivers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("license_number", sa.String(length=100), nullable=True),
        sa.Column("id_passport_number", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assigned_vehicle_id", sa.Uuid(), sa.ForeignKey("vehicles.id"), nullable=True),
        sa.Column("odoo_employee_id", sa.Integer(), nullable=True),
        sa.Column(
            "odoo_link_status", sa.String(length=20), nullable=False, server_default="unlinked"
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_drivers_tenant_id", "drivers", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_drivers_tenant_id", table_name="drivers")
    op.drop_table("drivers")

    op.drop_index("ix_vehicles_tenant_id", table_name="vehicles")
    op.drop_table("vehicles")
