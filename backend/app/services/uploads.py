from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import get_settings
from app.core.errors import bad_request


IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_ATTACHMENT_BYTES = 20 * 1024 * 1024

SAFE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".pdf",
    ".txt",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
}


def safe_extension(filename: str | None) -> str:
    extension = Path(filename or "").suffix.lower()
    return extension if extension in SAFE_EXTENSIONS else ""


def build_storage_name(filename: str | None) -> str:
    return f"{uuid4().hex}{safe_extension(filename)}"


async def store_upload(upload: UploadFile, *, item_id: int, media_type: str) -> tuple[str, int]:
    limit = MAX_IMAGE_BYTES if media_type == "images" else MAX_ATTACHMENT_BYTES
    content = await upload.read(limit + 1)
    byte_size = len(content)
    if byte_size > limit:
        raise bad_request("Upload file is too large")

    stored_filename = build_storage_name(upload.filename)
    relative_dir = Path("items") / str(item_id) / media_type
    storage_dir = Path(get_settings().upload_dir) / relative_dir
    storage_dir.mkdir(parents=True, exist_ok=True)
    (storage_dir / stored_filename).write_bytes(content)

    relative_path = (relative_dir / stored_filename).as_posix()
    return relative_path, byte_size
