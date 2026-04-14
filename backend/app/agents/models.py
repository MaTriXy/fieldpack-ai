"""Pydantic models for the 6-step retrieval pipeline.

These are the data contracts between every component in the field assistant.
Each model validates structured LLM output or internal pipeline state.
"""

from enum import StrEnum

from pydantic import BaseModel, Field


def extract_text(response) -> str:
    """Extract text content from an LLM response.

    Handles both Ollama (content is str) and Google AI Studio
    (content is list of dicts with 'text' keys).
    """
    content = response.content if hasattr(response, "content") else str(response)
    if isinstance(content, list):
        return "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )
    return str(content)


# --- Enums ---

class IntentType(StrEnum):
    DIAGNOSE_DISEASE = "diagnose_disease"
    GET_TREATMENT = "get_treatment"
    FARMING_ADVICE = "farming_advice"
    IDENTIFY_IMAGE = "identify_image"
    LOG_OBSERVATION = "log_observation"
    GENERAL_QUESTION = "general_question"
    FOLLOW_UP = "follow_up"


class SearchEngineType(StrEnum):
    CHROMA_EMBEDDING = "chroma_embedding"
    SQLITE_FTS = "sqlite_fts"
    SQLITE_STRUCTURED = "sqlite_structured"


class ResultType(StrEnum):
    CHROMA = "chroma"
    FTS = "fts"
    STRUCTURED = "structured"


# --- LLM Call #1: Classify + Extract ---

class SeasonType(StrEnum):
    WET = "wet"
    DRY = "dry"
    ALL = "all"


class GrowthStage(StrEnum):
    NURSERY = "nursery"
    SEEDLING = "seedling"
    VEGETATIVE = "vegetative"
    FLOWERING = "flowering"
    GRAIN_FILL = "grain_fill"
    HARVEST = "harvest"
    POST_HARVEST = "post_harvest"
    PLANNING = "planning"


class TopicSubtype(StrEnum):
    PLANTING = "planting"
    IRRIGATION = "irrigation"
    SOIL = "soil"
    PEST = "pest"
    HARVEST = "harvest"
    POST_HARVEST = "post_harvest"
    FERTILIZATION = "fertilization"
    VARIETIES = "varieties"


class ClassifyExtractOutput(BaseModel):
    """Structured output from the classification LLM call."""
    intent: IntentType = IntentType.GENERAL_QUESTION
    crop: str | None = None
    disease_name: str | None = None
    keywords: list[str] = Field(default_factory=list)
    needs_image: bool = False
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    season: SeasonType | None = None
    growth_stage: GrowthStage | None = None
    topic_subtype: TopicSubtype | None = None


# --- Routing (Python, no LLM) ---

class SearchRoute(BaseModel):
    """Deterministic routing result — which engines, collections, tables to query."""
    engines: list[SearchEngineType] = Field(default_factory=list)
    collections: list[str] = Field(default_factory=list)
    tables: list[str] = Field(default_factory=list)
    metadata_filters: dict = Field(default_factory=dict)


# --- LLM Call #2: Craft Search Query ---

class CraftedQuery(BaseModel):
    """Search query crafted by the LLM to match child chunk style."""
    embedding_query: str = ""
    fts_keywords: list[str] = Field(default_factory=list)
    reasoning: str = ""


# --- Search Results ---

class SearchResult(BaseModel):
    """Unified result from any search engine."""
    content: str
    source: str = ""
    metadata: dict = Field(default_factory=dict)
    score: float = Field(default=0.0, ge=0.0)
    result_type: ResultType = ResultType.CHROMA
    parent_id: str | None = None
    parent_content: str | None = None


class ScoredResult(BaseModel):
    """Re-ranked result with relevance score."""
    content: str
    source: str = ""
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    parent_id: str | None = None
    parent_content: str | None = None
    metadata: dict = Field(default_factory=dict)


# --- LLM Call #3: Re-Rank ---

class ReRankOutput(BaseModel):
    """Structured output from the re-ranking LLM call."""
    ranked_results: list[ScoredResult] = Field(default_factory=list)
    is_sufficient: bool = False
    reasoning: str = ""


# --- LLM Call #4: Generate Answer ---

class GenerateAnswerInput(BaseModel):
    """Input assembled for the answer generation LLM call."""
    query: str
    context_chunks: list[str] = Field(default_factory=list)
    conversation_history: list[dict] = Field(default_factory=list)
    intent: IntentType = IntentType.GENERAL_QUESTION
