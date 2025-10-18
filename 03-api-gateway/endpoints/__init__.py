"""
API Gateway Endpoints Package

This package contains all endpoint implementations for the Lucid API Gateway.
Each module corresponds to a specific endpoint category as defined in the
API specification.

Endpoint Categories:
- meta: Service metadata, health checks, version info
- auth: Authentication and authorization endpoints
- users: User management operations
- sessions: Session lifecycle management  
- manifests: Session manifest operations
- trust: Trust policy management
- chain: Blockchain proxy endpoints

All endpoints follow RESTful conventions and return standardized responses.
"""

__version__ = "1.0.0"
__all__ = [
    "meta",
    "auth",
    "users",
    "sessions",
    "manifests",
    "trust",
    "chain",
]

