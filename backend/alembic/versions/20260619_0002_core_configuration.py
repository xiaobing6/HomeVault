from alembic import op
import sqlalchemy as sa

revision = "20260619_0002"
down_revision = "20260618_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "home_spaces",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_home_spaces_id", "home_spaces", ["id"])
    op.create_index("ix_home_spaces_name", "home_spaces", ["name"], unique=True)

    op.create_table(
        "residences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("home_space_id", sa.Integer(), sa.ForeignKey("home_spaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("address", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_residences_id", "residences", ["id"])
    op.create_index("ix_residences_name", "residences", ["name"], unique=True)

    op.create_table(
        "location_nodes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("residence_id", sa.Integer(), sa.ForeignKey("residences.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("location_nodes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("node_type", sa.String(length=40), nullable=False, server_default="area"),
        sa.Column("icon", sa.String(length=60), nullable=False, server_default=""),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("note", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_location_nodes_id", "location_nodes", ["id"])

    op.create_table(
        "family_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("home_space_id", sa.Integer(), sa.ForeignKey("home_spaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("relation", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("phone", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("note", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_family_members_id", "family_members", ["id"])
    op.create_index("ix_family_members_name", "family_members", ["name"])

    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("icon", sa.String(length=60), nullable=False, server_default=""),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_categories_id", "categories", ["id"])
    op.create_index("ix_categories_code", "categories", ["code"], unique=True)

    op.create_table(
        "attribute_definitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("field_type", sa.String(length=40), nullable=False),
        sa.Column("default_value", sa.Text(), nullable=False, server_default=""),
        sa.Column("privacy_level", sa.String(length=40), nullable=False, server_default="normal"),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_filterable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("category_id", "key", name="uq_attribute_definition_category_key"),
    )
    op.create_index("ix_attribute_definitions_id", "attribute_definitions", ["id"])

    op.create_table(
        "attribute_options",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "definition_id",
            sa.Integer(),
            sa.ForeignKey("attribute_definitions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("value", sa.String(length=120), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("definition_id", "value", name="uq_attribute_option_definition_value"),
    )
    op.create_index("ix_attribute_options_id", "attribute_options", ["id"])

    op.create_table(
        "item_statuses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("semantic", sa.String(length=80), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_item_statuses_id", "item_statuses", ["id"])
    op.create_index("ix_item_statuses_code", "item_statuses", ["code"], unique=True)

    op.create_table(
        "dictionary_groups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_dictionary_groups_id", "dictionary_groups", ["id"])
    op.create_index("ix_dictionary_groups_code", "dictionary_groups", ["code"], unique=True)

    op.create_table(
        "dictionary_options",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("group_id", sa.Integer(), sa.ForeignKey("dictionary_groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("value", sa.String(length=120), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("group_id", "value", name="uq_dictionary_option_group_value"),
    )
    op.create_index("ix_dictionary_options_id", "dictionary_options", ["id"])


def downgrade() -> None:
    op.drop_index("ix_dictionary_options_id", table_name="dictionary_options")
    op.drop_table("dictionary_options")
    op.drop_index("ix_dictionary_groups_code", table_name="dictionary_groups")
    op.drop_index("ix_dictionary_groups_id", table_name="dictionary_groups")
    op.drop_table("dictionary_groups")
    op.drop_index("ix_item_statuses_code", table_name="item_statuses")
    op.drop_index("ix_item_statuses_id", table_name="item_statuses")
    op.drop_table("item_statuses")
    op.drop_index("ix_attribute_options_id", table_name="attribute_options")
    op.drop_table("attribute_options")
    op.drop_index("ix_attribute_definitions_id", table_name="attribute_definitions")
    op.drop_table("attribute_definitions")
    op.drop_index("ix_categories_code", table_name="categories")
    op.drop_index("ix_categories_id", table_name="categories")
    op.drop_table("categories")
    op.drop_index("ix_family_members_name", table_name="family_members")
    op.drop_index("ix_family_members_id", table_name="family_members")
    op.drop_table("family_members")
    op.drop_index("ix_location_nodes_id", table_name="location_nodes")
    op.drop_table("location_nodes")
    op.drop_index("ix_residences_name", table_name="residences")
    op.drop_index("ix_residences_id", table_name="residences")
    op.drop_table("residences")
    op.drop_index("ix_home_spaces_name", table_name="home_spaces")
    op.drop_index("ix_home_spaces_id", table_name="home_spaces")
    op.drop_table("home_spaces")
