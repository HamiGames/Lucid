"""
Lucid API Gateway - Middleware Package
File: 03-api-gateway/middleware/__init__.py
Purpose: Re-exports middleware from api/app/middleware for backwards compatibility.

Note: Primary middleware implementations are in api/app/middleware/
This package provides top-level access for import convenience.
"""

__version__ = "1.0.0"

# Re-export from actual middleware location
# Middleware is loaded via api.app.middleware in main.py

__all__ = []

