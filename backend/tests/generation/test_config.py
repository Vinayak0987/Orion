"""Tests for F63 - environment configuration.

The empty-variable case has its own test because it cost real debugging time: a
correctly configured SERPER_API_KEY in .env was being shadowed by an empty
SERPER_API_KEY exported in the environment, and /health reported the API as
unconfigured with no indication why.
"""

from __future__ import annotations

import pytest

from app.generation.config import Settings


def write_env(tmp_path, **values: str):
    path = tmp_path / ".env"
    path.write_text("\n".join(f"{k}={v}" for k, v in values.items()), encoding="utf-8")
    return str(path)


# =============================================================================
# Empty environment variables must not shadow .env
# =============================================================================


def test_empty_env_var_does_not_shadow_dotenv(tmp_path, monkeypatch) -> None:
    env_file = write_env(tmp_path, SERPER_API_KEY="real-key-from-dotenv")
    monkeypatch.setenv("SERPER_API_KEY", "")  # e.g. an unset CI secret

    settings = Settings(_env_file=env_file)

    assert settings.serper_api_key == "real-key-from-dotenv"
    assert settings.serper_available is True


def test_whitespace_only_env_var_does_not_shadow_dotenv(tmp_path, monkeypatch) -> None:
    env_file = write_env(tmp_path, GROQ_API_KEY="real-groq-key")
    monkeypatch.setenv("GROQ_API_KEY", "   ")

    assert Settings(_env_file=env_file).groq_api_key == "real-groq-key"


def test_non_empty_env_var_still_overrides_dotenv(tmp_path, monkeypatch) -> None:
    """Genuine overrides must keep working - this is how Docker Compose injects."""
    env_file = write_env(tmp_path, GEMINI_API_KEY="from-dotenv")
    monkeypatch.setenv("GEMINI_API_KEY", "from-environment")

    assert Settings(_env_file=env_file).gemini_api_key == "from-environment"


def test_numeric_env_var_override(tmp_path, monkeypatch) -> None:
    env_file = write_env(tmp_path, GENERATION_TIMEOUT_SECONDS="600")
    monkeypatch.setenv("GENERATION_TIMEOUT_SECONDS", "900")

    assert Settings(_env_file=env_file).generation_timeout_seconds == 900


def test_empty_numeric_env_var_falls_back_to_dotenv(tmp_path, monkeypatch) -> None:
    env_file = write_env(tmp_path, GENERATION_TIMEOUT_SECONDS="600")
    monkeypatch.setenv("GENERATION_TIMEOUT_SECONDS", "")

    assert Settings(_env_file=env_file).generation_timeout_seconds == 600


# =============================================================================
# Defaults and availability flags
# =============================================================================


def test_boots_with_no_configuration_at_all(tmp_path, monkeypatch) -> None:
    """The zero-cost guarantee: no keys, no .env, still a valid config."""
    for name in (
        "GROQ_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_PLACES_API_KEY",
        "SERPER_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = Settings(_env_file=str(tmp_path / "missing.env"))

    assert settings.groq_available is False
    assert settings.gemini_available is False
    assert settings.places_available is False
    assert settings.serper_available is False
    assert settings.ollama_base_url  # local fallback always configured


def test_feature_flag_disables_api_even_with_key(tmp_path, monkeypatch) -> None:
    """ENABLE_*_API=false is how the RQ3 ablation arm turns grounding off."""
    env_file = write_env(
        tmp_path, GOOGLE_PLACES_API_KEY="present", ENABLE_PLACES_API="false"
    )
    monkeypatch.delenv("GOOGLE_PLACES_API_KEY", raising=False)
    monkeypatch.delenv("ENABLE_PLACES_API", raising=False)

    settings = Settings(_env_file=env_file)

    assert settings.google_places_api_key == "present"
    assert settings.places_available is False


@pytest.mark.parametrize(
    ("key_name", "expected_fragment"),
    [
        ("GROQ_API_KEY", "GROQ_API_KEY missing"),
        ("GEMINI_API_KEY", "GEMINI_API_KEY missing"),
        ("GOOGLE_PLACES_API_KEY", "GOOGLE_PLACES_API_KEY missing"),
        ("SERPER_API_KEY", "market research"),
    ],
)
def test_warnings_name_the_degraded_capability(
    tmp_path, monkeypatch, key_name: str, expected_fragment: str
) -> None:
    """/health must say what is degraded, not just that a key is absent."""
    for name in (
        "GROQ_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_PLACES_API_KEY",
        "SERPER_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)

    warnings = Settings(_env_file=str(tmp_path / "missing.env")).warnings()
    assert any(expected_fragment in w for w in warnings)


def test_no_warnings_when_everything_configured(tmp_path, monkeypatch) -> None:
    env_file = write_env(
        tmp_path,
        GROQ_API_KEY="a",
        GEMINI_API_KEY="b",
        GOOGLE_PLACES_API_KEY="c",
        SERPER_API_KEY="d",
    )
    for name in (
        "GROQ_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_PLACES_API_KEY",
        "SERPER_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)

    assert Settings(_env_file=env_file).warnings() == []


def test_sqlite_file_creates_parent_directory(tmp_path, monkeypatch) -> None:
    target = tmp_path / "nested" / "deeper" / "mabgp.db"
    env_file = write_env(tmp_path, SQLITE_PATH=str(target))
    monkeypatch.delenv("SQLITE_PATH", raising=False)

    resolved = Settings(_env_file=env_file).sqlite_file

    assert resolved.parent.exists()
    assert resolved.name == "mabgp.db"
