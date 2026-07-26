"""add role and per-function permission booleans to users

Revision ID: 0007_user_perms
Revises: 0006_state_archive
Create Date: 2026-07-25

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007_user_perms"
down_revision: str | None = "0006_state_archive"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("role", sa.String(length=20), nullable=False, server_default="user")
    )
    op.add_column(
        "users",
        sa.Column("can_manage_connection", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "users",
        sa.Column("can_manage_warehouses", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "users",
        sa.Column(
            "can_manage_operation_types", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.add_column(
        "users",
        sa.Column("can_manage_fleet", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "users",
        sa.Column("can_run_planning", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "users",
        sa.Column("can_use_load_planning", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    # Every user that exists before this migration was created back when
    # there was no permission system at all — i.e. fully trusted. Back-fill
    # them to admin/all-permissions rather than silently locking existing
    # logins out of everything they could already do (same reasoning as
    # migration 0006's credential-state backfill).
    op.execute(
        """
        UPDATE users SET
            role = 'admin',
            can_manage_connection = true,
            can_manage_warehouses = true,
            can_manage_operation_types = true,
            can_manage_fleet = true,
            can_run_planning = true,
            can_use_load_planning = true
        """
    )


def downgrade() -> None:
    op.drop_column("users", "can_use_load_planning")
    op.drop_column("users", "can_run_planning")
    op.drop_column("users", "can_manage_fleet")
    op.drop_column("users", "can_manage_operation_types")
    op.drop_column("users", "can_manage_warehouses")
    op.drop_column("users", "can_manage_connection")
    op.drop_column("users", "role")
