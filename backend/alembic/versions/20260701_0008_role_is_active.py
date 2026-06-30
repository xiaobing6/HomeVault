"""add role active flag

Revision ID: 20260701_0008
Revises: 20260628_0007
Create Date: 2026-07-01 00:08:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260701_0008"
down_revision = "20260628_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "roles",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("roles", "is_active")
