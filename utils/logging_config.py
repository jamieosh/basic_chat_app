import logging
import sys
import os
from datetime import datetime
from pathlib import Path

def setup_logging(
    default_level=logging.INFO,
    log_to_file=False,
    log_dir="logs",
    app_name="ai_chat",
    component_levels=None
):
    """Set up logging configuration for the entire application
    
    Args:
        default_level: Default logging level for all components
        log_to_file: Whether to log to a file
        log_dir: Directory to store log files
        app_name: Name of the application (used for log file naming)
        component_levels: Dict mapping component names to logging levels
    """
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(default_level)
    
    # Clear existing handlers to avoid duplicates
    if root_logger.handlers:
        root_logger.handlers.clear()
    
    # Always add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Add file handler if requested
    if log_to_file:
        # Create log directory if it doesn't exist
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True, parents=True)
        
        # Create log file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_path / f"{app_name}_{timestamp}.log"
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Set component-specific log levels
    if component_levels:
        for component, level in component_levels.items():
            logger = logging.getLogger(component)
            logger.setLevel(level)

def get_logger(name):
    """Get a logger for a specific component"""
    return logging.getLogger(name)

def truncate_message(message, max_length=500):
    """Truncate a message to a maximum length for logging purposes"""
    if isinstance(message, str) and len(message) > max_length:
        return message[:max_length] + f"... [truncated, total length: {len(message)}]"
    return message

# Initialize logging based on environment variables
def init_logging():
    # Default log level
    default_level_name = os.getenv("LOG_LEVEL", "INFO")
    default_level = getattr(logging, default_level_name, logging.INFO)
    
    # Component-specific log levels from environment variables
    # Format: COMPONENT1=DEBUG,COMPONENT2=WARNING
    component_levels_str = os.getenv("COMPONENT_LOG_LEVELS", "")
    component_levels = {}
    
    if component_levels_str:
        for component_level in component_levels_str.split(","):
            if "=" in component_level:
                component, level_name = component_level.split("=")
                level = getattr(logging, level_name, None)
                if level is not None:
                    component_levels[component] = level
    
    # You can also hardcode specific component levels here
    # component_levels.update({
    #     "agent.openai": logging.DEBUG,
    #     "api": logging.INFO
    # })
    
    log_to_file = os.getenv("LOG_TO_FILE", "false").lower() == "true"
    log_dir = os.getenv("LOG_DIR", "logs")
    app_name = os.getenv("APP_NAME", "ai_chat")
    
    setup_logging(
        default_level=default_level,
        log_to_file=log_to_file,
        log_dir=log_dir,
        app_name=app_name,
        component_levels=component_levels
    )

# Initialize logging when module is imported
init_logging() 