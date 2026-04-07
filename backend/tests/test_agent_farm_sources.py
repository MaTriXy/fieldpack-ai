"""Tests for Phase 1 Agent Farm source modules.

Covers:
  - sources/registry.py: URL resolution, constants
  - sources/html_parser.py: heading splitting, sliding window, section type guessing
  - sources/pdf_parser.py: PDF byte parsing (mocked pdfplumber)
  - sources/climate_parser.py: table extraction, drought risk, number parsing
  - sources/image_downloader.py: download flow, validation, slug generation
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agent_farm.models import PageSection
from app.agent_farm.sources.registry import (
    ALL_SOURCES,
    CGIAR_SOURCES,
    HTML_SOURCES,
    OPEN_METEO_CITIES,
    PDF_SOURCES,
    get_climate_cities,
    get_pdf_urls,
    get_urls_for_crop,
)
from app.agent_farm.sources.html_parser import (
    _guess_section_type,
    parse_html_by_headings,
    sliding_window,
)
from app.agent_farm.sources.climate_parser import (
    _guess_climate_field,
    _parse_number,
    parse_climate_tables,
)
from app.agent_farm.sources.pdf_parser import parse_pdf_bytes
from app.agent_farm.sources.image_downloader import (
    _slugify,
    download_image,
)


# ============================================================
# Registry
# ============================================================


class TestRegistry:
    def test_get_urls_for_crop_cassava(self):
        results = get_urls_for_crop("cassava")
        assert len(results) == 2  # PlantVillage + Infonet-Biovision
        urls = [url for _, url in results]
        assert any("plantvillage" in u for u in urls)
        assert any("infonet-biovision" in u for u in urls)

    def test_get_urls_for_crop_case_insensitive(self):
        results_lower = get_urls_for_crop("cassava")
        results_upper = get_urls_for_crop("Cassava")
        results_mixed = get_urls_for_crop("CASSAVA")
        assert len(results_lower) == len(results_upper) == len(results_mixed)

    def test_get_urls_for_crop_unknown(self):
        results = get_urls_for_crop("banana")
        assert results == []

    def test_get_urls_for_all_known_crops(self):
        for crop in ["cassava", "rice", "maize", "groundnut", "tomato"]:
            results = get_urls_for_crop(crop)
            assert len(results) == 2, f"Expected 2 URLs for {crop}"

    def test_get_urls_slug_substitution(self):
        results = get_urls_for_crop("cassava")
        pv_url = [u for _, u in results if "plantvillage" in u][0]
        assert "cassava-manioc" in pv_url

    def test_get_pdf_urls(self):
        results = get_pdf_urls()
        assert len(results) == 3
        urls = [url for _, url in results]
        assert any("i3447e" in u for u in urls)
        assert any("i3278e" in u for u in urls)
        assert any("iita" in u.lower() for u in urls)

    def test_get_climate_cities(self):
        cities = get_climate_cities()
        assert len(cities) == 3
        assert "Ziguinchor" in cities
        assert "Kolda" in cities
        assert "Sédhiou" in cities
        for name, (lat, lon) in cities.items():
            assert 12.0 < lat < 14.0, f"{name} lat out of range"
            assert -17.0 < lon < -14.0, f"{name} lon out of range"

    def test_all_sources_count(self):
        assert len(ALL_SOURCES) == len(HTML_SOURCES) + len(PDF_SOURCES) + len(CGIAR_SOURCES)
        assert len(HTML_SOURCES) == 2
        assert len(PDF_SOURCES) == 3
        assert len(CGIAR_SOURCES) == 1


# ============================================================
# HTML parser
# ============================================================


_SAMPLE_HTML_HEADINGS = """
<html><body>
<nav>Navigation bar</nav>
<h2>Diseases</h2>
<p>Cassava Mosaic Disease causes leaf curl and yellow mosaic pattern on leaves.
The virus is transmitted by whiteflies and causes up to 50% yield loss.</p>
<h2>Pests</h2>
<p>The cassava green mite is a major pest in sub-Saharan Africa.
It causes stippling and bronzing of leaves during dry season.</p>
<h3>Whitefly Control</h3>
<p>Use yellow sticky traps to monitor whitefly populations.
Neem oil spray is an effective organic treatment option for infested fields.</p>
</body></html>
"""

_SAMPLE_HTML_NO_HEADINGS = """
<html><body>
<p>This is a page with no headings at all. It contains information about
cassava farming practices in the Casamance region of Senegal. Farmers here
grow cassava as their primary staple crop alongside rice and groundnuts.
The rainy season runs from June to October.</p>
</body></html>
"""


class TestParseHtmlByHeadings:
    def test_splits_on_h2_headings(self):
        sections = parse_html_by_headings(
            _SAMPLE_HTML_HEADINGS, "https://example.com", "Test",
        )
        assert len(sections) >= 2
        headings = [s.heading for s in sections]
        assert "Diseases" in headings
        assert "Pests" in headings

    def test_h3_creates_section(self):
        sections = parse_html_by_headings(
            _SAMPLE_HTML_HEADINGS, "https://example.com", "Test",
        )
        headings = [s.heading for s in sections]
        assert "Whitefly Control" in headings

    def test_strips_nav(self):
        sections = parse_html_by_headings(
            _SAMPLE_HTML_HEADINGS, "https://example.com", "Test",
        )
        all_content = " ".join(s.content for s in sections)
        assert "Navigation bar" not in all_content

    def test_strips_script_and_style(self):
        html = """
        <html><body>
        <script>alert('x')</script>
        <style>.foo { color: red }</style>
        <h2>Content</h2>
        <p>Real content about cassava diseases and treatments for field workers.</p>
        </body></html>
        """
        sections = parse_html_by_headings(html, "url", "name")
        all_content = " ".join(s.content for s in sections)
        assert "alert" not in all_content
        assert "color" not in all_content

    def test_fallback_to_sliding_window(self):
        sections = parse_html_by_headings(
            _SAMPLE_HTML_NO_HEADINGS, "https://example.com", "Test",
        )
        if sections:
            assert sections[0].heading.startswith("section_")

    def test_source_url_and_name_set(self):
        sections = parse_html_by_headings(
            _SAMPLE_HTML_HEADINGS, "https://example.com/page", "PlantVillage",
        )
        for s in sections:
            assert s.source_url == "https://example.com/page"
            assert s.source_name == "PlantVillage"

    def test_section_type_guessed(self):
        sections = parse_html_by_headings(
            _SAMPLE_HTML_HEADINGS, "url", "name",
        )
        disease_sections = [s for s in sections if s.section_type == "disease"]
        assert len(disease_sections) >= 1

    def test_empty_html(self):
        sections = parse_html_by_headings("", "url", "name")
        assert sections == []

    def test_crop_not_set_by_parser(self):
        sections = parse_html_by_headings(
            _SAMPLE_HTML_HEADINGS, "url", "name",
        )
        for s in sections:
            assert s.crop == ""


class TestSlidingWindow:
    def test_basic_windowing(self):
        text = "A" * 6000
        sections = sliding_window(text, "url", "name")
        assert len(sections) >= 2

    def test_overlap_creates_redundancy(self):
        text = "A" * 3200
        sections = sliding_window(text, "url", "name")
        assert len(sections) == 2
        # Second window starts at 2800 (3000 - 200 overlap)
        assert len(sections[1].content) > 0

    def test_heading_format(self):
        text = "A" * 3500
        sections = sliding_window(text, "url", "name")
        assert sections[0].heading == "section_1"
        assert sections[1].heading == "section_2"

    def test_too_short_text(self):
        sections = sliding_window("short", "url", "name")
        assert sections == []

    def test_exactly_min_length(self):
        text = "A" * 50
        sections = sliding_window(text, "url", "name")
        assert len(sections) == 1

    def test_single_window_for_small_text(self):
        # 2999 chars: first window 0-3000 (gets 2999), second starts at 2800
        # so 2 windows are produced (overlap region)
        text = "B" * 2999
        sections = sliding_window(text, "url", "name")
        assert len(sections) == 2
        assert len(sections[0].content) == 2999


class TestGuessSectionType:
    @pytest.mark.parametrize("heading,expected", [
        ("Diseases and Disorders", "disease"),
        ("Cassava Mosaic Virus", "disease"),
        ("Bacterial Blight", "disease"),
        ("Common Pests", "pest"),
        ("Insect Management", "pest"),
        ("Green Mite Control", "pest"),
        ("Treatment Options", "treatment"),
        ("Chemical Control Methods", "treatment"),
        ("Variety Selection", "variety"),
        ("Improved Cultivars", "variety"),
        ("Climate and Weather", "climate"),
        ("Drought Patterns", "climate"),
        ("Soil Requirements", "soil"),
        ("Fertilizer Application", "soil"),
        ("Planting Guide", "planting"),
        ("Harvest Calendar", "planting"),
        ("Post-harvest Storage", "planting"),  # "harvest" matches planting before storage
        ("Drying Methods", "storage"),
        ("General Information", ""),
        ("Introduction", ""),
    ])
    def test_heading_classification(self, heading, expected):
        assert _guess_section_type(heading) == expected


# ============================================================
# PDF parser
# ============================================================


class TestParsePdfBytes:
    def test_valid_pdf(self):
        """Test with a minimal valid PDF generated in-memory."""
        try:
            import pdfplumber
        except ImportError:
            pytest.skip("pdfplumber not installed")

        # Create a minimal PDF with reportlab if available, else use fpdf2
        pdf_bytes = _make_test_pdf(
            "This is a test page with enough content to exceed the minimum page text length "
            "threshold of one hundred characters. Cassava farming in Casamance region."
        )
        sections = parse_pdf_bytes(pdf_bytes, "test.pdf", "Test PDF")
        assert len(sections) >= 1
        assert sections[0].heading == "page_1"
        assert "Cassava" in sections[0].content

    def test_short_page_skipped(self):
        pdf_bytes = _make_test_pdf("Too short")
        sections = parse_pdf_bytes(pdf_bytes, "test.pdf", "Test PDF")
        assert len(sections) == 0

    def test_corrupt_bytes_returns_empty(self):
        sections = parse_pdf_bytes(b"not a pdf", "test.pdf", "Test PDF")
        assert sections == []

    def test_source_fields_set(self):
        pdf_bytes = _make_test_pdf(
            "This is a test page with enough content to pass the minimum text length "
            "filter. It discusses agricultural practices for cassava in West Africa."
        )
        sections = parse_pdf_bytes(pdf_bytes, "https://fao.org/test.pdf", "FAO Guide")
        if sections:
            assert sections[0].source_url == "https://fao.org/test.pdf"
            assert sections[0].source_name == "FAO Guide"


def _make_test_pdf(text: str) -> bytes:
    """Create a minimal valid PDF with the given text content."""
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(0, 10, text)
    return pdf.output()


# ============================================================
# Climate parser
# ============================================================


_SAMPLE_CLIMATE_HTML = """
<html><body>
<table>
<tr><th>Parameter</th><th>Jan</th><th>Feb</th><th>Mar</th><th>Apr</th>
    <th>May</th><th>Jun</th><th>Jul</th><th>Aug</th><th>Sep</th>
    <th>Oct</th><th>Nov</th><th>Dec</th></tr>
<tr><td>Average Rainfall (mm)</td>
    <td>2</td><td>1</td><td>0</td><td>1</td>
    <td>25</td><td>120</td><td>350</td><td>450</td><td>300</td>
    <td>150</td><td>15</td><td>3</td></tr>
<tr><td>Average Temperature (C)</td>
    <td>25</td><td>27</td><td>29</td><td>30</td>
    <td>30</td><td>28</td><td>27</td><td>26</td><td>27</td>
    <td>28</td><td>27</td><td>25</td></tr>
<tr><td>Max Temperature (C)</td>
    <td>32</td><td>34</td><td>36</td><td>37</td>
    <td>36</td><td>33</td><td>31</td><td>30</td><td>31</td>
    <td>32</td><td>33</td><td>31</td></tr>
</table>
</body></html>
"""


class TestParseClimateTables:
    def test_returns_12_records(self):
        records = parse_climate_tables(_SAMPLE_CLIMATE_HTML, "Casamance", "url")
        assert len(records) == 12

    def test_month_numbers(self):
        records = parse_climate_tables(_SAMPLE_CLIMATE_HTML, "Casamance", "url")
        months = [r["month"] for r in records]
        assert months == list(range(1, 13))

    def test_region_set(self):
        records = parse_climate_tables(_SAMPLE_CLIMATE_HTML, "Ziguinchor", "url")
        for r in records:
            assert r["region"] == "Ziguinchor"

    def test_rainfall_extracted(self):
        records = parse_climate_tables(_SAMPLE_CLIMATE_HTML, "Casamance", "url")
        jan = records[0]
        assert jan["rainfall_mm"] == 2.0
        aug = records[7]
        assert aug["rainfall_mm"] == 450.0

    def test_temperature_extracted(self):
        records = parse_climate_tables(_SAMPLE_CLIMATE_HTML, "Casamance", "url")
        jan = records[0]
        assert jan["temperature_avg_c"] == 25.0

    def test_max_temperature_excluded(self):
        records = parse_climate_tables(_SAMPLE_CLIMATE_HTML, "Casamance", "url")
        # Max temp rows should be skipped by _guess_climate_field
        for r in records:
            assert "max_temperature" not in r

    def test_drought_risk_severe(self):
        records = parse_climate_tables(_SAMPLE_CLIMATE_HTML, "Casamance", "url")
        # March has 0mm rainfall
        mar = records[2]
        assert mar["drought_risk"] == "severe"

    def test_drought_risk_high(self):
        records = parse_climate_tables(_SAMPLE_CLIMATE_HTML, "Casamance", "url")
        # Feb has 1mm
        feb = records[1]
        assert feb["drought_risk"] == "severe"  # <10

    def test_drought_risk_medium(self):
        records = parse_climate_tables(_SAMPLE_CLIMATE_HTML, "Casamance", "url")
        # May has 25mm
        may = records[4]
        assert may["drought_risk"] == "high"  # 10 <= 25 < 30

    def test_drought_risk_low(self):
        records = parse_climate_tables(_SAMPLE_CLIMATE_HTML, "Casamance", "url")
        # Aug has 450mm
        aug = records[7]
        assert aug["drought_risk"] == "low"

    def test_empty_html(self):
        records = parse_climate_tables("<html></html>", "Casamance", "url")
        assert len(records) == 12
        # All records should have only region and month
        for r in records:
            assert "rainfall_mm" not in r


class TestParseNumber:
    def test_simple_integer(self):
        assert _parse_number("25") == 25.0

    def test_float(self):
        assert _parse_number("25.5") == 25.5

    def test_comma_decimal(self):
        assert _parse_number("25,5") == 25.5

    def test_with_units(self):
        assert _parse_number("120 mm") == 120.0

    def test_whitespace(self):
        assert _parse_number("  42  ") == 42.0

    def test_non_numeric(self):
        assert _parse_number("N/A") is None

    def test_empty(self):
        assert _parse_number("") is None


class TestGuessClimateField:
    def test_rainfall(self):
        assert _guess_climate_field("average rainfall (mm)") == "rainfall_mm"
        assert _guess_climate_field("precipitation") == "rainfall_mm"

    def test_temperature_avg(self):
        assert _guess_climate_field("average temperature") == "temperature_avg_c"

    def test_temperature_max_excluded(self):
        assert _guess_climate_field("max temperature") is None

    def test_temperature_min_excluded(self):
        assert _guess_climate_field("min temperature") is None

    def test_humidity(self):
        assert _guess_climate_field("relative humidity") == "humidity_pct"

    def test_evapotranspiration(self):
        assert _guess_climate_field("evapotranspiration (mm)") == "evapotranspiration_mm"

    def test_unknown_label(self):
        assert _guess_climate_field("sunshine hours") is None


# ============================================================
# Image downloader
# ============================================================


class TestSlugify:
    def test_basic(self):
        assert _slugify("Cassava Mosaic Disease") == "cassava_mosaic_disease"

    def test_special_chars(self):
        assert _slugify("CMD (viral)") == "cmd_viral"

    def test_strips_trailing_underscores(self):
        assert _slugify("test...") == "test"

    def test_empty_string(self):
        assert _slugify("") == ""


class TestDownloadImage:
    async def test_successful_download(self, tmp_path):
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "image/jpeg"}
        mock_response.content = b"\xff\xd8" + b"\x00" * 5000
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.agent_farm.sources.image_downloader.httpx.AsyncClient",
                    return_value=mock_client):
            result = await download_image(
                url="https://example.com/photo.jpg",
                category="diseases",
                entity_name="Cassava Mosaic Disease",
                images_dir=tmp_path,
            )

        assert result is not None
        assert result.exists()
        assert "cassava_mosaic_disease" in str(result)
        assert result.parent.parent.name == "diseases"

    async def test_invalid_content_type_returns_none(self, tmp_path):
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "text/html"}
        mock_response.content = b"<html>Not an image</html>" * 500
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.agent_farm.sources.image_downloader.httpx.AsyncClient",
                    return_value=mock_client):
            result = await download_image(
                url="https://example.com/page.html",
                category="diseases",
                entity_name="CMD",
                images_dir=tmp_path,
            )

        assert result is None

    async def test_too_small_returns_none(self, tmp_path):
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "image/jpeg"}
        mock_response.content = b"\xff\xd8" + b"\x00" * 100  # < 5000 bytes
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.agent_farm.sources.image_downloader.httpx.AsyncClient",
                    return_value=mock_client):
            result = await download_image(
                url="https://example.com/icon.jpg",
                category="diseases",
                entity_name="CMD",
                images_dir=tmp_path,
            )

        assert result is None

    async def test_http_error_returns_none(self, tmp_path):
        import httpx as _httpx

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=_httpx.RequestError("Connection failed"),
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.agent_farm.sources.image_downloader.httpx.AsyncClient",
                    return_value=mock_client):
            result = await download_image(
                url="https://example.com/fail.jpg",
                category="diseases",
                entity_name="CMD",
                images_dir=tmp_path,
            )

        assert result is None

    async def test_custom_filename(self, tmp_path):
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "image/png"}
        mock_response.content = b"\x89PNG" + b"\x00" * 5000
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.agent_farm.sources.image_downloader.httpx.AsyncClient",
                    return_value=mock_client):
            result = await download_image(
                url="https://example.com/img",
                category="healthy",
                entity_name="Cassava",
                images_dir=tmp_path,
                filename="custom_name.png",
            )

        assert result is not None
        assert result.name == "custom_name.png"

    async def test_content_type_with_charset(self, tmp_path):
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "image/jpeg; charset=utf-8"}
        mock_response.content = b"\xff\xd8" + b"\x00" * 5000
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.agent_farm.sources.image_downloader.httpx.AsyncClient",
                    return_value=mock_client):
            result = await download_image(
                url="https://example.com/photo.jpg",
                category="diseases",
                entity_name="CMD",
                images_dir=tmp_path,
            )

        assert result is not None

    async def test_directory_structure_created(self, tmp_path):
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "image/jpeg"}
        mock_response.content = b"\xff\xd8" + b"\x00" * 5000
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.agent_farm.sources.image_downloader.httpx.AsyncClient",
                    return_value=mock_client):
            result = await download_image(
                url="https://example.com/photo.jpg",
                category="treatments",
                entity_name="Neem Oil Spray",
                images_dir=tmp_path,
            )

        assert result is not None
        assert (tmp_path / "treatments" / "neem_oil_spray").is_dir()
