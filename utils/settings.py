import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"


@dataclass(frozen=True)
class RuntimeSettings:
    openai_api_key: str | None
    openai_model: str
    openai_prompt_name: str
    openai_temperature: float
    openai_timeout_seconds: float
    cors_allowed_origins: list[str]
    cors_allow_credentials: bool
    cors_allowed_methods: list[str]
    cors_allowed_headers: list[str]

    def cors_middleware_kwargs(self) -> dict[str, object]:
        return {
            "allow_origins": self.cors_allowed_origins,
            "allow_credentials": self.cors_allow_credentials,
            "allow_methods": self.cors_allowed_methods,
            "allow_headers": self.cors_allowed_headers,
        }


def load_project_env(env_file: Path = DEFAULT_ENV_FILE) -> bool:
    return load_dotenv(dotenv_path=env_file)


def get_settings() -> RuntimeSettings:
    settings = RuntimeSettings(
        openai_api_key=_get_optional_env("OPENAI_API_KEY"),
        openai_model=_get_optional_env("OPENAI_MODEL") or "gpt-4o-mini",
        openai_prompt_name=_get_optional_env("OPENAI_PROMPT_NAME") or "default",
        openai_temperature=_get_float_env("OPENAI_TEMPERATURE", default=0.0),
        openai_timeout_seconds=_get_float_env("OPENAI_TIMEOUT_SECONDS", default=30.0),
        cors_allowed_origins=_get_csv_env("CORS_ALLOWED_ORIGINS", default=["*"]),
        cors_allow_credentials=_get_bool_env("CORS_ALLOW_CREDENTIALS", default=False),
        cors_allowed_methods=_get_csv_env("CORS_ALLOWED_METHODS", default=["*"]),
        cors_allowed_headers=_get_csv_env("CORS_ALLOWED_HEADERS", default=["*"]),
    )
    _validate_settings(settings)
    return settings


def _get_optional_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None

    normalized = value.strip()
    return normalized or None


def _get_bool_env(name: str, *, default: bool) -> bool:
    value = _get_optional_env(name)
    if value is None:
        return default

    return value.lower() in {"1", "true", "yes", "on"}


def _get_float_env(name: str, *, default: float) -> float:
    value = _get_optional_env(name)
    if value is None:
        return default

    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a valid number.") from exc


def _get_csv_env(name: str, *, default: list[str]) -> list[str]:
    value = _get_optional_env(name)
    if value is None:
        return list(default)

    items = [item.strip() for item in value.split(",") if item.strip()]
    return items or list(default)


def _validate_settings(settings: RuntimeSettings) -> None:
    if settings.cors_allow_credentials and "*" in settings.cors_allowed_origins:
        raise ValueError(
            "CORS_ALLOW_CREDENTIALS=true requires explicit CORS_ALLOWED_ORIGINS values instead of '*'."
        )

    if not 0.0 <= settings.openai_temperature <= 2.0:
        raise ValueError("OPENAI_TEMPERATURE must be between 0.0 and 2.0.")

    if settings.openai_timeout_seconds <= 0:
        raise ValueError("OPENAI_TIMEOUT_SECONDS must be greater than 0.")
