"""
Logging Configuration
File: gui_docker_manager/gui_docker_manager/utils/logging.py
"""

import logging
import sys
from typing import Optional

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)


def setup_logging(level: str = "INFO") -> None:
    """Setup logging configuration"""
    log_level = getattr(logging, level.upper(), logging.INFO)
    logging.get_logger().setLevel(log_level)


def get_logger(name: str) -> logging.Logger:
    """Get logger instance"""
    return logging.get_logger(name)
