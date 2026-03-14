from pathlib import Path

from utils import diagnostics
from utils.settings import RuntimeSettings


def test_collect_startup_checks_reports_missing_openai_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(
        diagnostics,
        "get_required_startup_paths",
        lambda _prompt_name: [
            (
                "system_prompt_template",
                Path("templates/prompts/openai/system_default.j2"),
                "Restore templates/prompts/openai/system_default.j2 or update the configured prompt name.",
            )
        ],
    )

    checks = diagnostics.collect_startup_checks(
        RuntimeSettings(
            openai_api_key=None,
            openai_model="gpt-4o-mini",
            openai_prompt_name="default",
            openai_temperature=0.0,
            openai_timeout_seconds=30.0,
            cors_allowed_origins=["*"],
            cors_allow_credentials=False,
            cors_allowed_methods=["*"],
            cors_allowed_headers=["*"],
        )
    )

    assert checks[0].name == "OPENAI_API_KEY"
    assert checks[0].ok is False
    assert "Set OPENAI_API_KEY in .env or the process environment before startup." in checks[0].detail


def test_collect_startup_checks_uses_configured_prompt_name(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    checks = diagnostics.collect_startup_checks(
        RuntimeSettings(
            openai_api_key="test-key",
            openai_model="gpt-4o-mini",
            openai_prompt_name="portable_baseline",
            openai_temperature=0.0,
            openai_timeout_seconds=30.0,
            cors_allowed_origins=["*"],
            cors_allow_credentials=False,
            cors_allowed_methods=["*"],
            cors_allowed_headers=["*"],
        )
    )

    prompt_check = next(check for check in checks if check.name == "system_prompt_template")
    assert prompt_check.ok is False
    assert "system_portable_baseline.j2" in prompt_check.detail


def test_build_readiness_payload_reports_failed_checks():
    status_code, payload = diagnostics.build_readiness_payload(
        startup_complete=False,
        agent_initialized=False,
    )

    assert status_code == 503
    assert payload == {
        "status": "not_ready",
        "checks": [
            {
                "name": "startup_completed",
                "status": "failed",
                "detail": "Application startup has not completed successfully.",
            },
            {
                "name": "agent_initialized",
                "status": "failed",
                "detail": "Chat agent is not available to process messages.",
            },
        ],
        "failed_checks": [
            {
                "name": "startup_completed",
                "status": "failed",
                "detail": "Application startup has not completed successfully.",
            },
            {
                "name": "agent_initialized",
                "status": "failed",
                "detail": "Chat agent is not available to process messages.",
            },
        ],
    }
