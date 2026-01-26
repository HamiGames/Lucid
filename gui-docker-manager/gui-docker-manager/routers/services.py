"""
Service Group Management Routers
File: gui-docker-manager/gui-docker-manager/routers/services.py
"""

import logging
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any

logger = logging.getLogger(__name__)
router = APIRouter()


# Dependency to get docker manager from app state
async def get_docker_manager():
    """Dependency to get Docker manager instance"""
    from ..main import docker_manager
    if not docker_manager:
        raise HTTPException(status_code=503, detail="Docker Manager not initialized")
    return docker_manager


# Service group configuration from gui-docker-manager.yml
SERVICE_GROUPS = {
    "foundation": {
        "name": "Foundation Services",
        "description": "Database, authentication, and core infrastructure",
        "services": ["lucid-mongodb", "lucid-redis", "lucid-elasticsearch", "lucid-auth-service"]
    },
    "core": {
        "name": "Core Services",
        "description": "API gateway, blockchain core, and service mesh",
        "services": ["lucid-api-gateway", "lucid-blockchain-engine"]
    },
    "application": {
        "name": "Application Services",
        "description": "Session management, RDP services, and node management",
        "services": ["lucid-session-pipeline", "lucid-node-management"]
    },
    "support": {
        "name": "Support Services",
        "description": "Admin interface and TRON payment services",
        "services": ["lucid-admin-interface", "lucid-tron-client"]
    }
}


@router.get("")
async def list_services():
    """List all service groups"""
    return {
        "status": "success",
        "data": SERVICE_GROUPS,
        "count": len(SERVICE_GROUPS)
    }


@router.get("/{group_name}")
async def get_service_group(group_name: str):
    """Get service group details"""
    if group_name not in SERVICE_GROUPS:
        raise HTTPException(status_code=404, detail=f"Service group {group_name} not found")
    
    return {
        "status": "success",
        "data": SERVICE_GROUPS[group_name]
    }


@router.post("/{group_name}/start")
async def start_service_group(group_name: str, manager = Depends(get_docker_manager)):
    """Start all containers in a service group"""
    if group_name not in SERVICE_GROUPS:
        raise HTTPException(status_code=404, detail=f"Service group {group_name} not found")
    
    try:
        group = SERVICE_GROUPS[group_name]
        results = []
        
        for service_name in group["services"]:
            try:
                result = await manager.start_container(service_name)
                results.append({"service": service_name, "status": "started"})
            except Exception as e:
                logger.warning(f"Failed to start {service_name}: {e}")
                results.append({"service": service_name, "status": "failed", "error": str(e)})
        
        return {
            "status": "success",
            "data": {
                "group": group_name,
                "results": results
            }
        }
    except Exception as e:
        logger.error(f"Failed to start service group {group_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{group_name}/stop")
async def stop_service_group(group_name: str, timeout: int = 10, manager = Depends(get_docker_manager)):
    """Stop all containers in a service group"""
    if group_name not in SERVICE_GROUPS:
        raise HTTPException(status_code=404, detail=f"Service group {group_name} not found")
    
    try:
        group = SERVICE_GROUPS[group_name]
        results = []
        
        # Stop in reverse order for dependencies
        for service_name in reversed(group["services"]):
            try:
                result = await manager.stop_container(service_name, timeout=timeout)
                results.append({"service": service_name, "status": "stopped"})
            except Exception as e:
                logger.warning(f"Failed to stop {service_name}: {e}")
                results.append({"service": service_name, "status": "failed", "error": str(e)})
        
        return {
            "status": "success",
            "data": {
                "group": group_name,
                "results": results
            }
        }
    except Exception as e:
        logger.error(f"Failed to stop service group {group_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
