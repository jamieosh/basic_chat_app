import openai
from openai.types.chat import ChatCompletionMessageParam
from pathlib import Path
from typing import Any
from collections.abc import Sequence

from .base_agent import BaseAgent, ConversationTurn
from utils.logging_config import get_logger
from utils.prompt_manager import PromptTemplateManager


class EmptyModelResponseError(RuntimeError):
    """Raised when the model response does not include text content."""


class OpenAIAgent(BaseAgent):
    """Agent that uses OpenAI's API to process messages"""

    def __init__(
        self,
        api_key,
        model="gpt-5-mini",
        prompt_name="default",
        temperature=1.0,
        timeout=30.0,
        templates_dir: str | Path | None = None,
    ):
        """Initialize the OpenAI agent
        
        Args:
            api_key: OpenAI API key
            model: OpenAI model to use
            
        Raises:
            FileNotFoundError: If the specified prompt templates don't exist
        """
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model
        self.prompt_name = prompt_name
        self.temperature = temperature
        self.timeout = timeout
        self.logger = get_logger("agent.openai")

        # Initialize prompt template manager
        self.prompt_manager = PromptTemplateManager(agent_name="openai", templates_dir=templates_dir)

        # Variables for templates
        self.system_template_vars = {
            "personality": "friendly, concise, and informative",
            "additional_instructions": "",
        }
        self.context_template_vars = {
            "user_preferences": "",
            "domain_knowledge": "",
        }

        # Verify that the prompt templates exist
        try:
            # Check if system prompt exists
            self.prompt_manager.get_system_prompt(self.prompt_name)
            
            # Try to get context prompt (this won't raise an error if it doesn't exist)
            try:
                self.prompt_manager.get_context_prompt(self.prompt_name)
            except FileNotFoundError:
                self.logger.warning(
                    "openai_agent.context_prompt_missing prompt=%s fallback=system_only",
                    self.prompt_name,
                )
                
            self.logger.info("openai_agent.initialized model=%s prompt=%s", model, self.prompt_name)
        except FileNotFoundError as e:
            self.logger.critical("openai_agent.initialization_failed detail=%s", str(e))
            raise
    
    @property
    def display_name(self):
        """Return the user-friendly display name for the agent"""
        return "AI Chat"
    
    @property
    def model_display_name(self):
        """Return a user-friendly display name for the model"""
        model_display_names = {
            "gpt-3.5-turbo": "GPT-3.5",
            "gpt-4": "GPT-4",
            "gpt-4-turbo": "GPT-4 Turbo",
            "gpt-4o": "GPT-4o",
            "gpt-4o-mini": "GPT-4o Mini",
            "gpt-5-mini": "GPT-5 Mini",
        }
        
        # Return the display name if it exists, otherwise return the model name
        return model_display_names.get(self.model, self.model)
    
    def process_message(
        self,
        message: str,
        conversation_history: Sequence[ConversationTurn] | None = None,
    ) -> str:
        """
        Process a message using OpenAI's API
        
        Args:
            message: User message to process
            
        Returns:
            Response from the model
            
        Raises:
            ValueError: If the message is empty or invalid
            FileNotFoundError: If the prompt templates don't exist
            openai.APIError: For API-related errors
            openai.RateLimitError: When rate limit is exceeded
            openai.AuthenticationError: When API key is invalid
            Exception: For other unexpected errors
        """
        if not message or not message.strip():
            self.logger.error("Empty message received")
            raise ValueError("Message cannot be empty")
        
        try:
            # Get system prompt content
            system_content = self.prompt_manager.get_system_prompt(
                self.prompt_name, **self.system_template_vars
            )
            
            # Try to get context prompt content
            try:
                context_content = self.prompt_manager.get_context_prompt(
                    self.prompt_name, **self.context_template_vars
                ).strip()

                # Combine message with context if any
                user_content = f"{context_content}\n\n{message}" if context_content else message
            except FileNotFoundError:
                # If context prompt doesn't exist, just use the message
                user_content = message
            
            # Format messages for OpenAI API
            messages: list[ChatCompletionMessageParam] = [{"role": "system", "content": system_content}]
            for turn in conversation_history or ():
                messages.append({"role": turn.role, "content": turn.content})
            messages.append({"role": "user", "content": user_content})
            
            # Log which prompt is being used
            self.logger.debug("openai_agent.prompt_selected prompt=%s", self.prompt_name)
            
            try:
                self.logger.info("openai_agent.request_started model=%s message_chars=%s", self.model, len(message))
                
                # Call OpenAI API
                response = self.client.chat.completions.create(**self._build_completion_request(messages))

                response_text = self._extract_response_text(response)

                self.logger.info(
                    "openai_agent.request_succeeded model=%s response_chars=%s",
                    self.model,
                    len(response_text),
                )
                
                return response_text
                
            except openai.APITimeoutError as e:
                self.logger.warning("openai_agent.timeout detail=%s", str(e))
                raise

            except openai.APIConnectionError as e:
                self.logger.warning("openai_agent.connection_error detail=%s", str(e))
                raise
                
            except openai.RateLimitError as e:
                self.logger.warning("openai_agent.rate_limited detail=%s", str(e))
                raise
                
            except openai.AuthenticationError as e:
                self.logger.warning("openai_agent.authentication_failed detail=%s", str(e))
                raise

            except openai.BadRequestError as e:
                self.logger.warning("openai_agent.bad_request detail=%s", str(e))
                raise
                
            except openai.APIError as e:
                self.logger.warning("openai_agent.api_error detail=%s", str(e))
                raise
                
            except Exception as e:
                self.logger.error("openai_agent.unexpected_error detail=%s", str(e), exc_info=True)
                raise
                
        except FileNotFoundError as e:
            self.logger.critical("openai_agent.prompt_template_error detail=%s", str(e))
            raise

    def _extract_response_text(self, response) -> str:
        choices = getattr(response, "choices", None)
        if not choices:
            error_msg = "AI response contained no choices"
            self.logger.error("openai_agent.empty_response detail=%s model=%s", error_msg, self.model)
            raise EmptyModelResponseError(error_msg)

        message = getattr(choices[0], "message", None)
        if message is None:
            error_msg = "AI response choice was missing a message"
            self.logger.error("openai_agent.empty_response detail=%s model=%s", error_msg, self.model)
            raise EmptyModelResponseError(error_msg)

        response_text = getattr(message, "content", None)
        if response_text is None:
            error_msg = "AI response did not include any text content"
            self.logger.error("openai_agent.empty_response detail=%s model=%s", error_msg, self.model)
            raise EmptyModelResponseError(error_msg)

        if not isinstance(response_text, str):
            error_msg = "AI response returned non-text content"
            self.logger.error("openai_agent.empty_response detail=%s model=%s", error_msg, self.model)
            raise EmptyModelResponseError(error_msg)

        if not response_text.strip():
            error_msg = "AI response returned an empty text response"
            self.logger.error("openai_agent.empty_response detail=%s model=%s", error_msg, self.model)
            raise EmptyModelResponseError(error_msg)

        return response_text

    def _build_completion_request(self, messages: list[ChatCompletionMessageParam]) -> dict[str, Any]:
        request: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "timeout": self.timeout,
        }

        if self._supports_custom_temperature():
            request["temperature"] = self.temperature
        elif self.temperature != 1.0:
            self.logger.info(
                "openai_agent.temperature_omitted model=%s configured_temperature=%s",
                self.model,
                self.temperature,
            )

        return request

    def _supports_custom_temperature(self) -> bool:
        return not self.model.startswith("gpt-5")
