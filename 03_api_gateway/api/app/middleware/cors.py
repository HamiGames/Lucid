"""
CORS Configuration

File: 03_api_gateway/api/app/middleware/cors.py
Purpose: CORS configuration and utilities.
All configuration from environment variables via app.config.
"""

import os
from typing import List
from ..config import Settings, get_settings
log_level = os.getenv(get_settings().LOG_LEVEL(), "INFO").upper()
settings = os.getenv(Settings().LOG_LEVEL(), "INFO").upper()
try:
    from ..utils.logging import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger(__name__)
settings(__name__)


class CORSConfig:
    """CORS configuration helper - all values from environment"""
    
    @staticmethod
    def get_allowed_origins() -> List[str]:
        """Get list of allowed CORS origins from settings"""
        origins = settings.CORS_ORIGINS
        logger.debug(f"CORS origins configured: {origins}")
        return origins
    
    @staticmethod
    def get_allowed_hosts() -> List[str]:
        """Get list of allowed hosts from settings"""
        return settings.ALLOWED_HOSTS
    
    @staticmethod
    def get_allowed_methods() -> List[str]:
        """Get list of allowed HTTP methods"""
        return ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    
    @staticmethod
    def get_allowed_headers() -> List[str]:
        """Get list of allowed headers"""
        return [
            "Accept",
            "Accept-Language",
            "Content-Type",
            "Authorization",
            "X-Request-ID",
            "X-Forwarded-For",
            "X-Real-IP",
        ]
    
    @staticmethod
    def get_expose_headers() -> List[str]:
        """Get list of headers to expose to the client"""
        return [
            "X-Request-ID",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
        ]
