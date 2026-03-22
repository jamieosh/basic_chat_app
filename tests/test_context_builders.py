from agents.base_agent import (
    ChatContextBuilder,
    ChatHarnessContext,
    ChatHarnessRequest,
    ContextMessage,
    ConversationTurn,
)
from agents.context_builders import DefaultContextBuilder


class SummaryOnlyContextBuilder:
    def build(self, request: ChatHarnessRequest) -> ChatHarnessContext:
        return ChatHarnessContext(
            messages=(
                ContextMessage(role="system", content="You are concise."),
                ContextMessage(role="assistant", content="Summary: user asked about travel plans."),
                ContextMessage(role="user", content=request.message),
            ),
            metadata={"builder": "summary_only"},
        )


def test_default_context_builder_replays_transcript_and_optional_user_context():
    builder = DefaultContextBuilder(
        system_prompt="You are helpful.",
        user_context="Prefer metric units.",
    )

    context = builder.build(
        ChatHarnessRequest(
            message="How far is the walk?",
            conversation_history=(
                ConversationTurn(role="user", content="Plan my route"),
                ConversationTurn(role="assistant", content="Where are you starting?"),
            ),
        )
    )

    assert context.messages == (
        ContextMessage(role="system", content="You are helpful."),
        ContextMessage(role="user", content="Plan my route"),
        ContextMessage(role="assistant", content="Where are you starting?"),
        ContextMessage(role="user", content="Prefer metric units.\n\nHow far is the walk?"),
    )
    assert context.metadata == {"builder": "default_transcript"}


def test_custom_context_builder_can_swap_memory_policy_behind_same_request_contract():
    builder: ChatContextBuilder = SummaryOnlyContextBuilder()

    context = builder.build(
        ChatHarnessRequest(
            message="What should I book next?",
            conversation_history=(
                ConversationTurn(role="user", content="Show my full trip history"),
                ConversationTurn(role="assistant", content="Here is the full transcript"),
            ),
        )
    )

    assert context.messages == (
        ContextMessage(role="system", content="You are concise."),
        ContextMessage(role="assistant", content="Summary: user asked about travel plans."),
        ContextMessage(role="user", content="What should I book next?"),
    )
    assert context.metadata == {"builder": "summary_only"}
