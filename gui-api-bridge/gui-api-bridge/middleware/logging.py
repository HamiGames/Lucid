"""
Logging Middleware for GUI API Bridge
File: gui-api-bridge/gui-api-bridge/middleware/logging.py
"""

import logging
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for structured request/response logging"""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Log request and response"""
        start_time = time.time()
        
        # Log request
        logger.info(
            f"Request: {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
            },
        )
        
        try:
            # Call next middleware/endpoint
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log response
            logger.info(
                f"Response: {response.status_code} in {duration:.3f}s",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration * 1000,
                },
            )
            
            return response
        
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"Error: {str(e)} in {duration:.3f}s",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration * 1000,
                },
                exc_info=True,
            )
            raise
