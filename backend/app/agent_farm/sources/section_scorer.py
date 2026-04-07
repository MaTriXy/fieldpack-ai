"""Fuzzy relevance scorer for PageSection objects.

Scores sections 0.0-1.0 based on agricultural content relevance.
Uses weighted keyword density, length heuristics, and boilerplate
detection — all pure Python, no LLM calls.

The scorer is used by source_gathering to cap sections per source
(keep top-N by score) and to filter low-quality sections globally.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.agent_farm.models import PageSection


# ------------------------------------------------------------------
# Keyword dictionaries with weights
# ------------------------------------------------------------------

# High-value agricultural terms (boost)
_AG_KEYWORDS: dict[str, float] = {
    # Diseases & pests
    "mosaic": 1.0, "blight": 1.0, "wilt": 0.9, "rot": 0.9,
    "virus": 0.9, "bacterial": 0.9, "fungal": 0.9, "disease": 0.8,
    "symptom": 1.0, "diagnos": 0.9, "infect": 0.8,
    "whitefly": 1.0, "mealybug": 1.0, "mite": 0.9, "nematode": 0.9,
    "pest": 0.8, "insect": 0.7, "larva": 0.8,
    # Treatments
    "treatment": 1.0, "control": 0.8, "pesticide": 0.8, "fungicide": 0.8,
    "neem": 1.0, "spray": 0.7, "resistant": 0.9, "tolerance": 0.8,
    "organic": 0.7, "biological control": 1.0, "ipm": 0.9,
    # Agronomy
    "variety": 0.9, "cultivar": 0.9, "yield": 0.9, "harvest": 0.8,
    "planting": 0.8, "spacing": 0.8, "intercrop": 0.9,
    "fertiliz": 0.8, "compost": 0.8, "manure": 0.7, "npk": 0.8,
    "irrigat": 0.7, "drought": 0.9, "rainfall": 0.7,
    "soil": 0.7, "soil ph": 0.6, "nutrient": 0.7,
    "storage": 0.8, "post-harvest": 0.9, "drying": 0.7,
    "propagat": 0.8, "stem cutting": 1.0, "seed": 0.7,
    # Crops we care about
    "cassava": 0.6, "rice": 0.5, "maize": 0.5, "groundnut": 0.5,
    "tomato": 0.5, "manioc": 0.6,
    # Region
    "senegal": 0.7, "casamance": 0.9, "africa": 0.4,
    "tropical": 0.4,
}

# Pedagogical / meta terms (penalty)
_PEDAGOGY_KEYWORDS: dict[str, float] = {
    "facilitator": 0.8, "participant": 0.6, "exercise": 0.6,
    "group discussion": 0.8, "session": 0.4, "training": 0.4,
    "learning objective": 0.7, "role play": 0.7, "brainstorm": 0.6,
    "flipchart": 0.8, "marker pen": 0.8, "handout": 0.6,
    "curriculum": 0.7, "module": 0.3, "lesson plan": 0.7,
    "evaluate the session": 0.9, "wrap up": 0.5,
}

# Boilerplate patterns (strong penalty)
_BOILERPLATE_RES: list[re.Pattern] = [
    re.compile(r"table of contents", re.IGNORECASE),
    re.compile(r"acknowledgement", re.IGNORECASE),
    re.compile(r"bibliography|references cited", re.IGNORECASE),
    re.compile(r"ISBN\s*[\d-]+", re.IGNORECASE),
    re.compile(r"FAO\s+TECHNICAL\s+PAPERS", re.IGNORECASE),
    re.compile(r"printed\s+in\s+\w+", re.IGNORECASE),
    re.compile(r"all\s+rights\s+reserved", re.IGNORECASE),
    re.compile(r"copyright\s+©", re.IGNORECASE),
    re.compile(r"annex\s+\d+", re.IGNORECASE),
    re.compile(r"appendix\s+[A-Z\d]", re.IGNORECASE),
]

# OCR garbage pattern — high ratio of non-alphanumeric chars
_OCR_GARBAGE_THRESHOLD = 0.35  # if >35% of chars are non-alpha, likely OCR noise


# ------------------------------------------------------------------
# Scorer
# ------------------------------------------------------------------


@dataclass
class SectionScore:
    """Detailed scoring breakdown for debugging/logging."""
    section: PageSection
    total: float
    ag_score: float       # agricultural keyword contribution
    pedagogy_penalty: float
    boilerplate_penalty: float
    length_factor: float
    ocr_penalty: float


def score_section(section: PageSection) -> SectionScore:
    """Score a section's agricultural relevance from 0.0 to 1.0.

    Scoring formula (all fuzzy, weighted):
      base = agricultural_keyword_density (0-1)
      penalties = pedagogy + boilerplate + OCR + length
      total = clamp(base - penalties, 0, 1)

    Higher = more relevant to agricultural knowledge extraction.
    """
    content = section.content
    content_lower = content.lower()
    word_count = max(len(content_lower.split()), 1)

    # --- Agricultural keyword score (0-1) ---
    ag_hits = 0.0
    ag_matches = 0
    for keyword, weight in _AG_KEYWORDS.items():
        count = content_lower.count(keyword)
        if count > 0:
            # Diminishing returns: first hit = full weight, extras = 0.3x
            ag_hits += weight + (count - 1) * weight * 0.3
            ag_matches += 1

    # Normalize by word count — density matters more than absolute count
    # Cap at 1.0, scale so ~5 weighted hits per 100 words = 0.7
    ag_density = ag_hits / (word_count / 100.0)
    ag_score = min(ag_density / 7.0, 1.0)

    # Bonus for breadth: more distinct keywords = better
    breadth_bonus = min(ag_matches / 8.0, 0.2)
    ag_score = min(ag_score + breadth_bonus, 1.0)

    # --- Pedagogy penalty (0-0.5) ---
    ped_hits = 0.0
    for keyword, weight in _PEDAGOGY_KEYWORDS.items():
        count = content_lower.count(keyword)
        if count > 0:
            ped_hits += weight * min(count, 3)

    ped_density = ped_hits / (word_count / 100.0)
    pedagogy_penalty = min(ped_density / 6.0, 0.5)

    # --- Boilerplate penalty (0-0.6) ---
    boilerplate_hits = sum(
        1 for pattern in _BOILERPLATE_RES if pattern.search(content)
    )
    boilerplate_penalty = min(boilerplate_hits * 0.2, 0.6)

    # --- Length factor ---
    # Very short sections (<200 chars) are likely headers/fragments
    # Very long sections (>3000 chars) are fine but might be reference lists
    char_count = len(content)
    if char_count < 150:
        length_factor = -0.3  # strong penalty
    elif char_count < 300:
        length_factor = -0.1  # mild penalty
    elif char_count > 3000:
        # Long is fine unless it's boilerplate (already penalized above)
        length_factor = 0.0
    else:
        length_factor = 0.0

    # --- OCR garbage detection ---
    alpha_count = sum(1 for c in content if c.isalpha() or c.isspace())
    alpha_ratio = alpha_count / max(len(content), 1)
    ocr_penalty = 0.0
    if alpha_ratio < (1 - _OCR_GARBAGE_THRESHOLD):
        # High non-alpha ratio — likely OCR noise
        ocr_penalty = 0.4 * (1 - alpha_ratio)

    # --- Combine ---
    total = ag_score - pedagogy_penalty - boilerplate_penalty + length_factor - ocr_penalty
    total = max(0.0, min(1.0, total))

    return SectionScore(
        section=section,
        total=total,
        ag_score=ag_score,
        pedagogy_penalty=pedagogy_penalty,
        boilerplate_penalty=boilerplate_penalty,
        length_factor=length_factor,
        ocr_penalty=ocr_penalty,
    )


def rank_sections(
    sections: list[PageSection],
    max_sections: int | None = None,
    min_score: float = 0.05,
) -> list[PageSection]:
    """Score and rank sections, optionally capping to top N.

    Args:
        sections: Sections to rank.
        max_sections: If set, keep only the top N by score.
        min_score: Drop sections below this score regardless of cap.

    Returns:
        Filtered and sorted sections (highest relevance first).
    """
    scored = [score_section(s) for s in sections]

    # Filter below minimum
    scored = [s for s in scored if s.total >= min_score]

    # Sort by score descending
    scored.sort(key=lambda s: s.total, reverse=True)

    # Cap
    if max_sections is not None and len(scored) > max_sections:
        scored = scored[:max_sections]

    return [s.section for s in scored]


def score_and_log(sections: list[PageSection]) -> list[SectionScore]:
    """Score all sections and return detailed breakdowns (for debugging)."""
    return sorted(
        [score_section(s) for s in sections],
        key=lambda s: s.total,
        reverse=True,
    )
