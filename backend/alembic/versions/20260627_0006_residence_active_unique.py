from alembic import op
import sqlalchemy as sa

revision = "20260627_0006"
down_revision = "20260620_0005"
branch_labels = None
depends_on = None


def _index_exists(index_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return index_name in {index["name"] for index in inspector.get_indexes("residences")}


def upgrade() -> None:
    if _index_exists("ix_residences_name"):
        op.drop_index("ix_residences_name", table_name="residences")
    op.create_index("ix_residences_name", "residences", ["name"], unique=False)
    op.create_index(
        "uq_residences_active_name",
        "residences",
        ["name"],
        unique=True,
        sqlite_where=sa.text("is_active = 1"),
        postgresql_where=sa.text("is_active = true"),
    )


def downgrade() -> None:
    if _index_exists("uq_residences_active_name"):
        op.drop_index("uq_residences_active_name", table_name="residences")
    if _index_exists("ix_residences_name"):
        op.drop_index("ix_residences_name", table_name="residences")
    op.create_index("ix_residences_name", "residences", ["name"], unique=True)
