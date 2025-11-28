"""
Lucid Authentication Service - Audit Log Middleware
Logs all authentication-related events for security and compliance
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime
import logging
import json
from typing import Optional, Dict, Any
import time

from config import settings

logger = logging.getLogger(__name__)


class AuditLogMiddleware(BaseHTTPMiddleware):
    """
    Audit logging middleware for authentication events
    
    Logs:
    - Authentication attempts (success/failure)
    - Token operations (issue, refresh, revoke)
    - Permission checks
    - Role changes
    - Sensitive operations
    """
    
    # Sensitive fields to mask in logs
    SENSITIVE_FIELDS = settings.AUDIT_LOG_SENSITIVE_FIELDS
    
    # Events to always log
    CRITICAL_EVENTS = [
        "/auth/login",
        "/auth/register",
        "/auth/logout",
        "/auth/refresh",
        "/users/{user_id}/role",
        "/sessions/{session_id}/revoke"
    ]
    
    def __init__(self, app):
        super().__init__(app)
        self.enabled = settings.AUDIT_LOG_ENABLED
    
    async def dispatch(self, request: Request, call_next):
        """Process request with audit logging"""
        
        if not self.enabled:
            return await call_next(request)
        
        # Start timing
        start_time = time.time()
        
        # Capture request details
        request_details = await self.capture_request_details(request)
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000
        
        # Capture response details
        response_details = self.capture_response_details(response)
        
        # Log audit event
        await self.log_audit_event(
            request=request,
            request_details=request_details,
            response_details=response_details,
            duration_ms=duration_ms
        )
        
        return response
    
    async def capture_request_details(self, request: Request) -> Dict[str, Any]:
        """Capture request details for audit log"""
        
        details = {
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "headers": {
                "user-agent": request.headers.get("user-agent"),
                "x-forwarded-for": request.headers.get("x-forwarded-for"),
                "x-real-ip": request.headers.get("x-real-ip")
            },
            "client_ip": request.client.host if request.client else None,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Add user context if authenticated
        if hasattr(request.state, "user_id"):
            details["user_id"] = request.state.user_id
            details["role"] = request.state.role
        
        # Capture request body for critical events (excluding sensitive fields)
        if self.is_critical_event(request.url.path):
            try:
                body = await request.body()
                if body:
                    body_json = json.loads(body)
                    details["body"] = self.mask_sensitive_data(body_json)
            except Exception as e:
                logger.debug(f"Could not capture request body: {e}")
        
        return details
    
    def capture_response_details(self, response) -> Dict[str, Any]:
        """Capture response details for audit log"""
        
        return {
            "status_code": response.status_code,
            "headers": {
                "content-type": response.headers.get("content-type")
            }
        }
    
    async def log_audit_event(
        self,
        request: Request,
        request_details: Dict[str, Any],
        response_details: Dict[str, Any],
        duration_ms: float
    ):
        """Write audit log entry"""
        
        # Determine event severity
        severity = self.get_event_severity(
            request_details["path"],
            response_details["status_code"]
        )
        
        # Build audit log entry
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "service": "auth-service",
            "event_type": "authentication",
            "severity": severity,
            "request": request_details,
            "response": response_details,
            "duration_ms": round(duration_ms, 2)
        }
        
        # Log based on severity
        if severity == "CRITICAL":
            logger.warning(f"AUDIT: {json.dumps(audit_entry)}")
        elif severity == "HIGH":
            logger.info(f"AUDIT: {json.dumps(audit_entry)}")
        else:
            logger.debug(f"AUDIT: {json.dumps(audit_entry)}")
        
        # Store in database for long-term retention
        if self.is_critical_event(request_details["path"]) or response_details["status_code"] >= 400:
            await self.store_audit_log(audit_entry)
    
    def is_critical_event(self, path: str) -> bool:
        """Check if event is critical and should always be logged"""
        for critical_path in self.CRITICAL_EVENTS:
            # Simple prefix matching (can be enhanced with regex)
            if critical_path.replace("{user_id}", "").replace("{session_id}", "") in path:
                return True
        return False
    
    def get_event_severity(self, path: str, status_code: int) -> str:
        """Determine event severity"""
        
        # Failed authentication attempts are critical
        if "auth" in path and status_code in [401, 403]:
            return "CRITICAL"
        
        # Other auth events are high severity
        if "auth" in path:
            return "HIGH"
        
        # Errors are medium severity
        if status_code >= 400:
            return "MEDIUM"
        
        return "LOW"
    
    def mask_sensitive_data(self, data: Any) -> Any:
        """Recursively mask sensitive fields in data"""
        
        if isinstance(data, dict):
            masked = {}
            for key, value in data.items():
                if key.lower() in [f.lower() for f in self.SENSITIVE_FIELDS]:
                    masked[key] = "***MASKED***"
                else:
                    masked[key] = self.mask_sensitive_data(value)
            return masked
        
        elif isinstance(data, list):
            return [self.mask_sensitive_data(item) for item in data]
        
        else:
            return data
    
    async def store_audit_log(self, audit_entry: Dict[str, Any]):
        """Store audit log in database for long-term retention"""
        
        # TODO: Implement database storage
        # This would typically store in MongoDB with retention policy
        
        try:
            # For now, just log that we would store it
            logger.debug(f"Would store audit log: {audit_entry['timestamp']}")
        except Exception as e:
            logger.error(f"Failed to store audit log: {e}")

