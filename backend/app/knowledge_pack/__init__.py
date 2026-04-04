"""Knowledge Pack schema, builder, and loader.

The three schema modules define the data layer:
  schema_sqlite   — SQLite tables, FTS5, triggers, indexes
  schema_chroma   — ChromaDB collections, embeddings, parent/child model
  schema_manifest — manifest.json validation and creation
"""

from app.knowledge_pack.schema_sqlite import (
    init_sqlite_db,
    verify_sqlite_schema,
    VALID_TABLES,
    FTS_TABLE_MAP,
    TABLE_JOINS,
)
from app.knowledge_pack.schema_chroma import (
    init_chroma_db,
    verify_chroma_collections,
    get_embedding_function,
    CHROMA_COLLECTIONS,
)
from app.knowledge_pack.schema_manifest import (
    ManifestSchema,
    RegionInfo,
    Statistics,
    ModelsUsed,
    validate_manifest,
    create_manifest,
)
