from dataclasses import dataclass, field
from pathlib import Path

from utils.settings import RuntimeSettings

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class DiagnosticCheck:
    name: str
    ok: bool
    detail: str
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", dict(self.metadata))

    def as_readiness_item(self) -> dict[str, object]:
        item: dict[str, object] = {
            "name": self.name,
            "status": "ok" if self.ok else "failed",
            "detail": self.detail,
        }
        if self.metadata:
            item["metadata"] = dict(self.metadata)
        return item


class StartupDiagnosticsError(RuntimeError):
    """Raised when required startup diagnostics fail."""

    def __init__(self, failures: list[DiagnosticCheck]):
        self.failures = failures
        summary = "; ".join(f"{failure.name}: {failure.detail}" for failure in failures)
        super().__init__(f"Startup diagnostics failed: {summary}")


def get_required_startup_paths(harness_key: str, prompt_name: str) -> list[tuple[str, Path, str]]:
    return [
        (
            "templates_dir",
            PROJECT_ROOT / "templates",
            "Restore the templates directory in the project root.",
        ),
        (
            f"{harness_key}_prompts_dir",
            PROJECT_ROOT / f"templates/prompts/{harness_key}",
            f"Restore the {harness_key} prompt templates directory.",
        ),
        (
            "system_prompt_template",
            PROJECT_ROOT / f"templates/prompts/{harness_key}/system_{prompt_name}.j2",
            (
                f"Restore templates/prompts/{harness_key}/system_{prompt_name}.j2 "
                f"or update {harness_key.upper()}_PROMPT_NAME."
            ),
        ),
        (
            "static_dir",
            PROJECT_ROOT / "static",
            "Restore the static assets directory in the project root.",
        ),
    ]


def collect_startup_checks(settings: RuntimeSettings) -> list[DiagnosticCheck]:
    configured_harness = _configured_startup_harness(settings)
    checks = [
        _check_required_path(
            "templates_dir",
            PROJECT_ROOT / "templates",
            remediation="Restore the templates directory in the project root.",
        ),
        _check_required_path(
            "static_dir",
            PROJECT_ROOT / "static",
            remediation="Restore the static assets directory in the project root.",
        ),
    ]

    if configured_harness is None:
        return checks

    checks.insert(
        0,
        _check_required_setting(
            configured_harness["api_key_name"],
            configured_harness["api_key_value"],
            detail_prefix="Environment variable",
            remediation=(
                f"Set {configured_harness['api_key_name']} in .env or the process environment "
                "before startup."
            ),
        ),
    )

    for name, path, remediation in get_required_startup_paths(
        configured_harness["harness_key"],
        configured_harness["prompt_name"],
    ):
        if name in {"templates_dir", "static_dir"}:
            continue
        checks.append(_check_required_path(name, path, remediation=remediation))

    return checks


def raise_for_failed_startup_checks(checks: list[DiagnosticCheck]) -> None:
    failures = [check for check in checks if not check.ok]
    if failures:
        raise StartupDiagnosticsError(failures)


def build_readiness_checks(
    *,
    startup_complete: bool,
    harness_initialized: bool,
    storage_initialized: bool,
    harness_metadata: dict[str, str] | None = None,
) -> list[DiagnosticCheck]:
    checks = [
        DiagnosticCheck(
            name="startup_completed",
            ok=startup_complete,
            detail=(
                "Application startup completed."
                if startup_complete
                else "Application startup has not completed successfully."
            ),
        ),
        DiagnosticCheck(
            name="harness_initialized",
            ok=harness_initialized,
            detail=(
                "Chat harness is initialized."
                if harness_initialized
                else "Chat harness is not available to process messages."
            ),
            metadata=(harness_metadata or {}) if harness_initialized else {},
        ),
        DiagnosticCheck(
            name="storage_initialized",
            ok=storage_initialized,
            detail=(
                "Chat storage is initialized."
                if storage_initialized
                else "Chat storage is not available to process requests."
            ),
        ),
    ]
    return checks


def build_readiness_payload(
    *,
    startup_complete: bool,
    harness_initialized: bool,
    storage_initialized: bool,
    harness_metadata: dict[str, str] | None = None,
) -> tuple[int, dict[str, object]]:
    checks = build_readiness_checks(
        startup_complete=startup_complete,
        harness_initialized=harness_initialized,
        storage_initialized=storage_initialized,
        harness_metadata=harness_metadata,
    )
    failures = [check for check in checks if not check.ok]
    payload: dict[str, object] = {
        "status": "ok" if not failures else "not_ready",
        "checks": [check.as_readiness_item() for check in checks],
    }
    if failures:
        payload["failed_checks"] = [check.as_readiness_item() for check in failures]
        return 503, payload
    return 200, payload


def _check_required_setting(
    name: str,
    value: str | None,
    *,
    detail_prefix: str,
    remediation: str,
) -> DiagnosticCheck:
    if value and value.strip():
        return DiagnosticCheck(name=name, ok=True, detail=f"{detail_prefix} {name} is set.")

    return DiagnosticCheck(
        name=name,
        ok=False,
        detail=f"Missing required environment variable {name}. {remediation}",
    )


def _check_required_path(name: str, path: Path, *, remediation: str) -> DiagnosticCheck:
    if path.exists():
        return DiagnosticCheck(name=name, ok=True, detail=f"Found required path: {path}.")

    return DiagnosticCheck(
        name=name,
        ok=False,
        detail=f"Missing required path: {path}. {remediation}",
    )


def _configured_startup_harness(settings: RuntimeSettings) -> dict[str, str | None] | None:
    if settings.default_harness_key == "openai":
        return {
            "harness_key": "openai",
            "api_key_name": "OPENAI_API_KEY",
            "api_key_value": settings.openai_api_key,
            "prompt_name": settings.openai_prompt_name,
        }
    if settings.default_harness_key == "anthropic":
        return {
            "harness_key": "anthropic",
            "api_key_name": "ANTHROPIC_API_KEY",
            "api_key_value": settings.anthropic_api_key,
            "prompt_name": settings.anthropic_prompt_name,
        }
    return None
