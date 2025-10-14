"""
Logging Middleware

File: 03-api-gateway/api/app/middleware/logging.py
Purpose: Request/response logging with correlation IDs
"""

import logging
import time
import uuid
from fastapi import Request

logger = logging.getLogger(__name__)


class LoggingMiddleware:
    """Logging middleware for request/response tracking"""
    
    def __init__(self, app):
        self.app = app
        logger.info("LoggingMiddleware initialized")
    
    async def __call__(self, scope, receive, send):
        """Process request through logging middleware"""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        logger.info(f"Request started: {request.method} {request.url.path}", extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "client_ip": request.client.host
        })
        
        await self.app(scope, receive, send)
        
        duration = time.time() - start_time
        logger.info(f"Request completed: {request.method} {request.url.path}", extra={
            "request_id": request_id,
            "duration_ms": duration * 1000
        })
