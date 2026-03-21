#!/usr/bin/env python3
"""
Logging utilities for Lucid Session services
Provides standardized logging setup and logger access
"""


import sys
import logging
from typing import Optional
# Default log format
DEFAULT_LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DEFAULT_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
import os
from sessions.pipeline.config import PipelineConfig, PipelineSettings
from sessions.api.config import CONFIG, SETTINGS
if CONFIG is None:
    CONFIG = PipelineConfig()
if SETTINGS is None:
    SETTINGS = PipelineSettings()
logger = logging.getLogger(__name__)
logger.basicConfig(
    level=getattr(logging, CONFIG.LOG_LEVEL(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)



def setup_logging(
    level: Optional[str] = None,
    format_string: Optional[str] = None,
    date_format: Optional[str] = None
) -> None:
    """
    Setup logging configuration for the application
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL). Defaults to INFO or LOG_LEVEL env var
        format_string: Log format string. Defaults to DEFAULT_LOG_FORMAT
        date_format: Date format string. Defaults to DEFAULT_DATE_FORMAT
    """
    # Get log level from environment or parameter
    if level is None:
        level = CONFIG.LOG_LEVEL()
    
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Setup basic configuration
    log_format = format_string or DEFAULT_LOG_FORMAT
    date_fmt = date_format or DEFAULT_DATE_FORMAT
    
    logging.basicConfig(
        level=numeric_level,
        format=log_format,
        datefmt=date_fmt,
        stream=sys.stdout,
        force=True  # Override any existing configuration
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the given name
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Logger instance
    """
    # Ensure logging is set up if not already configured
    if not logging.get_logger().handlers:
        setup_logging()
    
    return logging.get_logger(name)

