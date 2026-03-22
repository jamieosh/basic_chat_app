import openai
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)

from .base_agent import (
    BaseAgent,
    ChatContextBuilder,
    ChatHarnessCapabilities,
    ChatHarnessContext,
    ChatHarnessEvent,
    ChatHarnessExecutionError,
    ChatHarnessFailure,
    ChatHarnessIdentity,
    ChatHarnessObservability,
    ChatHarnessRequest,
    ConversationTurn,
)
from .context_builders import DefaultContextBuilder
from utils.logging_config import get_logger
from utils.prompt_manager import PromptTemplateManager


class EmptyModelResponseError(RuntimeError):
    """Raised when the model response does not include text content."""


class OpenAIAgent(BaseAgent):
    """OpenAI-backed harness adapter."""

    def __init__(
        self,
        api_key,
        model="gpt-5-mini",
        prompt_name="default",
        temperature=1.0,
        timeout=30.0,
        templates_dir: str | Path | None = None,
    ):
        """Initialize the OpenAI-backed harness.

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

        self.prompt_manager = PromptTemplateManager(agent_name="openai", templates_dir=templates_dir)

        self.system_template_vars = {
            "personality": "friendly, concise, and informative",
            "additional_instructions": "",
        }
        self.context_template_vars = {
            "user_preferences": "",
            "domain_knowledge": "",
        }

        try:
            self.prompt_manager.get_system_prompt(self.prompt_name)

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
        return model_display_names.get(self.model, self.model)

    @property
    def identity(self) -> ChatHarnessIdentity:
        return ChatHarnessIdentity(
            key="openai",
            display_name=self.display_name,
            model_display_name=self.model_display_name,
            provider_name="openai",
        )

    @property
    def capabilities(self) -> ChatHarnessCapabilities:
        return ChatHarnessCapabilities(
            supports_context_builders=True,
            supports_tool_call_events=False,
            supports_tool_result_events=False,
            supports_tool_orchestration=False,
        )

    @property
    def context_builder(self) -> ChatContextBuilder:
        system_prompt = self.prompt_manager.get_system_prompt(
            self.prompt_name, **self.system_template_vars
        )
        user_context = self.prompt_manager.get_optional_context_prompt(
            self.prompt_name, **self.context_template_vars
        )
        return DefaultContextBuilder(
            system_prompt=system_prompt,
            user_context=user_context,
            builder_name="openai_default",
        )

    def run_events(self, request: ChatHarnessRequest):
        try:
            context = self._build_context(request)
            response_text = self._run_openai_request(request, context)
        except ValueError:
            raise
        except Exception as exc:
            raise ChatHarnessExecutionError(self.normalize_exception(exc)) from exc
        observability = ChatHarnessObservability(
            model=self.model,
            provider="openai",
            request_id=request.request_id,
            tags={
                "harness_key": self.identity.key,
                "provider_name": self.identity.provider_name or "unknown",
                "context_builder": context.metadata.get("builder", "unknown"),
                "prompt_name": self.prompt_name,
            },
        )
        metadata = {
            "context_builder": context.metadata.get("builder", "unknown"),
            "model_display_name": self.model_display_name,
            "prompt_name": self.prompt_name,
        }
        yield ChatHarnessEvent(
            event_type="output_text",
            output_text=response_text,
            observability=observability,
            sequence=0,
            metadata=metadata,
        )
        yield ChatHarnessEvent(
            event_type="completed",
            observability=observability,
            sequence=1,
            metadata=metadata,
        )

    def normalize_exception(self, exc: Exception) -> ChatHarnessFailure:
        if isinstance(exc, openai.RateLimitError):
            return ChatHarnessFailure(
                code="rate_limited",
                message="The AI service is currently busy. Please try again in a few moments.",
                retryable=True,
                detail=str(exc),
            )
        if isinstance(exc, openai.AuthenticationError):
            return ChatHarnessFailure(
                code="authentication_failed",
                message="The AI service authentication failed.",
                retryable=False,
                detail=str(exc),
            )
        if isinstance(exc, openai.APITimeoutError):
            return ChatHarnessFailure(
                code="timeout",
                message="The AI service took too long to respond.",
                retryable=True,
                detail=str(exc),
            )
        if isinstance(exc, openai.APIConnectionError):
            return ChatHarnessFailure(
                code="connection_error",
                message="Could not connect to the AI service.",
                retryable=True,
                detail=str(exc),
            )
        if isinstance(exc, openai.BadRequestError):
            return ChatHarnessFailure(
                code="invalid_request",
                message="The AI service rejected the request.",
                retryable=False,
                detail=str(exc),
            )
        if isinstance(exc, openai.APIError):
            return ChatHarnessFailure(
                code="provider_error",
                message="The AI service encountered an error.",
                retryable=True,
                detail=str(exc),
            )
        if isinstance(exc, EmptyModelResponseError):
            return ChatHarnessFailure(
                code="empty_response",
                message="The AI service returned an empty response.",
                retryable=False,
                detail=str(exc),
            )
        return super().normalize_exception(exc)

    def process_message(
        self,
        message: str,
        conversation_history: Sequence[ConversationTurn] | None = None,
    ) -> str:
        """
        Compatibility shim for legacy call sites.

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
        request = ChatHarnessRequest(
            message=message,
            conversation_history=tuple(conversation_history or ()),
        )
        return self._run_openai_request(
            request,
            self._build_context(request),
        )

    def _build_context(self, request: ChatHarnessRequest) -> ChatHarnessContext:
        return self.context_builder.build(request)

    def _run_openai_request(self, request: ChatHarnessRequest, context: ChatHarnessContext) -> str:
        if not request.message or not request.message.strip():
            self.logger.error("Empty message received")
            raise ValueError("Message cannot be empty")

        try:
            messages = self._build_messages(context)
            self.logger.debug("openai_agent.prompt_selected prompt=%s", self.prompt_name)

            try:
                self.logger.info(
                    "openai_agent.request_started model=%s message_chars=%s",
                    self.model,
                    len(request.message),
                )
                response = self.client.chat.completions.create(
                    **self._build_completion_request(messages)
                )
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

    def _build_messages(self, context: ChatHarnessContext) -> list[ChatCompletionMessageParam]:
        messages: list[ChatCompletionMessageParam] = []
        for message in context.messages:
            if message.role == "system":
                messages.append(
                    ChatCompletionSystemMessageParam(role="system", content=message.content)
                )
            elif message.role == "user":
                messages.append(ChatCompletionUserMessageParam(role="user", content=message.content))
            else:
                messages.append(
                    ChatCompletionAssistantMessageParam(role="assistant", content=message.content)
                )
        return messages

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
