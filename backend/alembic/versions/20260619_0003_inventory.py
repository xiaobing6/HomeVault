from alembic import op
import sqlalchemy as sa

revision = "20260619_0003"
down_revision = "20260619_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status_id", sa.Integer(), sa.ForeignKey("item_statuses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 2), nullable=False, server_default="1"),
        sa.Column("unit", sa.String(length=40), nullable=False, server_default="件"),
        sa.Column("owner_member_id", sa.Integer(), sa.ForeignKey("family_members.id", ondelete="SET NULL"), nullable=True),
        sa.Column("keeper_member_id", sa.Integer(), sa.ForeignKey("family_members.id", ondelete="SET NULL"), nullable=True),
        sa.Column("location_node_id", sa.Integer(), sa.ForeignKey("location_nodes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("container_item_id", sa.Integer(), sa.ForeignKey("items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_container", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("privacy_level", sa.String(length=40), nullable=False, server_default="normal"),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("archive_reason", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(location_node_id IS NULL OR container_item_id IS NULL)",
            name="ck_item_location_or_container",
        ),
    )
    op.create_index("ix_items_id", "items", ["id"])
    op.create_index("ix_items_name", "items", ["name"])
    op.create_index("ix_items_category_id", "items", ["category_id"])
    op.create_index("ix_items_status_id", "items", ["status_id"])
    op.create_index("ix_items_location_node_id", "items", ["location_node_id"])
    op.create_index("ix_items_container_item_id", "items", ["container_item_id"])
    op.create_index("ix_items_is_archived", "items", ["is_archived"])

    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("normalized_name", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_tags_id", "tags", ["id"])
    op.create_index("ix_tags_normalized_name", "tags", ["normalized_name"], unique=True)

    op.create_table(
        "item_attribute_values",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("items.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "attribute_definition_id",
            sa.Integer(),
            sa.ForeignKey("attribute_definitions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("value", sa.Text(), nullable=False, server_default=""),
        sa.UniqueConstraint("item_id", "attribute_definition_id", name="uq_item_attribute_value_item_definition"),
    )
    op.create_index("ix_item_attribute_values_id", "item_attribute_values", ["id"])
    op.create_index("ix_item_attribute_values_item_id", "item_attribute_values", ["item_id"])
    op.create_index(
        "ix_item_attribute_values_attribute_definition_id",
        "item_attribute_values",
        ["attribute_definition_id"],
    )

    op.create_table(
        "item_images",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_filename", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("byte_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("uploaded_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_item_images_id", "item_images", ["id"])
    op.create_index("ix_item_images_item_id", "item_images", ["item_id"])
    op.create_index("ix_item_images_is_archived", "item_images", ["is_archived"])
    op.create_index(
        "uq_item_images_active_primary_item_id",
        "item_images",
        ["item_id"],
        unique=True,
        sqlite_where=sa.text("is_primary = 1 AND is_archived = 0"),
        postgresql_where=sa.text("is_primary = true AND is_archived = false"),
    )

    op.create_table(
        "item_attachments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_filename", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("byte_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("uploaded_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_item_attachments_id", "item_attachments", ["id"])
    op.create_index("ix_item_attachments_item_id", "item_attachments", ["item_id"])
    op.create_index("ix_item_attachments_is_archived", "item_attachments", ["is_archived"])

    op.create_table(
        "item_tags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tag_id", sa.Integer(), sa.ForeignKey("tags.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("item_id", "tag_id", name="uq_item_tag_item_tag"),
    )
    op.create_index("ix_item_tags_id", "item_tags", ["id"])
    op.create_index("ix_item_tags_item_id", "item_tags", ["item_id"])
    op.create_index("ix_item_tags_tag_id", "item_tags", ["tag_id"])

    op.create_table(
        "item_movements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("items.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "previous_location_node_id",
            sa.Integer(),
            sa.ForeignKey("location_nodes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "new_location_node_id",
            sa.Integer(),
            sa.ForeignKey("location_nodes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "previous_container_item_id",
            sa.Integer(),
            sa.ForeignKey("items.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "new_container_item_id",
            sa.Integer(),
            sa.ForeignKey("items.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "previous_status_id",
            sa.Integer(),
            sa.ForeignKey("item_statuses.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "new_status_id",
            sa.Integer(),
            sa.ForeignKey("item_statuses.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("movement_type", sa.String(length=40), nullable=False, server_default="manual"),
        sa.Column("reason", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_item_movements_id", "item_movements", ["id"])
    op.create_index("ix_item_movements_item_id", "item_movements", ["item_id"])

    op.create_table(
        "item_quantity_changes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quantity_before", sa.Numeric(12, 2), nullable=False),
        sa.Column("quantity_after", sa.Numeric(12, 2), nullable=False),
        sa.Column("quantity_delta", sa.Numeric(12, 2), nullable=False),
        sa.Column("unit", sa.String(length=40), nullable=False, server_default="件"),
        sa.Column("reason", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_item_quantity_changes_id", "item_quantity_changes", ["id"])
    op.create_index("ix_item_quantity_changes_item_id", "item_quantity_changes", ["item_id"])

    op.create_table(
        "item_loans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("borrower_name", sa.String(length=160), nullable=False),
        sa.Column("borrower_contact", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("expected_return_date", sa.Date(), nullable=True),
        sa.Column("loan_note", sa.Text(), nullable=False, server_default=""),
        sa.Column("loaned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("returned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("return_note", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "return_location_node_id",
            sa.Integer(),
            sa.ForeignKey("location_nodes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "return_container_item_id",
            sa.Integer(),
            sa.ForeignKey("items.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("loan_actor_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("return_actor_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_item_loans_id", "item_loans", ["id"])
    op.create_index("ix_item_loans_item_id", "item_loans", ["item_id"])
    op.create_index(
        "uq_item_loans_active_item_id",
        "item_loans",
        ["item_id"],
        unique=True,
        sqlite_where=sa.text("returned_at IS NULL"),
        postgresql_where=sa.text("returned_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_item_loans_active_item_id", table_name="item_loans")
    op.drop_index("ix_item_loans_item_id", table_name="item_loans")
    op.drop_index("ix_item_loans_id", table_name="item_loans")
    op.drop_table("item_loans")
    op.drop_index("ix_item_quantity_changes_item_id", table_name="item_quantity_changes")
    op.drop_index("ix_item_quantity_changes_id", table_name="item_quantity_changes")
    op.drop_table("item_quantity_changes")
    op.drop_index("ix_item_movements_item_id", table_name="item_movements")
    op.drop_index("ix_item_movements_id", table_name="item_movements")
    op.drop_table("item_movements")
    op.drop_index("ix_item_tags_tag_id", table_name="item_tags")
    op.drop_index("ix_item_tags_item_id", table_name="item_tags")
    op.drop_index("ix_item_tags_id", table_name="item_tags")
    op.drop_table("item_tags")
    op.drop_index("ix_item_attachments_is_archived", table_name="item_attachments")
    op.drop_index("ix_item_attachments_item_id", table_name="item_attachments")
    op.drop_index("ix_item_attachments_id", table_name="item_attachments")
    op.drop_table("item_attachments")
    op.drop_index("uq_item_images_active_primary_item_id", table_name="item_images")
    op.drop_index("ix_item_images_is_archived", table_name="item_images")
    op.drop_index("ix_item_images_item_id", table_name="item_images")
    op.drop_index("ix_item_images_id", table_name="item_images")
    op.drop_table("item_images")
    op.drop_index("ix_item_attribute_values_attribute_definition_id", table_name="item_attribute_values")
    op.drop_index("ix_item_attribute_values_item_id", table_name="item_attribute_values")
    op.drop_index("ix_item_attribute_values_id", table_name="item_attribute_values")
    op.drop_table("item_attribute_values")
    op.drop_index("ix_tags_normalized_name", table_name="tags")
    op.drop_index("ix_tags_id", table_name="tags")
    op.drop_table("tags")
    op.drop_index("ix_items_is_archived", table_name="items")
    op.drop_index("ix_items_container_item_id", table_name="items")
    op.drop_index("ix_items_location_node_id", table_name="items")
    op.drop_index("ix_items_status_id", table_name="items")
    op.drop_index("ix_items_category_id", table_name="items")
    op.drop_index("ix_items_name", table_name="items")
    op.drop_index("ix_items_id", table_name="items")
    op.drop_table("items")
