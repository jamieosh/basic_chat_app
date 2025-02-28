import os
from jinja2 import Environment, FileSystemLoader
from utils.logging_config import get_logger

class PromptTemplateManager:
    """Manager for loading and rendering prompt templates"""
    
    def __init__(self, agent_name, templates_dir="templates/prompts"):
        self.templates_dir = templates_dir
        self.agent_name = agent_name
        self.logger = get_logger("prompt_manager")
        
        # Create templates directory if it doesn't exist
        os.makedirs(templates_dir, exist_ok=True)
        
        # Check if the required directories for this agent type exist
        agent_dir = os.path.join(templates_dir, agent_name)
        system_dir = os.path.join(agent_dir, "system")
        context_dir = os.path.join(agent_dir, "context")
        
        if not os.path.exists(agent_dir):
            error_msg = f"Templates directory for agent type '{agent_name}' does not exist: {agent_dir}"
            self.logger.critical(error_msg)
            raise FileNotFoundError(error_msg)
            
        for prompt_dir in [system_dir, context_dir]:
            if not os.path.exists(prompt_dir):
                error_msg = f"Required prompt directory does not exist: {prompt_dir}"
                self.logger.critical(error_msg)
                raise FileNotFoundError(error_msg)
        
        # Initialize Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(os.path.dirname(templates_dir)),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        self.logger.info("PromptTemplateManager initialized for agent type '%s' with templates directory: %s", 
                         agent_name, templates_dir)
    
    def render_template(self, template_path, **variables):
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
            template = self.env.get_template(template_path)
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
        template_path = f"prompts/{self.agent_name}/system/{prompt_name}.j2"
        try:
            return self.render_template(template_path, **variables)
        except Exception as e:
            self.logger.critical(
                "System prompt %s not found for %s: %s",
                prompt_name, self.agent_name, str(e)
            )
            raise FileNotFoundError(f"System prompt '{prompt_name}' not found for agent type '{self.agent_name}'")
    
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
        template_path = f"prompts/{self.agent_name}/context/{prompt_name}.j2"
        try:
            return self.render_template(template_path, **variables)
        except Exception as e:
            self.logger.critical(
                "Context prompt %s not found for %s: %s",
                prompt_name, self.agent_name, str(e)
            )
            raise FileNotFoundError(f"Context prompt '{prompt_name}' not found for agent type '{self.agent_name}'")
    