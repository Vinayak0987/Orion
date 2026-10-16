"""Orion v2 — Environment Configuration.

Single source of truth for all settings. Loaded once at import time.
Never read os.environ directly anywhere else in the codebase.

This is the fresh mission-engine backend. The legacy backend/ tree is kept as
reference only; nothing here imports from it.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All Orion v2 settings. Every field has a safe default so the app boots
    without a .env file (falls back to Ollama-only, no external tools)."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- LLM providers -------------------------------------------------------
    groq_api_key: str = ""
    gemini_api_key: str = ""
    openai_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    # Second local model tried if the primary Ollama model errors.
    ollama_model_fallback: str = ""

    # --- Model selection -----------------------------------------------------
    groq_model_fast: str = "llama-3.1-8b-instant"
    groq_model_reasoning: str = "llama-3.3-70b-versatile"
    gemini_model_fast: str = "gemini-2.0-flash-lite"
    gemini_model_reasoning: str = "gemini-2.0-flash"
    openai_model: str = "gpt-4o-mini"

    # --- Free-tier rate limits ----------------------------------------------
    groq_daily_request_limit: int = 14_400
    gemini_requests_per_minute: int = 15
    gemini_daily_token_limit: int = 1_000_000

    # --- Tool API keys -------------------------------------------------------
    serper_api_key: str = ""
    google_places_api_key: str = ""

    # --- File storage (Cloudinary) -------------------------------------------
    # Images and documents (avatars, uploaded knowledge files) are stored in
    # Cloudinary. Keys come from .env: CLOUD_NAME / CLOUD_API_KEY / CLOUD_API_SECRET.
    cloud_name: str = ""
    cloud_api_key: str = ""
    cloud_api_secret: str = ""

    # --- Storage -------------------------------------------------------------
    sqlite_path: str = "./data/orion2.db"
    chroma_path: str = "./data/chroma2"

    # --- User / website data layer (MongoDB Atlas) ---------------------------
    # Separate from the agent stores (SQLite + ChromaDB). User accounts live in
    # MongoDB so the schema can evolve independently. Reached only via app.auth.
    mongodb_uri: str = ""
    mongo_db_name: str = "orion_app"

    # --- Authentication (JWT) ------------------------------------------------
    jwt_secret: str = "dev-insecure-change-me"
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30
    refresh_cookie_name: str = "orion_refresh"
    cookie_secure: bool = False

    # --- Encryption at rest --------------------------------------------------
    # Fernet key for encrypting user API keys in the database. If unset, a
    # deterministic dev key is derived from jwt_secret so the app still boots;
    # set a real ENCRYPTION_KEY (a urlsafe base64 32-byte key) outside dev.
    encryption_key: str = ""

    # --- Runtime -------------------------------------------------------------
    app_env: str = "development"
    log_level: str = "INFO"
    # A single task may not run longer than this (seconds).
    task_timeout_seconds: int = 120
    # A whole mission may not run longer than this (seconds).
    mission_timeout_seconds: int = 600
    # Planning phase (clarify + title + plan) must finish within this (seconds).
    planning_timeout_seconds: int = 60
    # Max ReAct loop steps per task before forcing a final answer.
    max_task_steps: int = 10

    # --- Derived helpers -----------------------------------------------------
    @property
    def groq_available(self) -> bool:
        return bool(self.groq_api_key.strip())

    @property
    def gemini_available(self) -> bool:
        return bool(self.gemini_api_key.strip())

    @property
    def openai_available(self) -> bool:
        return bool(self.openai_api_key.strip())

    @property
    def serper_available(self) -> bool:
        return bool(self.serper_api_key.strip())

    @property
    def cloudinary_available(self) -> bool:
        return bool(
            self.cloud_name.strip()
            and self.cloud_api_key.strip()
            and self.cloud_api_secret.strip()
        )

    @property
    def sqlite_file(self) -> Path:
        path = Path(self.sqlite_path).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def chroma_dir(self) -> Path:
        path = Path(self.chroma_path).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def mongo_available(self) -> bool:
        return bool(self.mongodb_uri.strip())

    @property
    def refresh_cookie_secure(self) -> bool:
        """Secure cookie is forced off in development (plain http on localhost
        would silently drop a Secure cookie and break the login/refresh flow)."""
        if self.app_env == "development":
            return False
        return self.cookie_secure


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor. Import this, not Settings directly."""
    return Settings()


settings = get_settings()
