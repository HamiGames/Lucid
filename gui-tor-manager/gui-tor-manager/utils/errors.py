"""
Error Handling and Custom Exceptions for GUI Tor Manager
"""

from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class GuiTorManagerException(Exception):
    """Base exception for GUI Tor Manager"""
    
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class TorProxyConnectionError(GuiTorManagerException):
    """Error connecting to Tor proxy service"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="TOR_PROXY_CONNECTION_ERROR",
            details=details
        )


class TorOperationError(GuiTorManagerException):
    """Error executing Tor operation"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="TOR_OPERATION_ERROR",
            details=details
        )


class OnionServiceError(GuiTorManagerException):
    """Error managing onion service"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="ONION_SERVICE_ERROR",
            details=details
        )


class ConfigurationError(GuiTorManagerException):
    """Configuration error"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="CONFIGURATION_ERROR",
            details=details
        )


class ValidationError(GuiTorManagerException):
    """Validation error"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            details=details
        )


def to_http_exception(exc: GuiTorManagerException, status_code: int = 500) -> HTTPException:
    """
    Convert GuiTorManagerException to HTTPException
    
    Args:
        exc: The GuiTorManagerException
        status_code: HTTP status code (default: 500)
    
    Returns:
        HTTPException with error details
    """
    return HTTPException(
        status_code=status_code,
        detail={
            "error": exc.code,
            "message": exc.message,
            "details": exc.details,
        }
    )
