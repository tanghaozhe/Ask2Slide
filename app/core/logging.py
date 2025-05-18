import logging
import sys
from typing import Optional


# Configure logging
def setup_logger(
    name: Optional[str] = None, level: int = logging.INFO
) -> logging.Logger:
    """
    Set up a logger with the specified name and level.

    Args:
        name: Name of the logger. If None, the root logger is returned.
        level: Logging level (default: INFO)

    Returns:
        Configured logger instance
    """
    logger_instance = logging.getLogger(name)
    logger_instance.setLevel(level)

    # Check if the logger already has handlers to avoid duplicate handlers
    if not logger_instance.handlers:
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)

        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(formatter)

        # Add handler to logger
        logger_instance.addHandler(console_handler)

    return logger_instance


# Create default logger
logger = setup_logger("ask2slide")
