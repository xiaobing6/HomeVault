from __future__ import annotations

from asyncio import run
from io import BytesIO
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.datastructures import Headers, UploadFile

from app.core.config import get_settings
from app.main import create_app
from app.models.auth import User
from app.models.configuration import Category, ItemStatus
from app.models.inventory import Item, ItemAttachment, ItemImage
from app.services import inventory


MAX_IMAGE_BYTES = 5 * 1024 * 1024
PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
JPEG_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00"
WEBP_BYTES = b"RIFF\x0c\x00\x00\x00WEBPVP8 "


@pytest.fixture()
def upload_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "uploads"
    path.mkdir()
    monkeypatch.setattr(get_settings(), "upload_dir", str(path), raising=False)
    return path


@pytest.fixture()
def inventory_item(db_session: Session) -> Item:
    uploader = User(id=42, username="uploader", password_hash="hash", display_name="Uploader")
    archiver = User(id=7, username="archiver", password_hash="hash", display_name="Archiver")
    category = Category(code="media", name="Media")
    status = ItemStatus(code="in_stock", name="In stock", semantic="in_inventory", is_system=True)
    item = Item(name="Camera", category=category, status=status, unit="pcs")
    db_session.add_all([uploader, archiver, category, status, item])
    db_session.commit()
    return item


def make_upload(
    filename: str,
    content: bytes,
    content_type: str,
) -> UploadFile:
    return UploadFile(
        file=BytesIO(content),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


def test_image_upload_rejects_unsupported_type(
    db_session: Session,
    inventory_item: Item,
    upload_dir: Path,
) -> None:
    upload = make_upload("notes.txt", b"not an image", "text/plain")

    with pytest.raises(HTTPException) as exc_info:
        run(inventory.add_item_image(db_session, inventory_item.id, upload))

    assert exc_info.value.status_code == 400
    assert db_session.scalars(select(ItemImage)).all() == []
    assert list(upload_dir.rglob("*")) == []


def test_image_upload_rejects_large_file(
    db_session: Session,
    inventory_item: Item,
    upload_dir: Path,
) -> None:
    upload = make_upload("large.png", b"x" * (MAX_IMAGE_BYTES + 1), "image/png")

    with pytest.raises(HTTPException) as exc_info:
        run(inventory.add_item_image(db_session, inventory_item.id, upload))

    assert exc_info.value.status_code == 400
    assert db_session.scalars(select(ItemImage)).all() == []
    assert [path for path in upload_dir.rglob("*") if path.is_file()] == []


def test_image_upload_rejects_spoofed_content_type_without_writing_file(
    db_session: Session,
    inventory_item: Item,
    upload_dir: Path,
) -> None:
    upload = make_upload("fake.png", b"not actually a png", "image/png")

    with pytest.raises(HTTPException) as exc_info:
        run(inventory.add_item_image(db_session, inventory_item.id, upload))

    assert exc_info.value.status_code == 400
    assert db_session.scalars(select(ItemImage)).all() == []
    assert [path for path in upload_dir.rglob("*") if path.is_file()] == []


def test_store_upload_generates_safe_filename(upload_dir: Path) -> None:
    from app.services.uploads import store_upload

    upload = make_upload("../../../Warranty Scan.exe", b"safe content", "application/pdf")

    relative_path, byte_size = run(store_upload(upload, item_id=123, media_type="attachments"))

    stored_path = upload_dir / Path(relative_path)
    assert byte_size == len(b"safe content")
    assert relative_path.startswith("items/123/attachments/")
    assert relative_path.endswith(".exe") is False
    assert stored_path.read_bytes() == b"safe content"
    assert "/" in relative_path
    assert "\\" not in relative_path


def test_first_image_becomes_primary(
    db_session: Session,
    inventory_item: Item,
    upload_dir: Path,
) -> None:
    image = run(
        inventory.add_item_image(
            db_session,
            inventory_item.id,
            make_upload("front.jpg", JPEG_BYTES, "image/jpeg"),
        )
    )

    detail = inventory.get_item_detail(db_session, inventory_item.id)
    assert image.is_primary is True
    assert [stored_image.is_primary for stored_image in detail.images] == [True]
    assert image.file_path.startswith("items/")
    assert image.url == f"/uploads/{image.file_path}"
    assert detail.primary_image_url == f"/uploads/{image.file_path}"


def test_primary_image_replacement_keeps_single_primary(
    db_session: Session,
    inventory_item: Item,
    upload_dir: Path,
) -> None:
    first = run(
        inventory.add_item_image(
            db_session,
            inventory_item.id,
            make_upload("front.jpg", JPEG_BYTES, "image/jpeg"),
        )
    )
    second = run(
        inventory.add_item_image(
            db_session,
            inventory_item.id,
            make_upload("back.webp", WEBP_BYTES, "image/webp"),
            is_primary=True,
        )
    )

    detail = inventory.get_item_detail(db_session, inventory_item.id)

    assert first.id != second.id
    assert [image.id for image in detail.images if image.is_primary] == [second.id]
    assert detail.primary_image_url == f"/uploads/{second.file_path}"


def test_image_upload_cleans_up_file_when_db_flush_fails(
    db_session: Session,
    inventory_item: Item,
    upload_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_flush = db_session.flush

    def fail_once(*args: object, **kwargs: object) -> object:
        monkeypatch.setattr(db_session, "flush", original_flush)
        raise IntegrityError("insert item_images", {}, Exception("forced flush failure"))

    monkeypatch.setattr(db_session, "flush", fail_once)

    with pytest.raises(HTTPException) as exc_info:
        run(
            inventory.add_item_image(
                db_session,
                inventory_item.id,
                make_upload("front.png", PNG_BYTES, "image/png"),
            )
        )

    assert exc_info.value.status_code == 400
    assert db_session.scalars(select(ItemImage)).all() == []
    assert [path for path in upload_dir.rglob("*") if path.is_file()] == []


def test_image_upload_cleans_up_file_when_db_flush_raises_sqlalchemy_error(
    db_session: Session,
    inventory_item: Item,
    upload_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_flush = db_session.flush

    def fail_once(*args: object, **kwargs: object) -> object:
        monkeypatch.setattr(db_session, "flush", original_flush)
        raise SQLAlchemyError("forced flush failure")

    monkeypatch.setattr(db_session, "flush", fail_once)

    with pytest.raises(HTTPException) as exc_info:
        run(
            inventory.add_item_image(
                db_session,
                inventory_item.id,
                make_upload("front.png", PNG_BYTES, "image/png"),
            )
        )

    assert exc_info.value.status_code == 400
    assert db_session.scalars(select(ItemImage)).all() == []
    assert [path for path in upload_dir.rglob("*") if path.is_file()] == []


def test_attachment_upload_rejects_unsafe_unknown_file_without_writing(
    db_session: Session,
    inventory_item: Item,
    upload_dir: Path,
) -> None:
    upload = make_upload("tool.exe", b"MZ executable", "application/octet-stream")

    with pytest.raises(HTTPException) as exc_info:
        run(inventory.add_item_attachment(db_session, inventory_item.id, upload))

    assert exc_info.value.status_code == 400
    assert db_session.scalars(select(ItemAttachment)).all() == []
    assert [path for path in upload_dir.rglob("*") if path.is_file()] == []


def test_attachment_upload_cleans_up_file_when_db_commit_fails(
    db_session: Session,
    inventory_item: Item,
    upload_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_commit = db_session.commit

    def fail_once(*args: object, **kwargs: object) -> object:
        monkeypatch.setattr(db_session, "commit", original_commit)
        raise IntegrityError("insert item_attachments", {}, Exception("forced commit failure"))

    monkeypatch.setattr(db_session, "commit", fail_once)

    with pytest.raises(HTTPException) as exc_info:
        run(
            inventory.add_item_attachment(
                db_session,
                inventory_item.id,
                make_upload("manual.pdf", b"%PDF-1.7\n", "application/pdf"),
            )
        )

    assert exc_info.value.status_code == 400
    assert db_session.scalars(select(ItemAttachment)).all() == []
    assert [path for path in upload_dir.rglob("*") if path.is_file()] == []


def test_attachment_upload_cleans_up_file_when_db_commit_raises_sqlalchemy_error(
    db_session: Session,
    inventory_item: Item,
    upload_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_commit = db_session.commit

    def fail_once(*args: object, **kwargs: object) -> object:
        monkeypatch.setattr(db_session, "commit", original_commit)
        raise SQLAlchemyError("forced commit failure")

    monkeypatch.setattr(db_session, "commit", fail_once)

    with pytest.raises(HTTPException) as exc_info:
        run(
            inventory.add_item_attachment(
                db_session,
                inventory_item.id,
                make_upload("manual.pdf", b"%PDF-1.7\n", "application/pdf"),
            )
        )

    assert exc_info.value.status_code == 400
    assert db_session.scalars(select(ItemAttachment)).all() == []
    assert [path for path in upload_dir.rglob("*") if path.is_file()] == []


def test_archive_image_and_attachment_hide_media_from_detail(
    db_session: Session,
    inventory_item: Item,
    upload_dir: Path,
) -> None:
    first = run(
        inventory.add_item_image(
            db_session,
            inventory_item.id,
            make_upload("front.png", PNG_BYTES, "image/png"),
            is_primary=True,
            actor_id=42,
        )
    )
    second = run(
        inventory.add_item_image(
            db_session,
            inventory_item.id,
            make_upload("side.png", PNG_BYTES + b"side", "image/png"),
            actor_id=42,
        )
    )
    attachment = run(
        inventory.add_item_attachment(
            db_session,
            inventory_item.id,
            make_upload("manual.pdf", b"manual", "application/pdf"),
            actor_id=42,
        )
    )

    detail_before = inventory.get_item_detail(db_session, inventory_item.id)
    assert [image.id for image in detail_before.images] == [first.id, second.id]
    assert [stored_attachment.id for stored_attachment in detail_before.attachments] == [attachment.id]

    image_archived = inventory.archive_item_image(db_session, inventory_item.id, first.id, actor_id=7)
    attachment_archived = inventory.archive_item_attachment(db_session, inventory_item.id, attachment.id, actor_id=7)
    image_row = db_session.get(ItemImage, first.id)
    attachment_row = db_session.get(ItemAttachment, attachment.id)

    assert [image.id for image in image_archived.images] == [second.id]
    assert [image.id for image in image_archived.images if image.is_primary] == [second.id]
    assert attachment_archived.attachments == []
    assert image_row is not None and image_row.is_archived is True
    assert attachment_row is not None and attachment_row.is_archived is True


def test_create_app_mounts_uploads(upload_dir: Path) -> None:
    app = create_app()

    assert any(getattr(route, "path", None) == "/uploads" for route in app.routes)


def test_create_app_creates_missing_upload_dir_and_serves_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing_upload_dir = tmp_path / "missing-uploads"
    monkeypatch.setattr(get_settings(), "upload_dir", str(missing_upload_dir), raising=False)

    app = create_app()
    assert missing_upload_dir.is_dir()

    stored_file = missing_upload_dir / "items" / "1" / "images" / "front.png"
    stored_file.parent.mkdir(parents=True)
    stored_file.write_bytes(PNG_BYTES)

    response = TestClient(app).get("/uploads/items/1/images/front.png")

    assert response.status_code == 200
    assert response.content == PNG_BYTES
