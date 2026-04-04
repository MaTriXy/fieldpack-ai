"""Node 5: RE-RANK (LLM call #3).

Scores and filters search results by relevance. Uses index-based
scoring: LLM sees truncated results and outputs {index, score, keep}.

Keep threshold: 0.4 (tunable in Phase 7).
Sufficient: 2+ results with score >= 0.5.
NL + smart parsing approach.
"""

import json
import re

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.models import ScoredResult, SearchResult
from app.agents.state import FieldAssistantState
from app.logger import Step, pipeline_logger as log
from app.models.offline_llm import get_field_llm


# Thresholds (tunable in Phase 7)
KEEP_THRESHOLD = 0.4
SUFFICIENT_THRESHOLD = 0.5
SUFFICIENT_MIN_COUNT = 2
MAX_RESULTS_FOR_RERANK = 8
MAX_WORDS_PER_RESULT = 200

RERANK_SYSTEM_PROMPT = """You are a relevance judge for an agricultural knowledge system in Casamance, Senegal.

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
        # Use parent_content if available, else content
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
    """Parse LLM re-rank response into scored results.

    Returns (ranked_results, is_sufficient).

    Fallback: if parsing fails completely, keep all results with
    their original scores.
    """
    scored: list[ScoredResult] = []

    # Try to extract JSON array
    parsed_items = None

    # Tier 1: Direct array parse
    try:
        parsed_items = json.loads(response_text.strip())
    except json.JSONDecodeError:
        pass

    # Tier 2: Extract array from text
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
            idx = item.get("index", 0) - 1  # Convert 1-based to 0-based
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
                ))
    else:
        # Fallback: keep all results with original scores as relevance
        log.log_step(Step.RERANK, "parse_fallback", level="WARNING",
                     details={"response_preview": response_text[:200]})
        for r in search_results:
            scored.append(ScoredResult(
                content=r.parent_content or r.content,
                source=r.source,
                relevance_score=min(1.0, r.score),
                parent_id=r.parent_id,
                parent_content=r.parent_content,
            ))

    # Sort by relevance descending
    scored.sort(key=lambda s: s.relevance_score, reverse=True)

    # Determine sufficiency
    high_quality = [s for s in scored if s.relevance_score >= SUFFICIENT_THRESHOLD]
    is_sufficient = len(high_quality) >= SUFFICIENT_MIN_COUNT

    return scored, is_sufficient


def rerank_results(state: FieldAssistantState) -> dict:
    """Re-rank search results by relevance using LLM scoring.

    LLM call #3. Truncates results, sends to E4B for scoring,
    filters by keep threshold, determines if results are sufficient.

    Returns dict with: ranked_results, is_sufficient, retrieval_attempts.
    """
    search_results = state.get("search_results", [])
    user_message = state.get("user_message", "")
    attempts = state.get("retrieval_attempts", 0)

    # Empty results → insufficient
    if not search_results:
        log.log_step(Step.RERANK, "no_results", details={"attempts": attempts})
        return {
            "ranked_results": [],
            "is_sufficient": False,
            "retrieval_attempts": attempts + 1,
        }

    # Cap results for context window
    top_results = search_results[:MAX_RESULTS_FOR_RERANK]

    with log.timed(Step.RERANK, "llm_call") as t:
        # Prepare truncated results for LLM
        truncated = _truncate_for_context(top_results)

        # Build prompt
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
            llm = get_field_llm(temperature=0.1)
            response = llm.invoke(messages)
            response_text = response.content if hasattr(response, "content") else str(response)
        except Exception as e:
            log.log_step(Step.RERANK, "llm_error", level="ERROR",
                         details={"error": str(e)})
            # Fallback: keep all with original scores
            ranked = [
                ScoredResult(
                    content=r.parent_content or r.content,
                    source=r.source,
                    relevance_score=min(1.0, r.score),
                    parent_id=r.parent_id,
                    parent_content=r.parent_content,
                )
                for r in top_results
            ]
            return {
                "ranked_results": ranked,
                "is_sufficient": len(ranked) >= SUFFICIENT_MIN_COUNT,
                "retrieval_attempts": attempts + 1,
            }

        ranked, is_sufficient = _parse_rerank_response(response_text, top_results)

        t.set(details={
            "input_count": len(top_results),
            "kept_count": len(ranked),
            "is_sufficient": is_sufficient,
            "top_scores": [round(s.relevance_score, 3) for s in ranked[:5]],
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
