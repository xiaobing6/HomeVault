from alembic import op
import sqlalchemy as sa

revision = "20260620_0005"
down_revision = "20260620_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reminders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("source_type", sa.String(length=40), nullable=False, server_default="manual"),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("loan_id", sa.Integer(), sa.ForeignKey("item_loans.id", ondelete="SET NULL"), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("remind_at", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="pending"),
        sa.Column("priority", sa.String(length=40), nullable=False, server_default="normal"),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("completed_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("dismissed_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('pending', 'done', 'dismissed')", name="ck_reminders_status"),
        sa.CheckConstraint("source_type IN ('manual', 'loan_return')", name="ck_reminders_source_type"),
        sa.CheckConstraint("priority IN ('low', 'normal', 'high')", name="ck_reminders_priority"),
    )
    op.create_index("ix_reminders_id", "reminders", ["id"])
    op.create_index("ix_reminders_title", "reminders", ["title"])
    op.create_index("ix_reminders_source_type", "reminders", ["source_type"])
    op.create_index("ix_reminders_item_id", "reminders", ["item_id"])
    op.create_index("ix_reminders_loan_id", "reminders", ["loan_id"])
    op.create_index("ix_reminders_due_date", "reminders", ["due_date"])
    op.create_index("ix_reminders_remind_at", "reminders", ["remind_at"])
    op.create_index("ix_reminders_status", "reminders", ["status"])
    op.create_index("ix_reminders_archived_at", "reminders", ["archived_at"])
    op.create_index("ix_reminders_pending_due_date", "reminders", ["status", "due_date"])
    op.create_index("ix_reminders_pending_remind_at", "reminders", ["status", "remind_at"])


def downgrade() -> None:
    op.drop_index("ix_reminders_pending_remind_at", table_name="reminders")
    op.drop_index("ix_reminders_pending_due_date", table_name="reminders")
    op.drop_index("ix_reminders_archived_at", table_name="reminders")
    op.drop_index("ix_reminders_status", table_name="reminders")
    op.drop_index("ix_reminders_remind_at", table_name="reminders")
    op.drop_index("ix_reminders_due_date", table_name="reminders")
    op.drop_index("ix_reminders_loan_id", table_name="reminders")
    op.drop_index("ix_reminders_item_id", table_name="reminders")
    op.drop_index("ix_reminders_source_type", table_name="reminders")
    op.drop_index("ix_reminders_title", table_name="reminders")
    op.drop_index("ix_reminders_id", table_name="reminders")
    op.drop_table("reminders")
