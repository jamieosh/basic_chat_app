import pytest

from utils.prompt_manager import PromptTemplateManager


def test_system_prompt_renders_variables():
    manager = PromptTemplateManager(agent_name="openai")

    rendered = manager.get_system_prompt(
        "default",
        personality="calm and direct",
        additional_instructions="Use short answers.",
    )

    assert "calm and direct" in rendered
    assert "Use short answers." in rendered


def test_missing_prompt_raises_file_not_found():
    manager = PromptTemplateManager(agent_name="openai")

    with pytest.raises(FileNotFoundError):
        manager.get_system_prompt("does_not_exist")


def test_context_prompt_renders_variables():
    manager = PromptTemplateManager(agent_name="openai")

    rendered = manager.get_context_prompt(
        "default",
        domain_knowledge="Cats are mammals.",
        user_preferences="Short replies.",
    )

    assert "Cats are mammals." in rendered
    assert "Short replies." in rendered


def test_missing_context_prompt_raises_file_not_found():
    manager = PromptTemplateManager(agent_name="openai")

    with pytest.raises(FileNotFoundError):
        manager.get_context_prompt("does_not_exist")


def test_missing_templates_directory_raises_file_not_found(tmp_path):
    missing_dir = tmp_path / "missing_templates"

    with pytest.raises(FileNotFoundError, match="Templates directory does not exist"):
        PromptTemplateManager(agent_name="openai", templates_dir=str(missing_dir))


def test_missing_agent_templates_directory_raises_file_not_found(tmp_path):
    templates_dir = tmp_path / "templates_prompts"
    templates_dir.mkdir()
    expected_agent_dir = templates_dir / "openai"

    with pytest.raises(
        FileNotFoundError,
        match="Templates directory for agent type 'openai' does not exist",
    ) as exc_info:
        PromptTemplateManager(agent_name="openai", templates_dir=str(templates_dir))

    assert str(expected_agent_dir) in str(exc_info.value)
