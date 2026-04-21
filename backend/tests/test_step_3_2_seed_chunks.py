"""Tests for Step 3.2: ChromaDB seed chunks (parent/child pairs)."""

import pytest

from app.knowledge_pack.seed_chunks import get_all_chunks
from app.knowledge_pack.schema_chroma import CHROMA_COLLECTIONS


@pytest.fixture(scope="module")
def all_chunks():
    """Load chunks once for all tests (they're deterministic)."""
    return get_all_chunks()


class TestChunkStructure:

    def test_four_collection_keys(self, all_chunks):
        assert set(all_chunks.keys()) == set(CHROMA_COLLECTIONS.keys())

    def test_each_collection_non_empty(self, all_chunks):
        for name, chunks in all_chunks.items():
            assert len(chunks) > 0, f"Collection {name} is empty"

    def test_every_chunk_has_required_keys(self, all_chunks):
        for name, chunks in all_chunks.items():
            for chunk in chunks:
                assert "id" in chunk, f"Missing 'id' in {name} chunk"
                assert "content" in chunk, f"Missing 'content' in {name} chunk"
                assert "metadata" in chunk, f"Missing 'metadata' in {name} chunk"

    def test_no_duplicate_ids_within_collection(self, all_chunks):
        for name, chunks in all_chunks.items():
            ids = [c["id"] for c in chunks]
            assert len(ids) == len(set(ids)), f"Duplicate IDs in {name}"

    def test_no_duplicate_ids_across_collections(self, all_chunks):
        all_ids = []
        for chunks in all_chunks.values():
            all_ids.extend(c["id"] for c in chunks)
        assert len(all_ids) == len(set(all_ids)), "Duplicate IDs across collections"


class TestParentChildPairing:

    def test_every_child_has_matching_parent(self, all_chunks):
        for name, chunks in all_chunks.items():
            children = [c for c in chunks if c["metadata"]["chunk_type"] == "child"]
            parent_topic_ids = {
                c["metadata"]["topic_id"]
                for c in chunks
                if c["metadata"]["chunk_type"] == "parent"
            }
            for child in children:
                topic_id = child["metadata"]["topic_id"]
                assert topic_id in parent_topic_ids, (
                    f"Child '{child['id']}' in {name} has topic_id '{topic_id}' "
                    f"with no matching parent"
                )

    def test_every_parent_has_matching_child(self, all_chunks):
        for name, chunks in all_chunks.items():
            parents = [c for c in chunks if c["metadata"]["chunk_type"] == "parent"]
            child_topic_ids = {
                c["metadata"]["topic_id"]
                for c in chunks
                if c["metadata"]["chunk_type"] == "child"
            }
            for parent in parents:
                topic_id = parent["metadata"]["topic_id"]
                assert topic_id in child_topic_ids, (
                    f"Parent '{parent['id']}' in {name} has no matching child"
                )

    def test_chunk_type_is_child_or_parent(self, all_chunks):
        for name, chunks in all_chunks.items():
            for chunk in chunks:
                assert chunk["metadata"]["chunk_type"] in ("child", "parent"), (
                    f"Invalid chunk_type in {name}: {chunk['metadata']['chunk_type']}"
                )

    def test_balanced_pairs(self, all_chunks):
        """Each collection should have equal children and parents."""
        for name, chunks in all_chunks.items():
            children = sum(1 for c in chunks if c["metadata"]["chunk_type"] == "child")
            parents = sum(1 for c in chunks if c["metadata"]["chunk_type"] == "parent")
            assert children == parents, (
                f"{name}: {children} children vs {parents} parents"
            )


class TestChunkContent:

    def test_child_chunks_are_short(self, all_chunks):
        """Child chunks should be under 100 words for precise search."""
        for name, chunks in all_chunks.items():
            children = [c for c in chunks if c["metadata"]["chunk_type"] == "child"]
            for child in children:
                word_count = len(child["content"].split())
                assert word_count <= 100, (
                    f"Child '{child['id']}' in {name} has {word_count} words (max 100)"
                )

    def test_parent_chunks_are_detailed(self, all_chunks):
        """Parent chunks should be over 40 words for full context."""
        for name, chunks in all_chunks.items():
            parents = [c for c in chunks if c["metadata"]["chunk_type"] == "parent"]
            for parent in parents:
                word_count = len(parent["content"].split())
                assert word_count >= 40, (
                    f"Parent '{parent['id']}' in {name} has only {word_count} words (min 40)"
                )

    def test_no_empty_content(self, all_chunks):
        for name, chunks in all_chunks.items():
            for chunk in chunks:
                assert len(chunk["content"].strip()) > 0, (
                    f"Empty content in {name}: {chunk['id']}"
                )


class TestDiseaseChunks:

    def test_disease_knowledge_count(self, all_chunks):
        """15 diseases x 2 pairs (symptoms + prevention) x 2 (child + parent) = ~60."""
        dk = all_chunks["disease_knowledge"]
        assert len(dk) >= 50  # Some diseases may not have prevention

    def test_treatment_guides_count(self, all_chunks):
        """31 treatments x 2 (child + parent) = 62."""
        tg = all_chunks["treatment_guides"]
        assert len(tg) >= 60

    def test_disease_knowledge_has_crop_metadata(self, all_chunks):
        for chunk in all_chunks["disease_knowledge"]:
            assert "crop" in chunk["metadata"], f"Missing crop metadata in {chunk['id']}"
            assert chunk["metadata"]["crop"] != "unknown"

    def test_treatment_guides_has_disease_metadata(self, all_chunks):
        for chunk in all_chunks["treatment_guides"]:
            assert "disease_id" in chunk["metadata"], f"Missing disease_id in {chunk['id']}"


class TestFarmingPracticeChunks:

    def test_non_empty(self, all_chunks):
        assert len(all_chunks["farming_practices"]) >= 6  # At least 3 pairs

    def test_has_topic_metadata(self, all_chunks):
        for chunk in all_chunks["farming_practices"]:
            assert "topic" in chunk["metadata"]
            assert "practice_type" in chunk["metadata"]


class TestRegionalContextChunks:

    def test_non_empty(self, all_chunks):
        assert len(all_chunks["regional_context"]) >= 4  # At least 2 pairs

    def test_has_region_metadata(self, all_chunks):
        for chunk in all_chunks["regional_context"]:
            assert "region" in chunk["metadata"]
            assert chunk["metadata"]["region"] == "Casamance"


class TestTotalCounts:

    def test_total_chunk_count(self, all_chunks):
        total = sum(len(chunks) for chunks in all_chunks.values())
        # ~60 disease + ~62 treatment + ~8 farming + ~6 regional = ~136
        assert total >= 100, f"Only {total} total chunks — expected 100+"


class TestMetadataCaseNormalization:
    """`crop` metadata must be lowercase so ChromaDB `$eq` filters in
    route_intent match. A future seed author writing `"Cassava"` would
    silently break filtered search before this guard.
    """

    def test_all_crop_metadata_is_lowercase(self, all_chunks):
        mixed = []
        for name, chunks in all_chunks.items():
            for chunk in chunks:
                crop = chunk.get("metadata", {}).get("crop")
                if isinstance(crop, str) and crop != crop.lower():
                    mixed.append((name, chunk["id"], crop))
        assert not mixed, f"Found {len(mixed)} non-lowercase crop values: {mixed[:5]}"

    def test_normalizer_fixes_mixed_case_input(self):
        from app.knowledge_pack.seed_chunks import _normalize_metadata_case
        chunks = [
            {"id": "a", "content": "...", "metadata": {"crop": "Cassava", "chunk_type": "child"}},
            {"id": "b", "content": "...", "metadata": {"crop": "RICE", "chunk_type": "parent"}},
            {"id": "c", "content": "...", "metadata": {"chunk_type": "child"}},  # no crop
        ]
        _normalize_metadata_case(chunks)
        assert chunks[0]["metadata"]["crop"] == "cassava"
        assert chunks[1]["metadata"]["crop"] == "rice"
        assert "crop" not in chunks[2]["metadata"]
