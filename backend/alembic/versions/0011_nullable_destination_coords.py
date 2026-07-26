"""make destination_locations.lat/lng nullable

Revision ID: 0011_nullable_destination_coords
Revises: 0010_tenant_subscription
Create Date: 2026-07-27

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0011_nullable_destination_coords"
down_revision: str | None = "0010_tenant_subscription"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("destination_locations", "lat", existing_type=sa.Float(), nullable=True)
    op.alter_column("destination_locations", "lng", existing_type=sa.Float(), nullable=True)


def downgrade() -> None:
    # Any row auto-created with a null lat/lng (see app.services.picking_sync)
    # would violate the restored NOT NULL constraint — this downgrade only
    # works cleanly if every row has real coordinates by the time it runs.
    op.alter_column("destination_locations", "lng", existing_type=sa.Float(), nullable=False)
    op.alter_column("destination_locations", "lat", existing_type=sa.Float(), nullable=False)
