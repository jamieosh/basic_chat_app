from pathlib import Path

import pytest

from utils import diagnostics
from utils.diagnostics import DiagnosticCheck, StartupDiagnosticsError
from utils.settings import RuntimeSettings


def test_collect_startup_checks_reports_missing_openai_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(
        diagnostics,
        "get_required_startup_paths",
        lambda _harness_key, _prompt_name: [
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
            openai_model="gpt-5-mini",
            openai_prompt_name="default",
            openai_temperature=1.0,
            openai_timeout_seconds=30.0,
            chat_database_path=Path("data/chat.db"),
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
            openai_model="gpt-5-mini",
            openai_prompt_name="portable_baseline",
            openai_temperature=1.0,
            openai_timeout_seconds=30.0,
            chat_database_path=Path("data/chat.db"),
            cors_allowed_origins=["*"],
            cors_allow_credentials=False,
            cors_allowed_methods=["*"],
            cors_allowed_headers=["*"],
        )
    )

    prompt_check = next(check for check in checks if check.name == "system_prompt_template")
    assert prompt_check.ok is False
    assert "system_portable_baseline.j2" in prompt_check.detail


def test_collect_startup_checks_reports_missing_anthropic_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(
        diagnostics,
        "get_required_startup_paths",
        lambda _harness_key, _prompt_name: [
            (
                "system_prompt_template",
                Path("templates/prompts/anthropic/system_default.j2"),
                "Restore templates/prompts/anthropic/system_default.j2 or update the configured prompt name.",
            )
        ],
    )

    checks = diagnostics.collect_startup_checks(
        RuntimeSettings(
            openai_api_key=None,
            openai_model="gpt-5-mini",
            openai_prompt_name="default",
            openai_temperature=1.0,
            openai_timeout_seconds=30.0,
            chat_database_path=Path("data/chat.db"),
            cors_allowed_origins=["*"],
            cors_allow_credentials=False,
            cors_allowed_methods=["*"],
            cors_allowed_headers=["*"],
            default_harness_key="anthropic",
            anthropic_api_key=None,
        )
    )

    assert checks[0].name == "ANTHROPIC_API_KEY"
    assert checks[0].ok is False
    assert "Set ANTHROPIC_API_KEY in .env or the process environment before startup." in checks[0].detail


def test_diagnostic_check_as_readiness_item_maps_status():
    check = DiagnosticCheck(name="startup_completed", ok=False, detail="Not ready yet.")

    assert check.as_readiness_item() == {
        "name": "startup_completed",
        "status": "failed",
        "detail": "Not ready yet.",
    }


def test_diagnostic_check_as_readiness_item_includes_metadata():
    check = DiagnosticCheck(
        name="harness_initialized",
        ok=True,
        detail="Chat harness is initialized.",
        metadata={"harness_key": "openai", "provider_name": "openai"},
    )

    assert check.as_readiness_item() == {
        "name": "harness_initialized",
        "status": "ok",
        "detail": "Chat harness is initialized.",
        "metadata": {
            "harness_key": "openai",
            "provider_name": "openai",
        },
    }


def test_raise_for_failed_startup_checks_preserves_all_failures():
    checks = [
        DiagnosticCheck(name="OPENAI_API_KEY", ok=False, detail="Missing required environment variable."),
        DiagnosticCheck(name="static_dir", ok=False, detail="Missing required path."),
    ]

    with pytest.raises(StartupDiagnosticsError) as exc_info:
        diagnostics.raise_for_failed_startup_checks(checks)

    assert exc_info.value.failures == checks
    assert "OPENAI_API_KEY: Missing required environment variable." in str(exc_info.value)
    assert "static_dir: Missing required path." in str(exc_info.value)


def test_get_required_startup_paths_uses_configured_prompt_name():
    paths = diagnostics.get_required_startup_paths("openai", "portable")

    prompt_path = next(path for name, path, _remediation in paths if name == "system_prompt_template")
    assert prompt_path == diagnostics.PROJECT_ROOT / "templates/prompts/openai/system_portable.j2"


def test_get_required_startup_paths_supports_anthropic_prompt_tree():
    paths = diagnostics.get_required_startup_paths("anthropic", "portable")

    prompt_dir = next(path for name, path, _remediation in paths if name == "anthropic_prompts_dir")
    prompt_path = next(path for name, path, _remediation in paths if name == "system_prompt_template")
    assert prompt_dir == diagnostics.PROJECT_ROOT / "templates/prompts/anthropic"
    assert prompt_path == diagnostics.PROJECT_ROOT / "templates/prompts/anthropic/system_portable.j2"


def test_build_readiness_payload_reports_failed_checks():
    status_code, payload = diagnostics.build_readiness_payload(
        startup_complete=False,
        harness_initialized=False,
        storage_initialized=False,
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
                "name": "harness_initialized",
                "status": "failed",
                "detail": "Chat harness is not available to process messages.",
            },
            {
                "name": "storage_initialized",
                "status": "failed",
                "detail": "Chat storage is not available to process requests.",
            },
        ],
        "failed_checks": [
            {
                "name": "startup_completed",
                "status": "failed",
                "detail": "Application startup has not completed successfully.",
            },
            {
                "name": "harness_initialized",
                "status": "failed",
                "detail": "Chat harness is not available to process messages.",
            },
            {
                "name": "storage_initialized",
                "status": "failed",
                "detail": "Chat storage is not available to process requests.",
            },
        ],
    }


def test_build_readiness_payload_includes_harness_identity_metadata_when_ready():
    status_code, payload = diagnostics.build_readiness_payload(
        startup_complete=True,
        harness_initialized=True,
        storage_initialized=True,
        harness_metadata={
            "harness_key": "openai",
            "provider_name": "openai",
            "model": "gpt-5-mini",
        },
    )

    assert status_code == 200
    assert payload == {
        "status": "ok",
        "checks": [
            {
                "name": "startup_completed",
                "status": "ok",
                "detail": "Application startup completed.",
            },
            {
                "name": "harness_initialized",
                "status": "ok",
                "detail": "Chat harness is initialized.",
                "metadata": {
                    "harness_key": "openai",
                    "provider_name": "openai",
                    "model": "gpt-5-mini",
                },
            },
            {
                "name": "storage_initialized",
                "status": "ok",
                "detail": "Chat storage is initialized.",
            },
        ],
    }


def test_build_readiness_payload_preserves_non_default_harness_metadata():
    status_code, payload = diagnostics.build_readiness_payload(
        startup_complete=True,
        harness_initialized=True,
        storage_initialized=True,
        harness_metadata={
            "harness_key": "fake-alt",
            "harness_version": "v2",
            "provider_name": "fake-provider",
            "model": "Fake Alt Model",
        },
    )

    assert status_code == 200
    assert payload["checks"][1] == {
        "name": "harness_initialized",
        "status": "ok",
        "detail": "Chat harness is initialized.",
        "metadata": {
            "harness_key": "fake-alt",
            "harness_version": "v2",
            "provider_name": "fake-provider",
            "model": "Fake Alt Model",
        },
    }
