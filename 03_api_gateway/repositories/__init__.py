"""
File: /app/03_api_gateway/repositories/__init__.py
x-lucid-file-path: /app/03_api_gateway/repositories/__init__.py
x-lucid-file-type: python

Lucid API Gateway - Repositories Package
Data access layer repositories.
the repositories calls the api gateway repositories
"""
from api.app.config import get_settings

__all__ = [
    "get_settings"
]