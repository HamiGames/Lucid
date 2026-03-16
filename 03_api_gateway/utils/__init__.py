"""
Lucid API Gateway - Utilities Package
Utility functions and helpers.
file: 03_api_gateway/utils/__init__.py
the utils calls the api gateway utils
"""
from api.app.config import get_settings

__all__ = [
    "get_settings"
]