import pytest

from utils import settings as settings_module
from utils.settings import get_settings, load_project_env


def test_get_settings_defaults_match_no_auth_baseline(monkeypatch):
    for name in (
        "OPENAI_MODEL",
        "OPENAI_PROMPT_NAME",
        "OPENAI_TEMPERATURE",
        "OPENAI_TIMEOUT_SECONDS",
        "ANTHROPIC_MODEL",
        "ANTHROPIC_PROMPT_NAME",
        "ANTHROPIC_TEMPERATURE",
        "ANTHROPIC_TIMEOUT_SECONDS",
        "ANTHROPIC_MAX_TOKENS",
        "CHAT_DATABASE_PATH",
        "CORS_ALLOWED_ORIGINS",
        "CORS_ALLOW_CREDENTIALS",
        "CORS_ALLOWED_METHODS",
        "CORS_ALLOWED_HEADERS",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = get_settings()

    assert settings.openai_model == "gpt-5-mini"
    assert settings.openai_prompt_name == "default"
    assert settings.openai_temperature == 1.0
    assert settings.openai_timeout_seconds == 30.0
    assert settings.anthropic_model == "claude-sonnet-4-20250514"
    assert settings.anthropic_prompt_name == "default"
    assert settings.anthropic_temperature == 1.0
    assert settings.anthropic_timeout_seconds == 30.0
    assert settings.anthropic_max_tokens == 1024
    assert settings.chat_database_path == settings_module.PROJECT_ROOT / "data/chat.db"
    assert settings.cors_allowed_origins == ["*"]
    assert settings.cors_allow_credentials is False
    assert settings.cors_allowed_methods == ["*"]
    assert settings.cors_allowed_headers == ["*"]
    assert settings.default_harness_key == "openai"


def test_get_settings_parses_env_driven_configuration(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
    monkeypatch.setenv("OPENAI_PROMPT_NAME", "portable")
    monkeypatch.setenv("OPENAI_TEMPERATURE", "0.7")
    monkeypatch.setenv("OPENAI_TIMEOUT_SECONDS", "12.5")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-3-7-sonnet-20250219")
    monkeypatch.setenv("ANTHROPIC_PROMPT_NAME", "portable")
    monkeypatch.setenv("ANTHROPIC_TEMPERATURE", "0.3")
    monkeypatch.setenv("ANTHROPIC_TIMEOUT_SECONDS", "18")
    monkeypatch.setenv("ANTHROPIC_MAX_TOKENS", "4096")
    monkeypatch.setenv("CHAT_DATABASE_PATH", "~/tmp/basic-chat-app.sqlite3")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://example.com, https://internal.example")
    monkeypatch.setenv("CORS_ALLOW_CREDENTIALS", "true")
    monkeypatch.setenv("CORS_ALLOWED_METHODS", "GET,POST")
    monkeypatch.setenv("CORS_ALLOWED_HEADERS", "Content-Type,HX-Request")
    monkeypatch.setenv("DEFAULT_CHAT_HARNESS_KEY", "openai")

    settings = get_settings()

    assert settings.openai_model == "gpt-4o"
    assert settings.openai_prompt_name == "portable"
    assert settings.openai_temperature == 0.7
    assert settings.openai_timeout_seconds == 12.5
    assert settings.anthropic_model == "claude-3-7-sonnet-20250219"
    assert settings.anthropic_prompt_name == "portable"
    assert settings.anthropic_temperature == 0.3
    assert settings.anthropic_timeout_seconds == 18
    assert settings.anthropic_max_tokens == 4096
    assert settings.chat_database_path == settings_module.Path("~/tmp/basic-chat-app.sqlite3").expanduser()
    assert settings.cors_allowed_origins == ["https://example.com", "https://internal.example"]
    assert settings.cors_allow_credentials is True
    assert settings.cors_allowed_methods == ["GET", "POST"]
    assert settings.cors_allowed_headers == ["Content-Type", "HX-Request"]
    assert settings.default_harness_key == "openai"


def test_get_settings_rejects_wildcard_origin_with_credentials(monkeypatch):
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "*")
    monkeypatch.setenv("CORS_ALLOW_CREDENTIALS", "true")

    with pytest.raises(ValueError, match="CORS_ALLOW_CREDENTIALS=true requires explicit"):
        get_settings()


def test_get_settings_rejects_invalid_temperature_value(monkeypatch):
    monkeypatch.setenv("OPENAI_TEMPERATURE", "not-a-number")

    with pytest.raises(ValueError, match="OPENAI_TEMPERATURE must be a valid number."):
        get_settings()


@pytest.mark.parametrize("value", ["-0.1", "2.1"], ids=["below_range", "above_range"])
def test_get_settings_rejects_out_of_range_temperature(monkeypatch, value):
    monkeypatch.setenv("OPENAI_TEMPERATURE", value)

    with pytest.raises(ValueError, match="OPENAI_TEMPERATURE must be between 0.0 and 2.0."):
        get_settings()


def test_get_settings_rejects_invalid_timeout_value(monkeypatch):
    monkeypatch.setenv("OPENAI_TIMEOUT_SECONDS", "later")

    with pytest.raises(ValueError, match="OPENAI_TIMEOUT_SECONDS must be a valid number."):
        get_settings()


def test_get_settings_rejects_invalid_anthropic_max_tokens(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_MAX_TOKENS", "many")

    with pytest.raises(ValueError, match="ANTHROPIC_MAX_TOKENS must be a valid integer."):
        get_settings()


@pytest.mark.parametrize("value", ["-0.1", "1.1"], ids=["below_range", "above_range"])
def test_get_settings_rejects_out_of_range_anthropic_temperature(monkeypatch, value):
    monkeypatch.setenv("ANTHROPIC_TEMPERATURE", value)

    with pytest.raises(ValueError, match="ANTHROPIC_TEMPERATURE must be between 0.0 and 1.0."):
        get_settings()


@pytest.mark.parametrize("value", ["0", "-1"], ids=["zero", "negative"])
def test_get_settings_rejects_non_positive_anthropic_timeout(monkeypatch, value):
    monkeypatch.setenv("ANTHROPIC_TIMEOUT_SECONDS", value)

    with pytest.raises(ValueError, match="ANTHROPIC_TIMEOUT_SECONDS must be greater than 0."):
        get_settings()


@pytest.mark.parametrize("value", ["0", "-1"], ids=["zero", "negative"])
def test_get_settings_rejects_non_positive_anthropic_max_tokens(monkeypatch, value):
    monkeypatch.setenv("ANTHROPIC_MAX_TOKENS", value)

    with pytest.raises(ValueError, match="ANTHROPIC_MAX_TOKENS must be greater than 0."):
        get_settings()


@pytest.mark.parametrize("value", ["0", "-1"], ids=["zero", "negative"])
def test_get_settings_rejects_non_positive_timeout(monkeypatch, value):
    monkeypatch.setenv("OPENAI_TIMEOUT_SECONDS", value)

    with pytest.raises(ValueError, match="OPENAI_TIMEOUT_SECONDS must be greater than 0."):
        get_settings()


def test_get_settings_rejects_database_directory_path(monkeypatch, tmp_path):
    monkeypatch.setenv("CHAT_DATABASE_PATH", str(tmp_path))

    with pytest.raises(ValueError, match="CHAT_DATABASE_PATH must point to a SQLite database file"):
        get_settings()


def test_get_settings_empty_csv_values_fall_back_to_defaults(monkeypatch):
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", " , ")
    monkeypatch.setenv("CORS_ALLOWED_METHODS", " , ")
    monkeypatch.setenv("CORS_ALLOWED_HEADERS", " , ")

    settings = get_settings()

    assert settings.cors_allowed_origins == ["*"]
    assert settings.cors_allowed_methods == ["*"]
    assert settings.cors_allowed_headers == ["*"]


@pytest.mark.parametrize("value", ["false", "0", "off"], ids=["false", "zero", "off"])
def test_get_settings_parses_falsey_credentials_values(monkeypatch, value):
    monkeypatch.setenv("CORS_ALLOW_CREDENTIALS", value)

    settings = get_settings()

    assert settings.cors_allow_credentials is False


def test_load_project_env_uses_project_root_env_file(monkeypatch):
    captured = {}

    def fake_load_dotenv(*, dotenv_path):
        captured["dotenv_path"] = dotenv_path
        return True

    monkeypatch.setattr(settings_module, "load_dotenv", fake_load_dotenv)

    result = load_project_env()

    assert result is True
    assert captured["dotenv_path"] == settings_module.DEFAULT_ENV_FILE
