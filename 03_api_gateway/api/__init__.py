#!/usr/bin/env python3

"""
Lucid API Gateway - API Package
File: 03_api_gateway/api/__init__.py
Purpose: Re-exports API from api/app for backwards compatibility.
"""

from app import *
from app.config import Settings
from app.utils.logging import get_logger
from app.middleware import *

logger = get_logger(__name__)

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
    "app.database","logger", "get_logger",
    "app.db",
    "app.scripts",
    "app.security",
    "app.routes",
    "settings",
    "Settings"
    ]
