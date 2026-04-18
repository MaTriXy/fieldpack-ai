"""Node 5: RE-RANK.

Two-tier reranking strategy:
  1. Heuristic (fast, ~0ms): normalize scores per engine type,
     dedup, sort, check sufficiency. Used on first attempt.
  2. LLM fallback (slow, ~20s): only fires if heuristic marks
     results as insufficient on retry attempts.

Scores by engine:
  - Chroma: cosine similarity already 0-1, use as-is
  - FTS: BM25 scores normalized to 0-1 within batch
  - Structured: flat 0.7 (neutral), boosted to 0.85 on exact name match
"""

import json
import re

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.models import ResultType, ScoredResult, SearchResult, extract_text
from app.agents.state import FieldAssistantState
from app.logger import Step, pipeline_logger as log
from app.models.offline_llm import get_field_llm


# Thresholds
KEEP_THRESHOLD = 0.4
SUFFICIENT_THRESHOLD = 0.5
SUFFICIENT_MIN_COUNT = 2
MAX_RESULTS_FOR_RERANK = 5
MAX_WORDS_PER_RESULT = 200


# ============================================================
# Tier 1: Heuristic rerank (fast path)
# ============================================================

def _normalize_scores(results: list[SearchResult]) -> list[ScoredResult]:
    """Normalize scores across engine types to a common 0-1 scale.

    BM25 scores arrive already normalized to [0,1] by execute_search.
    FTS/structured results are capped at 0.8 because they lack the rich
    parent-chunk prose that ChromaDB results provide — this prevents
    thin tabular content from outranking detailed narrative chunks.
    """
    # FTS scores already normalized 0-1 by execute_search._normalize_bm25_scores
    FTS_SCORE_CAP = 0.8
    STRUCTURED_SCORE = 0.65

    scored = []
    for r in results:
        if r.result_type == ResultType.CHROMA:
            # Cosine similarity already 0-1
            norm_score = r.score
        elif r.result_type == ResultType.FTS:
            # Already 0-1 from execute_search; cap to avoid outranking ChromaDB
            norm_score = min(FTS_SCORE_CAP, max(0.3, r.score))
        else:
            # Structured: fixed score, useful for context but not primary
            norm_score = STRUCTURED_SCORE

        scored.append(ScoredResult(
            content=r.parent_content or r.content,
            source=r.source,
            relevance_score=min(1.0, max(0.0, norm_score)),
            parent_id=r.parent_id,
            parent_content=r.parent_content,
            metadata=r.metadata,
        ))

    return scored


def _dedup_results(scored: list[ScoredResult]) -> list[ScoredResult]:
    """Remove duplicate results, keeping the highest-scored version."""
    seen = {}
    for r in scored:
        # Dedup by parent_id (same source doc), fall back to content prefix
        key = r.parent_id if r.parent_id else (r.content or "")[:100]
        if key not in seen or r.relevance_score > seen[key].relevance_score:
            seen[key] = r
    return list(seen.values())


def _apply_image_symptom_boost(
    scored: list[ScoredResult],
    image_description: str,
) -> list[ScoredResult]:
    """Boost results whose content mentions symptoms from the image analysis.

    Each matching symptom adds a small score bump. This helps results whose
    disease symptoms overlap with the observed visual symptoms outrank
    diseases with weaker symptom matches.
    """
    # Extract symptom terms from "... Symptoms: x, y, z" suffix
    symptom_terms = []
    if "Symptoms:" in image_description:
        symptom_str = image_description.split("Symptoms:")[-1]
        for s in symptom_str.split(","):
            term = s.strip().strip(".").lower()
            if term:
                symptom_terms.append(term)

    if not symptom_terms:
        return scored

    BOOST_PER_MATCH = 0.04  # +0.04 per matching symptom term
    MAX_BOOST = 0.15        # Cap total boost

    for result in scored:
        content_lower = (result.content or "").lower()
        matches = sum(1 for t in symptom_terms if t in content_lower)
        if matches:
            boost = min(matches * BOOST_PER_MATCH, MAX_BOOST)
            result.relevance_score = min(1.0, result.relevance_score + boost)

    return scored


def _apply_crop_boost(
    scored: list[ScoredResult],
    crop: str,
) -> list[ScoredResult]:
    """Boost results whose metadata or source ID matches the detected crop.
    Penalize results that explicitly name a different crop.

    Checks metadata["crop"] (chroma tags) and source string (e.g. "rice_blast_005").
    """
    crop_lower = crop.lower()
    CROP_BOOST = 0.12
    CROP_MISMATCH_PENALTY = 0.15

    for result in scored:
        meta_crop = ((result.metadata or {}).get("crop") or "").lower()
        source_lower = (result.source or "").lower()
        if meta_crop == crop_lower or source_lower.startswith(crop_lower + "_"):
            result.relevance_score = min(1.0, result.relevance_score + CROP_BOOST)
        elif meta_crop and meta_crop != crop_lower:
            result.relevance_score = max(0.0, result.relevance_score - CROP_MISMATCH_PENALTY)

    return scored


def _heuristic_rerank(
    search_results: list[SearchResult],
    image_description: str | None = None,
    detected_crop: str | None = None,
) -> tuple[list[ScoredResult], bool]:
    """Fast heuristic rerank: normalize, dedup, sort, check sufficiency."""
    scored = _normalize_scores(search_results)
    scored = _dedup_results(scored)

    # Filter by keep threshold
    scored = [s for s in scored if s.relevance_score >= KEEP_THRESHOLD]

    # Boost results matching the detected crop before sorting
    if detected_crop:
        scored = _apply_crop_boost(scored, detected_crop)

    # Boost results matching image symptoms before sorting
    if image_description:
        scored = _apply_image_symptom_boost(scored, image_description)

    # Sort by relevance descending
    scored.sort(key=lambda s: s.relevance_score, reverse=True)

    # Determine sufficiency
    high_quality = [s for s in scored if s.relevance_score >= SUFFICIENT_THRESHOLD]
    is_sufficient = len(high_quality) >= SUFFICIENT_MIN_COUNT

    return scored, is_sufficient


# ============================================================
# Tier 2: LLM rerank (slow fallback)
# ============================================================

RERANK_SYSTEM_PROMPT = """You are a relevance judge for an agricultural knowledge system.

Given a user question and search results, score each result for relevance.

For each result, output:
- index: the result number
- score: 0.0 (irrelevant) to 1.0 (perfectly relevant)
- keep: true if score >= 0.4

Output a JSON array:
[{"index": 1, "score": 0.8, "keep": true}, {"index": 2, "score": 0.2, "keep": false}]

Score higher if the result:
- Directly answers the question
- Contains specific, actionable information
- Mentions the correct crop or disease
- Provides practical advice for field conditions

Score lower if the result:
- Is about a different crop or disease
- Is too generic or vague
- Contradicts the question context

Output ONLY the JSON array."""


def _truncate_for_context(
    results: list[SearchResult],
    max_words: int = MAX_WORDS_PER_RESULT,
) -> list[dict]:
    """Truncate each result for the re-rank context window."""
    truncated = []
    for i, r in enumerate(results):
        text = r.parent_content or r.content
        words = text.split()
        if len(words) > max_words:
            text = " ".join(words[:max_words]) + "..."
        truncated.append({
            "index": i + 1,
            "content": text,
            "source": r.source,
            "score": round(r.score, 3),
        })
    return truncated


def _parse_rerank_response(
    response_text: str,
    search_results: list[SearchResult],
) -> tuple[list[ScoredResult], bool]:
    """Parse LLM re-rank response into scored results."""
    scored: list[ScoredResult] = []
    parsed_items = None

    try:
        parsed_items = json.loads(response_text.strip())
    except json.JSONDecodeError:
        pass

    if parsed_items is None:
        array_match = re.search(r"\[.*\]", response_text, re.DOTALL)
        if array_match:
            try:
                parsed_items = json.loads(array_match.group())
            except json.JSONDecodeError:
                pass

    if parsed_items and isinstance(parsed_items, list):
        for item in parsed_items:
            if not isinstance(item, dict):
                continue
            idx = item.get("index", 0) - 1
            score = float(item.get("score", 0.0))
            keep = item.get("keep", score >= KEEP_THRESHOLD)

            if 0 <= idx < len(search_results) and keep and score >= KEEP_THRESHOLD:
                r = search_results[idx]
                scored.append(ScoredResult(
                    content=r.parent_content or r.content,
                    source=r.source,
                    relevance_score=min(1.0, max(0.0, score)),
                    parent_id=r.parent_id,
                    parent_content=r.parent_content,
                    metadata=r.metadata,
                ))
    else:
        log.log_step(Step.RERANK, "llm_parse_fallback", level="WARNING",
                     details={"response_preview": response_text[:200]})
        for r in search_results:
            score = min(1.0, r.score)
            if score >= KEEP_THRESHOLD:
                scored.append(ScoredResult(
                    content=r.parent_content or r.content,
                    source=r.source,
                    relevance_score=score,
                    parent_id=r.parent_id,
                    parent_content=r.parent_content,
                    metadata=r.metadata,
                ))

    scored.sort(key=lambda s: s.relevance_score, reverse=True)

    high_quality = [s for s in scored if s.relevance_score >= SUFFICIENT_THRESHOLD]
    is_sufficient = len(high_quality) >= SUFFICIENT_MIN_COUNT

    return scored, is_sufficient


def _llm_rerank(
    search_results: list[SearchResult],
    user_message: str,
    detected_crop: str | None = None,
    image_description: str | None = None,
) -> tuple[list[ScoredResult], bool]:
    """Slow LLM rerank — only used as fallback on retry."""
    truncated = _truncate_for_context(search_results)
    results_text = "\n".join(
        f"[{item['index']}] (raw score: {item['score']}) {item['content']}"
        for item in truncated
    )

    messages = [
        SystemMessage(content=RERANK_SYSTEM_PROMPT),
        HumanMessage(content=(
            f"User question: {user_message}\n\n"
            f"Search results:\n{results_text}"
        )),
    ]

    try:
        llm = get_field_llm(temperature=0.1, num_predict=256, format="json")
        response = llm.invoke(messages)
        response_text = extract_text(response)
    except Exception as e:
        log.log_step(Step.RERANK, "llm_error", level="ERROR",
                     details={"error": str(e)})
        # Fall through to heuristic with all boosts preserved
        return _heuristic_rerank(search_results, image_description=image_description, detected_crop=detected_crop)

    return _parse_rerank_response(response_text, search_results)


# ============================================================
# Main entry point
# ============================================================

def rerank_results(state: FieldAssistantState) -> dict:
    """Re-rank search results with two-tier strategy.

    Attempt 1: heuristic rerank (fast, ~0ms).
    Attempt 2+: LLM rerank (slow, ~20s) only if heuristic was insufficient.

    Returns dict with: ranked_results, is_sufficient, retrieval_attempts.
    """
    search_results = state.get("search_results", [])
    user_message = state.get("user_message", "")
    attempts = state.get("retrieval_attempts", 0)

    if not search_results:
        log.log_step(Step.RERANK, "no_results", details={"attempts": attempts})
        return {
            "ranked_results": [],
            "is_sufficient": False,
            "retrieval_attempts": attempts + 1,
        }

    top_results = search_results[:MAX_RESULTS_FOR_RERANK]

    # Tier 1: heuristic (always runs first)
    image_description = state.get("image_description")
    classify_result = state.get("classify_result")
    detected_crop = classify_result.crop if classify_result and classify_result.crop else None
    with log.timed(Step.RERANK, "heuristic_rerank") as t:
        ranked, is_sufficient = _heuristic_rerank(top_results, image_description, detected_crop)
        t.set(details={
            "input_count": len(top_results),
            "kept_count": len(ranked),
            "is_sufficient": is_sufficient,
            "top_scores": [round(s.relevance_score, 3) for s in ranked[:5]],
            "method": "heuristic",
        })

    # Tier 2: LLM fallback — only on retry attempts when heuristic says insufficient
    if not is_sufficient and attempts >= 1:
        log.log_step(Step.RERANK, "escalating_to_llm",
                     details={"attempt": attempts, "heuristic_kept": len(ranked)})
        with log.timed(Step.RERANK, "llm_call") as t:
            ranked, is_sufficient = _llm_rerank(top_results, user_message, detected_crop, image_description)
            t.set(details={
                "input_count": len(top_results),
                "kept_count": len(ranked),
                "is_sufficient": is_sufficient,
                "top_scores": [round(s.relevance_score, 3) for s in ranked[:5]],
                "method": "llm",
            })

    log.log_rerank(
        total_input=len(top_results),
        total_kept=len(ranked),
        is_sufficient=is_sufficient,
        top_scores=[s.relevance_score for s in ranked[:5]],
    )

    return {
        "ranked_results": ranked,
        "is_sufficient": is_sufficient,
        "retrieval_attempts": attempts + 1,
    }
