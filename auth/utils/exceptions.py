"""
Lucid Authentication Service - Custom Exceptions
"""


class AuthenticationError(Exception):
    """Base authentication error"""
    def __init__(self, message: str, code: str = "LUCID_ERR_2000"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class TokenExpiredError(AuthenticationError):
    """Token has expired"""
    def __init__(self, message: str = "Token has expired"):
        super().__init__(message, code="LUCID_ERR_2002")


class InvalidTokenError(AuthenticationError):
    """Token is invalid"""
    def __init__(self, message: str = "Invalid token"):
        super().__init__(message, code="LUCID_ERR_2003")


class SessionNotFoundError(AuthenticationError):
    """Session not found"""
    def __init__(self, message: str = "Session not found"):
        super().__init__(message, code="LUCID_ERR_2004")


class MaxSessionsExceededError(AuthenticationError):
    """Maximum concurrent sessions exceeded"""
    def __init__(self, message: str = "Maximum concurrent sessions exceeded"):
        super().__init__(message, code="LUCID_ERR_2005")


class InvalidSignatureError(AuthenticationError):
    """Signature verification failed"""
    def __init__(self, message: str = "Invalid signature"):
        super().__init__(message, code="LUCID_ERR_2006")


class HardwareWalletError(AuthenticationError):
    """Hardware wallet operation failed"""
    def __init__(self, message: str = "Hardware wallet error"):
        super().__init__(message, code="LUCID_ERR_2007")


class UserNotFoundError(AuthenticationError):
    """User not found"""
    def __init__(self, message: str = "User not found"):
        super().__init__(message, code="LUCID_ERR_2008")


class PermissionDeniedError(AuthenticationError):
    """Permission denied"""
    def __init__(self, message: str = "Permission denied"):
        super().__init__(message, code="LUCID_ERR_2009")


class AccountLockedError(AuthenticationError):
    """Account is locked"""
    def __init__(self, message: str = "Account is locked"):
        super().__init__(message, code="LUCID_ERR_2010")


class InvalidCredentialsError(AuthenticationError):
    """Invalid credentials"""
    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(message, code="LUCID_ERR_2011")

