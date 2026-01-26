"""
Logging Middleware for GUI Tor Manager
Logs all HTTP requests and responses in structured format
"""

import time
import json
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse

from utils.logging import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for structured logging of HTTP requests/responses"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log with timing"""
        # Start timer
        start_time = time.time()
        
        # Capture request details
        request_body = b""
        if request.method in ["POST", "PUT", "PATCH"]:
            request_body = await request.body()
            # Recreate request body for next middleware
            async def receive():
                return {"type": "http.request", "body": request_body}
            request._receive = receive
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log request
        log_data = {
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "process_time_ms": round(process_time * 1000, 2),
            "client": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", ""),
        }
        
        if request.method in ["POST", "PUT", "PATCH"] and request_body:
            try:
                log_data["request_body"] = json.loads(request_body.decode())
            except Exception:
                log_data["request_body"] = str(request_body[:100])
        
        logger.info(f"HTTP Request", extra=log_data)
        
        return response
