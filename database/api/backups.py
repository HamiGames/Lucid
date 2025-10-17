"""
Database Backup Management API

Provides endpoints for database backup and restore operations:
- Create backups (MongoDB, Redis, Elasticsearch)
- List backups
- Restore from backups
- Delete backups
- Schedule automated backups

Port: 8088 (Storage-Database Cluster)
Phase: Phase 1 - Foundation
"""

from fastapi import APIRouter, HTTPException, Query, status
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from ..services.backup_service import BackupService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/database/backups",
    tags=["database-backups"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"}
    }
)

# Service instance
backup_service: BackupService = None


def init_service(backup: BackupService):
    """Initialize backup service instance"""
    global backup_service
    backup_service = backup


# Request/Response Models
class CreateBackupRequest(BaseModel):
    """Request model for creating a backup"""
    databases: List[str] = Field(..., description="List of databases to backup (mongodb, redis, elasticsearch)")
    backup_type: str = Field("full", description="Backup type: full or incremental")
    compress: bool = Field(True, description="Whether to compress the backup")
    encrypt: bool = Field(False, description="Whether to encrypt the backup")
    upload_to_s3: bool = Field(False, description="Whether to upload to S3")


class RestoreBackupRequest(BaseModel):
    """Request model for restoring from backup"""
    backup_id: str = Field(..., description="Backup ID to restore from")
    databases: Optional[List[str]] = Field(None, description="Specific databases to restore (default: all)")
    force: bool = Field(False, description="Force restore even if data exists")


@router.get("/", response_model=List[Dict[str, Any]])
async def list_backups(
    database: Optional[str] = Query(None, description="Filter by database (mongodb, redis, elasticsearch)"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of backups to return")
):
    """
    List all available backups
    
    Args:
        database: Optional filter by database type
        limit: Maximum number of backups to return
        
    Returns:
        List of backup metadata
    """
    try:
        if not backup_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Backup service not available"
            )
        
        backups = await backup_service.list_backups(database=database, limit=limit)
        
        return backups
        
    except Exception as e:
        logger.error(f"Error listing backups: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list backups: {str(e)}"
        )


@router.get("/{backup_id}", response_model=Dict[str, Any])
async def get_backup_info(backup_id: str):
    """
    Get information about a specific backup
    
    Args:
        backup_id: Backup identifier
        
    Returns:
        Backup metadata and status
    """
    try:
        if not backup_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Backup service not available"
            )
        
        backup_info = await backup_service.get_backup_info(backup_id)
        
        if not backup_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Backup '{backup_id}' not found"
            )
        
        return backup_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting backup info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get backup info: {str(e)}"
        )


@router.post("/", response_model=Dict[str, Any], status_code=status.HTTP_202_ACCEPTED)
async def create_backup(request: CreateBackupRequest):
    """
    Create a new backup
    
    Args:
        request: Backup creation request
        
    Returns:
        Backup job information
        
    Note:
        This operation is asynchronous. Use GET /backups/{backup_id} to check status.
    """
    try:
        if not backup_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Backup service not available"
            )
        
        # Validate databases
        valid_databases = ["mongodb", "redis", "elasticsearch"]
        for db in request.databases:
            if db not in valid_databases:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid database: {db}. Must be one of {valid_databases}"
                )
        
        # Create backup
        backup_job = await backup_service.create_backup(
            databases=request.databases,
            backup_type=request.backup_type,
            compress=request.compress,
            encrypt=request.encrypt,
            upload_to_s3=request.upload_to_s3
        )
        
        return {
            "success": True,
            "message": "Backup job created successfully",
            "backup_id": backup_job.get("backup_id"),
            "databases": request.databases,
            "status": "in_progress",
            "started_at": datetime.utcnow().isoformat() + "Z"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating backup: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create backup: {str(e)}"
        )


@router.post("/restore", response_model=Dict[str, Any], status_code=status.HTTP_202_ACCEPTED)
async def restore_backup(request: RestoreBackupRequest):
    """
    Restore from a backup
    
    Args:
        request: Restore request
        
    Returns:
        Restore job information
        
    Warning:
        This operation will overwrite existing data. Use with caution.
    """
    try:
        if not backup_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Backup service not available"
            )
        
        # Verify backup exists
        backup_info = await backup_service.get_backup_info(request.backup_id)
        if not backup_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Backup '{request.backup_id}' not found"
            )
        
        # Restore from backup
        restore_job = await backup_service.restore_backup(
            backup_id=request.backup_id,
            databases=request.databases,
            force=request.force
        )
        
        return {
            "success": True,
            "message": "Restore job started successfully",
            "backup_id": request.backup_id,
            "restore_job_id": restore_job.get("restore_job_id"),
            "databases": request.databases or backup_info.get("databases"),
            "status": "in_progress",
            "started_at": datetime.utcnow().isoformat() + "Z"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restoring backup: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restore backup: {str(e)}"
        )


@router.delete("/{backup_id}", response_model=Dict[str, Any])
async def delete_backup(backup_id: str):
    """
    Delete a backup
    
    Args:
        backup_id: Backup identifier
        
    Returns:
        Success message
    """
    try:
        if not backup_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Backup service not available"
            )
        
        # Verify backup exists
        backup_info = await backup_service.get_backup_info(backup_id)
        if not backup_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Backup '{backup_id}' not found"
            )
        
        # Delete backup
        result = await backup_service.delete_backup(backup_id)
        
        return {
            "success": True,
            "message": f"Backup '{backup_id}' deleted successfully",
            "backup_id": backup_id,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting backup: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete backup: {str(e)}"
        )


@router.post("/verify/{backup_id}", response_model=Dict[str, Any])
async def verify_backup(backup_id: str):
    """
    Verify backup integrity
    
    Args:
        backup_id: Backup identifier
        
    Returns:
        Verification results
    """
    try:
        if not backup_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Backup service not available"
            )
        
        # Verify backup exists
        backup_info = await backup_service.get_backup_info(backup_id)
        if not backup_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Backup '{backup_id}' not found"
            )
        
        # Verify backup
        verification_result = await backup_service.verify_backup(backup_id)
        
        return {
            "backup_id": backup_id,
            "valid": verification_result.get("valid", False),
            "checksum_match": verification_result.get("checksum_match", False),
            "files_verified": verification_result.get("files_verified", 0),
            "errors": verification_result.get("errors", []),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying backup: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify backup: {str(e)}"
        )


@router.post("/cleanup", response_model=Dict[str, Any])
async def cleanup_old_backups(retention_days: int = Query(30, ge=1, le=365)):
    """
    Clean up old backups based on retention policy
    
    Args:
        retention_days: Number of days to keep backups (default: 30)
        
    Returns:
        Cleanup summary
    """
    try:
        if not backup_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Backup service not available"
            )
        
        cleanup_result = await backup_service.cleanup_old_backups(retention_days)
        
        return {
            "success": True,
            "message": f"Cleaned up backups older than {retention_days} days",
            "retention_days": retention_days,
            "backups_deleted": cleanup_result.get("backups_deleted", 0),
            "space_freed_bytes": cleanup_result.get("space_freed_bytes", 0),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up backups: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup backups: {str(e)}"
        )


@router.get("/schedule/status", response_model=Dict[str, Any])
async def get_backup_schedule():
    """
    Get current backup schedule configuration
    
    Returns:
        Backup schedule information
    """
    try:
        if not backup_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Backup service not available"
            )
        
        schedule_info = await backup_service.get_backup_schedule()
        
        return {
            "enabled": schedule_info.get("enabled", False),
            "schedule": schedule_info.get("schedule", "0 2 * * *"),
            "retention_days": schedule_info.get("retention_days", 30),
            "databases": schedule_info.get("databases", ["mongodb", "redis", "elasticsearch"]),
            "next_run": schedule_info.get("next_run"),
            "last_run": schedule_info.get("last_run"),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error(f"Error getting backup schedule: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get backup schedule: {str(e)}"
        )

