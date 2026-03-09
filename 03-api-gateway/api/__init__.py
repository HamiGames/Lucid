#!/usr/bin/env python3

"""
Lucid API Gateway - API Package
File: 03-api-gateway/api/__init__.py
Purpose: Re-exports API from api/app for backwards compatibility.
"""

from ..api.app import *

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
    "app.routes"
    ]
