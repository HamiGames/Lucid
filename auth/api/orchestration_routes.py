"""
Lucid Authentication Service - Service Orchestration Routes
API endpoints for spawning and managing services

File: auth/api/orchestration_routes.py
Purpose: HTTP endpoints for service orchestration (spawning MongoDB clones, etc.)
Dependencies: fastapi, Request, HTTPException, orchestrator
"""

from fastapi import APIRouter, HTTPException, status, Request
from typing import List, Optional
from auth.models.permissions import Permission
from auth.permissions import RBACManager
from auth.main import rbac_manager
from auth.services.orchestrator import ServiceOrchestrator
from auth.services.mongodb_clone import MongoDBCloneManager
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize orchestrator (disabled by default for security)
# Enable via environment variable: ENABLE_SERVICE_ORCHESTRATION=true
orchestrator = ServiceOrchestrator(
    enabled=os.getenv("ENABLE_SERVICE_ORCHESTRATION", "false").lower() == "true"
)
mongodb_clone_manager = MongoDBCloneManager(orchestrator)


def get_current_user_id(request: Request) -> str:
    """Extract current user ID from request state (set by AuthMiddleware)"""
    if not hasattr(request.state, 'user_id') or not request.state.authenticated:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return request.state.user_id


async def check_orchestration_permission(user_id: str, permission: Permission) -> bool:
    """Check if user has orchestration permission"""
    if not rbac_manager:
        return False
    return await rbac_manager.check_permission(user_id, permission)


# Request/Response Models
class SpawnMongoDBCloneRequest(BaseModel):
    """Request to spawn MongoDB clone for a node"""
    node_id: str = Field(..., description="Node ID")
    node_tron_address: str = Field(..., description="Node's TRON address")
    port: Optional[int] = Field(None, description="MongoDB port (auto-assign if not specified)")
    ip_address: Optional[str] = Field(None, description="Static IP address (optional)")
    network: str = Field(default="lucid-pi-network", description="Docker network name")
    resource_limits: Optional[dict] = Field(None, description="Resource limits (memory, CPU)")


class MongoDBCloneResponse(BaseModel):
    """Response for MongoDB clone creation"""
    clone_id: str
    node_id: str
    instance_name: str
    mongodb_uri: str
    database_name: str
    status: str
    created_at: str
    service_info: dict


class ServiceStatusResponse(BaseModel):
    """Response for service status"""
    service_id: str
    status: str
    container_name: Optional[str] = None
    health: Optional[str] = None


@router.post("/mongodb/clone", response_model=MongoDBCloneResponse, status_code=status.HTTP_201_CREATED)
async def spawn_mongodb_clone(request: SpawnMongoDBCloneRequest, http_request: Request):
    """
    Spawn a MongoDB clone instance for a node.
    
    Requires ADMIN or SUPER_ADMIN role with SPAWN_SERVICES permission.
    """
    try:
        user_id = get_current_user_id(http_request)
        
        # Check permission
        has_permission = await check_orchestration_permission(user_id, Permission.SPAWN_SERVICES)
        if not has_permission:
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions: SPAWN_SERVICES required"
            )
        
        # Check if orchestration is enabled
        if not orchestrator.is_enabled():
            raise HTTPException(
                status_code=503,
                detail="Service orchestration is disabled. Set ENABLE_SERVICE_ORCHESTRATION=true to enable."
            )
        
        logger.info(f"User {user_id} requesting MongoDB clone for node {request.node_id}")
        
        # Create MongoDB clone
        clone_info = await mongodb_clone_manager.create_node_mongodb(
            node_id=request.node_id,
            node_tron_address=request.node_tron_address,
            port=request.port,
            network=request.network,
            ip_address=request.ip_address
        )
        
        return MongoDBCloneResponse(**clone_info)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error spawning MongoDB clone: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to spawn MongoDB clone: {str(e)}")


@router.get("/mongodb/clones", response_model=List[MongoDBCloneResponse])
async def list_mongodb_clones(http_request: Request):
    """
    List all MongoDB clones.
    
    Requires ADMIN or SUPER_ADMIN role with VIEW_SPAWNED_SERVICES permission.
    """
    try:
        user_id = get_current_user_id(http_request)
        
        # Check permission
        has_permission = await check_orchestration_permission(user_id, Permission.VIEW_SPAWNED_SERVICES)
        if not has_permission:
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions: VIEW_SPAWNED_SERVICES required"
            )
        
        clones = await mongodb_clone_manager.list_node_clones()
        return [MongoDBCloneResponse(**clone) for clone in clones]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing MongoDB clones: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/mongodb/clones/{node_id}", response_model=MongoDBCloneResponse)
async def get_mongodb_clone(node_id: str, http_request: Request):
    """
    Get MongoDB clone information for a node.
    
    Requires ADMIN or SUPER_ADMIN role with VIEW_SPAWNED_SERVICES permission.
    """
    try:
        user_id = get_current_user_id(http_request)
        
        # Check permission
        has_permission = await check_orchestration_permission(user_id, Permission.VIEW_SPAWNED_SERVICES)
        if not has_permission:
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions: VIEW_SPAWNED_SERVICES required"
            )
        
        clone_info = await mongodb_clone_manager.get_node_mongodb(node_id)
        if not clone_info:
            raise HTTPException(status_code=404, detail=f"MongoDB clone not found for node {node_id}")
        
        return MongoDBCloneResponse(**clone_info)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting MongoDB clone: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/mongodb/clones/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_mongodb_clone(node_id: str, http_request: Request):
    """
    Remove MongoDB clone for a node.
    
    Requires ADMIN or SUPER_ADMIN role with MANAGE_SERVICE_LIFECYCLE permission.
    """
    try:
        user_id = get_current_user_id(http_request)
        
        # Check permission
        has_permission = await check_orchestration_permission(user_id, Permission.MANAGE_SERVICE_LIFECYCLE)
        if not has_permission:
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions: MANAGE_SERVICE_LIFECYCLE required"
            )
        
        success = await mongodb_clone_manager.remove_node_mongodb(node_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"MongoDB clone not found for node {node_id}")
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing MongoDB clone: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/mongodb/clones/{node_id}/health")
async def check_mongodb_clone_health(node_id: str, http_request: Request):
    """
    Check health of MongoDB clone for a node.
    
    Requires ADMIN or SUPER_ADMIN role with VIEW_SPAWNED_SERVICES permission.
    """
    try:
        user_id = get_current_user_id(http_request)
        
        # Check permission
        has_permission = await check_orchestration_permission(user_id, Permission.VIEW_SPAWNED_SERVICES)
        if not has_permission:
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions: VIEW_SPAWNED_SERVICES required"
            )
        
        health = await mongodb_clone_manager.health_check(node_id)
        return health
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking MongoDB clone health: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/services/spawned", response_model=List[dict])
async def list_spawned_services(http_request: Request, node_id: Optional[str] = None):
    """
    List all spawned services, optionally filtered by node_id.
    
    Requires ADMIN or SUPER_ADMIN role with VIEW_SPAWNED_SERVICES permission.
    """
    try:
        user_id = get_current_user_id(http_request)
        
        # Check permission
        has_permission = await check_orchestration_permission(user_id, Permission.VIEW_SPAWNED_SERVICES)
        if not has_permission:
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions: VIEW_SPAWNED_SERVICES required"
            )
        
        services = await orchestrator.list_spawned_services(node_id=node_id)
        return services
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing spawned services: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/services/{service_id}/status", response_model=ServiceStatusResponse)
async def get_service_status(service_id: str, http_request: Request):
    """
    Get status of a spawned service.
    
    Requires ADMIN or SUPER_ADMIN role with VIEW_SPAWNED_SERVICES permission.
    """
    try:
        user_id = get_current_user_id(http_request)
        
        # Check permission
        has_permission = await check_orchestration_permission(user_id, Permission.VIEW_SPAWNED_SERVICES)
        if not has_permission:
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions: VIEW_SPAWNED_SERVICES required"
            )
        
        status_info = await orchestrator.get_service_status(service_id)
        if not status_info:
            raise HTTPException(status_code=404, detail=f"Service {service_id} not found")
        
        return ServiceStatusResponse(**status_info)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting service status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/services/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_service(service_id: str, http_request: Request):
    """
    Remove a spawned service.
    
    Requires ADMIN or SUPER_ADMIN role with MANAGE_SERVICE_LIFECYCLE permission.
    """
    try:
        user_id = get_current_user_id(http_request)
        
        # Check permission
        has_permission = await check_orchestration_permission(user_id, Permission.MANAGE_SERVICE_LIFECYCLE)
        if not has_permission:
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions: MANAGE_SERVICE_LIFECYCLE required"
            )
        
        success = await orchestrator.remove_service(service_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Service {service_id} not found")
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing service: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# Note: Router is included in auth/api/__init__.py conditionally
# based on ENABLE_SERVICE_ORCHESTRATION environment variable

