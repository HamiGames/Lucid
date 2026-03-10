"""
Admin Utilities

File: admin/utils/__init__.py
Purpose: Utility functions and helper modules
"""

from admin.utils.logging import setup_logging, get_logger
logger = get_logger(__name__)

__all__ = [
    "setup_logging",
    "get_logger", "logger"
]