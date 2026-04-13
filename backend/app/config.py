from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Google AI Studio (Phase 1)
    google_ai_studio_api_key: str = ""
    online_model_large: str = "gemma-4-31b-it"
    online_model_research: str = "gemma-4-26b-a4b-it"

    # Ollama (Phase 2)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "fieldpack-assistant-lite"
    ollama_tunnel_token: str = ""  # Auth token for remote Ollama (Colab GPU tunnel)
    ollama_num_ctx: int = 4096
    ollama_keep_alive: int = -1
    ollama_timeout: int = 120
    ollama_num_gpu: int = -1  # -1 = auto, 0 = CPU-only (use 0 for Intel iGPU)

    # Field LLM provider: "ollama" for local, "google" for AI Studio API
    field_llm_provider: str = "ollama"
    field_llm_google_model: str = "gemma-4-31b-it"

    # Tavily (Phase 1 gap analysis)
    tavily_api_key: str = ""

    # Embeddings
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimensions: int = 384

    # Paths
    knowledge_pack_dir: Path = Path("../packs")
    upload_dir: Path = Path("../uploads")

    # Logging
    log_dir: Path = Path("../logs")
    log_level: str = "DEBUG"
    log_buffer_size: int = 500  # In-memory ring buffer entries

    # Demo mode — serves pre-computed responses for video recording
    demo_mode: bool = False  # Override with DEMO_MODE=true in .env
    demo_script_path: Path = Path("../demo/script.json")

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False  # Override with DEBUG=true in .env for local dev

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def logs_path(self) -> Path:
        path = Path(__file__).resolve().parent.parent / self.log_dir
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def packs_path(self) -> Path:
        path = Path(__file__).resolve().parent.parent / self.knowledge_pack_dir
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def uploads_path(self) -> Path:
        path = Path(__file__).resolve().parent.parent / self.upload_dir
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def data_path(self) -> Path:
        path = Path(__file__).resolve().parent.parent / "data"
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()
