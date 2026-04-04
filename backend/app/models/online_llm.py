from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import settings


def get_planner_llm() -> ChatGoogleGenerativeAI:
    """Gemma 4 31B — used for mission planning and knowledge compilation."""
    return ChatGoogleGenerativeAI(
        model=settings.online_model_large,
        google_api_key=settings.google_ai_studio_api_key,
        temperature=0.3,
    )


def get_research_llm() -> ChatGoogleGenerativeAI:
    """Gemma 4 26B MoE — used for parallel research agents."""
    return ChatGoogleGenerativeAI(
        model=settings.online_model_research,
        google_api_key=settings.google_ai_studio_api_key,
        temperature=0.4,
    )
