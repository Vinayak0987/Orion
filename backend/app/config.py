"""F63 - Environment Configuration.

Single source of truth for all settings. Loaded once at import time.
Never read os.environ directly anywhere else in the codebase.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


class NonEmptyEnvSettingsSource(EnvSettingsSource):
    """Environment-variable source that ignores variables set to an empty string.

    By default pydantic-settings ranks OS environment above the .env file, so a
    variable exported as `GROQ_API_KEY=` silently shadows a real key configured
    in .env and the provider is reported as unavailable with no explanation.

    That happens easily in practice: a `docker-compose.yml` `environment:` block
    listing a key with no value, a CI runner that exports every declared secret
    whether or not it is populated, or a shell that sourced an older .env.

    Treating empty as "not set" keeps genuine overrides working while letting the
    .env file supply anything the environment left blank.
    """

    def __call__(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in super().__call__().items()
            if not (isinstance(value, str) and value.strip() == "")
        }


class Settings(BaseSettings):
    """All MABGP settings. Every field has a safe default so the app boots
    without a .env file (it will fall back to Ollama-only, no external APIs)."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Same precedence as the default, but empty env vars no longer shadow .env."""
        return (
            init_settings,
            NonEmptyEnvSettingsSource(settings_cls),
            dotenv_settings,
            file_secret_settings,
        )

    # --- LLM providers -------------------------------------------------------
    groq_api_key: str = ""
    gemini_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"

    # --- Model selection -----------------------------------------------------
    groq_model_fast: str = "llama-3.1-8b-instant"
    groq_model_reasoning: str = "llama-3.3-70b-versatile"

    # Gemini 1.5 Flash (named in the original project spec) was retired by
    # Google and returns 404 for new API keys; 2.5-flash is closed to new users.
    # These are the current stable equivalents on the v1 endpoint.
    #   gemini_model          STRUCTURED tier - intent extraction (F2).
    #                         flash-lite answers the intent prompt in ~63 tokens
    #                         against ~394 for full flash, which matters against
    #                         a daily token budget.
    #   gemini_baseline_model F53 single-LLM baseline - needs the stronger model
    #                         so RQ1 compares against a fair opponent.
    gemini_model: str = "gemini-3.5-flash-lite"
    gemini_baseline_model: str = "gemini-3.6-flash"
    gemini_api_version: str = "v1"

    # --- Free-tier rate limits (used by the fallback chain, F9) --------------
    groq_daily_request_limit: int = 14_400
    gemini_requests_per_minute: int = 15
    gemini_daily_token_limit: int = 1_000_000

    # --- External data APIs --------------------------------------------------
    google_places_api_key: str = ""
    serper_api_key: str = ""

    # --- Storage -------------------------------------------------------------
    sqlite_path: str = "./data/mabgp.db"
    # "local" uses chromadb.PersistentClient against chroma_path - no server and
    # no Docker needed, which keeps the evaluation sweep reproducible on a bare
    # Python install. "server" targets the docker-compose chromadb service.
    chroma_mode: str = "local"
    chroma_path: str = "./data/chroma"
    chroma_host: str = "localhost"
    chroma_port: int = 8000

    # --- User / website data layer (MongoDB Atlas) ---------------------------
    # DELIBERATELY SEPARATE from the agent data stores above. SQLite (mabgp.db)
    # and ChromaDB hold agent/generation/operating data; user accounts and other
    # application data live in MongoDB so their schema can evolve independently.
    #
    # MONGODB_URI is the full Atlas connection string (mongodb+srv://...), read
    # from .env - never hardcoded. MONGODB_USERNAME / MONGODB_PASSWORD are read
    # too for setups whose URI carries <user>/<pass> placeholders; if the URI
    # already embeds credentials they are simply unused.
    mongodb_uri: str = ""
    mongodb_username: str = ""
    mongodb_password: str = ""
    mongo_db_name: str = "orion_app"

    # --- Authentication (JWT) ------------------------------------------------
    # jwt_secret signs access + refresh tokens. It has a throwaway dev default so
    # the app boots without config, but warnings() flags it when running outside
    # development - a shared/default secret in production lets anyone mint tokens.
    jwt_secret: str = "dev-insecure-change-me"
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30
    # Name of the httpOnly cookie that carries the refresh token.
    refresh_cookie_name: str = "orion_refresh"
    # Set true behind HTTPS so the refresh cookie is only sent over TLS.
    cookie_secure: bool = False

    # --- Runtime -------------------------------------------------------------
    app_env: str = "development"
    log_level: str = "INFO"
    generation_timeout_seconds: int = 120

    # --- Feature flags -------------------------------------------------------
    enable_places_api: bool = True
    # OpenStreetMap (Overpass + Nominatim) needs no key and no billing account,
    # so competitor grounding works out of the box. Google Places takes over
    # automatically when GOOGLE_PLACES_API_KEY is set.
    enable_overpass: bool = True
    enable_serper_api: bool = True
    enable_chroma_cache: bool = True
    enable_dynamic_routing: bool = True

    # --- Derived helpers -----------------------------------------------------
    @property
    def groq_available(self) -> bool:
        return bool(self.groq_api_key.strip())

    @property
    def gemini_available(self) -> bool:
        return bool(self.gemini_api_key.strip())

    @property
    def places_available(self) -> bool:
        return self.enable_places_api and bool(self.google_places_api_key.strip())

    @property
    def serper_available(self) -> bool:
        return self.enable_serper_api and bool(self.serper_api_key.strip())

    @property
    def sqlite_file(self) -> Path:
        path = Path(self.sqlite_path).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def mongo_available(self) -> bool:
        return bool(self.mongodb_uri.strip())

    @property
    def refresh_cookie_secure(self) -> bool:
        """Whether to mark the refresh cookie `Secure` (TLS-only).

        In development the app is served over plain http on localhost, where a
        Secure cookie is silently dropped by the browser — which would break the
        login/refresh flow entirely. So Secure is forced off in development
        regardless of COOKIE_SECURE, and honoured everywhere else. Set
        APP_ENV=production (and serve over HTTPS) to get a Secure cookie.
        """
        if self.app_env == "development":
            return False
        return self.cookie_secure

    def warnings(self) -> list[str]:
        """Non-fatal configuration warnings surfaced on /health (F64)."""
        issues: list[str] = []
        if not self.groq_available:
            issues.append("GROQ_API_KEY missing - Groq provider disabled")
        if not self.gemini_available:
            issues.append("GEMINI_API_KEY missing - Gemini provider disabled")
        if not self.places_available:
            fallback = (
                "falling back to OpenStreetMap, which has sparser Indian "
                "small-business coverage and no ratings"
                if self.enable_overpass
                else "competitor discovery (F38) will be LLM-only"
            )
            issues.append(f"GOOGLE_PLACES_API_KEY missing - {fallback}; weakens RQ3")
        if not self.serper_available:
            issues.append(
                "SERPER_API_KEY missing - market research (F39) will fall back to LLM-only"
            )
        if not self.mongo_available:
            issues.append(
                "MONGODB_URI missing - authentication / user data layer disabled"
            )
        if self.app_env != "development" and self.jwt_secret == "dev-insecure-change-me":
            issues.append(
                "JWT_SECRET is the insecure development default - set a strong secret "
                "outside development or anyone can forge auth tokens"
            )
        return issues


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor. Import this, not Settings directly."""
    return Settings()


settings = get_settings()
