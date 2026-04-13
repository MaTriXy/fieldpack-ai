"""Live pipeline tests — runs against real APIs.

Usage (from backend/):
    # Phase A only (zero cost, no API keys):
    PYTHONPATH=. ../venv/Scripts/python.exe -m pytest tests/test_live_pipeline.py -v -k "phase_a" --timeout=120

    # Phase B only (needs GOOGLE_AI_STUDIO_API_KEY):
    PYTHONPATH=. ../venv/Scripts/python.exe -m pytest tests/test_live_pipeline.py -v -k "phase_b" --timeout=300

    # Phase C only (needs both API keys):
    PYTHONPATH=. ../venv/Scripts/python.exe -m pytest tests/test_live_pipeline.py -v -k "phase_c" --timeout=300

    # Phase D only (needs GOOGLE_AI_STUDIO_API_KEY):
    PYTHONPATH=. ../venv/Scripts/python.exe -m pytest tests/test_live_pipeline.py -v -k "phase_d" --timeout=600

    # Full E2E (needs both API keys):
    PYTHONPATH=. ../venv/Scripts/python.exe -m pytest tests/test_live_pipeline.py -v -k "e2e" --timeout=900

    # Everything:
    PYTHONPATH=. ../venv/Scripts/python.exe -m pytest tests/test_live_pipeline.py -v --timeout=900

Checkpoint files are saved to backend/data/live_test_checkpoints/ so you
can restart from any phase without re-running earlier ones.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path

import pytest

from app.config import settings

# ---------------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------------

_CHECKPOINT_DIR = Path(__file__).resolve().parent.parent / "data" / "live_test_checkpoints"


def _save_checkpoint(name: str, data: dict) -> Path:
    """Save intermediate state as JSON for restart capability."""
    _CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    path = _CHECKPOINT_DIR / f"{name}.json"

    # Convert non-serializable objects
    def _default(obj):
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        return str(obj)

    path.write_text(json.dumps(data, indent=2, default=_default), encoding="utf-8")
    return path


def _load_checkpoint(name: str) -> dict | None:
    path = _CHECKPOINT_DIR / f"{name}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


# ---------------------------------------------------------------------------
# Skip conditions
# ---------------------------------------------------------------------------

_has_google_key = bool(settings.google_ai_studio_api_key)
_has_tavily_key = bool(settings.tavily_api_key)

skip_no_google = pytest.mark.skipif(
    not _has_google_key,
    reason="GOOGLE_AI_STUDIO_API_KEY not set in .env",
)
skip_no_tavily = pytest.mark.skipif(
    not _has_tavily_key,
    reason="TAVILY_API_KEY not set in .env",
)


# ===========================================================================
# PHASE A: Source Gathering (zero cost — HTTP only)
# ===========================================================================


class TestPhaseA:
    """Test real HTTP fetches against known source URLs."""

    @pytest.mark.asyncio
    async def test_phase_a_html_plantvillage(self):
        """Fetch PlantVillage cassava page and parse into sections."""
        from app.agent_farm.sources.html_parser import parse_html_by_headings
        from app.agent_farm.tools.web_fetch import fetch_html

        url = "https://plantvillage.psu.edu/topics/cassava-manioc/infos"
        html = await fetch_html(url)

        assert html is not None, f"Failed to fetch {url}"
        assert len(html) > 5000, f"Page too short ({len(html)} chars)"

        sections = parse_html_by_headings(html, source_url=url, source_name="PlantVillage")
        assert len(sections) > 0, "No sections parsed from PlantVillage"

        print(f"\n  PlantVillage cassava: {len(html):,} chars -> {len(sections)} sections")
        for s in sections[:5]:
            print(f"    [{s.heading}] {len(s.content)} chars")

        _save_checkpoint("phase_a_pv_sections", {
            "url": url,
            "html_length": len(html),
            "section_count": len(sections),
            "sections": [
                {"heading": s.heading, "content": s.content[:300], "tables": len(s.tables)}
                for s in sections
            ],
        })

    @pytest.mark.asyncio
    async def test_phase_a_html_infonet(self):
        """Fetch Infonet-Biovision cassava page and parse into sections."""
        from app.agent_farm.sources.html_parser import parse_html_by_headings
        from app.agent_farm.tools.web_fetch import fetch_html

        url = "https://infonet-biovision.org/crops-fruits-vegetables/cassava-revised"
        html = await fetch_html(url)

        assert html is not None, f"Failed to fetch {url}"
        assert len(html) > 3000, f"Page too short ({len(html)} chars)"

        sections = parse_html_by_headings(html, source_url=url, source_name="Infonet-Biovision")
        assert len(sections) > 0, "No sections parsed from Infonet-Biovision"

        print(f"\n  Infonet cassava: {len(html):,} chars -> {len(sections)} sections")
        for s in sections[:5]:
            print(f"    [{s.heading}] {len(s.content)} chars")

    @pytest.mark.asyncio
    async def test_phase_a_pdf_fao(self):
        """Fetch FAO Cassava FFS PDF and parse into sections."""
        from app.agent_farm.sources.pdf_parser import parse_pdf_bytes
        from app.agent_farm.tools.web_fetch import fetch_pdf_bytes

        url = "https://www.fao.org/4/i3447e/i3447e.pdf"
        pdf_bytes = await fetch_pdf_bytes(url)

        assert pdf_bytes is not None, f"Failed to fetch PDF from {url}"
        assert len(pdf_bytes) > 10000, f"PDF too small ({len(pdf_bytes)} bytes)"

        sections = parse_pdf_bytes(pdf_bytes, source_url=url, source_name="FAO Cassava FFS")
        assert len(sections) > 0, "No sections parsed from FAO PDF"

        print(f"\n  FAO Cassava FFS: {len(pdf_bytes):,} bytes -> {len(sections)} sections")
        for s in sections[:3]:
            print(f"    [{s.heading}] {len(s.content)} chars")

    @pytest.mark.asyncio
    async def test_phase_a_climate(self):
        """Fetch climate data from Open-Meteo for Ziguinchor."""
        from app.agent_farm.sources.open_meteo import fetch_climate_open_meteo

        records = await fetch_climate_open_meteo(12.56, -16.27, "Ziguinchor")

        assert len(records) == 12, f"Expected 12 months, got {len(records)}"
        assert records[0].get("rainfall_mm") is not None, "Missing rainfall data"
        assert records[0].get("temperature_avg_c") is not None, "Missing temperature data"

        print(f"\n  Ziguinchor climate (Open-Meteo): {len(records)} monthly records")
        for r in records[:3]:
            print(f"    Month {r.get('month')}: {r.get('rainfall_mm')}mm, {r.get('temperature_avg_c')}C, {r.get('humidity_pct')}%")

        _save_checkpoint("phase_a_climate", {"records": records})

    @pytest.mark.asyncio
    async def test_phase_a_full_gathering(self):
        """Run full source_gathering phase with cassava only."""
        from app.agent_farm.phases.source_gathering import source_gathering

        state = {
            "crops": ["cassava"],
            "region": "Casamance, Senegal",
            "status_messages": [],
            "current_phase": "starting",
        }

        t0 = time.perf_counter()
        result = await source_gathering(state)
        elapsed = time.perf_counter() - t0

        sections = result.get("sections", [])
        climate = result.get("climate_records", [])
        messages = result.get("status_messages", [])

        assert len(sections) > 0, "No sections gathered"

        print(f"\n  Phase A complete in {elapsed:.1f}s:")
        print(f"    Sections: {len(sections)}")
        print(f"    Climate records: {len(climate)}")
        for msg in messages:
            print(f"    > {msg}")

        # Save for Phase B
        _save_checkpoint("phase_a_full", {
            "sections": [
                {
                    "source_url": s.source_url,
                    "source_name": s.source_name,
                    "heading": s.heading,
                    "content": s.content,
                    "crop": s.crop,
                    "section_type": s.section_type,
                    "tables": s.tables,
                }
                for s in sections
            ],
            "climate_records": climate,
            "messages": messages,
            "elapsed_seconds": round(elapsed, 1),
        })


# ===========================================================================
# PHASE B: Knowledge Extraction (Gemma 4 26B via AI Studio)
# ===========================================================================


@skip_no_google
class TestPhaseB:
    """Test LLM extraction on real sections from Phase A."""

    @pytest.mark.asyncio
    async def test_phase_b_single_section(self):
        """Extract findings from one real PlantVillage section."""
        from app.agent_farm.models import ExtractionOutput, PageSection
        from app.models.online_llm import get_research_llm, invoke_structured

        # Use a checkpoint section or create a minimal one
        checkpoint = _load_checkpoint("phase_a_full")
        if checkpoint and checkpoint.get("sections"):
            sec_data = checkpoint["sections"][0]
            section = PageSection(**sec_data)
        else:
            section = PageSection(
                source_url="https://plantvillage.psu.edu/topics/cassava-manioc/infos",
                source_name="PlantVillage",
                heading="Diseases",
                content=(
                    "Cassava mosaic disease (CMD) is caused by several species of "
                    "cassava mosaic geminiviruses. It is the most important disease "
                    "of cassava in Africa, causing yield losses of 20-95%. Symptoms "
                    "include leaf curling, mosaic patterns of light and dark green "
                    "areas on leaves, and stunted growth. The virus is transmitted "
                    "by the whitefly Bemisia tabaci and through infected stem cuttings."
                ),
                crop="cassava",
                section_type="disease",
            )

        llm = get_research_llm()

        prompt = (
            f"You are an agricultural knowledge extraction agent.\n\n"
            f"CROP: {section.crop}\nSOURCE: {section.source_url}\n\n"
            f"--- TEXT ---\n{section.content}\n--- END TEXT ---\n\n"
            f"Extract all distinct knowledge nuggets from this text."
        )

        t0 = time.perf_counter()
        result = await invoke_structured(llm, prompt, ExtractionOutput)
        elapsed = time.perf_counter() - t0

        assert isinstance(result, ExtractionOutput), f"Wrong type: {type(result)}"
        assert len(result.findings) > 0, "No findings extracted"

        print(f"\n  Single section extraction in {elapsed:.1f}s:")
        print(f"    Source: {section.source_name} — {section.heading}")
        print(f"    Findings: {len(result.findings)}")
        for fe in result.findings:
            print(f"    [{fe.domain}] {fe.entity_name}: {fe.content[:100]}...")

    @pytest.mark.asyncio
    async def test_phase_b_batch_extraction(self):
        """Extract from 5 real sections — tests concurrency + rate limiter."""
        from app.agent_farm.models import PageSection
        from app.agent_farm.phases.knowledge_extraction import knowledge_extraction

        checkpoint = _load_checkpoint("phase_a_full")
        if not checkpoint or not checkpoint.get("sections"):
            pytest.skip("Run Phase A tests first to generate checkpoint data")

        # Take first 5 sections to keep API calls low
        sections = [PageSection(**s) for s in checkpoint["sections"][:5]]
        climate = checkpoint.get("climate_records", [])

        state = {
            "sections": sections,
            "climate_records": climate,
            "status_messages": [],
            "current_phase": "gathering",
        }

        t0 = time.perf_counter()
        result = await knowledge_extraction(state)
        elapsed = time.perf_counter() - t0

        findings = result.get("findings", [])
        messages = result.get("status_messages", [])

        assert len(findings) > 0, "No findings extracted"

        # Count by domain
        domain_counts: dict[str, int] = {}
        for f in findings:
            domain_counts[f.domain] = domain_counts.get(f.domain, 0) + 1

        print(f"\n  Batch extraction ({len(sections)} sections + {len(climate)} climate) in {elapsed:.1f}s:")
        print(f"    Total findings: {len(findings)}")
        print(f"    Domain distribution: {domain_counts}")
        for msg in messages:
            print(f"    > {msg}")

        # Save for Phase C/D
        _save_checkpoint("phase_b_findings", {
            "findings": [
                {
                    "domain": f.domain,
                    "entity_name": f.entity_name,
                    "content": f.content,
                    "related_entities": f.related_entities,
                    "source": f.source,
                    "confidence": f.confidence,
                    "raw_data": f.raw_data,
                }
                for f in findings
            ],
            "domain_counts": domain_counts,
            "elapsed_seconds": round(elapsed, 1),
        })


# ===========================================================================
# PHASE C: Gap Analysis (Gemma 4 31B + Tavily)
# ===========================================================================


@skip_no_google
@skip_no_tavily
class TestPhaseC:
    """Test gap analysis with real findings and live Tavily search."""

    @pytest.mark.asyncio
    async def test_phase_c_tavily_text_search(self):
        """Verify Tavily text search works with agricultural query."""
        from app.agent_farm.tools.web_search import search_text

        results = await asyncio.to_thread(
            search_text,
            query="cassava mosaic disease treatment Senegal",
            max_results=3,
            include_domains=["fao.org", "cgiar.org", "iita.org"],
        )

        assert isinstance(results, list), f"Wrong type: {type(results)}"
        print(f"\n  Tavily text search: {len(results)} results")
        for r in results:
            print(f"    {r.get('title', 'N/A')[:60]} — {r.get('url', 'N/A')[:60]}")

    @pytest.mark.asyncio
    async def test_phase_c_tavily_image_search(self):
        """Verify Tavily image search returns URLs."""
        from app.agent_farm.tools.web_search import search_images

        results = await asyncio.to_thread(
            search_images,
            query="cassava mosaic disease symptoms plant photo",
            max_results=3,
        )

        assert isinstance(results, list), f"Wrong type: {type(results)}"
        print(f"\n  Tavily image search: {len(results)} images")
        for r in results:
            print(f"    {r.get('url', 'N/A')[:80]}")

    @pytest.mark.asyncio
    async def test_phase_c_full_gap_analysis(self):
        """Run full gap_analysis phase on real findings."""
        from app.agent_farm.models import Finding
        from app.agent_farm.phases.gap_analysis import gap_analysis

        checkpoint = _load_checkpoint("phase_b_findings")
        if not checkpoint or not checkpoint.get("findings"):
            pytest.skip("Run Phase B tests first to generate checkpoint data")

        findings = [Finding(**f) for f in checkpoint["findings"]]

        state = {
            "findings": findings,
            "crops": ["cassava"],
            "region": "Casamance, Senegal",
            "status_messages": [],
            "current_phase": "extracting",
        }

        t0 = time.perf_counter()
        result = await gap_analysis(state)
        elapsed = time.perf_counter() - t0

        new_findings = result.get("findings", [])
        gaps = result.get("identified_gaps", [])
        queries = result.get("gap_search_queries", [])
        images = result.get("image_urls", [])
        messages = result.get("status_messages", [])

        print(f"\n  Gap analysis in {elapsed:.1f}s:")
        print(f"    Input findings: {len(findings)}")
        print(f"    Output findings: {len(new_findings)} (+{len(new_findings) - len(findings)} new)")
        print(f"    Gaps identified: {len(gaps)}")
        print(f"    Images found: {len(images)}")
        for msg in messages:
            print(f"    > {msg}")
        if gaps:
            print(f"    Top gaps:")
            for g in gaps[:5]:
                print(f"      - {g}")

        # Save for Phase D
        _save_checkpoint("phase_c_results", {
            "findings": [
                {
                    "domain": f.domain,
                    "entity_name": f.entity_name,
                    "content": f.content,
                    "related_entities": f.related_entities,
                    "source": f.source,
                    "confidence": f.confidence,
                    "raw_data": f.raw_data,
                }
                for f in new_findings
            ],
            "gaps": gaps,
            "queries": queries,
            "image_count": len(images),
            "elapsed_seconds": round(elapsed, 1),
        })


# ===========================================================================
# PHASE D: Compilation (Gemma 4 31B — 10 LLM calls)
# ===========================================================================


@skip_no_google
class TestPhaseD:
    """Test decomposed compilation with real findings."""

    @pytest.mark.asyncio
    async def test_phase_d_compile_crops_only(self):
        """Compile just the crops table — smallest test of the compiler."""
        from app.agent_farm.models import Finding
        from app.agent_farm.phases.compilation import _COMPILATION_STEPS, _compile_one_table

        # Load best available findings
        checkpoint = _load_checkpoint("phase_c_results") or _load_checkpoint("phase_b_findings")
        if not checkpoint or not checkpoint.get("findings"):
            pytest.skip("Run Phase B or C first to generate checkpoint data")

        findings = [Finding(**f) for f in checkpoint["findings"]]
        compiled_ids: dict[str, dict[int, str]] = {}

        # Compile crops (first step, no FK deps)
        crops_step = _COMPILATION_STEPS[0]
        assert crops_step.table_name == "crops"

        t0 = time.perf_counter()
        records, attempts = await _compile_one_table(
            crops_step, findings, compiled_ids,
            region="Casamance, Senegal",
            crops=["cassava"],
            currency="XOF (West African CFA franc)",
        )
        elapsed = time.perf_counter() - t0

        assert len(records) > 0, "No crop records compiled"

        print(f"\n  Crops compilation in {elapsed:.1f}s ({attempts} attempt(s)):")
        for r in records:
            d = r.model_dump()
            print(f"    [{d['id']}] {d['name']} — {d.get('scientific_name', 'N/A')}")

    @pytest.mark.asyncio
    async def test_phase_d_full_compilation(self):
        """Run full compilation phase — all 11 tables."""
        from app.agent_farm.models import Finding
        from app.agent_farm.phases.compilation import compilation

        checkpoint = _load_checkpoint("phase_c_results") or _load_checkpoint("phase_b_findings")
        if not checkpoint or not checkpoint.get("findings"):
            pytest.skip("Run Phase B or C first to generate checkpoint data")

        findings = [Finding(**f) for f in checkpoint["findings"]]

        state = {
            "findings": findings,
            "region": "Casamance, Senegal",
            "crops": ["cassava"],
            "currency": "XOF (West African CFA franc)",
            "status_messages": [],
            "current_phase": "gap_analysis",
        }

        t0 = time.perf_counter()
        result = await compilation(state)
        elapsed = time.perf_counter() - t0

        comp = result.get("compilation")
        json_dir = result.get("json_output_dir", "")
        messages = result.get("status_messages", [])

        assert comp is not None, "No compilation output"

        # Summarize all tables
        table_counts = {}
        for table_name in [
            "crops", "diseases", "crop_diseases", "treatments", "climate",
            "pests", "varieties", "fertilization_schedule", "planting_calendar",
            "storage_guidelines", "soil_requirements",
        ]:
            records = getattr(comp, table_name, [])
            table_counts[table_name] = len(records)

        total = sum(table_counts.values())

        print(f"\n  Full compilation in {elapsed:.1f}s:")
        print(f"    Total records: {total}")
        print(f"    JSON output: {json_dir}")
        for table, count in table_counts.items():
            status = "OK" if count > 0 else "EMPTY"
            print(f"    {table:25s}: {count:3d} records  [{status}]")
        for msg in messages:
            print(f"    > {msg}")

        # Save compilation checkpoint
        _save_checkpoint("phase_d_compilation", {
            "table_counts": table_counts,
            "total_records": total,
            "json_output_dir": json_dir,
            "elapsed_seconds": round(elapsed, 1),
        })


# ===========================================================================
# FULL E2E: run_agent_farm() with cassava
# ===========================================================================


@skip_no_google
class TestE2E:
    """Full end-to-end pipeline test."""

    @pytest.mark.asyncio
    async def test_e2e_single_crop(self):
        """Run full Agent Farm pipeline with cassava only."""
        from app.agent_farm.graph import run_agent_farm

        t0 = time.perf_counter()
        final_state = await run_agent_farm(
            crops=["cassava"],
            region="Casamance, Senegal",
            mission_description=(
                "Deploying to Casamance to help smallholder cassava farmers. "
                "Need disease identification, treatment advice with local materials, "
                "and drought-resistant variety recommendations."
            ),
        )
        elapsed = time.perf_counter() - t0

        # Validate state
        sections = final_state.get("sections", [])
        findings = final_state.get("findings", [])
        comp = final_state.get("compilation")
        chunks = final_state.get("chunks", {})
        json_dir = final_state.get("json_output_dir", "")
        downloaded = final_state.get("downloaded_images", [])
        messages = final_state.get("status_messages", [])

        assert len(sections) > 0, "No sections gathered"
        assert len(findings) > 0, "No findings extracted"
        assert comp is not None, "No compilation output"

        # Table summary
        table_counts = {}
        for table_name in [
            "crops", "diseases", "crop_diseases", "treatments", "climate",
            "pests", "varieties", "fertilization_schedule", "planting_calendar",
            "storage_guidelines", "soil_requirements",
        ]:
            table_counts[table_name] = len(getattr(comp, table_name, []))

        total_records = sum(table_counts.values())
        total_chunks = sum(len(v) for v in chunks.values())

        print(f"\n{'='*60}")
        print(f"  E2E PIPELINE COMPLETE — {elapsed:.1f}s")
        print(f"{'='*60}")
        print(f"  Sections gathered:  {len(sections)}")
        print(f"  Findings extracted: {len(findings)}")
        print(f"  Tables compiled:    {total_records} records across 11 tables")
        print(f"  Chunks generated:   {total_chunks}")
        print(f"  Images downloaded:  {len(downloaded)}")
        print(f"  JSON output dir:    {json_dir}")
        print()
        for table, count in table_counts.items():
            status = "OK" if count > 0 else "EMPTY"
            print(f"    {table:25s}: {count:3d} records  [{status}]")
        print()
        print("  Chunk collections:")
        for collection, chunk_list in chunks.items():
            print(f"    {collection:25s}: {len(chunk_list):3d} chunks")
        print()
        print("  Status messages:")
        for msg in messages:
            print(f"    > {msg}")

        # Verify critical tables have data
        assert table_counts["crops"] >= 1, "Need at least 1 crop record"
        assert table_counts["diseases"] >= 1, "Need at least 1 disease record"
        assert total_chunks > 0, "Need at least some chunks"

        # Save final checkpoint
        _save_checkpoint("e2e_complete", {
            "elapsed_seconds": round(elapsed, 1),
            "sections_count": len(sections),
            "findings_count": len(findings),
            "table_counts": table_counts,
            "total_records": total_records,
            "total_chunks": total_chunks,
            "images_downloaded": len(downloaded),
            "json_output_dir": json_dir,
            "messages": messages,
        })
