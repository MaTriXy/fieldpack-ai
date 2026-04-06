"""Source registry for Phase A deterministic fetching.

Each SourceConfig defines a known high-quality data source with URL templates,
crop-slug mappings, and parser type. Adding a new source = one config entry.
"""

from app.agent_farm.models import SourceConfig


# ============================================================
# Tier 1: Known HTML sources (fetch + parse by headings)
# ============================================================

PLANTVILLAGE = SourceConfig(
    name="PlantVillage",
    url_template="https://plantvillage.psu.edu/topics/{slug}/infos",
    slug_map={
        "cassava": "cassava-manioc",
        "rice": "rice",
        "maize": "maize",
        "groundnut": "peanut-groundnut",
        "tomato": "tomato",
    },
    parser_type="html_headings",
    tier=1,
)

INFONET_BIOVISION = SourceConfig(
    name="Infonet-Biovision",
    url_template="https://infonet-biovision.org/crops-fruits-vegetables/{slug}",
    slug_map={
        "cassava": "cassava-revised",
        "rice": "rice",
        "maize": "maize",
        "groundnut": "groundnut",
        "tomato": "tomato-solanum-lycopersicum",
    },
    parser_type="html_headings",
    tier=1,
)

# EPPO uses pest/disease codes, not crop slugs — entries added during gap analysis
EPPO = SourceConfig(
    name="EPPO Global Database",
    url_template="https://gd.eppo.int/taxon/{slug}/datasheet",
    slug_map={},  # populated dynamically per disease/pest code
    parser_type="html_headings",
    tier=1,
)

# ============================================================
# Tier 2: PDF sources (download + pdfplumber)
# ============================================================

FAO_CASSAVA_FFS = SourceConfig(
    name="FAO Cassava Farmer Field School Guide",
    url_template="https://www.fao.org/4/i3447e/i3447e.pdf",
    slug_map={"cassava": ""},  # single PDF, no slug needed
    parser_type="pdf_pages",
    tier=2,
)

FAO_SAVE_AND_GROW = SourceConfig(
    name="FAO Save and Grow: Cassava",
    url_template="https://www.fao.org/4/i3278e/i3278e03.pdf",
    slug_map={"cassava": ""},
    parser_type="pdf_pages",
    tier=2,
)

IITA_CASSAVA_MANUAL = SourceConfig(
    name="IITA Cassava in Tropical Africa Reference Manual",
    url_template="https://www.iita.org/wp-content/uploads/2016/06/Cassava_in_tropical_Africa_a_reference_manual_1990.pdf",
    slug_map={"cassava": ""},
    parser_type="pdf_pages",
    tier=2,
)

# ============================================================
# Tier 3: Climate data (parse tables directly, no LLM)
# ============================================================

WEATHER_AND_CLIMATE = SourceConfig(
    name="Weather and Climate",
    url_template="https://weather-and-climate.com/average-monthly-Rainfall-Temperature-Sunshine,{slug},Senegal",
    slug_map={
        "ziguinchor": "Ziguinchor",
        "kolda": "Kolda",
        "sedhiou": "Sedhiou",
    },
    parser_type="climate_table",
    tier=3,
)

# ============================================================
# Aggregated lists
# ============================================================

HTML_SOURCES = [PLANTVILLAGE, INFONET_BIOVISION]
PDF_SOURCES = [FAO_CASSAVA_FFS, FAO_SAVE_AND_GROW, IITA_CASSAVA_MANUAL]
CLIMATE_SOURCES = [WEATHER_AND_CLIMATE]

ALL_SOURCES = HTML_SOURCES + PDF_SOURCES + CLIMATE_SOURCES


def get_urls_for_crop(crop: str) -> list[tuple[SourceConfig, str]]:
    """Return (source_config, resolved_url) pairs for a given crop."""
    results = []
    for source in HTML_SOURCES:
        slug = source.slug_map.get(crop.lower())
        if slug:
            results.append((source, source.url_template.format(slug=slug)))
    return results


def get_pdf_urls() -> list[tuple[SourceConfig, str]]:
    """Return (source_config, url) pairs for all PDF sources."""
    return [(source, source.url_template) for source in PDF_SOURCES]


def get_climate_urls() -> list[tuple[SourceConfig, str]]:
    """Return (source_config, resolved_url) pairs for climate data."""
    results = []
    for source in CLIMATE_SOURCES:
        for city, slug in source.slug_map.items():
            results.append((source, source.url_template.format(slug=slug)))
    return results
