"""
CORS Configuration

File: 03-api-gateway/api/app/middleware/cors.py
Purpose: CORS configuration and utilities
"""

import logging
from typing import List
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CORSConfig:
    """CORS configuration helper"""
    
    @staticmethod
    def get_allowed_origins() -> List[str]:
        """Get list of allowed CORS origins"""
        origins = settings.CORS_ORIGINS
        logger.info(f"CORS origins configured: {origins}")
        return origins
    
    @staticmethod
    def get_allowed_methods() -> List[str]:
        """Get list of allowed HTTP methods"""
        return ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    
    @staticmethod
    def get_allowed_headers() -> List[str]:
        """Get list of allowed headers"""
        return ["*"]

