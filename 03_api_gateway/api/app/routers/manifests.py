"""
Manifest Endpoints Router

File: 03_api_gateway/api/app/routers/manifests.py
Purpose: Session manifest operations
"""

import os 
from api.app.config import get_settings

try:
    from api.app.utils.logging import get_logger
    logger = get_logger("LOG_LEVEL", "INFO", optional=[get_settings()])
except ImportError:
    import logging
    logger = logging.getLogger("LOG_LEVEL", "INFO", optional=[get_settings()])
    

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/{manifest_id}")
async def get_manifest(manifest_id: str):
    """Get manifest details"""
    # TODO: Implement get manifest
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.post("")
async def create_manifest():
    """Create new manifest"""
    # TODO: Implement create manifest
    raise HTTPException(status_code=501, detail="Not implemented yet")

