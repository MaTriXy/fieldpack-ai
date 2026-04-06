"""SQLite schema for Knowledge Packs.

Defines all tables, FTS5 virtual tables, triggers, and indexes.
The schema is designed for the field assistant's three query patterns:
  1. Structured queries (exact lookups, JOINs)
  2. FTS5 keyword search (BM25 ranking, prefix matching)
  3. JSON field queries (json_each for materials, common names)
"""

import sqlite3
from pathlib import Path


# ============================================================
# Core tables
# ============================================================

SQLITE_SCHEMA_DDL = """
-- Crops
CREATE TABLE IF NOT EXISTS crops (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    scientific_name TEXT,
    family TEXT,
    growing_season TEXT,
    water_needs_mm_per_week REAL,
    drought_tolerance TEXT CHECK(drought_tolerance IN ('low', 'medium', 'high')),
    region_suitability TEXT,
    planting_notes TEXT,
    harvest_notes TEXT,
    soil_ph_min REAL,
    soil_ph_max REAL,
    seed_rate_kg_per_ha REAL,
    intercrop_companions TEXT
);

-- Diseases
CREATE TABLE IF NOT EXISTS diseases (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    common_names TEXT,
    type TEXT CHECK(type IN ('viral', 'bacterial', 'fungal', 'pest', 'nutritional', 'environmental')),
    symptoms_text TEXT NOT NULL,
    visual_markers TEXT NOT NULL,
    severity_scale TEXT CHECK(severity_scale IN ('low', 'medium', 'high', 'critical')),
    spread_mechanism TEXT,
    prevention_notes TEXT,
    affected_growth_stage TEXT,
    season_risk_peak TEXT
);

-- Crop-Disease relationship (many-to-many)
CREATE TABLE IF NOT EXISTS crop_diseases (
    crop_id INTEGER REFERENCES crops(id),
    disease_id INTEGER REFERENCES diseases(id),
    susceptibility TEXT CHECK(susceptibility IN ('low', 'medium', 'high')),
    PRIMARY KEY (crop_id, disease_id)
);

-- Treatments
CREATE TABLE IF NOT EXISTS treatments (
    id INTEGER PRIMARY KEY,
    disease_id INTEGER REFERENCES diseases(id),
    method TEXT NOT NULL,
    description TEXT NOT NULL,
    materials_needed TEXT,
    difficulty TEXT CHECK(difficulty IN ('easy', 'medium', 'hard')),
    is_organic BOOLEAN DEFAULT 1,
    local_availability TEXT,
    effectiveness TEXT CHECK(effectiveness IN ('low', 'medium', 'high')),
    application_timing TEXT,
    safety_notes TEXT,
    cost_estimate_xof INTEGER,
    treatment_type TEXT CHECK(treatment_type IN ('preventive', 'curative', 'cultural'))
);

-- Climate data
CREATE TABLE IF NOT EXISTS climate (
    id INTEGER PRIMARY KEY,
    region TEXT NOT NULL,
    month INTEGER,
    rainfall_mm REAL,
    temperature_avg_c REAL,
    humidity_pct REAL,
    drought_risk TEXT CHECK(drought_risk IN ('low', 'medium', 'high', 'severe')),
    notes TEXT,
    evapotranspiration_mm REAL,
    flooding_risk TEXT CHECK(flooding_risk IN ('none', 'low', 'moderate', 'high'))
);

-- Image references
CREATE TABLE IF NOT EXISTS image_refs (
    id INTEGER PRIMARY KEY,
    file_path TEXT NOT NULL,
    disease_id INTEGER REFERENCES diseases(id),
    crop_id INTEGER REFERENCES crops(id),
    type TEXT CHECK(type IN ('disease_symptom', 'healthy_reference', 'treatment_demo')),
    description TEXT,
    visual_features TEXT
);

-- Field observations (populated offline, synced later)
CREATE TABLE IF NOT EXISTS field_observations (
    id INTEGER PRIMARY KEY,
    timestamp TEXT NOT NULL,
    type TEXT,
    location TEXT,
    details TEXT,
    image_path TEXT,
    synced BOOLEAN DEFAULT 0,
    crop_id INTEGER REFERENCES crops(id),
    severity_observed TEXT CHECK(severity_observed IN ('mild', 'moderate', 'severe'))
);

-- Pests
CREATE TABLE IF NOT EXISTS pests (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    common_names TEXT,
    crop_id INTEGER REFERENCES crops(id),
    type TEXT CHECK(type IN ('insect', 'rodent', 'bird', 'nematode', 'mollusk')),
    damage_description TEXT,
    season_peak TEXT,
    identification_notes TEXT,
    control_organic TEXT,
    control_chemical TEXT,
    economic_threshold TEXT,
    prevention_notes TEXT
);

-- Crop varieties
CREATE TABLE IF NOT EXISTS varieties (
    id INTEGER PRIMARY KEY,
    crop_id INTEGER REFERENCES crops(id),
    name TEXT NOT NULL,
    local_names TEXT,
    days_to_maturity INTEGER,
    yield_potential_kg_per_ha REAL,
    disease_resistance TEXT,
    drought_tolerance TEXT CHECK(drought_tolerance IN ('low', 'medium', 'high')),
    seed_source_in_region TEXT,
    planting_density TEXT,
    notes TEXT
);

-- Fertilization schedule
CREATE TABLE IF NOT EXISTS fertilization_schedule (
    id INTEGER PRIMARY KEY,
    crop_id INTEGER REFERENCES crops(id),
    growth_stage TEXT NOT NULL,
    fertilizer_type TEXT NOT NULL,
    dose_per_ha TEXT,
    application_method TEXT,
    timing_notes TEXT,
    organic_alternative TEXT,
    cost_estimate_xof INTEGER
);

-- Planting calendar (month-by-activity)
CREATE TABLE IF NOT EXISTS planting_calendar (
    id INTEGER PRIMARY KEY,
    crop_id INTEGER REFERENCES crops(id),
    month INTEGER NOT NULL CHECK(month >= 1 AND month <= 12),
    activity TEXT NOT NULL,
    details TEXT,
    is_critical BOOLEAN DEFAULT 0
);

-- Storage guidelines (post-harvest)
CREATE TABLE IF NOT EXISTS storage_guidelines (
    id INTEGER PRIMARY KEY,
    crop_id INTEGER REFERENCES crops(id),
    method TEXT NOT NULL,
    optimal_temp_c TEXT,
    moisture_target_pct REAL,
    max_duration_months INTEGER,
    pest_risks TEXT,
    quality_indicators TEXT,
    local_materials TEXT
);

-- Soil requirements
CREATE TABLE IF NOT EXISTS soil_requirements (
    id INTEGER PRIMARY KEY,
    crop_id INTEGER REFERENCES crops(id),
    ph_min REAL,
    ph_max REAL,
    preferred_texture TEXT,
    drainage_needs TEXT,
    amendments_needed TEXT,
    preparation_notes TEXT
);
"""

# ============================================================
# Indexes for fast lookups and JOINs
# ============================================================

INDEXES_DDL = """
-- Foreign key indexes for JOIN performance
CREATE INDEX IF NOT EXISTS idx_treatments_disease_id ON treatments(disease_id);
CREATE INDEX IF NOT EXISTS idx_crop_diseases_crop_id ON crop_diseases(crop_id);
CREATE INDEX IF NOT EXISTS idx_crop_diseases_disease_id ON crop_diseases(disease_id);
CREATE INDEX IF NOT EXISTS idx_image_refs_disease_id ON image_refs(disease_id);
CREATE INDEX IF NOT EXISTS idx_image_refs_crop_id ON image_refs(crop_id);

-- Name indexes for fast exact and LIKE lookups
CREATE INDEX IF NOT EXISTS idx_crops_name ON crops(name);
CREATE INDEX IF NOT EXISTS idx_diseases_name ON diseases(name);

-- Climate lookups by region and month
CREATE INDEX IF NOT EXISTS idx_climate_region_month ON climate(region, month);

-- Field observations by sync status
CREATE INDEX IF NOT EXISTS idx_observations_synced ON field_observations(synced);
CREATE INDEX IF NOT EXISTS idx_observations_crop_id ON field_observations(crop_id);

-- New table indexes
CREATE INDEX IF NOT EXISTS idx_pests_crop_id ON pests(crop_id);
CREATE INDEX IF NOT EXISTS idx_varieties_crop_id ON varieties(crop_id);
CREATE INDEX IF NOT EXISTS idx_fertilization_crop_id ON fertilization_schedule(crop_id);
CREATE INDEX IF NOT EXISTS idx_planting_calendar_crop_id ON planting_calendar(crop_id);
CREATE INDEX IF NOT EXISTS idx_planting_calendar_month ON planting_calendar(month);
CREATE INDEX IF NOT EXISTS idx_storage_crop_id ON storage_guidelines(crop_id);
CREATE INDEX IF NOT EXISTS idx_soil_crop_id ON soil_requirements(crop_id);
"""

# ============================================================
# FTS5 virtual tables (keyword search with BM25 ranking)
# ============================================================

FTS5_DDL = """
-- Diseases full-text search
CREATE VIRTUAL TABLE IF NOT EXISTS diseases_fts USING fts5(
    name,
    common_names,
    symptoms_text,
    visual_markers,
    prevention_notes,
    content='diseases',
    content_rowid='id',
    tokenize='unicode61',
    prefix='2,3'
);

-- Treatments full-text search
CREATE VIRTUAL TABLE IF NOT EXISTS treatments_fts USING fts5(
    method,
    description,
    materials_needed,
    local_availability,
    safety_notes,
    content='treatments',
    content_rowid='id',
    tokenize='unicode61',
    prefix='2,3'
);

-- Crops full-text search
CREATE VIRTUAL TABLE IF NOT EXISTS crops_fts USING fts5(
    name,
    scientific_name,
    region_suitability,
    planting_notes,
    harvest_notes,
    content='crops',
    content_rowid='id',
    tokenize='unicode61',
    prefix='2,3'
);

-- Pests full-text search
CREATE VIRTUAL TABLE IF NOT EXISTS pests_fts USING fts5(
    name,
    common_names,
    damage_description,
    identification_notes,
    control_organic,
    prevention_notes,
    content='pests',
    content_rowid='id',
    tokenize='unicode61',
    prefix='2,3'
);

-- Varieties full-text search
CREATE VIRTUAL TABLE IF NOT EXISTS varieties_fts USING fts5(
    name,
    local_names,
    disease_resistance,
    seed_source_in_region,
    notes,
    content='varieties',
    content_rowid='id',
    tokenize='unicode61',
    prefix='2,3'
);

-- Fertilization schedule full-text search
CREATE VIRTUAL TABLE IF NOT EXISTS fertilization_schedule_fts USING fts5(
    growth_stage,
    fertilizer_type,
    organic_alternative,
    timing_notes,
    content='fertilization_schedule',
    content_rowid='id',
    tokenize='unicode61',
    prefix='2,3'
);

-- Storage guidelines full-text search
CREATE VIRTUAL TABLE IF NOT EXISTS storage_guidelines_fts USING fts5(
    method,
    pest_risks,
    quality_indicators,
    local_materials,
    content='storage_guidelines',
    content_rowid='id',
    tokenize='unicode61',
    prefix='2,3'
);
"""

# ============================================================
# FTS5 sync triggers (keep FTS tables in sync with base tables)
# ============================================================

FTS5_TRIGGERS_DDL = """
-- Diseases triggers
CREATE TRIGGER IF NOT EXISTS diseases_ai AFTER INSERT ON diseases BEGIN
    INSERT INTO diseases_fts(rowid, name, common_names, symptoms_text, visual_markers, prevention_notes)
    VALUES (new.id, new.name, new.common_names, new.symptoms_text, new.visual_markers, new.prevention_notes);
END;

CREATE TRIGGER IF NOT EXISTS diseases_ad AFTER DELETE ON diseases BEGIN
    INSERT INTO diseases_fts(diseases_fts, rowid, name, common_names, symptoms_text, visual_markers, prevention_notes)
    VALUES ('delete', old.id, old.name, old.common_names, old.symptoms_text, old.visual_markers, old.prevention_notes);
END;

CREATE TRIGGER IF NOT EXISTS diseases_au AFTER UPDATE ON diseases BEGIN
    INSERT INTO diseases_fts(diseases_fts, rowid, name, common_names, symptoms_text, visual_markers, prevention_notes)
    VALUES ('delete', old.id, old.name, old.common_names, old.symptoms_text, old.visual_markers, old.prevention_notes);
    INSERT INTO diseases_fts(rowid, name, common_names, symptoms_text, visual_markers, prevention_notes)
    VALUES (new.id, new.name, new.common_names, new.symptoms_text, new.visual_markers, new.prevention_notes);
END;

-- Treatments triggers
CREATE TRIGGER IF NOT EXISTS treatments_ai AFTER INSERT ON treatments BEGIN
    INSERT INTO treatments_fts(rowid, method, description, materials_needed, local_availability, safety_notes)
    VALUES (new.id, new.method, new.description, new.materials_needed, new.local_availability, new.safety_notes);
END;

CREATE TRIGGER IF NOT EXISTS treatments_ad AFTER DELETE ON treatments BEGIN
    INSERT INTO treatments_fts(treatments_fts, rowid, method, description, materials_needed, local_availability, safety_notes)
    VALUES ('delete', old.id, old.method, old.description, old.materials_needed, old.local_availability, old.safety_notes);
END;

CREATE TRIGGER IF NOT EXISTS treatments_au AFTER UPDATE ON treatments BEGIN
    INSERT INTO treatments_fts(treatments_fts, rowid, method, description, materials_needed, local_availability, safety_notes)
    VALUES ('delete', old.id, old.method, old.description, old.materials_needed, old.local_availability, old.safety_notes);
    INSERT INTO treatments_fts(rowid, method, description, materials_needed, local_availability, safety_notes)
    VALUES (new.id, new.method, new.description, new.materials_needed, new.local_availability, new.safety_notes);
END;

-- Crops triggers
CREATE TRIGGER IF NOT EXISTS crops_ai AFTER INSERT ON crops BEGIN
    INSERT INTO crops_fts(rowid, name, scientific_name, region_suitability, planting_notes, harvest_notes)
    VALUES (new.id, new.name, new.scientific_name, new.region_suitability, new.planting_notes, new.harvest_notes);
END;

CREATE TRIGGER IF NOT EXISTS crops_ad AFTER DELETE ON crops BEGIN
    INSERT INTO crops_fts(crops_fts, rowid, name, scientific_name, region_suitability, planting_notes, harvest_notes)
    VALUES ('delete', old.id, old.name, old.scientific_name, old.region_suitability, old.planting_notes, old.harvest_notes);
END;

CREATE TRIGGER IF NOT EXISTS crops_au AFTER UPDATE ON crops BEGIN
    INSERT INTO crops_fts(crops_fts, rowid, name, scientific_name, region_suitability, planting_notes, harvest_notes)
    VALUES ('delete', old.id, old.name, old.scientific_name, old.region_suitability, old.planting_notes, old.harvest_notes);
    INSERT INTO crops_fts(rowid, name, scientific_name, region_suitability, planting_notes, harvest_notes)
    VALUES (new.id, new.name, new.scientific_name, new.region_suitability, new.planting_notes, new.harvest_notes);
END;

-- Pests triggers
CREATE TRIGGER IF NOT EXISTS pests_ai AFTER INSERT ON pests BEGIN
    INSERT INTO pests_fts(rowid, name, common_names, damage_description, identification_notes, control_organic, prevention_notes)
    VALUES (new.id, new.name, new.common_names, new.damage_description, new.identification_notes, new.control_organic, new.prevention_notes);
END;

CREATE TRIGGER IF NOT EXISTS pests_ad AFTER DELETE ON pests BEGIN
    INSERT INTO pests_fts(pests_fts, rowid, name, common_names, damage_description, identification_notes, control_organic, prevention_notes)
    VALUES ('delete', old.id, old.name, old.common_names, old.damage_description, old.identification_notes, old.control_organic, old.prevention_notes);
END;

CREATE TRIGGER IF NOT EXISTS pests_au AFTER UPDATE ON pests BEGIN
    INSERT INTO pests_fts(pests_fts, rowid, name, common_names, damage_description, identification_notes, control_organic, prevention_notes)
    VALUES ('delete', old.id, old.name, old.common_names, old.damage_description, old.identification_notes, old.control_organic, old.prevention_notes);
    INSERT INTO pests_fts(rowid, name, common_names, damage_description, identification_notes, control_organic, prevention_notes)
    VALUES (new.id, new.name, new.common_names, new.damage_description, new.identification_notes, new.control_organic, new.prevention_notes);
END;

-- Varieties triggers
CREATE TRIGGER IF NOT EXISTS varieties_ai AFTER INSERT ON varieties BEGIN
    INSERT INTO varieties_fts(rowid, name, local_names, disease_resistance, seed_source_in_region, notes)
    VALUES (new.id, new.name, new.local_names, new.disease_resistance, new.seed_source_in_region, new.notes);
END;

CREATE TRIGGER IF NOT EXISTS varieties_ad AFTER DELETE ON varieties BEGIN
    INSERT INTO varieties_fts(varieties_fts, rowid, name, local_names, disease_resistance, seed_source_in_region, notes)
    VALUES ('delete', old.id, old.name, old.local_names, old.disease_resistance, old.seed_source_in_region, old.notes);
END;

CREATE TRIGGER IF NOT EXISTS varieties_au AFTER UPDATE ON varieties BEGIN
    INSERT INTO varieties_fts(varieties_fts, rowid, name, local_names, disease_resistance, seed_source_in_region, notes)
    VALUES ('delete', old.id, old.name, old.local_names, old.disease_resistance, old.seed_source_in_region, old.notes);
    INSERT INTO varieties_fts(rowid, name, local_names, disease_resistance, seed_source_in_region, notes)
    VALUES (new.id, new.name, new.local_names, new.disease_resistance, new.seed_source_in_region, new.notes);
END;

-- Fertilization schedule triggers
CREATE TRIGGER IF NOT EXISTS fertilization_schedule_ai AFTER INSERT ON fertilization_schedule BEGIN
    INSERT INTO fertilization_schedule_fts(rowid, growth_stage, fertilizer_type, organic_alternative, timing_notes)
    VALUES (new.id, new.growth_stage, new.fertilizer_type, new.organic_alternative, new.timing_notes);
END;

CREATE TRIGGER IF NOT EXISTS fertilization_schedule_ad AFTER DELETE ON fertilization_schedule BEGIN
    INSERT INTO fertilization_schedule_fts(fertilization_schedule_fts, rowid, growth_stage, fertilizer_type, organic_alternative, timing_notes)
    VALUES ('delete', old.id, old.growth_stage, old.fertilizer_type, old.organic_alternative, old.timing_notes);
END;

CREATE TRIGGER IF NOT EXISTS fertilization_schedule_au AFTER UPDATE ON fertilization_schedule BEGIN
    INSERT INTO fertilization_schedule_fts(fertilization_schedule_fts, rowid, growth_stage, fertilizer_type, organic_alternative, timing_notes)
    VALUES ('delete', old.id, old.growth_stage, old.fertilizer_type, old.organic_alternative, old.timing_notes);
    INSERT INTO fertilization_schedule_fts(rowid, growth_stage, fertilizer_type, organic_alternative, timing_notes)
    VALUES (new.id, new.growth_stage, new.fertilizer_type, new.organic_alternative, new.timing_notes);
END;

-- Storage guidelines triggers
CREATE TRIGGER IF NOT EXISTS storage_guidelines_ai AFTER INSERT ON storage_guidelines BEGIN
    INSERT INTO storage_guidelines_fts(rowid, method, pest_risks, quality_indicators, local_materials)
    VALUES (new.id, new.method, new.pest_risks, new.quality_indicators, new.local_materials);
END;

CREATE TRIGGER IF NOT EXISTS storage_guidelines_ad AFTER DELETE ON storage_guidelines BEGIN
    INSERT INTO storage_guidelines_fts(storage_guidelines_fts, rowid, method, pest_risks, quality_indicators, local_materials)
    VALUES ('delete', old.id, old.method, old.pest_risks, old.quality_indicators, old.local_materials);
END;

CREATE TRIGGER IF NOT EXISTS storage_guidelines_au AFTER UPDATE ON storage_guidelines BEGIN
    INSERT INTO storage_guidelines_fts(storage_guidelines_fts, rowid, method, pest_risks, quality_indicators, local_materials)
    VALUES ('delete', old.id, old.method, old.pest_risks, old.quality_indicators, old.local_materials);
    INSERT INTO storage_guidelines_fts(rowid, method, pest_risks, quality_indicators, local_materials)
    VALUES (new.id, new.method, new.pest_risks, new.quality_indicators, new.local_materials);
END;
"""

# ============================================================
# Valid tables for the structured query builder (allowlist)
# ============================================================

# ============================================================
# Conversation tables (runtime, not part of core knowledge schema)
# ============================================================

CONVERSATIONS_DDL = """
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL CHECK(type IN ('field', 'mission')),
    title TEXT NOT NULL DEFAULT 'New conversation',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    message_count INTEGER NOT NULL DEFAULT 0,
    summary TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS conversation_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL REFERENCES conversations(id),
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    image_path TEXT,
    metadata TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_conv_type_updated ON conversations(type, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_conv_messages_conv_id ON conversation_messages(conversation_id, created_at);
"""


def ensure_conversations_tables(db_path: Path) -> None:
    """Create conversation tables if they don't exist yet (idempotent)."""
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.executescript(CONVERSATIONS_DDL)
        conn.commit()
    finally:
        conn.close()


VALID_TABLES = [
    "crops",
    "diseases",
    "crop_diseases",
    "treatments",
    "climate",
    "image_refs",
    "field_observations",
    "pests",
    "varieties",
    "fertilization_schedule",
    "planting_calendar",
    "storage_guidelines",
    "soil_requirements",
]

FTS_TABLE_MAP = {
    "diseases": "diseases_fts",
    "treatments": "treatments_fts",
    "crops": "crops_fts",
    "pests": "pests_fts",
    "varieties": "varieties_fts",
    "fertilization_schedule": "fertilization_schedule_fts",
    "storage_guidelines": "storage_guidelines_fts",
}

TABLE_JOINS = {
    "treatments": {
        "diseases": {"on": "treatments.disease_id = diseases.id"},
    },
    "crop_diseases": {
        "crops": {"on": "crop_diseases.crop_id = crops.id"},
        "diseases": {"on": "crop_diseases.disease_id = diseases.id"},
    },
    "image_refs": {
        "diseases": {"on": "image_refs.disease_id = diseases.id"},
        "crops": {"on": "image_refs.crop_id = crops.id"},
    },
    "pests": {
        "crops": {"on": "pests.crop_id = crops.id"},
    },
    "varieties": {
        "crops": {"on": "varieties.crop_id = crops.id"},
    },
    "fertilization_schedule": {
        "crops": {"on": "fertilization_schedule.crop_id = crops.id"},
    },
    "planting_calendar": {
        "crops": {"on": "planting_calendar.crop_id = crops.id"},
    },
    "storage_guidelines": {
        "crops": {"on": "storage_guidelines.crop_id = crops.id"},
    },
    "soil_requirements": {
        "crops": {"on": "soil_requirements.crop_id = crops.id"},
    },
    "field_observations": {
        "crops": {"on": "field_observations.crop_id = crops.id"},
    },
}


# ============================================================
# Database initialization
# ============================================================

def init_sqlite_db(db_path: Path) -> sqlite3.Connection:
    """Create and initialize a Knowledge Pack SQLite database.

    Creates all tables, indexes, FTS5 virtual tables, and sync triggers.
    Enables WAL mode for better concurrent read performance.
    """
    from app.logger import Step, pipeline_logger as log

    with log.timed(Step.PACK_BUILD, "init_sqlite") as t:
        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")

        conn.executescript(SQLITE_SCHEMA_DDL)
        conn.executescript(INDEXES_DDL)
        conn.executescript(FTS5_DDL)
        conn.executescript(FTS5_TRIGGERS_DDL)

        conn.commit()

        schema = verify_sqlite_schema(conn)
        t.set(details={
            "db_path": str(db_path),
            "tables": len([k for k in schema if not k.endswith("_fts")]),
            "fts_tables": len([k for k in schema if k.endswith("_fts")]),
        })

    return conn


def verify_sqlite_schema(conn: sqlite3.Connection) -> dict:
    """Introspect the database and return {table_name: column_count}.

    Includes both regular tables and FTS5 virtual tables.
    """
    result = {}

    # Regular tables
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    for (table_name,) in cursor.fetchall():
        col_cursor = conn.execute(f"PRAGMA table_info({table_name})")
        result[table_name] = len(col_cursor.fetchall())

    # FTS5 tables (show up as type='table' but PRAGMA table_info doesn't work)
    # Detect them by checking for _fts suffix
    for base_table, fts_table in FTS_TABLE_MAP.items():
        try:
            conn.execute(f"SELECT * FROM {fts_table} LIMIT 0")
            result[fts_table] = result.get(fts_table, 0) or -1  # -1 signals FTS5
        except sqlite3.OperationalError:
            pass

    return result
