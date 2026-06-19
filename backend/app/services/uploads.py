from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import get_settings
from app.core.errors import bad_request


IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_ATTACHMENT_BYTES = 20 * 1024 * 1024
UPLOAD_URL_PREFIX = "/uploads"

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

ATTACHMENT_CONTENT_TYPES_BY_EXTENSION = {
    ".pdf": {"application/pdf"},
    ".txt": {"text/plain"},
    ".doc": {"application/msword"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    ".xls": {"application/vnd.ms-excel"},
    ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
}


def safe_extension(filename: str | None) -> str:
    extension = Path(filename or "").suffix.lower()
    return extension if extension in SAFE_EXTENSIONS else ""


def build_storage_name(filename: str | None) -> str:
    return f"{uuid4().hex}{safe_extension(filename)}"


def stored_upload_path(relative_path: str) -> Path:
    return Path(get_settings().upload_dir) / Path(relative_path)


def delete_stored_upload(relative_path: str) -> None:
    try:
        stored_upload_path(relative_path).unlink(missing_ok=True)
    except OSError:
        pass


def public_upload_url(relative_path: str | None) -> str | None:
    if relative_path is None:
        return None
    return f"{UPLOAD_URL_PREFIX}/{relative_path.lstrip('/')}"


async def validate_image_signature(upload: UploadFile, content_type: str) -> None:
    prefix = await upload.read(16)
    await upload.seek(0)
    if content_type == "image/jpeg" and prefix.startswith(b"\xff\xd8\xff"):
        return
    if content_type == "image/png" and prefix.startswith(b"\x89PNG\r\n\x1a\n"):
        return
    if content_type == "image/webp" and prefix.startswith(b"RIFF") and prefix[8:12] == b"WEBP":
        return
    raise bad_request("Image content does not match declared type")


def validate_attachment_metadata(filename: str | None, content_type: str) -> None:
    extension = safe_extension(filename)
    allowed_content_types = ATTACHMENT_CONTENT_TYPES_BY_EXTENSION.get(extension)
    if allowed_content_types is None or content_type not in allowed_content_types:
        raise bad_request("Attachment type is not supported")


async def store_upload(upload: UploadFile, *, item_id: int, media_type: str) -> tuple[str, int]:
    limit = MAX_IMAGE_BYTES if media_type == "images" else MAX_ATTACHMENT_BYTES
    content = await upload.read(limit + 1)
    byte_size = len(content)
    if byte_size > limit:
        raise bad_request("Upload file is too large")

    stored_filename = build_storage_name(upload.filename)
    relative_dir = Path("items") / str(item_id) / media_type
    storage_dir = stored_upload_path(relative_dir.as_posix())
    storage_dir.mkdir(parents=True, exist_ok=True)
    (storage_dir / stored_filename).write_bytes(content)

    relative_path = (relative_dir / stored_filename).as_posix()
    return relative_path, byte_size
