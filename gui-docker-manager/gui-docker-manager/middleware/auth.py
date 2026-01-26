"""
Authentication Middleware
File: gui-docker-manager/gui-docker-manager/middleware/auth.py
"""

import logging
from fastapi import Request, HTTPException
from typing import Callable

logger = logging.getLogger(__name__)


async def auth_middleware(request: Request, call_next: Callable) -> any:
    """
    Basic authentication middleware
    Can be extended to validate JWT tokens
    """
    # For now, allow all requests
    # In production, validate JWT tokens here
    response = await call_next(request)
    return response
