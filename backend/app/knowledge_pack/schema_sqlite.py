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
    harvest_notes TEXT
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
    prevention_notes TEXT
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
    safety_notes TEXT
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
    notes TEXT
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
    synced BOOLEAN DEFAULT 0
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
"""

# ============================================================
# Valid tables for the structured query builder (allowlist)
# ============================================================

VALID_TABLES = [
    "crops",
    "diseases",
    "crop_diseases",
    "treatments",
    "climate",
    "image_refs",
    "field_observations",
]

FTS_TABLE_MAP = {
    "diseases": "diseases_fts",
    "treatments": "treatments_fts",
    "crops": "crops_fts",
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
