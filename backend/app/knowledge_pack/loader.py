"""Knowledge Pack loader.

Loads a built Knowledge Pack for offline use by the field assistant.
Provides access to SQLite, ChromaDB, and manifest via a single object.
Module-level singleton pattern for the active pack.
"""

import sqlite3
from pathlib import Path

import chromadb

from app.knowledge_pack.schema_chroma import (
    CHROMA_COLLECTIONS,
    get_embedding_function,
    verify_chroma_collections,
)
from app.knowledge_pack.schema_manifest import ManifestSchema, validate_manifest
from app.knowledge_pack.schema_sqlite import (
    FTS5_DDL,
    FTS5_TRIGGERS_DDL,
    verify_sqlite_schema,
)
from app.logger import Step, pipeline_logger as log


def _ensure_fts_tables(db_path: Path) -> None:
    """Create any missing FTS5 virtual tables and backfill them.

    Opens the DB read-write briefly. All DDL uses IF NOT EXISTS so this
    is idempotent and safe to run on every pack load.
    """
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(FTS5_DDL)
        conn.executescript(FTS5_TRIGGERS_DDL)
        # Backfill any FTS table that's empty but whose source table has data.
        # FTS5 'rebuild' command re-reads all rows from the content table.
        for fts_table in [
            "diseases_fts", "treatments_fts", "crops_fts", "pests_fts",
            "varieties_fts", "fertilization_schedule_fts",
            "storage_guidelines_fts", "planting_calendar_fts",
        ]:
            try:
                count = conn.execute(f"SELECT COUNT(*) FROM {fts_table}").fetchone()[0]
                if count == 0:
                    conn.execute(f"INSERT INTO {fts_table}({fts_table}) VALUES('rebuild')")
            except Exception:
                pass
        conn.commit()
    finally:
        conn.close()


class KnowledgePack:
    """A loaded Knowledge Pack, ready for queries.

    Lazy-loads all resources on first access. Use as context manager
    or call close() when done.
    """

    def __init__(self, pack_path: Path):
        self._pack_path = Path(pack_path)
        if not self._pack_path.exists():
            raise FileNotFoundError(f"Pack not found: {self._pack_path}")
        if not (self._pack_path / "manifest.json").exists():
            raise FileNotFoundError(f"No manifest.json in {self._pack_path}")

        self._manifest: ManifestSchema | None = None
        self._sqlite_conn: sqlite3.Connection | None = None
        self._chroma_client: chromadb.ClientAPI | None = None
        self._embedding_fn = None

    @property
    def path(self) -> Path:
        return self._pack_path

    @property
    def manifest(self) -> ManifestSchema:
        if self._manifest is None:
            self._manifest = validate_manifest(self._pack_path / "manifest.json")
        return self._manifest

    @property
    def sqlite_conn(self) -> sqlite3.Connection:
        if self._sqlite_conn is None:
            db_path = self._pack_path / "knowledge.db"
            if not db_path.exists():
                raise FileNotFoundError(f"No knowledge.db in {self._pack_path}")
            # Ensure FTS tables exist (migration for packs built before new FTS tables)
            _ensure_fts_tables(db_path)
            self._sqlite_conn = sqlite3.connect(
                f"file:{db_path}?mode=ro", uri=True, check_same_thread=False,
            )
            self._sqlite_conn.row_factory = sqlite3.Row
            self._sqlite_conn.execute("PRAGMA foreign_keys=ON")
        return self._sqlite_conn

    @property
    def chroma_client(self) -> chromadb.ClientAPI:
        if self._chroma_client is None:
            chroma_path = self._pack_path / "chroma_db"
            if not chroma_path.exists():
                raise FileNotFoundError(f"No chroma_db in {self._pack_path}")
            self._embedding_fn = get_embedding_function()
            self._chroma_client = chromadb.PersistentClient(path=str(chroma_path))
        return self._chroma_client

    def get_collection(self, name: str) -> chromadb.Collection:
        """Get a ChromaDB collection by name."""
        if name not in CHROMA_COLLECTIONS:
            raise ValueError(f"Unknown collection: {name}. Valid: {list(CHROMA_COLLECTIONS.keys())}")
        return self.chroma_client.get_collection(
            name=name,
            embedding_function=self._embedding_fn,
        )

    def health_check(self) -> dict:
        """Return pack status with row counts and collection doc counts."""
        result = {
            "pack_name": self.manifest.name,
            "pack_path": str(self._pack_path),
            "region": self.manifest.region.name,
            "crops": self.manifest.crops,
        }

        # SQLite row counts
        try:
            sqlite_info = verify_sqlite_schema(self.sqlite_conn)
            row_counts = {}
            for table in ["crops", "diseases", "treatments", "climate"]:
                if table in sqlite_info:
                    count = self.sqlite_conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    row_counts[table] = count
            result["sqlite_tables"] = row_counts
        except Exception as e:
            result["sqlite_error"] = str(e)

        # ChromaDB doc counts
        try:
            result["chroma_collections"] = verify_chroma_collections(self.chroma_client)
        except Exception as e:
            result["chroma_error"] = str(e)

        return result

    def close(self):
        """Close all connections."""
        if self._sqlite_conn:
            self._sqlite_conn.close()
            self._sqlite_conn = None
        if self._chroma_client is not None:
            # ChromaDB caches a System per (tenant, database, persist_directory)
            # in SharedSystemClient. Without clearing, repeated load/unload of
            # packs at different paths (tests, pack hot-reload) leaves stale
            # System references that keep Rust-side file handles open on the
            # old HNSW files, causing "Nothing found on disk" errors when the
            # next pack's query tries to read its own fresh HNSW index.
            from chromadb.api.shared_system_client import SharedSystemClient
            try:
                SharedSystemClient.clear_system_cache()
            except Exception:
                pass
            self._chroma_client = None
            # Force Python GC so any lingering client refs are released, then
            # give the Rust runtime a moment to drop file handles on Windows
            # (where mmap'd HNSW files stay locked longer than on POSIX).
            import gc
            gc.collect()
        self._embedding_fn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


# ============================================================
# Module-level singleton for the active pack
# ============================================================

_active_pack: KnowledgePack | None = None


def load_pack(pack_path: Path) -> KnowledgePack:
    """Load a Knowledge Pack and set it as the active pack."""
    global _active_pack

    with log.timed(Step.PACK_LOAD, "load_pack") as t:
        if _active_pack is not None:
            _active_pack.close()

        _active_pack = KnowledgePack(pack_path)
        health = _active_pack.health_check()
        t.set(details={
            "pack_name": health.get("pack_name"),
            "sqlite_tables": health.get("sqlite_tables"),
            "chroma_collections": health.get("chroma_collections"),
        })

    return _active_pack


def get_active_pack() -> KnowledgePack | None:
    """Get the currently loaded Knowledge Pack, or None."""
    return _active_pack


def unload_pack():
    """Unload the active Knowledge Pack."""
    global _active_pack
    if _active_pack:
        _active_pack.close()
        _active_pack = None
        log.log_step(Step.PACK_LOAD, "pack_unloaded")
