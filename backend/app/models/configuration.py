from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class HomeSpace(Base):
    __tablename__ = "home_spaces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )

    residences: Mapped[list[Residence]] = relationship(
        back_populates="home_space",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    family_members: Mapped[list[FamilyMember]] = relationship(
        back_populates="home_space",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class Residence(Base):
    __tablename__ = "residences"
    __table_args__ = (
        Index(
            "uq_residences_active_name",
            "name",
            unique=True,
            sqlite_where=text("is_active = 1"),
            postgresql_where=text("is_active = true"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    home_space_id: Mapped[int] = mapped_column(ForeignKey("home_spaces.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    address: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    image_path: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    image_original_filename: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    image_content_type: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    image_byte_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )

    home_space: Mapped[HomeSpace] = relationship(back_populates="residences", lazy="selectin")
    created_by: Mapped[object | None] = relationship("User", foreign_keys=[created_by_id], lazy="selectin")
    updated_by: Mapped[object | None] = relationship("User", foreign_keys=[updated_by_id], lazy="selectin")
    location_nodes: Mapped[list[LocationNode]] = relationship(
        back_populates="residence",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="LocationNode.sort_order",
    )


class LocationNode(Base):
    __tablename__ = "location_nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    residence_id: Mapped[int] = mapped_column(ForeignKey("residences.id", ondelete="CASCADE"), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("location_nodes.id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    node_type: Mapped[str] = mapped_column(String(40), default="area", nullable=False)
    icon: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    note: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    residence: Mapped[Residence] = relationship(back_populates="location_nodes", lazy="selectin")
    parent: Mapped[LocationNode | None] = relationship(
        back_populates="children",
        remote_side=[id],
        lazy="selectin",
    )
    children: Mapped[list[LocationNode]] = relationship(
        back_populates="parent",
        lazy="selectin",
        order_by="LocationNode.sort_order",
    )


class FamilyMember(Base):
    __tablename__ = "family_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    home_space_id: Mapped[int] = mapped_column(ForeignKey("home_spaces.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    relation: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    phone: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    note: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    home_space: Mapped[HomeSpace] = relationship(back_populates="family_members", lazy="selectin")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    icon: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    parent: Mapped[Category | None] = relationship(
        back_populates="children",
        remote_side=[id],
        lazy="selectin",
    )
    children: Mapped[list[Category]] = relationship(
        back_populates="parent",
        lazy="selectin",
        order_by="Category.sort_order",
    )
    attribute_definitions: Mapped[list[AttributeDefinition]] = relationship(
        back_populates="category",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="AttributeDefinition.sort_order",
    )


class AttributeDefinition(Base):
    __tablename__ = "attribute_definitions"
    __table_args__ = (
        UniqueConstraint("category_id", "key", name="uq_attribute_definition_category_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    key: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    field_type: Mapped[str] = mapped_column(String(40), nullable=False)
    default_value: Mapped[str] = mapped_column(Text, default="", nullable=False)
    privacy_level: Mapped[str] = mapped_column(String(40), default="normal", nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_filterable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    category: Mapped[Category] = relationship(back_populates="attribute_definitions", lazy="selectin")
    options: Mapped[list[AttributeOption]] = relationship(
        back_populates="definition",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="AttributeOption.sort_order",
    )


class AttributeOption(Base):
    __tablename__ = "attribute_options"
    __table_args__ = (
        UniqueConstraint("definition_id", "value", name="uq_attribute_option_definition_value"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    definition_id: Mapped[int] = mapped_column(ForeignKey("attribute_definitions.id", ondelete="CASCADE"), nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[str] = mapped_column(String(120), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    definition: Mapped[AttributeDefinition] = relationship(back_populates="options", lazy="selectin")


class ItemStatus(Base):
    __tablename__ = "item_statuses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    semantic: Mapped[str] = mapped_column(String(80), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class DictionaryGroup(Base):
    __tablename__ = "dictionary_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    options: Mapped[list[DictionaryOption]] = relationship(
        back_populates="group",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="DictionaryOption.sort_order",
    )


class DictionaryOption(Base):
    __tablename__ = "dictionary_options"
    __table_args__ = (
        UniqueConstraint("group_id", "value", name="uq_dictionary_option_group_value"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("dictionary_groups.id", ondelete="CASCADE"), nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[str] = mapped_column(String(120), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    group: Mapped[DictionaryGroup] = relationship(back_populates="options", lazy="selectin")
