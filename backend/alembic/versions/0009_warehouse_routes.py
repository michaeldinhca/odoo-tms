"""replace flat warehouse_destination_locations with ordered warehouse_routes + route_stops

Revision ID: 0009_warehouse_routes
Revises: 0008_destinations
Create Date: 2026-07-26

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0009_warehouse_routes"
down_revision: str | None = "0008_destinations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # warehouse_destination_locations shipped same-day with no real usage
    # yet (confirmed empty live) — replaced by ordered, colored routes
    # below. This is the first hard DROP TABLE in this project's migration
    # history on a table that's actually been live (every prior drop_table
    # call lives in a downgrade(), reverting its own just-applied
    # migration), so fail loudly instead of silently discarding rows if
    # that "confirmed empty" assumption doesn't hold by the time this runs.
    row_count = op.get_bind().execute(
        sa.text("SELECT COUNT(*) FROM warehouse_destination_locations")
    ).scalar()
    if row_count:
        raise RuntimeError(
            f"warehouse_destination_locations has {row_count} row(s) — refusing to drop "
            "a non-empty table. This migration assumed the table was unused; write a "
            "data-preserving migration instead of editing this guard away."
        )
    op.drop_table("warehouse_destination_locations")

    op.create_table(
        "warehouse_routes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("warehouse_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("color", sa.String(length=7), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["warehouse_id"], ["synced_warehouses.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_warehouse_routes_tenant_id", "warehouse_routes", ["tenant_id"])
    op.create_index("ix_warehouse_routes_warehouse_id", "warehouse_routes", ["warehouse_id"])

    op.create_table(
        "route_stops",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("route_id", sa.Uuid(), nullable=False),
        sa.Column("destination_location_id", sa.Uuid(), nullable=False),
        sa.Column("stop_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["route_id"], ["warehouse_routes.id"]),
        sa.ForeignKeyConstraint(["destination_location_id"], ["destination_locations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("route_id", "destination_location_id", name="uq_route_stop"),
    )
    op.create_index("ix_route_stops_tenant_id", "route_stops", ["tenant_id"])
    op.create_index("ix_route_stops_route_id", "route_stops", ["route_id"])
    op.create_index(
        "ix_route_stops_destination_location_id", "route_stops", ["destination_location_id"]
    )


def downgrade() -> None:
    op.drop_table("route_stops")
    op.drop_table("warehouse_routes")

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
