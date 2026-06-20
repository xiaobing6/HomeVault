from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Reminder(Base):
    __tablename__ = "reminders"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'done', 'dismissed')", name="ck_reminders_status"),
        CheckConstraint("source_type IN ('manual', 'loan_return')", name="ck_reminders_source_type"),
        CheckConstraint("priority IN ('low', 'normal', 'high')", name="ck_reminders_priority"),
        Index("ix_reminders_pending_due_date", "status", "due_date"),
        Index("ix_reminders_pending_remind_at", "status", "remind_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), default="manual", nullable=False, index=True)
    item_id: Mapped[int | None] = mapped_column(ForeignKey("items.id", ondelete="SET NULL"), nullable=True, index=True)
    loan_id: Mapped[int | None] = mapped_column(ForeignKey("item_loans.id", ondelete="SET NULL"), nullable=True, index=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    remind_at: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(40), default="pending", nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(40), default="normal", nullable=False)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    completed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    dismissed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    item: Mapped[object | None] = relationship("Item", back_populates="reminders", lazy="selectin")
    loan: Mapped[object | None] = relationship("ItemLoan", back_populates="reminders", lazy="selectin")
    created_by_user: Mapped[object | None] = relationship("User", foreign_keys=[created_by_user_id], lazy="selectin")
    completed_by_user: Mapped[object | None] = relationship("User", foreign_keys=[completed_by_user_id], lazy="selectin")
    dismissed_by_user: Mapped[object | None] = relationship("User", foreign_keys=[dismissed_by_user_id], lazy="selectin")
