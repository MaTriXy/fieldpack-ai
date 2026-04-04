from langchain_ollama import ChatOllama

from app.config import settings


def get_field_llm() -> ChatOllama:
    """Gemma 4 E4B via Ollama — the offline field assistant LLM."""
    return ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=0.3,
    )
