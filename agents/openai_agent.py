import html
import openai
from .base_agent import BaseAgent
from utils.logging_config import get_logger, truncate_message
from utils.prompt_manager import PromptTemplateManager

class OpenAIAgent(BaseAgent):
    """Agent that uses OpenAI's API to process messages"""
    
    def __init__(self, api_key, model="gpt-3.5-turbo"):
        """Initialize the OpenAI agent
        
        Args:
            api_key: OpenAI API key
            model: OpenAI model to use
            prompt_name: Name of the prompt to use (default: "general")
            
        Raises:
            FileNotFoundError: If the specified prompt templates don't exist
        """
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model
        self.prompt_name = "default"
        self.logger = get_logger("agent.openai")
        
        # Initialize prompt template manager
        self.prompt_manager = PromptTemplateManager(agent_name="openai")
        
        # Variables for templates
        self.system_template_vars = {
            "personality": "friendly, concise, and informative",
            "additional_instructions": "",
        }
        self.context_template_vars = {
            "user_preferences": "",
            "domain_knowledge": "Lucky is a cockapoo dog. He is fox red and 8 years old.",
        }
        
        # Verify that the prompt templates exist
        try:
            # Check if system prompt exists
            self.prompt_manager.get_system_prompt(self.prompt_name)
            
            # Try to get context prompt (this won't raise an error if it doesn't exist)
            try:
                self.prompt_manager.get_context_prompt(self.prompt_name)
            except FileNotFoundError:
                self.logger.warning("No context prompt found for %s, will use only system prompt", self.prompt_name)
                
            self.logger.info("OpenAI agent initialized with model: %s, prompt: %s", model, self.prompt_name)
        except FileNotFoundError as e:
            self.logger.critical("Failed to initialize OpenAI agent: %s", str(e))
            raise
    
    @property
    def display_name(self):
        """Return a user-friendly display name for the agent based on the model"""
        model_display_names = {
            "gpt-3.5-turbo": "GPT-3.5",
            "gpt-4": "GPT-4",
            "gpt-4-turbo": "GPT-4 Turbo",
            "gpt-4o": "GPT-4o"
        }
        
        # Return the display name if it exists, otherwise return the model name
        return model_display_names.get(self.model, self.model)
    
    def process_message(self, message):
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
                )
                
                # Combine message with context if any
                user_content = f"{context_content}\n\n{message}" if context_content else message
            except FileNotFoundError:
                # If context prompt doesn't exist, just use the message
                user_content = message
            
            # Format messages for OpenAI API
            messages = [
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content}
            ]
            
            # Log which prompt is being used
            self.logger.info("Using prompt name: %s", self.prompt_name)
            
            try:
                self.logger.info("Sending request to %s: %s", self.model, truncate_message(message))
                self.logger.debug("Full message: %s", truncate_message(str(messages)))
                
                # Call OpenAI API
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    timeout=30  # Add timeout to prevent hanging requests
                )
                
                # Extract response text
                response_text = response.choices[0].message.content
                self.logger.info("Received response: %s", truncate_message(response_text))
                
                return response_text
                
            except openai.APIConnectionError as e:
                self.logger.error("Connection error when calling OpenAI API: %s", str(e), exc_info=True)
                raise openai.APIConnectionError(
                    f"Failed to connect to OpenAI API: {str(e)}. Please check your internet connection."
                )
                
            except openai.RateLimitError as e:
                self.logger.error("Rate limit exceeded when calling OpenAI API: %s", str(e), exc_info=True)
                raise openai.RateLimitError(
                    "OpenAI API rate limit exceeded. Please try again later."
                )
                
            except openai.AuthenticationError as e:
                self.logger.error("Authentication error when calling OpenAI API: %s", str(e), exc_info=True)
                raise openai.AuthenticationError(
                    "Invalid API key. Please check your OpenAI API key."
                )
                
            except openai.APIError as e:
                self.logger.error("API error when calling OpenAI API: %s", str(e), exc_info=True)
                raise openai.APIError(
                    f"OpenAI API returned an error: {str(e)}"
                )
                
            except openai.BadRequestError as e:
                self.logger.error("Bad request error when calling OpenAI API: %s", str(e), exc_info=True)
                raise openai.BadRequestError(
                    f"Invalid request to OpenAI API: {str(e)}"
                )
                
            except openai.Timeout as e:
                self.logger.error("Timeout when calling OpenAI API: %s", str(e), exc_info=True)
                raise openai.Timeout(
                    "Request to OpenAI API timed out. Please try again."
                )
                
            except Exception as e:
                self.logger.error("Unexpected error when calling OpenAI API: %s", str(e), exc_info=True)
                raise Exception(f"An unexpected error occurred: {str(e)}")
                
        except FileNotFoundError as e:
            self.logger.critical("Prompt template error: %s", str(e))
            raise
    
    async def format_response_as_html(self, response: str) -> str:
        """Format the response as HTML with code block handling"""
        # Escape HTML in the response to prevent XSS
        safe_response = html.escape(response)
        
        # Format the response with line breaks
        formatted_response = safe_response.replace('\n', '<br>')
        
        # Process code blocks if present (simple markdown-like formatting)
        if '```' in formatted_response:
            # Replace code blocks with styled pre elements
            parts = formatted_response.split('```')
            formatted_parts = []
            
            for i, part in enumerate(parts):
                if i % 2 == 0:  # Regular text
                    formatted_parts.append(part)
                else:  # Code block
                    # Check if the code block has a language specified
                    lines = part.split('<br>', 1)
                    if len(lines) > 1:
                        language = lines[0].strip()
                        code = lines[1]
                        formatted_parts.append(f'<pre class="bg-gray-800 text-gray-100 p-2 rounded-md overflow-x-auto text-sm my-2"><code class="language-{language}">{code}</code></pre>')
                    else:
                        formatted_parts.append(f'<pre class="bg-gray-800 text-gray-100 p-2 rounded-md overflow-x-auto text-sm my-2"><code>{part}</code></pre>')
            
            formatted_response = ''.join(formatted_parts)
            
        return formatted_response 