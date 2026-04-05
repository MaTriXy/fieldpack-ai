#!/usr/bin/env python3
"""Build the POC Knowledge Pack for demo and manual testing.

Usage:
    cd fieldpack-ai/backend
    PYTHONPATH=. python scripts/build_poc_pack.py

Creates: packs/casamance_agriculture/
         - knowledge.db (SQLite + FTS5)
         - chroma_db/ (vector embeddings)
         - manifest.json, README.md, SOURCES.md
"""

import sys
import time
from pathlib import Path

# Ensure backend/ is on PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.knowledge_pack.builder import build_pack
from app.knowledge_pack.loader import load_pack, unload_pack


def main():
    print("=" * 60)
    print("FieldPack AI - POC Knowledge Pack Builder")
    print("=" * 60)

    start = time.perf_counter()
    pack_path = build_pack("casamance_agriculture")
    build_time = time.perf_counter() - start

    print(f"\nPack built in {build_time:.1f}s: {pack_path}")

    # Verify by loading
    print("\nVerifying pack loads correctly...")
    try:
        pack = load_pack(pack_path)
        health = pack.health_check()
        print(f"  Pack name:    {health['pack_name']}")
        print(f"  Region:       {health['region']}")
        print(f"  Crops:        {', '.join(health['crops'])}")
        print(f"  SQLite:       {health.get('sqlite_tables', {})}")
        print(f"  ChromaDB:     {health.get('chroma_collections', {})}")
        print("\nHealth check PASSED")
    except Exception as e:
        print(f"\nHealth check FAILED: {e}")
        sys.exit(1)
    finally:
        unload_pack()

    print(f"\nPack ready at: {pack_path}")
    print("Load it with: POST /packs/load/casamance_agriculture")


if __name__ == "__main__":
    main()
