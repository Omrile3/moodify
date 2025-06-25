import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

def log_dict_info(message: str, **kwargs: Dict[str, Any]) -> None:
    """
    Helper function for structured info logging.
    
    Args:
        message: The log message
        kwargs: Additional data to be included in the log
    """
    logger.info(message, extra={'data': kwargs})

def log_dict_warning(message: str, **kwargs: Dict[str, Any]) -> None:
    """
    Helper function for structured warning logging.
    
    Args:
        message: The log message
        kwargs: Additional data to be included in the log
    """
    logger.warning(message, extra={'data': kwargs})

def log_dict_error(message: str, **kwargs: Dict[str, Any]) -> None:
    """
    Helper function for structured error logging.
    
    Args:
        message: The log message
        kwargs: Additional data to be included in the log
    """
    logger.error(message, extra={'data': kwargs})

def log_dict_debug(message: str, **kwargs: Dict[str, Any]) -> None:
    """
    Helper function for structured debug logging.
    
    Args:
        message: The log message
        kwargs: Additional data to be included in the log
    """
    logger.debug(message, extra={'data': kwargs})
