"""Knowledge Pack builder.

Assembles a complete Knowledge Pack from seed data:
  1. Creates directory structure
  2. Initializes SQLite with schema + seed data
  3. Initializes ChromaDB with collections + seed chunks (embedded)
  4. Writes manifest.json, README.md, SOURCES.md
"""

import shutil
import sqlite3
from pathlib import Path

from app.config import settings
from app.knowledge_pack.schema_chroma import init_chroma_db, verify_chroma_collections
from app.knowledge_pack.schema_manifest import (
    ManifestSchema,
    ModelsUsed,
    RegionInfo,
    Statistics,
    create_manifest,
)
from app.knowledge_pack.schema_sqlite import init_sqlite_db, verify_sqlite_schema
from app.knowledge_pack.seed_chunks import get_all_chunks
from app.knowledge_pack.seed_data import (
    CLIMATE,
    CROP_DISEASES,
    CROPS,
    DISEASES,
    TREATMENTS,
)
from app.knowledge_pack.seed_farming import (
    CROPS_EXTRA,
    FERTILIZATION_SCHEDULE,
    PESTS,
    PLANTING_CALENDAR,
    SOIL_REQUIREMENTS,
    STORAGE_GUIDELINES,
    VARIETIES,
)
from app.logger import Step, pipeline_logger as log


def build_pack(pack_name: str, base_path: Path | None = None) -> Path:
    """Build a complete Knowledge Pack from seed data.

    Creates the full directory structure, populates SQLite and ChromaDB,
    and writes the manifest. Returns the path to the created pack.
    """
    log.log_step(Step.PACK_BUILD, "build_start", details={"pack_name": pack_name})

    base = base_path or settings.packs_path
    pack_path = base / pack_name
    pack_path.mkdir(parents=True, exist_ok=True)

    # Directory structure
    (pack_path / "images" / "diseases").mkdir(parents=True, exist_ok=True)
    (pack_path / "images" / "healthy").mkdir(parents=True, exist_ok=True)
    (pack_path / "images" / "treatments").mkdir(parents=True, exist_ok=True)

    # SQLite — remove stale DB so schema changes take effect
    db_path = pack_path / "knowledge.db"
    for suffix in ("", "-wal", "-shm"):
        p = db_path.parent / (db_path.name + suffix)
        p.unlink(missing_ok=True)
    conn = init_sqlite_db(db_path)
    _insert_sqlite_data(conn)
    schema_info = verify_sqlite_schema(conn)
    conn.close()

    log.log_step(Step.PACK_BUILD, "sqlite_seeded", details={
        "crops": len(CROPS),
        "diseases": len(DISEASES),
        "treatments": len(TREATMENTS),
        "climate_records": len(CLIMATE),
        "pests": len(PESTS),
        "varieties": len(VARIETIES),
    })

    # ChromaDB — remove stale data so collection schemas stay current
    chroma_path = pack_path / "chroma_db"
    if chroma_path.exists():
        shutil.rmtree(chroma_path)
    client = init_chroma_db(chroma_path)
    chunks = get_all_chunks()
    _insert_chroma_chunks(client, chunks)
    chroma_info = verify_chroma_collections(client)

    total_chunks = sum(chroma_info.values())
    log.log_step(Step.PACK_BUILD, "chroma_seeded", details={
        "total_chunks": total_chunks,
        "collections": chroma_info,
    })

    # Manifest
    manifest = create_manifest(
        pack_path=pack_path,
        name="Casamance Agriculture Pack",
        description=(
            "Agricultural knowledge for humanitarian workers assisting "
            "smallholder farmers in the Casamance region of Senegal, "
            "focusing on cassava, rice, maize, groundnut, and tomato crops."
        ),
        region=RegionInfo(
            name="Casamance",
            country="Senegal",
            coordinates={"lat": 12.55, "lon": -15.5},
            climate_zone="tropical_savanna",
        ),
        crops=[c["name"] for c in CROPS],
        statistics=Statistics(
            diseases_count=len(DISEASES),
            treatments_count=len(TREATMENTS),
            farming_practices_count=len(chunks.get("farming_practices", [])) // 2,
            text_chunks=total_chunks,
            images_count=0,
        ),
        models_used=ModelsUsed(
            research_agents=settings.online_model_research,
            knowledge_compiler=settings.online_model_large,
            embedding_model=settings.embedding_model,
            embedding_dimensions=settings.embedding_dimensions,
        ),
        sources=["FAO", "IITA", "PlantVillage", "AfricaRice", "ICRISAT", "ISRA Senegal"],
    )

    # README
    (pack_path / "README.md").write_text(
        f"# {manifest.name}\n\n"
        f"{manifest.description}\n\n"
        f"## Contents\n\n"
        f"- **{len(CROPS)} crops**: {', '.join(c['name'] for c in CROPS)}\n"
        f"- **{len(DISEASES)} diseases** with visual identification guides\n"
        f"- **{len(TREATMENTS)} treatment protocols** (organic and conventional)\n"
        f"- **{len(PESTS)} pests** with identification and control methods\n"
        f"- **{len(VARIETIES)} crop varieties** with local adaptation data\n"
        f"- **{len(PLANTING_CALENDAR)} planting calendar** entries\n"
        f"- **12 months** of Casamance climate data\n"
        f"- **{total_chunks} knowledge chunks** for semantic search\n\n"
        f"## Usage\n\n"
        f"Load this pack with FieldPack AI's offline field assistant.\n"
        f"The recommended edge model is `{manifest.recommended_edge_model}`.\n",
        encoding="utf-8",
    )

    # SOURCES
    (pack_path / "SOURCES.md").write_text(
        "# Data Sources\n\n"
        "All data was gathered and validated by Gemma 4 agents from:\n\n"
        + "\n".join(f"- {s}" for s in manifest.sources)
        + "\n\nData is provided for educational and humanitarian purposes.\n",
        encoding="utf-8",
    )

    log.log_step(Step.PACK_BUILD, "build_complete", details={
        "pack_path": str(pack_path),
        "manifest_name": manifest.name,
    })

    return pack_path


def _insert_sqlite_data(conn: sqlite3.Connection):
    """Insert all seed data into SQLite tables in a single transaction."""
    with log.timed(Step.PACK_BUILD, "sqlite_insert") as t:
        cursor = conn.cursor()

        # Crops (base + extra columns)
        for crop in CROPS:
            extra = CROPS_EXTRA.get(crop["id"], {})
            cursor.execute(
                "INSERT INTO crops (id, name, scientific_name, family, growing_season, "
                "water_needs_mm_per_week, drought_tolerance, region_suitability, "
                "planting_notes, harvest_notes, soil_ph_min, soil_ph_max, "
                "seed_rate_kg_per_ha, intercrop_companions) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (crop["id"], crop["name"], crop["scientific_name"], crop["family"],
                 crop["growing_season"], crop["water_needs_mm_per_week"],
                 crop["drought_tolerance"], crop["region_suitability"],
                 crop["planting_notes"], crop["harvest_notes"],
                 extra.get("soil_ph_min"), extra.get("soil_ph_max"),
                 extra.get("seed_rate_kg_per_ha"), extra.get("intercrop_companions")),
            )

        # Diseases
        for disease in DISEASES:
            cursor.execute(
                "INSERT INTO diseases (id, name, common_names, type, symptoms_text, "
                "visual_markers, severity_scale, spread_mechanism, prevention_notes) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (disease["id"], disease["name"], disease.get("common_names"),
                 disease["type"], disease["symptoms_text"], disease["visual_markers"],
                 disease["severity_scale"], disease.get("spread_mechanism"),
                 disease.get("prevention_notes")),
            )

        # Crop-Disease M2M
        for cd in CROP_DISEASES:
            cursor.execute(
                "INSERT INTO crop_diseases (crop_id, disease_id, susceptibility) "
                "VALUES (?, ?, ?)",
                (cd["crop_id"], cd["disease_id"], cd["susceptibility"]),
            )

        # Treatments
        for treat in TREATMENTS:
            cursor.execute(
                "INSERT INTO treatments (id, disease_id, method, description, "
                "materials_needed, difficulty, is_organic, local_availability, "
                "effectiveness, application_timing, safety_notes) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (treat["id"], treat["disease_id"], treat["method"],
                 treat["description"], treat.get("materials_needed"),
                 treat["difficulty"], treat.get("is_organic", True),
                 treat.get("local_availability"), treat["effectiveness"],
                 treat.get("application_timing"), treat.get("safety_notes")),
            )

        # Climate
        for clim in CLIMATE:
            cursor.execute(
                "INSERT INTO climate (id, region, month, rainfall_mm, "
                "temperature_avg_c, humidity_pct, drought_risk, notes) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (clim["id"], clim["region"], clim["month"], clim["rainfall_mm"],
                 clim["temperature_avg_c"], clim["humidity_pct"],
                 clim["drought_risk"], clim.get("notes")),
            )

        # Pests
        for pest in PESTS:
            cursor.execute(
                "INSERT INTO pests (id, name, common_names, crop_id, type, "
                "damage_description, season_peak, identification_notes, "
                "control_organic, control_chemical, economic_threshold, prevention_notes) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (pest["id"], pest["name"], pest.get("common_names"),
                 pest["crop_id"], pest["type"], pest["damage_description"],
                 pest.get("season_peak"), pest.get("identification_notes"),
                 pest.get("control_organic"), pest.get("control_chemical"),
                 pest.get("economic_threshold"), pest.get("prevention_notes")),
            )

        # Varieties
        for var in VARIETIES:
            cursor.execute(
                "INSERT INTO varieties (id, crop_id, name, local_names, "
                "days_to_maturity, yield_potential_kg_per_ha, disease_resistance, "
                "drought_tolerance, seed_source_in_region, planting_density, notes) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (var["id"], var["crop_id"], var["name"], var.get("local_names"),
                 var["days_to_maturity"], var["yield_potential_kg_per_ha"],
                 var.get("disease_resistance"), var.get("drought_tolerance"),
                 var.get("seed_source_in_region"), var.get("planting_density"),
                 var.get("notes")),
            )

        # Fertilization schedule
        for fert in FERTILIZATION_SCHEDULE:
            cursor.execute(
                "INSERT INTO fertilization_schedule (id, crop_id, growth_stage, "
                "fertilizer_type, dose_per_ha, application_method, timing_notes, "
                "organic_alternative, cost_estimate_xof) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (fert["id"], fert["crop_id"], fert["growth_stage"],
                 fert["fertilizer_type"], fert["dose_per_ha"],
                 fert.get("application_method"), fert.get("timing_notes"),
                 fert.get("organic_alternative"), fert.get("cost_estimate_xof")),
            )

        # Planting calendar
        for cal in PLANTING_CALENDAR:
            cursor.execute(
                "INSERT INTO planting_calendar (id, crop_id, month, activity, "
                "details, is_critical) VALUES (?, ?, ?, ?, ?, ?)",
                (cal["id"], cal["crop_id"], cal["month"], cal["activity"],
                 cal.get("details"), cal.get("is_critical", 0)),
            )

        # Storage guidelines
        for stor in STORAGE_GUIDELINES:
            cursor.execute(
                "INSERT INTO storage_guidelines (id, crop_id, method, optimal_temp_c, "
                "moisture_target_pct, max_duration_months, pest_risks, "
                "quality_indicators, local_materials) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (stor["id"], stor["crop_id"], stor["method"],
                 stor.get("optimal_temp_c"), stor.get("moisture_target_pct"),
                 stor.get("max_duration_months"), stor.get("pest_risks"),
                 stor.get("quality_indicators"), stor.get("local_materials")),
            )

        # Soil requirements
        for soil in SOIL_REQUIREMENTS:
            cursor.execute(
                "INSERT INTO soil_requirements (id, crop_id, ph_min, ph_max, "
                "preferred_texture, drainage_needs, amendments_needed, preparation_notes) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (soil["id"], soil["crop_id"], soil["ph_min"], soil["ph_max"],
                 soil.get("preferred_texture"), soil.get("drainage_needs"),
                 soil.get("amendments_needed"), soil.get("preparation_notes")),
            )

        conn.commit()

        total_rows = (
            len(CROPS) + len(DISEASES) + len(CROP_DISEASES) + len(TREATMENTS)
            + len(CLIMATE) + len(PESTS) + len(VARIETIES)
            + len(FERTILIZATION_SCHEDULE) + len(PLANTING_CALENDAR)
            + len(STORAGE_GUIDELINES) + len(SOIL_REQUIREMENTS)
        )
        t.set(details={"rows_inserted": total_rows})


def _insert_chroma_chunks(client, chunks_by_collection: dict):
    """Insert all chunks into ChromaDB collections with embeddings."""
    for collection_name, chunks in chunks_by_collection.items():
        if not chunks:
            continue

        with log.timed(Step.PACK_BUILD, f"chroma_insert_{collection_name}") as t:
            collection = client.get_collection(collection_name)

            # Batch insert (ChromaDB handles embedding generation)
            ids = [c["id"] for c in chunks]
            documents = [c["content"] for c in chunks]
            metadatas = [c["metadata"] for c in chunks]

            collection.add(ids=ids, documents=documents, metadatas=metadatas)
            t.set(details={"collection": collection_name, "chunks": len(chunks)})
