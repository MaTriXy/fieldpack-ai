"""Tests for Step 2.2: ChromaDB collection setup with parent/child model."""

from pathlib import Path

import pytest

from app.knowledge_pack.schema_chroma import (
    CHROMA_COLLECTIONS,
    init_chroma_db,
    reset_embedding_cache,
    verify_chroma_collections,
)


@pytest.fixture(autouse=True)
def clean_embedding_cache():
    """Reset the embedding function cache between tests."""
    reset_embedding_cache()
    yield
    reset_embedding_cache()


@pytest.fixture
def chroma_client(tmp_path):
    """Create a fresh ChromaDB client with all collections."""
    chroma_path = tmp_path / "chroma_db"
    client = init_chroma_db(chroma_path)
    return client


# --- Collection creation ---

def test_four_collections_created(chroma_client):
    collections = chroma_client.list_collections()
    names = {c.name for c in collections}
    assert names == {"disease_knowledge", "treatment_guides", "farming_practices", "regional_context"}


def test_collections_use_cosine(chroma_client):
    for name in CHROMA_COLLECTIONS:
        collection = chroma_client.get_collection(name)
        assert collection.metadata.get("hnsw:space") == "cosine"


def test_collections_empty_initially(chroma_client):
    counts = verify_chroma_collections(chroma_client)
    for name, count in counts.items():
        assert count == 0


# --- Parent/child document model ---

def test_insert_parent_child_pair(chroma_client):
    collection = chroma_client.get_collection("disease_knowledge")

    # Insert child chunk (search target)
    collection.add(
        ids=["cmd_001_symptoms_child"],
        documents=["cassava brown spots curling leaves yellowing mosaic pattern leaf distortion"],
        metadatas=[{
            "disease_id": "1",
            "crop": "cassava",
            "type": "viral",
            "severity": "high",
            "topic_id": "cmd_001_symptoms",
            "chunk_type": "child",
        }],
    )

    # Insert parent chunk (full detail)
    collection.add(
        ids=["cmd_001_symptoms_parent"],
        documents=["Cassava Mosaic Disease (CMD) is caused by African cassava mosaic virus. "
                    "Early symptoms include yellow-green mosaic patterns on young leaves, "
                    "leaf curling, and reduced leaf size. Advanced cases show stunted growth "
                    "and small deformed tubers. Severity: high — 50-70% yield loss possible."],
        metadatas=[{
            "disease_id": "1",
            "crop": "cassava",
            "type": "viral",
            "severity": "high",
            "topic_id": "cmd_001_symptoms",
            "chunk_type": "parent",
        }],
    )

    assert collection.count() == 2


def test_search_child_returns_match(chroma_client):
    collection = chroma_client.get_collection("disease_knowledge")

    collection.add(
        ids=["cmd_001_symptoms_child"],
        documents=["cassava brown spots curling leaves yellowing mosaic pattern"],
        metadatas=[{
            "topic_id": "cmd_001_symptoms",
            "chunk_type": "child",
            "crop": "cassava",
        }],
    )

    results = collection.query(
        query_texts=["my cassava has yellow spots and curling leaves"],
        n_results=1,
        where={"chunk_type": "child"},
    )

    assert len(results["ids"][0]) == 1
    assert results["ids"][0][0] == "cmd_001_symptoms_child"


def test_fetch_parent_by_topic_id(chroma_client):
    """After finding a child, look up the parent by topic_id."""
    collection = chroma_client.get_collection("disease_knowledge")

    collection.add(
        ids=["cmd_001_symptoms_child", "cmd_001_symptoms_parent"],
        documents=[
            "cassava brown spots curling",
            "Full detailed description of Cassava Mosaic Disease...",
        ],
        metadatas=[
            {"topic_id": "cmd_001_symptoms", "chunk_type": "child", "crop": "cassava"},
            {"topic_id": "cmd_001_symptoms", "chunk_type": "parent", "crop": "cassava"},
        ],
    )

    # Search children
    child_results = collection.query(
        query_texts=["cassava yellow mosaic"],
        n_results=1,
        where={"chunk_type": "child"},
    )
    topic_id = child_results["metadatas"][0][0]["topic_id"]

    # Fetch parent by topic_id
    parent_results = collection.get(
        where={"$and": [
            {"topic_id": topic_id},
            {"chunk_type": "parent"},
        ]},
    )

    assert len(parent_results["ids"]) == 1
    assert "Full detailed description" in parent_results["documents"][0]


def test_metadata_filter_by_crop(chroma_client):
    collection = chroma_client.get_collection("disease_knowledge")

    collection.add(
        ids=["cassava_child", "rice_child"],
        documents=["cassava disease symptoms", "rice disease symptoms"],
        metadatas=[
            {"chunk_type": "child", "crop": "cassava", "topic_id": "c1"},
            {"chunk_type": "child", "crop": "rice", "topic_id": "r1"},
        ],
    )

    results = collection.query(
        query_texts=["disease symptoms"],
        n_results=5,
        where={"$and": [{"chunk_type": "child"}, {"crop": "cassava"}]},
    )

    assert len(results["ids"][0]) == 1
    assert results["ids"][0][0] == "cassava_child"


# --- Multiple collections ---

def test_different_collections_independent(chroma_client):
    disease_col = chroma_client.get_collection("disease_knowledge")
    treatment_col = chroma_client.get_collection("treatment_guides")

    disease_col.add(
        ids=["d1"], documents=["disease doc"],
        metadatas=[{"chunk_type": "child", "topic_id": "t1"}],
    )
    treatment_col.add(
        ids=["t1"], documents=["treatment doc"],
        metadatas=[{"chunk_type": "child", "topic_id": "t2"}],
    )

    assert disease_col.count() == 1
    assert treatment_col.count() == 1


# --- Idempotent initialization ---

def test_init_idempotent(tmp_path):
    """Calling init_chroma_db twice should not duplicate collections."""
    chroma_path = tmp_path / "chroma_db"
    client1 = init_chroma_db(chroma_path)
    client1.get_collection("disease_knowledge").add(
        ids=["test1"], documents=["test"],
        metadatas=[{"chunk_type": "child", "topic_id": "t1"}],
    )

    client2 = init_chroma_db(chroma_path)
    collections = client2.list_collections()
    assert len(collections) == 4
    assert client2.get_collection("disease_knowledge").count() == 1


# --- Persistence ---

def test_persistent_storage(tmp_path):
    """Data persists after client is closed and reopened."""
    chroma_path = tmp_path / "chroma_db"
    client = init_chroma_db(chroma_path)
    client.get_collection("disease_knowledge").add(
        ids=["persist_test"], documents=["persisted data"],
        metadatas=[{"chunk_type": "child", "topic_id": "t1"}],
    )
    del client

    # Reopen
    client2 = init_chroma_db(chroma_path)
    count = client2.get_collection("disease_knowledge").count()
    assert count == 1


# --- verify_chroma_collections ---

def test_verify_counts(chroma_client):
    chroma_client.get_collection("disease_knowledge").add(
        ids=["a", "b"], documents=["doc1", "doc2"],
        metadatas=[
            {"chunk_type": "child", "topic_id": "t1"},
            {"chunk_type": "parent", "topic_id": "t1"},
        ],
    )
    counts = verify_chroma_collections(chroma_client)
    assert counts["disease_knowledge"] == 2
    assert counts["treatment_guides"] == 0


# --- CHROMA_COLLECTIONS constant ---

def test_collection_definitions():
    assert len(CHROMA_COLLECTIONS) == 4
    for name, config in CHROMA_COLLECTIONS.items():
        assert "chunk_type" in config["metadata_fields"]
        assert "topic_id" in config["metadata_fields"]
