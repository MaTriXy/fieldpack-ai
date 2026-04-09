"""Seed sample observations for demo purposes.

Run: cd backend && PYTHONPATH=. python scripts/seed_observations.py
"""

import sqlite3
from datetime import datetime, timezone, timedelta

DB_PATH = "../packs/casamance_agriculture/knowledge.db"

now = datetime.now(timezone.utc)

OBSERVATIONS = [
    {
        "timestamp": (now - timedelta(hours=2)).isoformat(),
        "type": "disease_sighting",
        "location": "Field 3, near the river",
        "details": (
            "Brown spots on cassava leaves in the lower canopy, affecting about 30% "
            "of plants. Spots are circular, 2-3cm diameter with yellow halos. "
            "Whiteflies visible on leaf undersides."
        ),
        "severity_observed": "moderate",
    },
    {
        "timestamp": (now - timedelta(hours=4)).isoformat(),
        "type": "crop_condition",
        "location": "East plot",
        "details": (
            "Cassava plants showing vigorous growth after last week's rain. "
            "New leaf flush on most stems. No signs of disease. "
            "Estimated height 1.2m, good canopy coverage."
        ),
        "severity_observed": None,
    },
    {
        "timestamp": (now - timedelta(hours=6)).isoformat(),
        "type": "treatment_applied",
        "location": "Western cassava field",
        "details": (
            "Applied neem oil spray to control whitefly population. "
            "Mixed 50ml neem oil with 1L water and a few drops of liquid soap. "
            "Sprayed all affected plants in rows 4-8. Will repeat in 7 days."
        ),
        "severity_observed": None,
    },
    {
        "timestamp": (now - timedelta(hours=8)).isoformat(),
        "type": "disease_sighting",
        "location": "North rice paddy, section B",
        "details": (
            "Rice blast symptoms on several tillers \u2014 diamond-shaped lesions "
            "on leaves with gray centers. Affecting roughly 15% of the paddy. "
            "Humid conditions over the past week likely contributed."
        ),
        "severity_observed": "mild",
    },
    {
        "timestamp": (now - timedelta(days=1)).isoformat(),
        "type": "note",
        "location": None,
        "details": (
            "Spoke with extension officer from Ziguinchor. TME 419 cassava "
            "cuttings may be available next month. Will follow up. Also discussed "
            "potential for intercropping with groundnut."
        ),
        "severity_observed": None,
    },
    {
        "timestamp": (now - timedelta(days=1, hours=3)).isoformat(),
        "type": "crop_condition",
        "location": "Groundnut trial plot",
        "details": (
            "Groundnut seedlings emerging well, approximately 80% germination rate. "
            "Soil moisture adequate. Some minor leaf curling on eastern edge \u2014 "
            "possibly wind damage, not disease."
        ),
        "severity_observed": None,
    },
]


def seed():
    conn = sqlite3.connect(DB_PATH)
    inserted = 0
    for obs in OBSERVATIONS:
        conn.execute(
            "INSERT INTO field_observations "
            "(timestamp, type, location, details, image_path, synced, severity_observed) "
            "VALUES (?, ?, ?, ?, NULL, 0, ?)",
            (obs["timestamp"], obs["type"], obs["location"],
             obs["details"], obs["severity_observed"]),
        )
        inserted += 1
    conn.commit()
    conn.close()
    print(f"Seeded {inserted} observations into {DB_PATH}")


if __name__ == "__main__":
    seed()
