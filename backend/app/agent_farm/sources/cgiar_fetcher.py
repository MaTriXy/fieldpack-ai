"""CGIAR/IITA PDF discovery and download via CGSpace DSpace 7 API.

Searches the CGSpace repository for cassava fertilization papers,
then downloads the top PDFs for extraction by our existing pdf_parser.

API: https://cgspace.cgiar.org/server/api/discover/search/objects
No auth required for public items.
"""

from __future__ import annotations

import httpx

from app.agent_farm.models import PageSection
from app.agent_farm.sources.pdf_parser import parse_pdf_bytes
from app.logger import Step, pipeline_logger as log

_SEARCH_URL = "https://cgspace.cgiar.org/server/api/discover/search/objects"
_ITEM_URL = "https://cgspace.cgiar.org/server/api/core/items/{uuid}/bundles"
_BITSTREAM_URL = "https://cgspace.cgiar.org/server/api/core/bundles/{uuid}/bitstreams"
_DOWNLOAD_URL = "https://cgspace.cgiar.org/server/api/core/bitstreams/{uuid}/content"

_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
_PDF_TIMEOUT = httpx.Timeout(60.0, connect=15.0)
_MAX_PAPERS = 3  # download top N papers
_MAX_SECTIONS_PER_PAPER = 30  # cap sections per PDF


async def search_cgiar_papers(query: str, max_results: int = 5) -> list[dict]:
    """Search CGSpace for papers matching query. Returns item metadata."""
    params = {
        "query": query,
        "page": 0,
        "size": max_results,
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
        try:
            resp = await client.get(_SEARCH_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            log.log_step(Step.SYSTEM, "cgiar_search_failed", level="WARNING",
                         details={"query": query, "error": str(exc)[:200]})
            return []

    # Extract items from embedded search results
    embedded = data.get("_embedded", {})
    search_result = embedded.get("searchResult", {})
    results_embedded = search_result.get("_embedded", {})
    objects = results_embedded.get("objects", [])

    items = []
    for obj in objects:
        item = obj.get("_embedded", {}).get("indexableObject", {})
        if not item:
            continue

        uuid = item.get("uuid", "")
        name = item.get("name", "")

        items.append({"uuid": uuid, "name": name})

    log.log_step(Step.SYSTEM, "cgiar_search", details={
        "query": query, "results": len(items),
    })

    return items


async def _get_pdf_download_url(item_uuid: str, client: httpx.AsyncClient) -> str | None:
    """Resolve item UUID -> bundle -> bitstream -> PDF download URL."""
    try:
        # Get bundles
        resp = await client.get(_ITEM_URL.format(uuid=item_uuid))
        resp.raise_for_status()
        bundles_data = resp.json()

        bundles = bundles_data.get("_embedded", {}).get("bundles", [])

        for bundle in bundles:
            if bundle.get("name") != "ORIGINAL":
                continue

            bundle_uuid = bundle.get("uuid", "")
            if not bundle_uuid:
                continue

            # Get bitstreams in this bundle
            bs_resp = await client.get(_BITSTREAM_URL.format(uuid=bundle_uuid))
            bs_resp.raise_for_status()
            bs_data = bs_resp.json()

            bitstreams = bs_data.get("_embedded", {}).get("bitstreams", [])
            for bs in bitstreams:
                mime = bs.get("dc.format.mimetype") or ""
                name = bs.get("name", "")
                bs_uuid = bs.get("uuid", "")

                if "pdf" in mime.lower() or name.lower().endswith(".pdf"):
                    return _DOWNLOAD_URL.format(uuid=bs_uuid)

    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        log.log_step(Step.SYSTEM, "cgiar_resolve_failed", level="WARNING",
                     details={"uuid": item_uuid, "error": str(exc)[:200]})

    return None


async def fetch_cgiar_pdfs(
    query: str = "cassava fertilizer nutrient management West Africa",
    crops: list[str] | None = None,
) -> list[PageSection]:
    """Search CGIAR, download top PDFs, parse into PageSections.

    Args:
        query: Search query for CGSpace.
        crops: Crop names to tag sections with.

    Returns:
        List of PageSection objects from downloaded PDFs.
    """
    crops = crops or ["cassava"]

    # Step 1: Search
    items = await search_cgiar_papers(query, max_results=_MAX_PAPERS + 2)
    if not items:
        return []

    all_sections: list[PageSection] = []

    async with httpx.AsyncClient(
        timeout=_PDF_TIMEOUT, follow_redirects=True
    ) as client:
        downloaded = 0

        for item in items:
            if downloaded >= _MAX_PAPERS:
                break

            uuid = item["uuid"]
            name = item["name"]

            # Step 2: Resolve PDF URL
            pdf_url = await _get_pdf_download_url(uuid, client)
            if not pdf_url:
                log.log_step(Step.SYSTEM, "cgiar_no_pdf", level="WARNING",
                             details={"name": name, "uuid": uuid})
                continue

            # Step 3: Download PDF
            try:
                resp = await client.get(pdf_url)
                resp.raise_for_status()
                pdf_bytes = resp.content
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                log.log_step(Step.SYSTEM, "cgiar_download_failed", level="WARNING",
                             details={"name": name, "error": str(exc)[:200]})
                continue

            downloaded += 1

            log.log_step(Step.SYSTEM, "cgiar_pdf_downloaded", details={
                "name": name, "size_bytes": len(pdf_bytes),
            })

            # Step 4: Parse PDF into sections
            source_name = f"CGIAR: {name[:80]}"
            sections = parse_pdf_bytes(
                pdf_bytes,
                source_url=f"https://cgspace.cgiar.org/handle/{uuid}",
                source_name=source_name,
            )

            # Tag with crop and cap sections
            for s in sections[:_MAX_SECTIONS_PER_PAPER]:
                if len(crops) == 1:
                    s.crop = crops[0]
                all_sections.append(s)

    log.log_step(Step.SYSTEM, "cgiar_fetch_complete", details={
        "query": query,
        "papers_downloaded": downloaded,
        "total_sections": len(all_sections),
    })

    return all_sections
