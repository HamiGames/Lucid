"""
Lucid API Gateway - Repositories Package
Data access layer repositories.
file: 03_api_gateway/repositories/__init__.py
the repositories calls the api gateway repositories
"""
from api.app.config import get_settings

__all__ = [
    "get_settings"
]