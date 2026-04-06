"""Image downloader for the Agent Farm.

Downloads images from URLs, validates content-type and minimum resolution,
and saves to the Knowledge Pack images/ directory structure.
"""

from __future__ import annotations

import re
from pathlib import Path

import httpx

from app.logger import Step, pipeline_logger as log

_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
_MIN_SIZE_BYTES = 5_000  # skip tiny images (icons, spacers)
_VALID_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}


def _slugify(name: str) -> str:
    """Convert entity name to a filesystem-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")


async def download_image(
    url: str,
    category: str,
    entity_name: str,
    images_dir: Path,
    filename: str | None = None,
) -> Path | None:
    """Download an image and save to images/{category}/{entity_slug}/.

    Args:
        url: Image URL to download.
        category: "diseases", "healthy", or "treatments".
        entity_name: Entity name for subdirectory (e.g., "Cassava Mosaic Disease").
        images_dir: Root images/ directory of the Knowledge Pack.
        filename: Optional override filename. Auto-generated from URL if None.

    Returns:
        Path to saved image, or None on failure.
    """
    entity_slug = _slugify(entity_name)
    target_dir = images_dir / category / entity_slug
    target_dir.mkdir(parents=True, exist_ok=True)

    if filename is None:
        # Extract filename from URL, fallback to hash
        url_path = url.split("?")[0].split("/")[-1]
        ext = url_path.rsplit(".", 1)[1].lower() if "." in url_path else ""
        if ext in _ALLOWED_EXTENSIONS and len(url_path) < 100:
            filename = _slugify(url_path.rsplit(".", 1)[0]) + "." + ext
        else:
            filename = f"{entity_slug}_{abs(hash(url)) % 100000:05d}.jpg"

    target_path = target_dir / filename

    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()

            content_type = resp.headers.get("content-type", "").split(";")[0].strip()
            if content_type not in _VALID_CONTENT_TYPES:
                log.log_step(Step.SYSTEM, "image_skip_type", level="WARNING",
                             details={"url": url, "content_type": content_type})
                return None

            if len(resp.content) < _MIN_SIZE_BYTES:
                log.log_step(Step.SYSTEM, "image_skip_small", level="WARNING",
                             details={"url": url, "size": len(resp.content)})
                return None

            target_path.write_bytes(resp.content)

            log.log_step(Step.SYSTEM, "image_downloaded", details={
                "url": url, "path": str(target_path),
                "size_bytes": len(resp.content),
            })
            return target_path

        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            log.log_step(Step.SYSTEM, "image_download_error", level="WARNING",
                         details={"url": url, "error": str(exc)})
            return None
