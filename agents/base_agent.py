from abc import ABC, abstractmethod

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
    def process_message(self, message: str) -> str:
        """Process a user message and return a response"""
        pass
