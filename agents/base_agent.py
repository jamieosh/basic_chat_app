from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal, Sequence


@dataclass(frozen=True)
class ConversationTurn:
    role: Literal["user", "assistant"]
    content: str

class BaseAgent(ABC):
    """Abstract base class for all agents"""
    
    @property
    @abstractmethod
    def display_name(self):
        """Return the display name for the agent to be shown in the header"""
        pass
    
    @property
    @abstractmethod
    def model_display_name(self):
        """Return a user-friendly display name for the model"""
        pass
    
    @abstractmethod
    def process_message(
        self,
        message: str,
        conversation_history: Sequence[ConversationTurn] | None = None,
    ) -> str:
        """Process a user message and return a response"""
        pass
