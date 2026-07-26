"""add warehouse lat/lng and destination_locations + their warehouse routing

Revision ID: 0008_destinations
Revises: 0007_user_perms
Create Date: 2026-07-26

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0008_destinations"
down_revision: str | None = "0007_user_perms"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("synced_warehouses", sa.Column("lat", sa.Float(), nullable=True))
    op.add_column("synced_warehouses", sa.Column("lng", sa.Float(), nullable=True))

    op.create_table(
        "destination_locations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("street", sa.String(length=255), nullable=False),
        sa.Column("street2", sa.String(length=255), nullable=False),
        sa.Column("city", sa.String(length=255), nullable=False),
        sa.Column("state", sa.String(length=255), nullable=False),
        sa.Column("country", sa.String(length=255), nullable=False),
        sa.Column("zip", sa.String(length=20), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lng", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_destination_locations_tenant_id", "destination_locations", ["tenant_id"]
    )

    op.create_table(
        "warehouse_destination_locations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("warehouse_id", sa.Uuid(), nullable=False),
        sa.Column("destination_location_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["warehouse_id"], ["synced_warehouses.id"]),
        sa.ForeignKeyConstraint(["destination_location_id"], ["destination_locations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "warehouse_id", "destination_location_id", name="uq_warehouse_destination_location"
        ),
    )
    op.create_index(
        "ix_warehouse_destination_locations_tenant_id",
        "warehouse_destination_locations",
        ["tenant_id"],
    )
    op.create_index(
        "ix_warehouse_destination_locations_warehouse_id",
        "warehouse_destination_locations",
        ["warehouse_id"],
    )
    op.create_index(
        "ix_warehouse_destination_locations_destination_location_id",
        "warehouse_destination_locations",
        ["destination_location_id"],
    )


def downgrade() -> None:
    op.drop_table("warehouse_destination_locations")
    op.drop_table("destination_locations")
    op.drop_column("synced_warehouses", "lng")
    op.drop_column("synced_warehouses", "lat")
