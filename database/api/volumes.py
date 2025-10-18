"""
Database Volume Management API

Provides endpoints for managing storage volumes:
- List volumes
- Create volumes
- Volume usage statistics
- Volume backup and migration
- Volume health monitoring

Port: 8088 (Storage-Database Cluster)
Phase: Phase 1 - Foundation
"""

from fastapi import APIRouter, HTTPException, Query, status
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from ..services.volume_service import VolumeService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/database/volumes",
    tags=["database-volumes"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"}
    }
)

# Service instance
volume_service: VolumeService = None


def init_service(volume: VolumeService):
    """Initialize volume service instance"""
    global volume_service
    volume_service = volume


# Request/Response Models
class CreateVolumeRequest(BaseModel):
    """Request model for creating a volume"""
    name: str = Field(..., description="Volume name")
    size: str = Field(..., description="Volume size (e.g., '10G', '100M')")
    volume_type: str = Field(..., description="Volume type (mongodb, redis, elasticsearch, sessions, chunks, merkle, blocks, logs, backups)")
    mount_path: Optional[str] = Field(None, description="Custom mount path")


class ResizeVolumeRequest(BaseModel):
    """Request model for resizing a volume"""
    name: str = Field(..., description="Volume name")
    new_size: str = Field(..., description="New volume size")


@router.get("/", response_model=List[Dict[str, Any]])
async def list_volumes():
    """
    List all storage volumes
    
    Returns:
        List of volume information including usage and health
    """
    try:
        if not volume_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Volume service not available"
            )
        
        volumes = await volume_service.list_volumes()
        
        return volumes
        
    except Exception as e:
        logger.error(f"Error listing volumes: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list volumes: {str(e)}"
        )


@router.get("/{volume_name}", response_model=Dict[str, Any])
async def get_volume_info(volume_name: str):
    """
    Get information about a specific volume
    
    Args:
        volume_name: Name of the volume
        
    Returns:
        Volume information including usage, health, and configuration
    """
    try:
        if not volume_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Volume service not available"
            )
        
        # Check if volume exists
        exists = await volume_service.volume_exists(volume_name)
        if not exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Volume '{volume_name}' not found"
            )
        
        # Get volume info
        volume_info = await volume_service.get_volume_info(volume_name)
        
        return volume_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting volume info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get volume info: {str(e)}"
        )


@router.get("/{volume_name}/usage", response_model=Dict[str, Any])
async def get_volume_usage(volume_name: str):
    """
    Get volume usage statistics
    
    Args:
        volume_name: Name of the volume
        
    Returns:
        Volume usage information including used space, free space, and percentage
    """
    try:
        if not volume_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Volume service not available"
            )
        
        # Check if volume exists
        exists = await volume_service.volume_exists(volume_name)
        if not exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Volume '{volume_name}' not found"
            )
        
        # Get volume usage
        usage = await volume_service.get_volume_usage(volume_name)
        
        return {
            "volume": volume_name,
            "usage": usage,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting volume usage: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get volume usage: {str(e)}"
        )


@router.get("/{volume_name}/health", response_model=Dict[str, Any])
async def check_volume_health(volume_name: str):
    """
    Check volume health status
    
    Args:
        volume_name: Name of the volume
        
    Returns:
        Volume health status and diagnostics
    """
    try:
        if not volume_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Volume service not available"
            )
        
        # Check if volume exists
        exists = await volume_service.volume_exists(volume_name)
        if not exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Volume '{volume_name}' not found"
            )
        
        # Check health
        health = await volume_service.check_volume_health(volume_name)
        
        return {
            "volume": volume_name,
            "health": health,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking volume health: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check volume health: {str(e)}"
        )


@router.get("/{volume_name}/performance", response_model=Dict[str, Any])
async def get_volume_performance(volume_name: str):
    """
    Get volume performance metrics
    
    Args:
        volume_name: Name of the volume
        
    Returns:
        Volume performance metrics including I/O stats
    """
    try:
        if not volume_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Volume service not available"
            )
        
        # Check if volume exists
        exists = await volume_service.volume_exists(volume_name)
        if not exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Volume '{volume_name}' not found"
            )
        
        # Get performance metrics
        performance = await volume_service.get_volume_performance(volume_name)
        
        return {
            "volume": volume_name,
            "performance": performance,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting volume performance: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get volume performance: {str(e)}"
        )


@router.post("/", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_volume(request: CreateVolumeRequest):
    """
    Create a new storage volume
    
    Args:
        request: Volume creation request
        
    Returns:
        Created volume information
    """
    try:
        if not volume_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Volume service not available"
            )
        
        # Check if volume already exists
        exists = await volume_service.volume_exists(request.name)
        if exists:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Volume '{request.name}' already exists"
            )
        
        # Validate volume type
        valid_types = ["mongodb", "redis", "elasticsearch", "sessions", "chunks", "merkle", "blocks", "logs", "backups"]
        if request.volume_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid volume type. Must be one of: {valid_types}"
            )
        
        # Create volume
        result = await volume_service.create_volume(
            request.name,
            request.size,
            request.volume_type,
            request.mount_path
        )
        
        return {
            "success": True,
            "message": f"Volume '{request.name}' created successfully",
            "volume": result,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating volume: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create volume: {str(e)}"
        )


@router.delete("/{volume_name}", response_model=Dict[str, Any])
async def delete_volume(volume_name: str):
    """
    Delete a storage volume
    
    Args:
        volume_name: Name of the volume to delete
        
    Warning:
        This operation will delete all data in the volume. Use with caution.
        
    Returns:
        Success message
    """
    try:
        if not volume_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Volume service not available"
            )
        
        # Check if volume exists
        exists = await volume_service.volume_exists(volume_name)
        if not exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Volume '{volume_name}' not found"
            )
        
        # Delete volume
        result = await volume_service.delete_volume(volume_name)
        
        return {
            "success": True,
            "message": f"Volume '{volume_name}' deleted successfully",
            "volume": volume_name,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting volume: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete volume: {str(e)}"
        )


@router.post("/resize", response_model=Dict[str, Any])
async def resize_volume(request: ResizeVolumeRequest):
    """
    Resize a storage volume
    
    Args:
        request: Resize volume request
        
    Returns:
        Success message
    """
    try:
        if not volume_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Volume service not available"
            )
        
        # Check if volume exists
        exists = await volume_service.volume_exists(request.name)
        if not exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Volume '{request.name}' not found"
            )
        
        # Resize volume
        result = await volume_service.resize_volume(request.name, request.new_size)
        
        return {
            "success": True,
            "message": f"Volume '{request.name}' resized successfully",
            "volume": request.name,
            "new_size": request.new_size,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resizing volume: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resize volume: {str(e)}"
        )


@router.post("/{volume_name}/backup", response_model=Dict[str, Any], status_code=status.HTTP_202_ACCEPTED)
async def backup_volume(volume_name: str, output_path: Optional[str] = Query(None)):
    """
    Create a backup of a volume
    
    Args:
        volume_name: Name of the volume to backup
        output_path: Optional custom output path for backup
        
    Returns:
        Backup job information
    """
    try:
        if not volume_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Volume service not available"
            )
        
        # Check if volume exists
        exists = await volume_service.volume_exists(volume_name)
        if not exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Volume '{volume_name}' not found"
            )
        
        # Create backup
        backup_result = await volume_service.backup_volume(volume_name, output_path)
        
        return {
            "success": True,
            "message": f"Volume backup started for '{volume_name}'",
            "volume": volume_name,
            "backup_id": backup_result.get("backup_id"),
            "output_path": backup_result.get("output_path"),
            "status": "in_progress",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error backing up volume: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to backup volume: {str(e)}"
        )


@router.post("/{volume_name}/cleanup", response_model=Dict[str, Any])
async def cleanup_volume(volume_name: str):
    """
    Clean up temporary files and optimize a volume
    
    Args:
        volume_name: Name of the volume to clean up
        
    Returns:
        Cleanup summary
    """
    try:
        if not volume_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Volume service not available"
            )
        
        # Check if volume exists
        exists = await volume_service.volume_exists(volume_name)
        if not exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Volume '{volume_name}' not found"
            )
        
        # Cleanup volume
        cleanup_result = await volume_service.cleanup_volume(volume_name)
        
        return {
            "success": True,
            "message": f"Volume '{volume_name}' cleaned up successfully",
            "volume": volume_name,
            "space_freed_bytes": cleanup_result.get("space_freed_bytes", 0),
            "files_deleted": cleanup_result.get("files_deleted", 0),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cleaning up volume: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup volume: {str(e)}"
        )

