from langchain_ollama import ChatOllama

from app.config import settings


def get_field_llm(temperature: float = 0.3) -> ChatOllama:
    """Gemma 4 E4B via Ollama — the offline field assistant LLM.

    Args:
        temperature: Sampling temperature. Lower = more deterministic.
            Classify/ReRank: 0.1, CraftQuery: 0.3, Generate: 0.4.
    """
    return ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=temperature,
    )
