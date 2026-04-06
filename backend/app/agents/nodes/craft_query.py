"""Node 3: CRAFT SEARCH QUERY.

First attempt: template from classify fields (crop, disease, keywords,
growth_stage) — no LLM call (~0ms vs ~8s).

On retry (retrieval_attempts >= 1): LLM call generates 3 query variants:
  - Synonym / alternative phrasing
  - Local terminology (Wolof / French agricultural terms)
  - Broader / adjacent concept
"""

import json
import re

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.models import ClassifyExtractOutput, CraftedQuery, SearchEngineType
from app.agents.state import FieldAssistantState
from app.logger import Step, pipeline_logger as log
from app.models.offline_llm import get_field_llm



def _template_query(
    user_message: str,
    classify_result: ClassifyExtractOutput | None,
) -> CraftedQuery:
    """Build a search query from classify fields without an LLM call.

    Assembles crop, disease_name, keywords, growth_stage into a
    focused embedding query. Avoids raw user message to prevent
    filler words from diluting the embedding vector.
    """
    parts = []
    fts_keywords = []

    if classify_result:
        if classify_result.crop:
            parts.append(classify_result.crop)
            fts_keywords.append(classify_result.crop)
        if classify_result.disease_name:
            parts.append(classify_result.disease_name)
            fts_keywords.append(classify_result.disease_name)
        if classify_result.keywords:
            parts.extend(classify_result.keywords)
            fts_keywords.extend(classify_result.keywords)
        if classify_result.growth_stage:
            parts.append(classify_result.growth_stage.value)

    # Fall back to user message only when classify gave us nothing
    if not parts:
        parts.append(user_message)

    parts.append("Casamance")

    # Deduplicate while preserving order
    seen: set[str] = set()
    deduped: list[str] = []
    for p in parts:
        low = p.lower()
        if low not in seen:
            seen.add(low)
            deduped.append(p)

    # Deduplicate fts_keywords
    kw_seen: set[str] = set()
    unique_kw: list[str] = []
    for kw in fts_keywords:
        low = kw.lower()
        if low not in kw_seen:
            kw_seen.add(low)
            unique_kw.append(kw)

    return CraftedQuery(
        embedding_query=" ".join(deduped),
        fts_keywords=unique_kw[:7],
        reasoning="Template from classify fields (no LLM)",
    )


def _parse_craft_response(response_text: str) -> CraftedQuery:
    """Parse LLM response into CraftedQuery.

    Fallback chain:
      1. Direct JSON parse
      2. JSON from code block
      3. Regex JSON extraction
      4. Use raw text as embedding query
    """
    # Tier 1: Direct JSON
    try:
        data = json.loads(response_text.strip())
        return CraftedQuery.model_validate(data)
    except (json.JSONDecodeError, Exception):
        pass

    # Tier 2: Code block
    code_block = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL)
    if code_block:
        try:
            data = json.loads(code_block.group(1))
            return CraftedQuery.model_validate(data)
        except (json.JSONDecodeError, Exception):
            pass

    # Tier 3: Regex JSON
    json_match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", response_text, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group())
            return CraftedQuery.model_validate(data)
        except (json.JSONDecodeError, Exception):
            pass

    # Tier 4: Use raw text as embedding query
    log.log_step(Step.CRAFT_QUERY, "parse_fallback", level="WARNING",
                 details={"response_preview": response_text[:200]})
    clean_text = response_text.strip()[:200]
    words = [w for w in clean_text.split() if len(w) >= 3]
    return CraftedQuery(
        embedding_query=clean_text,
        fts_keywords=words[:5],
        reasoning="Fallback: used raw LLM text as query",
    )


RETRY_VARIANTS_PROMPT = """You help write search queries for an agricultural knowledge base about crops and diseases in Casamance, Senegal.

Your PREVIOUS search query was: "{previous_query}"
It returned insufficient results ({failure_reason}).

Generate 3 DIFFERENT search queries to try instead. Each must take a different angle:

1. SYNONYM variant: rephrase using different words, synonyms, or alternative descriptions of the same concept
2. LOCAL variant: use local terminology — Wolof names, French agricultural terms, regional crop variety names used in Casamance
3. BROAD variant: broaden the concept slightly — search for the crop family, symptom category, or general treatment approach

For each query, output:
{{"embedding_query": "...", "fts_keywords": ["...", "..."], "reasoning": "..."}}

Output a JSON array of exactly 3 objects:
[
  {{"embedding_query": "...", "fts_keywords": [...], "reasoning": "synonym variant: ..."}},
  {{"embedding_query": "...", "fts_keywords": [...], "reasoning": "local variant: ..."}},
  {{"embedding_query": "...", "fts_keywords": [...], "reasoning": "broad variant: ..."}}
]

Do NOT repeat the previous query. Each variant must be meaningfully different."""


def _parse_retry_variants(response_text: str, fallback_keywords: list[str]) -> list[CraftedQuery]:
    """Parse LLM response into a list of CraftedQuery variants."""
    variants = []

    # Try to extract JSON array
    parsed = None

    try:
        parsed = json.loads(response_text.strip())
    except json.JSONDecodeError:
        pass

    if parsed is None:
        array_match = re.search(r"\[.*\]", response_text, re.DOTALL)
        if array_match:
            try:
                parsed = json.loads(array_match.group())
            except json.JSONDecodeError:
                pass

    if parsed and isinstance(parsed, list):
        for item in parsed:
            if isinstance(item, dict) and "embedding_query" in item:
                try:
                    variants.append(CraftedQuery.model_validate(item))
                except Exception:
                    pass

    if not variants:
        log.log_step(Step.CRAFT_QUERY, "retry_parse_fallback", level="WARNING",
                     details={"response_preview": response_text[:200]})

    return variants


def craft_search_query(state: FieldAssistantState) -> dict:
    """Craft search query/queries optimized for child chunk matching.

    Skipped entirely when route has no chroma_embedding engine.

    First attempt: template from classify fields (no LLM call).
    Retry (retrieval_attempts >= 1): LLM generates 3 variant queries.

    Returns dict with: crafted_query (primary), crafted_queries (all variants on retry).
    """
    route = state.get("route")
    classify_result = state.get("classify_result")
    user_message = state.get("user_message", "")
    attempts = state.get("retrieval_attempts", 0)
    previous_query = state.get("crafted_query")
    is_sufficient = state.get("is_sufficient", False)
    ranked_results = state.get("ranked_results", [])

    # Skip if no embedding search needed
    if route is None or SearchEngineType.CHROMA_EMBEDDING not in route.engines:
        log.log_step(Step.CRAFT_QUERY, "skipped",
                     details={"reason": "No chroma_embedding in route"})
        fts_keywords = classify_result.keywords if classify_result else []
        fallback = CraftedQuery(
            embedding_query="",
            fts_keywords=fts_keywords,
            reasoning="Skipped: no embedding search in route",
        )
        return {"crafted_query": fallback, "crafted_queries": [fallback]}

    # --- RETRY PATH: generate 3 variants ---
    if attempts >= 1 and previous_query and previous_query.embedding_query:
        # Build failure reason
        kept_count = len(ranked_results)
        top_score = max((r.relevance_score for r in ranked_results), default=0)
        failure_reason = (
            f"reranker kept {kept_count} result(s), "
            f"highest relevance score was {top_score:.2f} (need 2+ above 0.5)"
        )

        prompt = RETRY_VARIANTS_PROMPT.format(
            previous_query=previous_query.embedding_query,
            failure_reason=failure_reason,
        )

        context_parts = [f"Original question: {user_message}"]
        if classify_result:
            if classify_result.crop:
                context_parts.append(f"Crop: {classify_result.crop}")
            if classify_result.disease_name:
                context_parts.append(f"Disease: {classify_result.disease_name}")

        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content="\n".join(context_parts)),
        ]

        with log.timed(Step.CRAFT_QUERY, "retry_variants") as t:
            try:
                llm = get_field_llm(temperature=0.5, num_predict=256, format="json")
                response = llm.invoke(messages)
                response_text = response.content if hasattr(response, "content") else str(response)
                fts_fallback = classify_result.keywords if classify_result else []
                variants = _parse_retry_variants(response_text, fts_fallback)
            except Exception as e:
                log.log_step(Step.CRAFT_QUERY, "retry_llm_error", level="ERROR",
                             details={"error": str(e)})
                variants = []

            t.set(details={
                "attempt": attempts,
                "variants_count": len(variants),
                "previous_query_preview": previous_query.embedding_query[:100],
            })

        # If we got variants, use the first as primary + all as list
        if variants:
            log.log_step(Step.CRAFT_QUERY, "retry_variants", details={
                "count": len(variants),
                "queries_preview": [v.embedding_query[:60] for v in variants],
            })
            return {
                "crafted_query": variants[0],
                "crafted_queries": variants,
            }

        # Fallback: reuse previous with minor modification
        fts_keywords = classify_result.keywords if classify_result else []
        modified = CraftedQuery(
            embedding_query=f"{user_message} {' '.join(fts_keywords)}",
            fts_keywords=fts_keywords,
            reasoning="Retry fallback: combined user message with classify keywords",
        )
        return {"crafted_query": modified, "crafted_queries": [modified]}

    # --- FIRST ATTEMPT: template from classify fields (no LLM) ---
    result = _template_query(user_message, classify_result)

    log.log_step(Step.CRAFT_QUERY, "template", details={
        "embedding_query_preview": result.embedding_query[:200],
        "fts_keywords": result.fts_keywords,
    })

    return {"crafted_query": result, "crafted_queries": [result]}
