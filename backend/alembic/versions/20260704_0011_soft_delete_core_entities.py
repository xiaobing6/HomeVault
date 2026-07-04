"""add soft delete fields to core entities

Revision ID: 20260704_0011
Revises: 20260704_0010
Create Date: 2026-07-04 15:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260704_0011"
down_revision = "20260704_0010"
branch_labels = None
depends_on = None


def _index_exists(table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return index_name in {index["name"] for index in inspector.get_indexes(table_name)}


def _add_soft_delete_columns(table_name: str, include_reason: bool = False) -> None:
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.add_column(sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()))
        if include_reason:
            batch_op.add_column(sa.Column("delete_reason", sa.String(length=255), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("deleted_by_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            f"fk_{table_name}_deleted_by_id_users",
            "users",
            ["deleted_by_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.create_index(f"ix_{table_name}_is_deleted", table_name, ["is_deleted"])


def _drop_soft_delete_columns(table_name: str, include_reason: bool = False) -> None:
    if _index_exists(table_name, f"ix_{table_name}_is_deleted"):
        op.drop_index(f"ix_{table_name}_is_deleted", table_name=table_name)
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.drop_constraint(f"fk_{table_name}_deleted_by_id_users", type_="foreignkey")
        batch_op.drop_column("deleted_by_id")
        batch_op.drop_column("deleted_at")
        if include_reason:
            batch_op.drop_column("delete_reason")
        batch_op.drop_column("is_deleted")


def upgrade() -> None:
    if _index_exists("residences", "uq_residences_active_name"):
        op.drop_index("uq_residences_active_name", table_name="residences")

    _add_soft_delete_columns("residences")
    _add_soft_delete_columns("location_nodes")
    _add_soft_delete_columns("family_members")
    _add_soft_delete_columns("items", include_reason=True)

    op.create_index(
        "uq_residences_active_name",
        "residences",
        ["name"],
        unique=True,
        sqlite_where=sa.text("is_active = 1 AND is_deleted = 0"),
        postgresql_where=sa.text("is_active = true AND is_deleted = false"),
    )

    if op.get_context().dialect.name != "sqlite":
        for table_name in ("residences", "location_nodes", "family_members", "items"):
            op.alter_column(table_name, "is_deleted", server_default=None)
        op.alter_column("items", "delete_reason", server_default=None)


def downgrade() -> None:
    if _index_exists("residences", "uq_residences_active_name"):
        op.drop_index("uq_residences_active_name", table_name="residences")

    _drop_soft_delete_columns("items", include_reason=True)
    _drop_soft_delete_columns("family_members")
    _drop_soft_delete_columns("location_nodes")
    _drop_soft_delete_columns("residences")

    op.create_index(
        "uq_residences_active_name",
        "residences",
        ["name"],
        unique=True,
        sqlite_where=sa.text("is_active = 1"),
        postgresql_where=sa.text("is_active = true"),
    )
