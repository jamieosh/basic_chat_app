from abc import ABC, abstractmethod

class BaseAgent(ABC):
    """Abstract base class for all agents"""
    
    @property
    @abstractmethod
    def display_name(self):
        """Return a user-friendly display name for the agent"""
        pass
    
    @abstractmethod
    def process_message(self, message: str) -> str:
        """Process a user message and return a response"""
        pass
    
    @abstractmethod
    async def format_response_as_html(self, response: str) -> str:
        """Format the response as HTML with code block handling"""
        pass
