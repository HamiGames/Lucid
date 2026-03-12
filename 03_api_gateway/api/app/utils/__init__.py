"""
Utils Package

File: 03_api_gateway/api/app/utils/__init__.py
Purpose: Utility functions and helper modules
"""

# Utility imports will be added as they are implemented
# from .security import hash_password, verify_password
# from .logging import setup_logging
from ..utils.config import (
    in_container, mongo_conn_str, service_name, service_version, mongo_timeouts_ms
    )
from ..utils.logging import (
    setup_logging, get_logger
    )

from ..utils.logger import (
    JsonFormatter, get_logger
    )
# from .validation import validate_email, validate_username
logger = get_logger(__name__)
__all__ = ['in_container', 'mongo_conn_str', 'service_name', 'service_version', 
           'mongo_timeouts_ms', 'setup_logging', 'get_logger', 'JsonFormatter', 'logger']

