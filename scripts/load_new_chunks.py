"""Load new chunks (diseases, treatments, practices) into ChromaDB.

Reads JSON files from scripts/data/, groups by collection, and inserts
via collection.add(). ChromaDB auto-embeds using the attached embedding function.
"""
import json
import sys
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

CHROMA_PATH = "packs/casamance_agriculture/chroma_db"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
DATA_DIR = Path("scripts/data")


def load_json(filename: str) -> list[dict]:
    """Load a JSON data file, return empty list if missing."""
    path = DATA_DIR / filename
    if not path.exists():
        print(f"  SKIP: {path} not found")
        return []
    with open(path) as f:
        data = json.load(f)
    print(f"  Loaded {len(data)} chunks from {filename}")
    return data


def main():
    print("Loading embedding model...")
    ef = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
    client = chromadb.PersistentClient(path=CHROMA_PATH)

    # Load all data files
    print("\nLoading data files...")
    all_chunks = []
    all_chunks.extend(load_json("new_diseases.json"))
    all_chunks.extend(load_json("new_treatments.json"))
    all_chunks.extend(load_json("new_practices.json"))

    if not all_chunks:
        print("No data to load!")
        sys.exit(1)

    # Group by collection
    by_collection: dict[str, list[dict]] = {}
    for chunk in all_chunks:
        col = chunk["collection"]
        by_collection.setdefault(col, []).append(chunk)

    print(f"\nTotal: {len(all_chunks)} chunks across {len(by_collection)} collections")

    # Check for ID conflicts with existing data
    print("\nChecking for ID conflicts...")
    for col_name, chunks in by_collection.items():
        collection = client.get_collection(col_name, embedding_function=ef)
        existing_ids = set(collection.get()["ids"])
        new_ids = [c["id"] for c in chunks]

        conflicts = [nid for nid in new_ids if nid in existing_ids]
        if conflicts:
            print(f"  WARNING: {len(conflicts)} ID conflicts in {col_name}: {conflicts[:5]}...")
            print(f"  Skipping conflicting IDs.")
            chunks[:] = [c for c in chunks if c["id"] not in existing_ids]

        dupes = [nid for nid in new_ids if new_ids.count(nid) > 1]
        if dupes:
            print(f"  WARNING: {len(set(dupes))} duplicate IDs in new data for {col_name}")
            seen = set()
            deduped = []
            for c in chunks:
                if c["id"] not in seen:
                    seen.add(c["id"])
                    deduped.append(c)
            chunks[:] = deduped

    # Insert into ChromaDB
    total_inserted = 0
    for col_name, chunks in by_collection.items():
        if not chunks:
            continue

        collection = client.get_collection(col_name, embedding_function=ef)
        before_count = collection.count()

        ids = [c["id"] for c in chunks]
        documents = [c["document"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]

        # Batch insert in groups of 20
        for batch_start in range(0, len(ids), 20):
            batch_ids = ids[batch_start:batch_start + 20]
            batch_docs = documents[batch_start:batch_start + 20]
            batch_metas = metadatas[batch_start:batch_start + 20]
            collection.add(ids=batch_ids, documents=batch_docs, metadatas=batch_metas)
            print(f"  [{col_name}] Inserted batch {batch_start // 20 + 1}: {len(batch_ids)} chunks")

        after_count = collection.count()
        inserted = after_count - before_count
        total_inserted += inserted
        print(f"  {col_name}: {before_count} -> {after_count} (+{inserted})")

    print(f"\n=== DONE: {total_inserted} new chunks inserted ===")

    # Summary
    print("\n=== FINAL COLLECTION COUNTS ===")
    for col in client.list_collections():
        results = col.get(include=["metadatas"])
        by_type = {}
        by_crop = {}
        for meta in results["metadatas"]:
            ct = meta.get("chunk_type", "?")
            by_type[ct] = by_type.get(ct, 0) + 1
            crop = meta.get("crop", "none")
            by_crop[crop] = by_crop.get(crop, 0) + 1
        print(f"  {col.name} ({col.count()}) — types: {by_type}, crops: {by_crop}")


if __name__ == "__main__":
    main()
