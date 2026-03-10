#!/usr/bin/env python3

"""
Lucid API Gateway - API Package
File: 03_api_gateway/api/__init__.py
Purpose: Re-exports API from api/app for backwards compatibility.
"""

from ..api.app import *
from ..api.app.config import Settings
settings = Settings()
__all__ = [
    "app",
    "app.middleware",
    "app.routes",
    "app.schemas",
    "app.services",
    "app.utils",
    "app.database",
    "app.db",
    "app.scripts",
    "app.security",
    "app.routes",
    "app.schemas",
    "app.services",
    "app.utils",
    "app.database",
    "app.db",
    "app.scripts",
    "app.security",
    "app.routes",
    "settings",
    "Settings"
    ]
