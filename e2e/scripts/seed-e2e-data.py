from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.auth import User
from app.models.configuration import Category, FamilyMember, HomeSpace, ItemStatus, LocationNode, Residence
from app.schemas.inventory import ItemCreate
from app.services.inventory import create_item


def main() -> None:
    db = SessionLocal()
    try:
        admin = db.scalar(select(User).where(User.username == "admin"))
        home = db.scalar(select(HomeSpace).where(HomeSpace.is_active.is_(True)).order_by(HomeSpace.id))
        status = db.scalar(select(ItemStatus).where(ItemStatus.code == "in_stock"))
        if admin is None or home is None or status is None:
            raise RuntimeError("E2E baseline seed is missing auth or core configuration data")

        residence = Residence(home_space=home, name="E2E Residence", description="", address="", sort_order=10)
        shelf = LocationNode(residence=residence, name="E2E Shelf", node_type="shelf", sort_order=10)
        member = FamilyMember(home_space=home, name="E2E Alex", relation="Owner", phone="", note="")
        category = Category(code="e2e_documents", name="E2E Documents", sort_order=10)
        db.add_all([residence, shelf, member, category])
        db.commit()
        db.refresh(shelf)
        db.refresh(member)
        db.refresh(category)

        create_item(
            db,
            ItemCreate(
                name="E2E Passport Folder",
                description="Seeded browser acceptance item",
                category_id=category.id,
                status_id=status.id,
                quantity=Decimal("1.00"),
                unit="件",
                importance="medium",
                owner_member_id=member.id,
                keeper_member_id=member.id,
                location_node_id=shelf.id,
                is_container=True,
                privacy_level="normal",
                attribute_values=[],
                tags=["E2E", "Travel"],
            ),
            actor_id=admin.id,
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
