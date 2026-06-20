from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Item(Base):
    __tablename__ = "items"
    __table_args__ = (
        CheckConstraint(
            "(location_node_id IS NULL OR container_item_id IS NULL)",
            name="ck_item_location_or_container",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(160), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status_id: Mapped[int] = mapped_column(
        ForeignKey("item_statuses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=1, nullable=False)
    unit: Mapped[str] = mapped_column(String(40), default="件", nullable=False)
    owner_member_id: Mapped[int | None] = mapped_column(
        ForeignKey("family_members.id", ondelete="SET NULL"),
        nullable=True,
    )
    keeper_member_id: Mapped[int | None] = mapped_column(
        ForeignKey("family_members.id", ondelete="SET NULL"),
        nullable=True,
    )
    location_node_id: Mapped[int | None] = mapped_column(
        ForeignKey("location_nodes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    container_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("items.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_container: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    privacy_level: Mapped[str] = mapped_column(String(40), default="normal", nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    archive_reason: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )

    category: Mapped[object] = relationship("Category", lazy="selectin")
    status: Mapped[object] = relationship("ItemStatus", lazy="selectin")
    owner_member: Mapped[object | None] = relationship(
        "FamilyMember",
        foreign_keys=[owner_member_id],
        lazy="selectin",
    )
    keeper_member: Mapped[object | None] = relationship(
        "FamilyMember",
        foreign_keys=[keeper_member_id],
        lazy="selectin",
    )
    location_node: Mapped[object | None] = relationship("LocationNode", lazy="selectin")
    container_item: Mapped[Item | None] = relationship(
        "Item",
        remote_side=[id],
        foreign_keys=[container_item_id],
        back_populates="children",
        lazy="selectin",
    )
    children: Mapped[list[Item]] = relationship(
        "Item",
        foreign_keys=[container_item_id],
        back_populates="container_item",
        lazy="selectin",
    )
    attribute_values: Mapped[list[ItemAttributeValue]] = relationship(
        back_populates="item",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    images: Mapped[list[ItemImage]] = relationship(
        back_populates="item",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    attachments: Mapped[list[ItemAttachment]] = relationship(
        back_populates="item",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    tag_links: Mapped[list[ItemTag]] = relationship(
        back_populates="item",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    movements: Mapped[list[ItemMovement]] = relationship(
        back_populates="item",
        cascade="all, delete-orphan",
        foreign_keys="ItemMovement.item_id",
        lazy="selectin",
    )
    quantity_changes: Mapped[list[ItemQuantityChange]] = relationship(
        back_populates="item",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    loans: Mapped[list[ItemLoan]] = relationship(
        back_populates="item",
        cascade="all, delete-orphan",
        foreign_keys="ItemLoan.item_id",
        lazy="selectin",
    )
    reminders: Mapped[list[object]] = relationship(
        "Reminder",
        back_populates="item",
        lazy="selectin",
    )


class ItemAttributeValue(Base):
    __tablename__ = "item_attribute_values"
    __table_args__ = (
        UniqueConstraint("item_id", "attribute_definition_id", name="uq_item_attribute_value_item_definition"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True)
    attribute_definition_id: Mapped[int] = mapped_column(
        ForeignKey("attribute_definitions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    value: Mapped[str] = mapped_column(Text, default="", nullable=False)

    item: Mapped[Item] = relationship(back_populates="attribute_values", lazy="selectin")
    attribute_definition: Mapped[object] = relationship("AttributeDefinition", lazy="selectin")


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    item_links: Mapped[list[ItemTag]] = relationship(
        back_populates="tag",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ItemTag(Base):
    __tablename__ = "item_tags"
    __table_args__ = (
        UniqueConstraint("item_id", "tag_id", name="uq_item_tag_item_tag"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), nullable=False, index=True)

    item: Mapped[Item] = relationship(back_populates="tag_links", lazy="selectin")
    tag: Mapped[Tag] = relationship(back_populates="item_links", lazy="selectin")


class ItemImage(Base):
    __tablename__ = "item_images"
    __table_args__ = (
        Index(
            "uq_item_images_active_primary_item_id",
            "item_id",
            unique=True,
            sqlite_where=text("is_primary = 1 AND is_archived = 0"),
            postgresql_where=text("is_primary = true AND is_archived = false"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    uploaded_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    item: Mapped[Item] = relationship(back_populates="images", lazy="selectin")
    uploaded_by: Mapped[object | None] = relationship("User", lazy="selectin")


class ItemAttachment(Base):
    __tablename__ = "item_attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    uploaded_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    item: Mapped[Item] = relationship(back_populates="attachments", lazy="selectin")
    uploaded_by: Mapped[object | None] = relationship("User", lazy="selectin")


class ItemMovement(Base):
    __tablename__ = "item_movements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True)
    previous_location_node_id: Mapped[int | None] = mapped_column(
        ForeignKey("location_nodes.id", ondelete="SET NULL"),
        nullable=True,
    )
    new_location_node_id: Mapped[int | None] = mapped_column(
        ForeignKey("location_nodes.id", ondelete="SET NULL"),
        nullable=True,
    )
    previous_container_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("items.id", ondelete="SET NULL"),
        nullable=True,
    )
    new_container_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("items.id", ondelete="SET NULL"),
        nullable=True,
    )
    previous_status_id: Mapped[int | None] = mapped_column(
        ForeignKey("item_statuses.id", ondelete="SET NULL"),
        nullable=True,
    )
    new_status_id: Mapped[int | None] = mapped_column(
        ForeignKey("item_statuses.id", ondelete="SET NULL"),
        nullable=True,
    )
    movement_type: Mapped[str] = mapped_column(String(40), default="manual", nullable=False)
    reason: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    item: Mapped[Item] = relationship(
        back_populates="movements",
        foreign_keys=[item_id],
        lazy="selectin",
    )
    previous_location_node: Mapped[object | None] = relationship(
        "LocationNode",
        foreign_keys=[previous_location_node_id],
        lazy="selectin",
    )
    new_location_node: Mapped[object | None] = relationship(
        "LocationNode",
        foreign_keys=[new_location_node_id],
        lazy="selectin",
    )
    previous_container_item: Mapped[Item | None] = relationship(
        "Item",
        foreign_keys=[previous_container_item_id],
        lazy="selectin",
    )
    new_container_item: Mapped[Item | None] = relationship(
        "Item",
        foreign_keys=[new_container_item_id],
        lazy="selectin",
    )
    previous_status: Mapped[object | None] = relationship(
        "ItemStatus",
        foreign_keys=[previous_status_id],
        lazy="selectin",
    )
    new_status: Mapped[object | None] = relationship(
        "ItemStatus",
        foreign_keys=[new_status_id],
        lazy="selectin",
    )
    actor: Mapped[object | None] = relationship("User", lazy="selectin")


class ItemQuantityChange(Base):
    __tablename__ = "item_quantity_changes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True)
    quantity_before: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    quantity_after: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    quantity_delta: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(40), default="件", nullable=False)
    reason: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    item: Mapped[Item] = relationship(back_populates="quantity_changes", lazy="selectin")
    actor: Mapped[object | None] = relationship("User", lazy="selectin")


class ItemLoan(Base):
    __tablename__ = "item_loans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True)
    borrower_name: Mapped[str] = mapped_column(String(160), nullable=False)
    borrower_contact: Mapped[str] = mapped_column(String(160), default="", nullable=False)
    expected_return_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    loan_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    loaned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    return_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    return_location_node_id: Mapped[int | None] = mapped_column(
        ForeignKey("location_nodes.id", ondelete="SET NULL"),
        nullable=True,
    )
    return_container_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("items.id", ondelete="SET NULL"),
        nullable=True,
    )
    loan_actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    return_actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )
    __table_args__ = (
        Index(
            "uq_item_loans_active_item_id",
            "item_id",
            unique=True,
            sqlite_where=returned_at.is_(None),
            postgresql_where=returned_at.is_(None),
        ),
    )

    item: Mapped[Item] = relationship(
        back_populates="loans",
        foreign_keys=[item_id],
        lazy="selectin",
    )
    return_location_node: Mapped[object | None] = relationship("LocationNode", lazy="selectin")
    return_container_item: Mapped[Item | None] = relationship(
        "Item",
        foreign_keys=[return_container_item_id],
        lazy="selectin",
    )
    loan_actor: Mapped[object | None] = relationship(
        "User",
        foreign_keys=[loan_actor_id],
        lazy="selectin",
    )
    return_actor: Mapped[object | None] = relationship(
        "User",
        foreign_keys=[return_actor_id],
        lazy="selectin",
    )
    reminders: Mapped[list[object]] = relationship(
        "Reminder",
        back_populates="loan",
        lazy="selectin",
    )
