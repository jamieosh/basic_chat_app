import pytest

from utils.settings import get_settings


def test_get_settings_defaults_match_no_auth_baseline(monkeypatch):
    for name in (
        "OPENAI_MODEL",
        "OPENAI_PROMPT_NAME",
        "OPENAI_TEMPERATURE",
        "OPENAI_TIMEOUT_SECONDS",
        "CORS_ALLOWED_ORIGINS",
        "CORS_ALLOW_CREDENTIALS",
        "CORS_ALLOWED_METHODS",
        "CORS_ALLOWED_HEADERS",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = get_settings()

    assert settings.openai_model == "gpt-4o-mini"
    assert settings.openai_prompt_name == "default"
    assert settings.openai_temperature == 0.0
    assert settings.openai_timeout_seconds == 30.0
    assert settings.cors_allowed_origins == ["*"]
    assert settings.cors_allow_credentials is False
    assert settings.cors_allowed_methods == ["*"]
    assert settings.cors_allowed_headers == ["*"]


def test_get_settings_parses_env_driven_configuration(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
    monkeypatch.setenv("OPENAI_PROMPT_NAME", "portable")
    monkeypatch.setenv("OPENAI_TEMPERATURE", "0.7")
    monkeypatch.setenv("OPENAI_TIMEOUT_SECONDS", "12.5")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://example.com, https://internal.example")
    monkeypatch.setenv("CORS_ALLOW_CREDENTIALS", "true")
    monkeypatch.setenv("CORS_ALLOWED_METHODS", "GET,POST")
    monkeypatch.setenv("CORS_ALLOWED_HEADERS", "Content-Type,HX-Request")

    settings = get_settings()

    assert settings.openai_model == "gpt-4o"
    assert settings.openai_prompt_name == "portable"
    assert settings.openai_temperature == 0.7
    assert settings.openai_timeout_seconds == 12.5
    assert settings.cors_allowed_origins == ["https://example.com", "https://internal.example"]
    assert settings.cors_allow_credentials is True
    assert settings.cors_allowed_methods == ["GET", "POST"]
    assert settings.cors_allowed_headers == ["Content-Type", "HX-Request"]


def test_get_settings_rejects_wildcard_origin_with_credentials(monkeypatch):
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "*")
    monkeypatch.setenv("CORS_ALLOW_CREDENTIALS", "true")

    with pytest.raises(ValueError, match="CORS_ALLOW_CREDENTIALS=true requires explicit"):
        get_settings()
