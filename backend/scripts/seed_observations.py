"""Seed sample observations for demo purposes.

Run: cd backend && PYTHONPATH=. python scripts/seed_observations.py
"""

import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

DB_PATH = "../packs/casamance_agriculture/knowledge.db"
from app.config import settings
UPLOADS_DIR = settings.uploads_path

now = datetime.now(timezone.utc)

OBSERVATIONS = [
    {
        "timestamp": (now - timedelta(hours=1)).isoformat(),
        "type": "disease_sighting",
        "location": "Field 3, near the river",
        "details": (
            "Cassava mosaic virus confirmed on 3 plants in row 6. Leaves show "
            "classic yellow-green mosaic pattern with curling. Whiteflies visible "
            "on undersides — likely the vector. Marked plants with red tape for "
            "monitoring."
        ),
        "image_path": str((UPLOADS_DIR / "seed_cassava_mosaic.jpg").resolve().as_posix()),
        "severity_observed": "severe",
    },
    {
        "timestamp": (now - timedelta(hours=3)).isoformat(),
        "type": "disease_sighting",
        "location": "North rice paddy, section B",
        "details": (
            "Rice blast lesions on lower leaves — diamond-shaped with gray "
            "centers. Affecting roughly 15% of the paddy near the drainage "
            "channel. Humid conditions this week likely contributed."
        ),
        "image_path": str((UPLOADS_DIR / "seed_rice_field.jpg").resolve().as_posix()),
        "severity_observed": "moderate",
    },
    {
        "timestamp": (now - timedelta(hours=5)).isoformat(),
        "type": "treatment_applied",
        "location": "Western cassava field, rows 4-8",
        "details": (
            "Applied neem oil spray to control whitefly population. Mixed 50ml "
            "neem oil concentrate with 1L water and a few drops of liquid soap "
            "as emulsifier. Sprayed all affected plants. Will repeat in 7 days "
            "if population doesn't decline."
        ),
        "image_path": None,
        "severity_observed": None,
    },
    {
        "timestamp": (now - timedelta(hours=8)).isoformat(),
        "type": "crop_condition",
        "location": "East plot",
        "details": (
            "Cassava plants showing vigorous growth after last week's rain. "
            "New leaf flush on most stems, estimated height 1.2m. Good canopy "
            "coverage, no disease signs. Ready for first weeding next week."
        ),
        "image_path": None,
        "severity_observed": None,
    },
    {
        "timestamp": (now - timedelta(hours=12)).isoformat(),
        "type": "crop_condition",
        "location": "Groundnut trial plot",
        "details": (
            "Groundnut plants showing excellent pod formation, pegging stage "
            "complete. Approximately 80% germination rate. Soil moisture "
            "adequate. Estimated 2-3 weeks to harvest."
        ),
        "image_path": str((UPLOADS_DIR / "seed_groundnut_field.jpg").resolve().as_posix()),
        "severity_observed": None,
    },
    {
        "timestamp": (now - timedelta(days=1)).isoformat(),
        "type": "treatment_applied",
        "location": "Field 3, cassava",
        "details": (
            "Removed 3 cassava stems showing severe mosaic symptoms and burned "
            "them at the edge of the field. Replanted gaps with clean TME 419 "
            "cuttings from the nursery. Will monitor neighbors for spread."
        ),
        "image_path": None,
        "severity_observed": None,
    },
    {
        "timestamp": (now - timedelta(days=1, hours=4)).isoformat(),
        "type": "crop_condition",
        "location": "Maize field A",
        "details": (
            "Maize at tasseling stage, good height (~2m), uniform stand. No "
            "visible pest damage or fall armyworm signs. Silk emergence starting "
            "on early rows. Expecting harvest in 4-5 weeks."
        ),
        "image_path": str((UPLOADS_DIR / "seed_maize_check.jpg").resolve().as_posix()),
        "severity_observed": None,
    },
    {
        "timestamp": (now - timedelta(days=1, hours=8)).isoformat(),
        "type": "note",
        "location": None,
        "details": (
            "Met with extension agent from Ziguinchor. Recommended new rice "
            "variety (NERICA-L19) for next season — better blast resistance. "
            "TME 419 cassava cuttings available next month. Also discussed "
            "intercropping schedule with groundnut."
        ),
        "image_path": None,
        "severity_observed": None,
    },
]


def seed():
    conn = sqlite3.connect(DB_PATH)

    # Clear previous seed data
    conn.execute("DELETE FROM field_observations")
    conn.commit()

    inserted = 0
    for obs in OBSERVATIONS:
        conn.execute(
            "INSERT INTO field_observations "
            "(timestamp, type, location, details, image_path, synced, severity_observed) "
            "VALUES (?, ?, ?, ?, ?, 1, ?)",
            (obs["timestamp"], obs["type"], obs["location"],
             obs["details"], obs["image_path"], obs["severity_observed"]),
        )
        inserted += 1
    conn.commit()
    conn.close()
    print(f"Seeded {inserted} observations into {DB_PATH}")


if __name__ == "__main__":
    seed()
