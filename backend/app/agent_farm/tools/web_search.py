"""Tavily search wrapper for Phase C gap analysis.

Provides text search and image search via the Tavily API.
Used only as a gap-filler — known sources are fetched first in Phase A.
"""

from __future__ import annotations

from tavily import TavilyClient

from app.config import settings
from app.logger import Step, pipeline_logger as log


def _get_client() -> TavilyClient:
    """Create a Tavily client using the API key from settings."""
    key = settings.tavily_api_key
    if not key:
        raise RuntimeError(
            "TAVILY_API_KEY not set. Add it to .env for Phase C gap analysis."
        )
    return TavilyClient(api_key=key)


def search_text(
    query: str,
    max_results: int = 5,
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
) -> list[dict]:
    """Run a Tavily text search and return results.

    Each result dict has: title, url, content, score.
    """
    client = _get_client()

    try:
        with log.timed(Step.SEARCH, "tavily_text") as t:
            response = client.search(
                query=query,
                max_results=max_results,
                include_domains=include_domains or [],
                exclude_domains=exclude_domains or [],
                search_depth="advanced",
                include_raw_content="text",
            )
            results = response.get("results", [])
            t.set(details={
                "query": query, "results_count": len(results),
            })
            return results

    except Exception as exc:
        log.log_step(Step.SEARCH, "tavily_error", level="ERROR",
                     details={"query": query, "error": str(exc)})
        return []


def search_images(
    query: str,
    max_results: int = 5,
) -> list[dict]:
    """Run a Tavily image search and return image URLs.

    Each result dict has: url (image URL) and potentially description.
    """
    client = _get_client()

    try:
        with log.timed(Step.SEARCH, "tavily_images") as t:
            response = client.search(
                query=query,
                max_results=max_results,
                search_depth="basic",
                include_images=True,
            )
            images = response.get("images", [])
            # Normalize: Tavily returns images as list of URL strings or dicts
            normalized: list[dict] = []
            for img in images:
                if isinstance(img, str):
                    normalized.append({"url": img})
                elif isinstance(img, dict):
                    normalized.append(img)

            t.set(details={
                "query": query, "images_count": len(normalized),
            })
            return normalized

    except Exception as exc:
        log.log_step(Step.SEARCH, "tavily_image_error", level="ERROR",
                     details={"query": query, "error": str(exc)})
        return []
