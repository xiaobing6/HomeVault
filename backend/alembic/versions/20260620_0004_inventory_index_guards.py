from alembic import op

revision = "20260620_0004"
down_revision = "20260619_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    dialect_name = op.get_bind().dialect.name
    if dialect_name == "sqlite":
        op.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_item_images_active_primary_item_id "
            "ON item_images (item_id) WHERE is_primary = 1 AND is_archived = 0"
        )
    else:
        op.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_item_images_active_primary_item_id "
            "ON item_images (item_id) WHERE is_primary = true AND is_archived = false"
        )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_item_loans_active_item_id "
        "ON item_loans (item_id) WHERE returned_at IS NULL"
    )


def downgrade() -> None:
    # These indexes belong to the inventory schema introduced in 20260619_0003.
    # The guard is a no-op on downgrade so the 0003 downgrade can drop them once.
    return None
