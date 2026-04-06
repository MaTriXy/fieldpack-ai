"""Image upload endpoint for mobile clients.

Accepts a photo (multipart or base64 JSON), saves to the uploads directory,
and returns the file path for use in subsequent chat messages.
"""

import base64
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel

from app.config import settings

router = APIRouter(prefix="/upload", tags=["upload"])

# Max age for uploaded files (1 hour). Cleanup runs on each upload.
_MAX_AGE_SECONDS = 3600

_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
_MAX_SIZE = 20 * 1024 * 1024  # 20 MB


class Base64Upload(BaseModel):
    data: str  # base64-encoded image
    format: str = "jpeg"  # jpeg, png, webp


class UploadResponse(BaseModel):
    image_path: str


@router.post("/image", response_model=UploadResponse)
async def upload_image(file: UploadFile) -> UploadResponse:
    """Upload an image file (multipart/form-data)."""
    ext = Path(file.filename or "photo.jpg").suffix.lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported format: {ext}. Use: {_ALLOWED_EXTENSIONS}")

    content = await file.read()
    if len(content) > _MAX_SIZE:
        raise HTTPException(400, f"File too large ({len(content) // 1024 // 1024}MB). Max: 20MB.")

    return _save_image(content, ext)


@router.post("/image/base64", response_model=UploadResponse)
async def upload_image_base64(body: Base64Upload) -> UploadResponse:
    """Upload a base64-encoded image (from Capacitor Camera plugin)."""
    fmt = body.format.lower().strip(".")
    if fmt == "jpg":
        fmt = "jpeg"
    ext = f".{fmt}"
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported format: {ext}. Use: {_ALLOWED_EXTENSIONS}")

    try:
        content = base64.b64decode(body.data)
    except Exception:
        raise HTTPException(400, "Invalid base64 data")

    if len(content) > _MAX_SIZE:
        raise HTTPException(400, f"File too large ({len(content) // 1024 // 1024}MB). Max: 20MB.")

    return _save_image(content, ext)


def _cleanup_old_uploads() -> None:
    """Remove uploaded files older than _MAX_AGE_SECONDS."""
    uploads = settings.uploads_path
    cutoff = time.time() - _MAX_AGE_SECONDS
    for f in uploads.iterdir():
        if f.is_file() and f.suffix.lower() in _ALLOWED_EXTENSIONS:
            try:
                if f.stat().st_mtime < cutoff:
                    f.unlink()
            except OSError:
                pass


def _save_image(content: bytes, ext: str) -> UploadResponse:
    """Save image bytes to uploads directory, return the path."""
    _cleanup_old_uploads()
    uploads = settings.uploads_path
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = uploads / filename
    filepath.write_bytes(content)
    # Use as_posix() for consistent forward-slash paths across platforms
    return UploadResponse(image_path=str(filepath.resolve().as_posix()))
