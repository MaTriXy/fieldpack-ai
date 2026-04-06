"""HTML parser for Phase A source gathering.

Splits HTML pages into PageSection objects by h2/h3 headings.
Fallback: sliding window (3000 chars, 200 overlap) for pages
without clean heading structure. NEVER truncates content.
"""

from __future__ import annotations

from bs4 import BeautifulSoup, Tag

from app.agent_farm.models import PageSection

_HEADING_TAGS = {"h2", "h3"}
_WINDOW_SIZE = 3000
_WINDOW_OVERLAP = 200
_MIN_SECTION_LENGTH = 50  # skip tiny sections (nav fragments, etc.)


def parse_html_by_headings(
    html: str,
    source_url: str,
    source_name: str,
) -> list[PageSection]:
    """Split HTML into sections by h2/h3 headings.

    Falls back to sliding window if fewer than 2 heading-based sections
    are found (indicating the page lacks clean heading structure).
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove script, style, nav, footer — not content
    for tag in soup.find_all(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    sections = _extract_heading_sections(soup, source_url, source_name)

    if len(sections) < 2:
        # Fallback: sliding window over full text
        full_text = soup.get_text(separator="\n", strip=True)
        sections = sliding_window(full_text, source_url, source_name)

    return sections


def _extract_heading_sections(
    soup: BeautifulSoup,
    source_url: str,
    source_name: str,
) -> list[PageSection]:
    """Walk the DOM and group content under h2/h3 headings.

    Uses find_all_next() instead of next_sibling so that content
    inside wrapper divs (common in CMS pages) is still captured.
    """
    sections: list[PageSection] = []
    headings = soup.find_all(_HEADING_TAGS)

    if not headings:
        return []

    for i, heading in enumerate(headings):
        heading_text = heading.get_text(strip=True)
        if not heading_text:
            continue

        # Collect all elements forward in the DOM until the next heading
        content_parts: list[str] = []
        for elem in heading.find_all_next():
            if isinstance(elem, Tag) and elem.name in _HEADING_TAGS:
                break
            # Only collect leaf text nodes from block-level elements
            # to avoid duplicating text from nested tags
            if isinstance(elem, Tag) and elem.name in (
                "p", "li", "td", "th", "dt", "dd", "blockquote", "figcaption",
            ):
                text = elem.get_text(strip=True)
                if text:
                    content_parts.append(text)

        content = "\n".join(content_parts).strip()
        if len(content) < _MIN_SECTION_LENGTH:
            continue

        section_type = _guess_section_type(heading_text)

        sections.append(PageSection(
            source_url=source_url,
            source_name=source_name,
            heading=heading_text,
            content=content,
            section_type=section_type,
        ))

    return sections


def sliding_window(
    text: str,
    source_url: str,
    source_name: str,
) -> list[PageSection]:
    """Split text into overlapping windows when headings are absent."""
    sections: list[PageSection] = []

    if len(text) < _MIN_SECTION_LENGTH:
        return []

    start = 0
    window_num = 1
    while start < len(text):
        end = start + _WINDOW_SIZE
        chunk = text[start:end].strip()

        if len(chunk) >= _MIN_SECTION_LENGTH:
            sections.append(PageSection(
                source_url=source_url,
                source_name=source_name,
                heading=f"section_{window_num}",
                content=chunk,
            ))
            window_num += 1

        # Advance by window - overlap, but at least 1 char to avoid infinite loop
        start += max(_WINDOW_SIZE - _WINDOW_OVERLAP, 1)

    return sections


def _guess_section_type(heading: str) -> str:
    """Heuristic: guess domain from heading text."""
    h = heading.lower()
    if any(w in h for w in ("disease", "virus", "blight", "wilt", "rot", "mosaic")):
        return "disease"
    if any(w in h for w in ("pest", "insect", "mite", "borer", "weevil", "fly")):
        return "pest"
    if any(w in h for w in ("treatment", "control", "manage", "spray", "remedy")):
        return "treatment"
    if any(w in h for w in ("variety", "cultivar", "breed")):
        return "variety"
    if any(w in h for w in ("climate", "weather", "rain", "drought", "temperature")):
        return "climate"
    if any(w in h for w in ("soil", "fertiliz", "nutrient", "compost")):
        return "soil"
    if any(w in h for w in ("plant", "sow", "harvest", "calendar", "season")):
        return "planting"
    if any(w in h for w in ("stor", "post-harvest", "dry")):
        return "storage"
    return ""
