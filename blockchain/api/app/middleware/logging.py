"""
Logging Middleware

This module contains request logging middleware for the Blockchain API.
Handles request/response logging, performance monitoring, and error tracking.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
import logging
from typing import Dict, Any

from ..logging_config import request_logger, security_logger, performance_logger
from ..metrics import api_metrics

logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    """Request logging middleware for API requests."""
    
    async def dispatch(self, request: Request, call_next):
        """Process request through logging middleware."""
        
        # Record start time
        start_time = time.time()
        
        # Extract request information
        method = request.method
        path = request.url.path
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("User-Agent")
        
        # Get user information if available
        user_id = None
        if hasattr(request.state, 'user'):
            user_id = request.state.user.get('user_id')
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate response time
            response_time = time.time() - start_time
            
            # Record API metrics
            api_metrics.record_request(method, path, response.status_code, response_time)
            
            # Log request
            request_logger.log_request(
                method=method,
                path=path,
                status_code=response.status_code,
                response_time=response_time,
                client_ip=client_ip,
                user_agent=user_agent,
                user_id=user_id
            )
            
            # Log slow requests
            performance_logger.log_slow_request(method, path, response_time)
            
            # Log security events
            if response.status_code == 401:
                security_logger.log_authentication_failure(
                    username=user_id or "unknown",
                    method="api_request",
                    client_ip=client_ip,
                    reason="Authentication failed"
                )
            elif response.status_code == 403:
                security_logger.log_authorization_failure(
                    user_id=user_id or "unknown",
                    resource=path,
                    action=method,
                    client_ip=client_ip
                )
            
            return response
            
        except Exception as e:
            # Calculate response time for errors
            response_time = time.time() - start_time
            
            # Record error metrics
            api_metrics.record_error(
                error_type=type(e).__name__,
                endpoint=path,
                error_message=str(e)
            )
            
            # Log error
            logger.error(f"Request failed: {method} {path} - {str(e)}", exc_info=True)
            
            # Re-raise the exception
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request."""
        # Try to get from X-Forwarded-For header first
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Fall back to client IP
        return request.client.host