"""
Logging Middleware

File: 03-api-gateway/api/app/middleware/logging.py
Purpose: Request/response logging with correlation IDs.
All configuration from environment variables via app.config.
"""

import logging
import time
import uuid
from typing import Callable
from fastapi import Request

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class LoggingMiddleware:
    """Logging middleware for request/response tracking"""
    
    # Paths to exclude from detailed logging
    EXCLUDED_PATHS = [
        "/health",
        "/api/v1/meta/health",
        "/metrics",
    ]
    
    def __init__(self, app):
        self.app = app
        self.log_level = settings.LOG_LEVEL
        self.service_name = settings.SERVICE_NAME
        logger.info(f"LoggingMiddleware initialized (level={self.log_level})")
    
    async def __call__(self, scope, receive, send):
        """Process request through logging middleware"""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        path = request.url.path
        
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Add request ID to scope state
        scope["state"] = scope.get("state", {})
        scope["state"]["request_id"] = request_id
        
        # Get client info
        client_ip = self._get_client_ip(request)
        method = request.method
        
        # Skip detailed logging for health checks
        if path not in self.EXCLUDED_PATHS:
            logger.info(
                f"[{request_id}] Request started: {method} {path}",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "client_ip": client_ip,
                    "service": self.service_name,
                    "user_agent": request.headers.get("User-Agent", "unknown"),
                }
            )
        
        # Track response status
        response_status = [0]  # Use list to allow modification in nested function
        
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                response_status[0] = message.get("status", 0)
                # Add request ID to response headers
                headers = list(message.get("headers", []))
                headers.append((b"X-Request-ID", request_id.encode()))
                message["headers"] = headers
            await send(message)
        
        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"[{request_id}] Request failed: {method} {path} - {str(e)}",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "duration_ms": duration_ms,
                    "error": str(e),
                    "service": self.service_name,
                }
            )
            raise
        
        # Log completion (skip for health checks)
        if path not in self.EXCLUDED_PATHS:
            duration_ms = (time.time() - start_time) * 1000
            log_level = logging.INFO if response_status[0] < 400 else logging.WARNING
            
            logger.log(
                log_level,
                f"[{request_id}] Request completed: {method} {path} -> {response_status[0]} ({duration_ms:.2f}ms)",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "status_code": response_status[0],
                    "duration_ms": duration_ms,
                    "service": self.service_name,
                }
            )
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP, handling proxy headers"""
        # Check X-Forwarded-For header (common for proxies)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        # Fall back to direct client
        return request.client.host if request.client else "unknown"
