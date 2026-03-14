import logging

from utils import logging_config


def test_parse_component_levels_strips_whitespace_and_ignores_invalid_entries():
    parsed = logging_config._parse_component_levels(
        " api = debug , invalid_entry , agent.openai = WARNING , other=notalevel "
    )

    assert parsed == {
        "api": logging.DEBUG,
        "agent.openai": logging.WARNING,
    }


def test_init_logging_uses_normalized_env_values(monkeypatch):
    captured = {}

    def fake_setup_logging(**kwargs):
        captured.update(kwargs)

    monkeypatch.setenv("LOG_LEVEL", " debug ")
    monkeypatch.setenv("COMPONENT_LOG_LEVELS", " api = warning , agent.openai = ERROR ")
    monkeypatch.setenv("LOG_TO_FILE", "TrUe")
    monkeypatch.setenv("LOG_DIR", "custom-logs")
    monkeypatch.setenv("APP_NAME", "chat-app")
    monkeypatch.setattr(logging_config, "setup_logging", fake_setup_logging)

    logging_config.init_logging()

    assert captured == {
        "default_level": logging.DEBUG,
        "log_to_file": True,
        "log_dir": "custom-logs",
        "app_name": "chat-app",
        "component_levels": {
            "api": logging.WARNING,
            "agent.openai": logging.ERROR,
        },
    }
