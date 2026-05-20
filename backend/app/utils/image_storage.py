"""Persist image payloads (data URLs or short paths) under UPLOAD_DIR."""

from __future__ import annotations

import base64
import binascii
import re
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status

from app.core.config import settings

_DATA_URL_RE = re.compile(r"^data:(image/[\w+.-]+);base64,(.+)$", re.IGNORECASE | re.DOTALL)
_MIME_EXT = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}

MAX_IMAGE_BYTES = 10 * 1024 * 1024


def _extension_for_mime(mime: str) -> str:
    normalized = mime.lower().split(";", 1)[0].strip()
    return _MIME_EXT.get(normalized, ".png")


def persist_image(
    value: str | None,
    folder: str,
    *,
    max_db_length: int = 500,
) -> str | None:
    """
    Store images on disk and return a short public path (e.g. `/uploads/classes/abc.png`).
    Accepts data URLs from the frontend or an existing `/uploads/...` path.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None

    if text.startswith("/uploads/") and len(text) <= max_db_length:
        return text

    if text.startswith("http://") or text.startswith("https://"):
        if len(text) <= max_db_length:
            return text
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image URL is too long; upload the file instead.",
        )

    match = _DATA_URL_RE.match(text)
    if match:
        mime, encoded = match.group(1), match.group(2)
        try:
            raw = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid image data.",
            ) from exc
        if len(raw) > MAX_IMAGE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Image file is too large (max 10 MB).",
            )
        ext = _extension_for_mime(mime)
        target_dir = Path(settings.upload_dir) / folder
        target_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid4().hex}{ext}"
        path = target_dir / filename
        path.write_bytes(raw)
        public_path = f"/uploads/{folder}/{filename}"
        if len(public_path) > max_db_length:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not store image path.",
            )
        return public_path

    if len(text) <= max_db_length:
        return text

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Image is too large. Use a smaller file (under 10 MB).",
    )
