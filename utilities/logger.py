"""
Logger module for type_registration.

This module provides a centralized logger that can be imported throughout the type_registration
module without causing circular import issues.
"""

import logging

# Module-level logger
logger: logging.Logger = logging.getLogger('type_registration')
logger.setLevel(logging.WARNING)  # Default to WARNING level to avoid spam

def set_logger(custom_logger: logging.Logger) -> None:
    """Allow users to provide their own logger."""
    global logger
    logger = custom_logger

def set_log_level(level: int) -> None:
    """Set the logging level for the module. 
    
    Args:
        level: logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, or logging.CRITICAL
    """
    logger.setLevel(level) 