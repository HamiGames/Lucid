"""
Docker Compose Management Routers
File: gui-docker-manager/gui-docker-manager/routers/compose.py
"""

import logging
import subprocess
import os
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any

logger = logging.getLogger(__name__)
router = APIRouter()


# Dependency to get docker manager from app state
async def get_docker_manager():
    """Dependency to get Docker manager instance"""
    from ..main import docker_manager
    if not docker_manager:
        raise HTTPException(status_code=503, detail="Docker Manager not initialized")
    return docker_manager


@router.post("/up")
async def compose_up(compose_file: str = "docker-compose.gui-integration.yml", manager = Depends(get_docker_manager)):
    """Start docker-compose project"""
    try:
        compose_path = f"/mnt/myssd/Lucid/Lucid/configs/docker/{compose_file}"
        
        # Use docker-compose CLI
        result = subprocess.run(
            ["docker-compose", "-f", compose_path, "up", "-d"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            raise Exception(result.stderr)
        
        return {
            "status": "success",
            "message": f"Started {compose_file}",
            "output": result.stdout
        }
    except Exception as e:
        logger.error(f"Failed to start compose: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/down")
async def compose_down(compose_file: str = "docker-compose.gui-integration.yml", manager = Depends(get_docker_manager)):
    """Stop docker-compose project"""
    try:
        compose_path = f"/mnt/myssd/Lucid/Lucid/configs/docker/{compose_file}"
        
        # Use docker-compose CLI
        result = subprocess.run(
            ["docker-compose", "-f", compose_path, "down"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            raise Exception(result.stderr)
        
        return {
            "status": "success",
            "message": f"Stopped {compose_file}",
            "output": result.stdout
        }
    except Exception as e:
        logger.error(f"Failed to stop compose: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def compose_status(compose_file: str = "docker-compose.gui-integration.yml", manager = Depends(get_docker_manager)):
    """Get docker-compose project status"""
    try:
        containers = await manager.list_containers(all=False)
        
        return {
            "status": "success",
            "data": {
                "compose_file": compose_file,
                "running_containers": len(containers),
                "containers": containers
            }
        }
    except Exception as e:
        logger.error(f"Failed to get compose status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
