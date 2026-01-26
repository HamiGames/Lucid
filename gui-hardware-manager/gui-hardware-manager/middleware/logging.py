"""
Logging middleware for request/response tracking
"""

import logging
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses"""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Log request and response"""
        
        # Record start time
        start_time = time.time()
        
        # Log request
        logger.info(f"{request.method} {request.url.path}")
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log response
            logger.info(
                f"{request.method} {request.url.path} "
                f"status={response.status_code} duration={duration:.2f}s"
            )
            
            return response
            
        except Exception as e:
            # Log error
            duration = time.time() - start_time
            logger.error(
                f"{request.method} {request.url.path} "
                f"error={str(e)} duration={duration:.2f}s",
                exc_info=True
            )
            raise
