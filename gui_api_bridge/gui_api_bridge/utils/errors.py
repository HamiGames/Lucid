"""
Error Handling Utilities
File: /app/gui_api_bridge/gui_api_bridge/utils/errors.py
x-lucid-file-path: /app/gui_api_bridge/gui_api_bridge/utils/errors.py
x-lucid-file-type: python
"""


class GuiAPIBridgeError(Exception):
    """Base exception for GUI API Bridge"""
    pass


class ServiceUnavailableError(GuiAPIBridgeError):
    """Backend service unavailable"""
    pass


class InvalidTokenError(GuiAPIBridgeError):
    """Invalid JWT token"""
    pass


class AuthorizationError(GuiAPIBridgeError):
    """User not authorized"""
    pass


class ValidationError(GuiAPIBridgeError):
    """Request validation failed"""
    pass


class SessionRecoveryError(GuiAPIBridgeError):
    """Session recovery failed"""
    pass
