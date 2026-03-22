import anthropic
from pathlib import Path
from typing import Any

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


class AnthropicAgent(BaseAgent):
    """Anthropic-backed harness adapter."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        prompt_name: str = "default",
        temperature: float = 1.0,
        timeout: float = 30.0,
        max_tokens: int = 1024,
        templates_dir: str | Path | None = None,
    ) -> None:
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.prompt_name = prompt_name
        self.temperature = temperature
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.logger = get_logger("agent.anthropic")

        self.prompt_manager = PromptTemplateManager(agent_name="anthropic", templates_dir=templates_dir)

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
                    "anthropic_agent.context_prompt_missing prompt=%s fallback=system_only",
                    self.prompt_name,
                )
            self.logger.info("anthropic_agent.initialized model=%s prompt=%s", model, self.prompt_name)
        except FileNotFoundError as exc:
            self.logger.critical("anthropic_agent.initialization_failed detail=%s", str(exc))
            raise

    @property
    def display_name(self) -> str:
        return "AI Chat"

    @property
    def model_display_name(self) -> str:
        model_display_names = {
            "claude-opus-4-20250514": "Claude Opus 4",
            "claude-sonnet-4-20250514": "Claude Sonnet 4",
            "claude-3-7-sonnet-20250219": "Claude Sonnet 3.7",
            "claude-3-5-haiku-latest": "Claude Haiku 3.5",
        }
        return model_display_names.get(self.model, self.model)

    @property
    def identity(self) -> ChatHarnessIdentity:
        return ChatHarnessIdentity(
            key="anthropic",
            display_name=self.display_name,
            model_display_name=self.model_display_name,
            provider_name="anthropic",
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
            builder_name="anthropic_default",
        )

    def run_events(self, request: ChatHarnessRequest):
        try:
            context = self._build_context(request)
            response_text = self._run_anthropic_request(request, context)
        except ValueError:
            raise
        except Exception as exc:
            raise ChatHarnessExecutionError(self.normalize_exception(exc)) from exc
        observability = ChatHarnessObservability(
            model=self.model,
            provider="anthropic",
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
        if isinstance(exc, anthropic.RateLimitError):
            return ChatHarnessFailure(
                code="rate_limited",
                message="The AI service is currently busy. Please try again in a few moments.",
                retryable=True,
                detail=str(exc),
            )
        if isinstance(exc, anthropic.AuthenticationError):
            return ChatHarnessFailure(
                code="authentication_failed",
                message="The AI service authentication failed.",
                retryable=False,
                detail=str(exc),
            )
        if isinstance(exc, anthropic.APITimeoutError):
            return ChatHarnessFailure(
                code="timeout",
                message="The AI service took too long to respond.",
                retryable=True,
                detail=str(exc),
            )
        if isinstance(exc, anthropic.APIConnectionError):
            return ChatHarnessFailure(
                code="connection_error",
                message="Could not connect to the AI service.",
                retryable=True,
                detail=str(exc),
            )
        if isinstance(exc, anthropic.BadRequestError):
            return ChatHarnessFailure(
                code="invalid_request",
                message="The AI service rejected the request.",
                retryable=False,
                detail=str(exc),
            )
        if isinstance(exc, anthropic.APIStatusError):
            is_retryable = getattr(exc, "status_code", 500) >= 500
            return ChatHarnessFailure(
                code="provider_error" if is_retryable else "invalid_request",
                message=(
                    "The AI service encountered an error."
                    if is_retryable
                    else "The AI service rejected the request."
                ),
                retryable=is_retryable,
                detail=str(exc),
            )
        if isinstance(exc, EmptyModelResponseError):
            return ChatHarnessFailure(
                code="empty_response",
                message="The AI service returned an empty response.",
                retryable=False,
                detail=str(exc),
            )
        if isinstance(exc, anthropic.APIError):
            return ChatHarnessFailure(
                code="provider_error",
                message="The AI service encountered an error.",
                retryable=True,
                detail=str(exc),
            )
        return super().normalize_exception(exc)

    def process_message(
        self,
        message: str,
        conversation_history: tuple[ConversationTurn, ...] | None = None,
    ) -> str:
        request = ChatHarnessRequest(
            message=message,
            conversation_history=tuple(conversation_history or ()),
        )
        return self._run_anthropic_request(
            request,
            self._build_context(request),
        )

    def _build_context(self, request: ChatHarnessRequest) -> ChatHarnessContext:
        return self.context_builder.build(request)

    def _run_anthropic_request(self, request: ChatHarnessRequest, context: ChatHarnessContext) -> str:
        if not request.message or not request.message.strip():
            self.logger.error("Empty message received")
            raise ValueError("Message cannot be empty")

        try:
            system_prompt, messages = self._build_messages(context)
            self.logger.debug("anthropic_agent.prompt_selected prompt=%s", self.prompt_name)

            try:
                self.logger.info(
                    "anthropic_agent.request_started model=%s message_chars=%s",
                    self.model,
                    len(request.message),
                )
                response = self.client.messages.create(
                    **self._build_message_request(system_prompt, messages)
                )
                response_text = self._extract_response_text(response)
                self.logger.info(
                    "anthropic_agent.request_succeeded model=%s response_chars=%s",
                    self.model,
                    len(response_text),
                )
                return response_text
            except anthropic.APITimeoutError as exc:
                self.logger.warning("anthropic_agent.timeout detail=%s", str(exc))
                raise
            except anthropic.APIConnectionError as exc:
                self.logger.warning("anthropic_agent.connection_error detail=%s", str(exc))
                raise
            except anthropic.RateLimitError as exc:
                self.logger.warning("anthropic_agent.rate_limited detail=%s", str(exc))
                raise
            except anthropic.AuthenticationError as exc:
                self.logger.warning("anthropic_agent.authentication_failed detail=%s", str(exc))
                raise
            except anthropic.BadRequestError as exc:
                self.logger.warning("anthropic_agent.bad_request detail=%s", str(exc))
                raise
            except anthropic.APIStatusError as exc:
                self.logger.warning("anthropic_agent.api_status_error detail=%s", str(exc))
                raise
            except anthropic.APIError as exc:
                self.logger.warning("anthropic_agent.api_error detail=%s", str(exc))
                raise
            except Exception as exc:
                self.logger.error(
                    "anthropic_agent.unexpected_error detail=%s", str(exc), exc_info=True
                )
                raise
        except FileNotFoundError as exc:
            self.logger.critical("anthropic_agent.prompt_template_error detail=%s", str(exc))
            raise

    def _build_messages(self, context: ChatHarnessContext) -> tuple[str | None, list[dict[str, str]]]:
        system_messages: list[str] = []
        messages: list[dict[str, str]] = []
        for message in context.messages:
            if message.role == "system":
                system_messages.append(message.content)
                continue
            messages.append(
                {
                    "role": message.role,
                    "content": message.content,
                }
            )
        system_prompt = "\n\n".join(part for part in system_messages if part.strip())
        return (system_prompt or None), messages

    def _extract_response_text(self, response: Any) -> str:
        content = getattr(response, "content", None)
        if not content:
            error_msg = "AI response did not include any content blocks"
            self.logger.error(
                "anthropic_agent.empty_response detail=%s model=%s", error_msg, self.model
            )
            raise EmptyModelResponseError(error_msg)

        text_parts: list[str] = []
        for block in content:
            if getattr(block, "type", None) != "text":
                continue
            text = getattr(block, "text", None)
            if isinstance(text, str):
                text_parts.append(text)

        response_text = "".join(text_parts)
        if not response_text.strip():
            error_msg = "AI response did not include any text content"
            self.logger.error(
                "anthropic_agent.empty_response detail=%s model=%s", error_msg, self.model
            )
            raise EmptyModelResponseError(error_msg)

        return response_text

    def _build_message_request(
        self,
        system_prompt: str | None,
        messages: list[dict[str, str]],
    ) -> dict[str, Any]:
        request: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": messages,
            "temperature": self.temperature,
            "timeout": self.timeout,
        }
        if system_prompt is not None:
            request["system"] = system_prompt
        return request
