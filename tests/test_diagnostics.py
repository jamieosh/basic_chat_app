from pathlib import Path

from utils import diagnostics


def test_collect_startup_checks_reports_missing_openai_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(
        diagnostics,
        "REQUIRED_STARTUP_PATHS",
        [
            (
                "system_prompt_template",
                Path("templates/prompts/openai/system_default.j2"),
                "Restore templates/prompts/openai/system_default.j2 or update the configured prompt name.",
            )
        ],
    )

    checks = diagnostics.collect_startup_checks()

    assert checks[0].name == "OPENAI_API_KEY"
    assert checks[0].ok is False
    assert "Set OPENAI_API_KEY in .env or the process environment before startup." in checks[0].detail


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
