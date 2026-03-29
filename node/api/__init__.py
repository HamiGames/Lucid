# Path: node/api/__init__.py
# Lucid Node Management API Package
# Based on LUCID-STRICT requirements per Spec-1c

"""
File: /app/node/api/__init__.py
x-lucid-file-path: /app/node/api/__init__.py
x-lucid-file-type: python

Lucid Node Management API Package

This package provides REST API endpoints for:
- Node lifecycle management (CRUD operations)
- Pool management and assignment
- Resource monitoring and metrics
- PoOT (Proof of Output) validation
- Payout processing and management

API Version: 1.0.0
Base URL: https://node-management.lucid.onion/api/v1
Port: 8095
"""

from ..api.routes import router as api_router
from ..api.nodes import router as nodes_router
from ..api.pools import router as pools_router
from ..api.resources import router as resources_router
from ..api.payouts import router as payouts_router
from ..api.poot import router as poot_router

__all__ = [
    "api_router",
    "nodes_router", 
    "pools_router",
    "resources_router",
    "payouts_router",
    "poot_router"
]

__version__ = "1.0.0"
__author__ = "Lucid Development Team"
__description__ = "Lucid Node Management API"
