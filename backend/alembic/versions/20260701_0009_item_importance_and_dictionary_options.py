"""add item importance and core dictionary options

Revision ID: 20260701_0009
Revises: 20260701_0008
Create Date: 2026-07-01 20:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260701_0009"
down_revision = "20260701_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "items",
        sa.Column("importance", sa.String(length=40), nullable=False, server_default="medium"),
    )
    op.create_index("ix_items_importance", "items", ["importance"])
    if op.get_context().dialect.name != "sqlite":
        op.alter_column("items", "importance", server_default=None)

    op.execute(
        sa.text(
            """
            DELETE FROM dictionary_options
            WHERE group_id IN (
                SELECT id FROM dictionary_groups
                WHERE code = 'storage_conditions' AND is_system = :is_system
            )
            """
        ).bindparams(sa.bindparam("is_system", value=True, type_=sa.Boolean()))
    )
    op.execute(
        sa.text(
            """
            DELETE FROM dictionary_groups
            WHERE code = 'storage_conditions' AND is_system = :is_system
            """
        ).bindparams(sa.bindparam("is_system", value=True, type_=sa.Boolean()))
    )
    seed_group("units", "\u5355\u4f4d", [("\u4ef6", "\u4ef6", 10), ("\u4e2a", "\u4e2a", 20), ("\u7bb1", "\u7bb1", 30), ("\u5957", "\u5957", 40)])
    seed_group("importance", "\u91cd\u8981\u7a0b\u5ea6", [("high", "\u9ad8", 10), ("medium", "\u4e2d", 20), ("low", "\u4f4e", 30)])
    seed_group("location_node_types", "\u4f4d\u7f6e\u7c7b\u578b", [("room", "\u623f\u95f4", 10), ("area", "\u533a\u57df", 20), ("cabinet", "\u67dc\u5b50", 30), ("shelf", "\u67b6\u5b50", 40), ("box", "\u7bb1/\u76d2", 50), ("other", "\u5176\u4ed6", 60)])


def downgrade() -> None:
    op.drop_index("ix_items_importance", table_name="items")
    op.drop_column("items", "importance")


def seed_group(code: str, name: str, options: list[tuple[str, str, int]]) -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO dictionary_groups (code, name, is_system, is_active)
            SELECT :code, :name, :is_system, :is_active
            WHERE NOT EXISTS (SELECT 1 FROM dictionary_groups WHERE code = :code)
            """
        ).bindparams(
            sa.bindparam("code", value=code),
            sa.bindparam("name", value=name),
            sa.bindparam("is_system", value=True, type_=sa.Boolean()),
            sa.bindparam("is_active", value=True, type_=sa.Boolean()),
        )
    )
    for value, label, sort_order in options:
        op.execute(
            sa.text(
                """
                INSERT INTO dictionary_options (group_id, label, value, sort_order, is_active)
                SELECT dictionary_groups.id, :label, :value, :sort_order, :is_active
                FROM dictionary_groups
                WHERE dictionary_groups.code = :code
                  AND NOT EXISTS (
                    SELECT 1 FROM dictionary_options
                    WHERE dictionary_options.group_id = dictionary_groups.id
                      AND dictionary_options.value = :value
                  )
                """
            ).bindparams(
                sa.bindparam("code", value=code),
                sa.bindparam("label", value=label),
                sa.bindparam("value", value=value),
                sa.bindparam("sort_order", value=sort_order),
                sa.bindparam("is_active", value=True, type_=sa.Boolean()),
            )
        )
