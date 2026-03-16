"""
Manifest Endpoints Router

File: 03_api_gateway/api/app/routers/manifests.py
Purpose: Session manifest operations
"""

import os 
from ..config import get_settings, Settings
log_level = os.getenv(get_settings().LOG_LEVEL(), "INFO").upper()
settings = os.getenv(Settings().LOG_LEVEL(), "INFO").upper()
try:
    from ..utils.logging import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


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

