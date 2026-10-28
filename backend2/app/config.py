"""Orion v2 — Environment Configuration.

Single source of truth for all settings. Loaded once at import time.
Never read os.environ directly anywhere else in the codebase.

This is the fresh mission-engine backend. The legacy backend/ tree is kept as
reference only; nothing here imports from it.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
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
    # Additional free-tier OpenAI-compatible providers (robust fallback chain).
    nvidia_nim_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("nvidia_nim_api_key", "nvidia_api_key_first", "nvidia_api_key"),
    )
    nvidia_nim_api_key_second: str = Field(
        default="",
        validation_alias=AliasChoices("nvidia_nim_api_key_second", "nvidia_api_key_second"),
    )
    cerebras_api_key: str = ""
    openrouter_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    # Strong local model (good tool-calling, no rate limit) as the floor.
    ollama_model: str = "qwen2.5:7b-instruct"
    # Second local model tried if the primary Ollama model errors.
    ollama_model_fallback: str = "fredrezones55/qwen3.5-opus:4b"

    # --- Model selection -----------------------------------------------------
    groq_model_fast: str = "openai/gpt-oss-20b"
    groq_model_reasoning: str = "openai/gpt-oss-120b"
    gemini_model_fast: str = "gemini-flash-latest"
    gemini_model_reasoning: str = "gemini-pro-latest"
    openai_model: str = "gpt-4o-mini"
    # NVIDIA NIM (build.nvidia.com) — 10k req/day free, great tool-calling.
    # Nemotron 3.5 Bolt E4B — accessible on the free account + tool-capable.
    nvidia_nim_model_fast: str = "nvidia/nemotron-3.5-bolt-e4b"
    nvidia_nim_model_reasoning: str = "nvidia/nemotron-3.5-bolt-e4b"
    # Cerebras (cloud.cerebras.ai) — very fast.
    cerebras_model_fast: str = "llama-3.3-70b"
    cerebras_model_reasoning: str = "llama-3.3-70b"
    # OpenRouter (openrouter.ai) — current free model variants (tested working).
    openrouter_model_fast: str = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"
    openrouter_model_reasoning: str = "nvidia/nemotron-3-ultra-550b-a55b:free"

    # --- Free-tier rate limits ----------------------------------------------
    groq_daily_request_limit: int = 14_400
    gemini_requests_per_minute: int = 15
    gemini_daily_token_limit: int = 1_000_000

    # --- Tool API keys -------------------------------------------------------
    serper_api_key: str = ""
    google_places_api_key: str = ""
    # Google Picker API browser key (developerKey) for the real Drive picker UI.
    google_picker_api_key: str = ""

    # --- OAuth 2.0 integrations ----------------------------------------------
    # One OAuth app per provider (Orion's own). Each user authorizes their own
    # account through it. Unset providers simply show as "not configured".
    oauth_redirect_base: str = "http://localhost:8081"   # callbacks derive from this
    frontend_url: str = "http://localhost:5173"          # where to send the browser after callback
    oauth_google_client_id: str = ""
    oauth_google_client_secret: str = ""
    oauth_microsoft_client_id: str = ""
    oauth_microsoft_client_secret: str = ""
    oauth_microsoft_tenant: str = "common"
    oauth_slack_client_id: str = ""
    oauth_slack_client_secret: str = ""
    oauth_github_client_id: str = ""
    oauth_github_client_secret: str = ""
    oauth_notion_client_id: str = ""
    oauth_notion_client_secret: str = ""

    # --- File storage (Cloudinary) -------------------------------------------
    # Images and documents (avatars, uploaded knowledge files) are stored in
    # Cloudinary. Keys come from .env: CLOUD_NAME / CLOUD_API_KEY / CLOUD_API_SECRET.
    cloud_name: str = ""
    cloud_api_key: str = ""
    cloud_api_secret: str = ""

    # --- Storage -------------------------------------------------------------
    sqlite_path: str = "./data/orion2.db"
    chroma_path: str = "./data/chroma2"
    # Sandbox root for file/document built-in tools. All file paths an agent
    # passes are resolved INSIDE this directory — never outside it.
    workspace_path: str = "./data/workspace"
    # code_interpreter runs untrusted code in a subprocess. Off unless enabled.
    code_interpreter_enabled: bool = True
    code_interpreter_timeout_seconds: int = 25
    # stdio (local command) MCP servers spawn local processes — OFF by default
    # since launching an arbitrary command is local code execution.
    mcp_stdio_enabled: bool = False
    # Browser-automation action tool (Playwright). OFF by default — needs the
    # Chromium runtime installed and is high-blast-radius (drives real sites).
    browser_action_enabled: bool = False

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
    # A single task may not run longer than this (seconds). Delegated department
    # tasks (Head + specialists) legitimately need more time than one agent.
    task_timeout_seconds: int = 300
    # A whole mission may not run longer than this (seconds).
    mission_timeout_seconds: int = 1200
    # Planning phase (clarify + title + plan) must finish within this (seconds).
    planning_timeout_seconds: int = 90
    # Max ReAct loop steps per task before forcing a final answer. Kept low so a
    # specialist doesn't burn the whole delegation budget on tool rounds.
    max_task_steps: int = 5
    # Hierarchical delegation bounds: a Head delegates at most this many
    # specialists per task; depth caps head→specialist→subagent recursion.
    max_delegation_fanout: int = 2
    max_delegation_depth: int = 2

    # --- Derived helpers -----------------------------------------------------
    @property
    def groq_available(self) -> bool:
        return bool(self.groq_api_key.strip())

    @property
    def gemini_available(self) -> bool:
        return bool(self.gemini_api_key.strip())

    @property
    def nvidia_nim_available(self) -> bool:
        return bool(self.nvidia_nim_api_key.strip())

    @property
    def cerebras_available(self) -> bool:
        return bool(self.cerebras_api_key.strip())

    @property
    def openrouter_available(self) -> bool:
        return bool(self.openrouter_api_key.strip())

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
    def workspace_dir(self) -> Path:
        path = Path(self.workspace_path).expanduser().resolve()
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
