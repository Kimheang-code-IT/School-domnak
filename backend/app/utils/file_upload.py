from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import settings


async def save_upload(file: UploadFile, folder: str) -> str:
    suffix = Path(file.filename or "").suffix
    target_dir = Path(settings.upload_dir) / folder
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{suffix}"
    path = target_dir / filename
    path.write_bytes(await file.read())
    return str(path).replace("\\", "/")
