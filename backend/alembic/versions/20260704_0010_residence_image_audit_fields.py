"""add residence image and audit fields

Revision ID: 20260704_0010
Revises: 20260701_0009
Create Date: 2026-07-04 11:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260704_0010"
down_revision = "20260701_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("residences") as batch_op:
        batch_op.add_column(sa.Column("image_path", sa.String(length=500), nullable=False, server_default=""))
        batch_op.add_column(
            sa.Column("image_original_filename", sa.String(length=255), nullable=False, server_default="")
        )
        batch_op.add_column(sa.Column("image_content_type", sa.String(length=120), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("image_byte_size", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("created_by_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("updated_by_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_residences_created_by_id_users",
            "users",
            ["created_by_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_residences_updated_by_id_users",
            "users",
            ["updated_by_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.drop_column("sort_order")

    if op.get_context().dialect.name != "sqlite":
        op.alter_column("residences", "image_path", server_default=None)
        op.alter_column("residences", "image_original_filename", server_default=None)
        op.alter_column("residences", "image_content_type", server_default=None)
        op.alter_column("residences", "image_byte_size", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("residences") as batch_op:
        batch_op.add_column(sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"))
        batch_op.drop_constraint("fk_residences_updated_by_id_users", type_="foreignkey")
        batch_op.drop_constraint("fk_residences_created_by_id_users", type_="foreignkey")
        batch_op.drop_column("updated_by_id")
        batch_op.drop_column("created_by_id")
        batch_op.drop_column("image_byte_size")
        batch_op.drop_column("image_content_type")
        batch_op.drop_column("image_original_filename")
        batch_op.drop_column("image_path")

    if op.get_context().dialect.name != "sqlite":
        op.alter_column("residences", "sort_order", server_default=None)
