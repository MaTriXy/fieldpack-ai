"""HTTP fetch tool for the Agent Farm.

Fetches HTML pages and PDF files using httpx with retry logic.
Returns raw bytes (PDF) or decoded text (HTML).
"""

from __future__ import annotations

import httpx

from app.logger import Step, pipeline_logger as log

_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
_MAX_RETRIES = 2

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; FieldPackAI/1.0; "
        "+https://github.com/fieldpack-ai) research bot"
    ),
    "Accept": "text/html,application/xhtml+xml,application/pdf,*/*",
    "Accept-Language": "en-US,en;q=0.9",
}


async def fetch_html(url: str) -> str | None:
    """Fetch a URL and return decoded HTML text, or None on failure."""
    async with httpx.AsyncClient(
        timeout=_TIMEOUT, headers=_HEADERS, follow_redirects=True
    ) as client:
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                resp = await client.get(url)
                if resp.status_code == 403:
                    log.log_step(Step.SYSTEM, "fetch_blocked", level="WARNING",
                                 details={"url": url, "status": 403})
                    return None
                resp.raise_for_status()
                log.log_step(Step.SYSTEM, "fetch_html", details={
                    "url": url, "status": resp.status_code,
                    "length": len(resp.text),
                })
                return resp.text
            except httpx.HTTPStatusError as exc:
                log.log_step(Step.SYSTEM, "fetch_error", level="WARNING",
                             details={"url": url, "status": exc.response.status_code,
                                      "attempt": attempt})
                if attempt == _MAX_RETRIES:
                    return None
            except httpx.RequestError as exc:
                log.log_step(Step.SYSTEM, "fetch_error", level="WARNING",
                             details={"url": url, "error": str(exc),
                                      "attempt": attempt})
                if attempt == _MAX_RETRIES:
                    return None
    return None


async def fetch_pdf_bytes(url: str) -> bytes | None:
    """Fetch a URL and return raw PDF bytes, or None on failure."""
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(60.0, connect=15.0),
        headers=_HEADERS,
        follow_redirects=True,
    ) as client:
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                content_type = resp.headers.get("content-type", "")
                if "pdf" not in content_type and not url.endswith(".pdf"):
                    log.log_step(Step.SYSTEM, "fetch_not_pdf", level="WARNING",
                                 details={"url": url, "content_type": content_type})
                    return None
                log.log_step(Step.SYSTEM, "fetch_pdf", details={
                    "url": url, "size_bytes": len(resp.content),
                })
                return resp.content
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                log.log_step(Step.SYSTEM, "fetch_error", level="WARNING",
                             details={"url": url, "error": str(exc),
                                      "attempt": attempt})
                if attempt == _MAX_RETRIES:
                    return None
    return None
