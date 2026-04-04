"""ChromaDB schema for Knowledge Packs.

Defines the 4 collections, parent/child document model,
embedding function setup, and collection initialization.

Distance metric: cosine (MiniLM was trained with cosine similarity).
Document model: parent/child pairs. Child chunks are search targets,
parent chunks contain full detail. Search hits children → fetch parents.
"""

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from pathlib import Path

from app.config import settings


# ============================================================
# Collection definitions
# ============================================================

CHROMA_COLLECTIONS = {
    "disease_knowledge": {
        "description": "Disease descriptions, symptoms, visual markers, progression",
        "metadata_fields": [
            "disease_id", "crop", "type", "severity",
            "topic_id", "chunk_type",  # "child" or "parent"
        ],
    },
    "treatment_guides": {
        "description": "Treatment protocols, materials, application steps",
        "metadata_fields": [
            "disease_id", "treatment_id", "is_organic", "difficulty",
            "topic_id", "chunk_type",
        ],
    },
    "farming_practices": {
        "description": "General agriculture advice, drought strategies, planting guides",
        "metadata_fields": [
            "topic", "crop", "season", "practice_type",
            "topic_id", "chunk_type",
        ],
    },
    "regional_context": {
        "description": "Region-specific climate, resources, infrastructure, contacts",
        "metadata_fields": [
            "region", "topic", "data_type",
            "topic_id", "chunk_type",
        ],
    },
}

# Document ID naming convention:
#   {entity_short}_{id}_{topic}_{child|parent}
# Examples:
#   cmd_001_symptoms_child
#   cmd_001_symptoms_parent
#   cmd_001_treatment_child
#   rice_blast_002_prevention_parent


# ============================================================
# Embedding function (swappable via config)
# ============================================================

_embedding_fn_cache = None


def get_embedding_function() -> SentenceTransformerEmbeddingFunction:
    """Return the embedding function, lazily loaded and cached.

    Uses the model specified in config (default: all-MiniLM-L6-v2).
    The function is cached at module level so the model loads only once.
    """
    global _embedding_fn_cache
    if _embedding_fn_cache is None:
        from app.logger import Step, pipeline_logger as log

        with log.timed(Step.SYSTEM, "load_embedding_model") as t:
            _embedding_fn_cache = SentenceTransformerEmbeddingFunction(
                model_name=settings.embedding_model,
            )
            t.set(details={"model": settings.embedding_model})
    return _embedding_fn_cache


def reset_embedding_cache():
    """Clear the cached embedding function. Useful for testing."""
    global _embedding_fn_cache
    _embedding_fn_cache = None


# ============================================================
# ChromaDB initialization
# ============================================================

def init_chroma_db(
    chroma_path: Path,
    embedding_function: SentenceTransformerEmbeddingFunction | None = None,
) -> chromadb.ClientAPI:
    """Create a persistent ChromaDB client and initialize all 4 collections.

    Each collection uses cosine distance (natural metric for MiniLM embeddings).
    If no embedding_function is provided, uses the default from config.
    """
    from app.logger import Step, pipeline_logger as log

    with log.timed(Step.PACK_BUILD, "init_chroma") as t:
        client = chromadb.PersistentClient(path=str(chroma_path))
        ef = embedding_function or get_embedding_function()

        for collection_name in CHROMA_COLLECTIONS:
            client.get_or_create_collection(
                name=collection_name,
                embedding_function=ef,
                metadata={"hnsw:space": "cosine"},
            )

        t.set(details={
            "chroma_path": str(chroma_path),
            "collections": list(CHROMA_COLLECTIONS.keys()),
            "distance_metric": "cosine",
        })

    return client


def verify_chroma_collections(client: chromadb.ClientAPI) -> dict:
    """Return {collection_name: document_count} for all collections."""
    result = {}
    for collection_name in CHROMA_COLLECTIONS:
        try:
            collection = client.get_collection(collection_name)
            result[collection_name] = collection.count()
        except Exception:
            result[collection_name] = -1  # Collection missing or broken
    return result
