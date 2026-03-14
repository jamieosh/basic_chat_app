from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class DiagnosticCheck:
    name: str
    ok: bool
    detail: str

    def as_readiness_item(self) -> dict[str, str]:
        return {
            "name": self.name,
            "status": "ok" if self.ok else "failed",
            "detail": self.detail,
        }


class StartupDiagnosticsError(RuntimeError):
    """Raised when required startup diagnostics fail."""

    def __init__(self, failures: list[DiagnosticCheck]):
        self.failures = failures
        summary = "; ".join(f"{failure.name}: {failure.detail}" for failure in failures)
        super().__init__(f"Startup diagnostics failed: {summary}")


REQUIRED_STARTUP_PATHS: list[tuple[str, Path, str]] = [
    (
        "templates_dir",
        PROJECT_ROOT / "templates",
        "Restore the templates directory in the project root.",
    ),
    (
        "openai_prompts_dir",
        PROJECT_ROOT / "templates/prompts/openai",
        "Restore the OpenAI prompt templates directory.",
    ),
    (
        "system_prompt_template",
        PROJECT_ROOT / "templates/prompts/openai/system_default.j2",
        "Restore templates/prompts/openai/system_default.j2 or update the configured prompt name.",
    ),
    (
        "static_dir",
        PROJECT_ROOT / "static",
        "Restore the static assets directory in the project root.",
    ),
]


def collect_startup_checks() -> list[DiagnosticCheck]:
    checks = [
        _check_required_env_var(
            "OPENAI_API_KEY",
            remediation="Set OPENAI_API_KEY in .env or the process environment before startup.",
        )
    ]

    for name, path, remediation in REQUIRED_STARTUP_PATHS:
        checks.append(_check_required_path(name, path, remediation=remediation))

    return checks


def raise_for_failed_startup_checks(checks: list[DiagnosticCheck]) -> None:
    failures = [check for check in checks if not check.ok]
    if failures:
        raise StartupDiagnosticsError(failures)


def build_readiness_checks(*, startup_complete: bool, agent_initialized: bool) -> list[DiagnosticCheck]:
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
            name="agent_initialized",
            ok=agent_initialized,
            detail=(
                "Chat agent is initialized."
                if agent_initialized
                else "Chat agent is not available to process messages."
            ),
        ),
    ]
    return checks


def build_readiness_payload(*, startup_complete: bool, agent_initialized: bool) -> tuple[int, dict[str, object]]:
    checks = build_readiness_checks(
        startup_complete=startup_complete,
        agent_initialized=agent_initialized,
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


def _check_required_env_var(name: str, *, remediation: str) -> DiagnosticCheck:
    import os

    value = os.getenv(name)
    if value and value.strip():
        return DiagnosticCheck(name=name, ok=True, detail=f"Environment variable {name} is set.")

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
