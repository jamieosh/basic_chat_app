from pathlib import Path

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from utils.logging_config import get_logger


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TEMPLATES_DIR = PROJECT_ROOT / "templates" / "prompts"


class PromptTemplateManager:
    """Manager for loading and rendering prompt templates"""

    def __init__(self, agent_name, templates_dir: str | Path | None = None):
        self.templates_dir = (
            Path(templates_dir)
            if templates_dir is not None
            else DEFAULT_TEMPLATES_DIR
        )
        self.agent_name = agent_name
        self.logger = get_logger("prompt_manager")

        # Check if the templates directory exists
        if not self.templates_dir.exists():
            error_msg = f"Templates directory does not exist: {self.templates_dir}"
            self.logger.critical(error_msg)
            raise FileNotFoundError(error_msg)
        else:
            self.logger.debug("prompt_manager.templates_dir_found path=%s", self.templates_dir)

        # Check if the required directories for this agent type exist
        agent_dir = self.templates_dir / agent_name
        if not agent_dir.exists():
            error_msg = f"Templates directory for agent type '{agent_name}' does not exist: {agent_dir}"
            self.logger.critical(error_msg)
            raise FileNotFoundError(error_msg)
        else:
            self.logger.debug("prompt_manager.agent_dir_found agent=%s path=%s", agent_name, agent_dir)

        # Initialize Jinja2 environment
        self.j2env = Environment(
            loader=FileSystemLoader(str(self.templates_dir.parent)),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        self.logger.debug(
            "prompt_manager.initialized agent=%s templates_dir=%s",
            agent_name,
            self.templates_dir,
        )

    def _render_template(self, template_path, **variables):
        """Render a template with the given variables

        Args:
            template_path: Path to the template relative to templates directory
            **variables: Variables to use in the template

        Returns:
            str: Rendered template

        Raises:
            FileNotFoundError: If the template doesn't exist
            Exception: For other template rendering errors
        """
        try:
            template = self.j2env.get_template(template_path)
            return template.render(**variables)
        except Exception as e:
            self.logger.error("Error rendering template %s: %s", template_path, str(e))
            raise

    def get_system_prompt(self, prompt_name="default", **variables):
        """Get a system prompt for the agent

        Args:
            prompt_name: Name of the prompt to use
            **variables: Variables to use in the template

        Returns:
            str: Rendered system prompt

        Raises:
            FileNotFoundError: If the system prompt template doesn't exist
            Exception: For other template rendering errors
        """
        template_path = f"prompts/{self.agent_name}/system_{prompt_name}.j2"
        try:
            return self._render_template(template_path, **variables)
        except TemplateNotFound as e:
            self.logger.critical(
                "System prompt %s not found for %s: %s",
                prompt_name, self.agent_name, str(e),
            )
            raise FileNotFoundError(
                f"System prompt '{prompt_name}' not found for agent type '{self.agent_name}'"
            ) from e

    def get_context_prompt(self, prompt_name="default", **variables):
        """Get a context prompt

        Args:
            prompt_name: Name of the prompt to use
            **variables: Variables to use in the template

        Returns:
            str: Rendered context prompt

        Raises:
            FileNotFoundError: If the context prompt template doesn't exist
            Exception: For other template rendering errors
        """
        template_path = f"prompts/{self.agent_name}/user_{prompt_name}.j2"
        try:
            return self._render_template(template_path, **variables)
        except TemplateNotFound as e:
            self.logger.critical(
                "Context prompt %s not found for %s: %s",
                prompt_name, self.agent_name, str(e),
            )
            raise FileNotFoundError(
                f"Context prompt '{prompt_name}' not found for agent type '{self.agent_name}'"
            ) from e

    def get_optional_context_prompt(self, prompt_name="default", **variables) -> str | None:
        """Return a rendered context prompt when present, otherwise None."""
        try:
            return self.get_context_prompt(prompt_name, **variables)
        except FileNotFoundError:
            return None
