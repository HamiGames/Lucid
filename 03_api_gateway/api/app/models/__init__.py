"""
Models Package

File: 03_api_gateway/api/app/models/__init__.py
Purpose: Data models and validation schemas
"""

# Model imports will be added as they are implemented
# from .user import UserModel, UserRole
# from .session import SessionModel, SessionStatus
# from .auth import TokenPayload, AuthResponse
# from .common import ErrorResponse, ErrorDetail, PaginationInfo
from app.models.common import ServiceInfo, HealthStatus, ErrorResponse, ErrorDetail, PaginationInfo
__all__ = [
    'ServiceInfo', 
    'HealthStatus', 
    'ErrorResponse', 
    'ErrorDetail', 
    'PaginationInfo'
]

