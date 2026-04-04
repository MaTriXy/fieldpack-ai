"""Node 3: CRAFT SEARCH QUERY (LLM call #2).

Generates a natural language embedding query matching child chunk style,
plus FTS keywords for keyword search. Only fires when chroma_embedding
is in the route engines.

NL + smart parsing approach (no structured output).
"""

import json
import re

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.models import CraftedQuery, SearchEngineType
from app.agents.state import FieldAssistantState
from app.logger import Step, pipeline_logger as log
from app.models.offline_llm import get_field_llm


CRAFT_QUERY_SYSTEM_PROMPT = """You help write search queries for an agricultural knowledge base about crops and diseases in Casamance, Senegal.

Given a user question, write:
1. A search query (under 50 words) that a farmer might use to describe the situation. Use simple, visual, practical language.
2. A list of 3-5 keywords for exact text search.

Output JSON:
{"embedding_query": "your search query here", "fts_keywords": ["keyword1", "keyword2", "keyword3"], "reasoning": "brief explanation"}

Focus on: crop names, visual symptoms, treatment materials, local conditions."""

FEW_SHOT_EXAMPLES = [
    {
        "user": "My cassava leaves have yellow patches and they are curling up",
        "output": {
            "embedding_query": "cassava plant sick leaves yellow patches curling edges mosaic pattern young leaves affected wilting",
            "fts_keywords": ["cassava", "mosaic", "yellow", "curl", "leaves"],
            "reasoning": "Yellow patches and curling on cassava suggest mosaic disease. Query uses farmer-style descriptions.",
        },
    },
    {
        "user": "How do I treat rice blast organically?",
        "output": {
            "embedding_query": "rice blast treatment organic local materials neem copper fungicide spray application method Casamance",
            "fts_keywords": ["rice", "blast", "organic", "treatment", "neem"],
            "reasoning": "Searching for organic treatment methods for rice blast using locally available materials.",
        },
    },
]


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


def craft_search_query(state: FieldAssistantState) -> dict:
    """Craft a search query optimized for child chunk matching.

    LLM call #2. Skipped entirely when route has no chroma_embedding engine.
    Generates both an embedding query and FTS keywords.

    Returns dict with: crafted_query.
    """
    route = state.get("route")
    classify_result = state.get("classify_result")
    user_message = state.get("user_message", "")

    # Skip if no embedding search needed
    if route is None or SearchEngineType.CHROMA_EMBEDDING not in route.engines:
        log.log_step(Step.CRAFT_QUERY, "skipped",
                     details={"reason": "No chroma_embedding in route"})
        # Fall back to classify keywords for FTS
        fts_keywords = classify_result.keywords if classify_result else []
        return {
            "crafted_query": CraftedQuery(
                embedding_query="",
                fts_keywords=fts_keywords,
                reasoning="Skipped: no embedding search in route",
            ),
        }

    # Build prompt
    messages = [SystemMessage(content=CRAFT_QUERY_SYSTEM_PROMPT)]

    for ex in FEW_SHOT_EXAMPLES:
        messages.append(HumanMessage(content=ex["user"]))
        messages.append(SystemMessage(content=json.dumps(ex["output"])))

    # Add context from classify
    context_parts = [user_message]
    if classify_result:
        if classify_result.crop:
            context_parts.append(f"Crop: {classify_result.crop}")
        if classify_result.disease_name:
            context_parts.append(f"Disease: {classify_result.disease_name}")
        if classify_result.keywords:
            context_parts.append(f"Keywords: {', '.join(classify_result.keywords)}")

    messages.append(HumanMessage(content="\n".join(context_parts)))

    with log.timed(Step.CRAFT_QUERY, "llm_call") as t:
        try:
            llm = get_field_llm(temperature=0.3)
            response = llm.invoke(messages)
            response_text = response.content if hasattr(response, "content") else str(response)
        except Exception as e:
            log.log_step(Step.CRAFT_QUERY, "llm_error", level="ERROR",
                         details={"error": str(e)})
            # Fallback: use user message as embedding query + classify keywords
            fts_keywords = classify_result.keywords if classify_result else []
            return {
                "crafted_query": CraftedQuery(
                    embedding_query=user_message,
                    fts_keywords=fts_keywords,
                    reasoning=f"LLM error fallback: {e}",
                ),
            }

        result = _parse_craft_response(response_text)
        t.set(details={
            "embedding_query_preview": result.embedding_query[:200],
            "fts_keywords": result.fts_keywords,
            "reasoning": result.reasoning[:200],
        })

    return {"crafted_query": result}
