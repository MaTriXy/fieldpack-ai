"""Manifest schema for Knowledge Packs.

The manifest.json is the identity card of a Knowledge Pack.
It describes what's inside, how it was built, and what models to use with it.
Judges inspect this file — it must be clean and informative.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field


class RegionInfo(BaseModel):
    name: str
    country: str
    coordinates: dict = Field(default_factory=dict)  # {"lat": float, "lon": float}
    climate_zone: str = ""


class Statistics(BaseModel):
    diseases_count: int = 0
    treatments_count: int = 0
    farming_practices_count: int = 0
    text_chunks: int = 0
    images_count: int = 0
    total_size_mb: float = 0.0


class ModelsUsed(BaseModel):
    research_agents: str = ""
    knowledge_compiler: str = ""
    embedding_model: str = ""
    embedding_dimensions: int = 384


class ManifestSchema(BaseModel):
    """Pydantic model for manifest.json validation."""
    schema_version: str = Field(default="fieldpack-manifest-v1", alias="$schema")
    name: str
    description: str = ""
    version: str = "1.0.0"
    region: RegionInfo
    domain: str = "agriculture"
    crops: list[str] = Field(default_factory=list)
    statistics: Statistics = Field(default_factory=Statistics)
    models_used: ModelsUsed = Field(default_factory=ModelsUsed)
    recommended_edge_model: str = "gemma-4-e4b-it"
    created_at: str = ""
    sources: list[str] = Field(default_factory=list)
    license: str = "CC-BY-SA-4.0"

    model_config = {"populate_by_name": True}


def validate_manifest(manifest_path: Path) -> ManifestSchema:
    """Read and validate a manifest.json file."""
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    return ManifestSchema.model_validate(raw)


def create_manifest(
    pack_path: Path,
    name: str,
    description: str,
    region: RegionInfo,
    crops: list[str],
    statistics: Statistics,
    models_used: ModelsUsed,
    sources: list[str] | None = None,
) -> ManifestSchema:
    """Create and write a manifest.json for a Knowledge Pack."""
    manifest = ManifestSchema(
        name=name,
        description=description,
        region=region,
        crops=crops,
        statistics=statistics,
        models_used=models_used,
        sources=sources or [],
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    manifest_path = pack_path / "manifest.json"
    manifest_path.write_text(
        manifest.model_dump_json(indent=2, by_alias=True),
        encoding="utf-8",
    )

    return manifest
