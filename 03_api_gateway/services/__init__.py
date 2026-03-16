"""
Lucid API Gateway - Services Package
Service layer for API Gateway operations.

file: 03_api_gateway/services/__init__.py
the services calls the api gateway services
"""
from api.app.config import get_settings

__all__ = [
    "get_settings"
]