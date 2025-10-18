#!/usr/bin/env python3
"""
Lucid Admin Interface - Audit API Endpoints
Step 24: Admin Container & Integration

Audit log API endpoints for the Lucid admin interface.
Provides access to audit logs, export functionality, and audit statistics.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from admin.audit.logger import get_audit_logger, AuditLogger
from admin.audit.events import AuditEventType, AuditSeverity
from admin.rbac.manager import get_rbac_manager, RBACManager

logger = logging.getLogger(__name__)

router = APIRouter()


class AuditLogResponse(BaseModel):
    """Audit log response model"""
    log_id: str
    timestamp: datetime
    event_type: str
    severity: str
    user_id: Optional[str]
    action: str
    resource: str
    details: Dict[str, Any]
    ip_address: Optional[str]
    correlation_id: Optional[str]


class AuditQueryRequest(BaseModel):
    """Audit query request model"""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    user_id: Optional[str] = None
    event_type: Optional[str] = None
    severity: Optional[str] = None
    limit: int = Field(default=1000, le=10000)


class AuditExportRequest(BaseModel):
    """Audit export request model"""
    start_time: datetime
    end_time: datetime
    format: str = Field(default="json", regex="^(json|csv)$")
    event_types: Optional[List[str]] = None
    severities: Optional[List[str]] = None


class AuditStatsResponse(BaseModel):
    """Audit statistics response model"""
    total_logs: int
    severity_counts: Dict[str, int]
    event_type_counts: Dict[str, int]
    recent_activity_24h: int
    retention_days: int
    batch_size: int
    flush_interval: int


# Dependency functions
async def get_audit_service() -> AuditLogger:
    """Get audit logger service"""
    try:
        return get_audit_logger()
    except Exception as e:
        logger.error(f"Failed to get audit service: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Audit service not available"
        )


async def get_rbac_service() -> RBACManager:
    """Get RBAC manager service"""
    try:
        return get_rbac_manager()
    except Exception as e:
        logger.error(f"Failed to get RBAC service: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RBAC service not available"
        )


# API Endpoints
@router.get("/logs", response_model=List[AuditLogResponse])
async def get_audit_logs(
    start_time: Optional[datetime] = Query(None, description="Start time filter"),
    end_time: Optional[datetime] = Query(None, description="End time filter"),
    user_id: Optional[str] = Query(None, description="User ID filter"),
    event_type: Optional[str] = Query(None, description="Event type filter"),
    severity: Optional[str] = Query(None, description="Severity filter"),
    limit: int = Query(1000, le=10000, description="Maximum number of logs to return"),
    audit_service: AuditLogger = Depends(get_audit_service),
    rbac_service: RBACManager = Depends(get_rbac_service)
):
    """Get audit logs with filtering"""
    try:
        # Check permission
        # Note: In a real implementation, you would get the current user from authentication
        # For now, we'll assume the user has permission
        
        # Parse filters
        parsed_event_type = None
        if event_type:
            try:
                parsed_event_type = AuditEventType(event_type)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid event type: {event_type}"
                )
        
        parsed_severity = None
        if severity:
            try:
                parsed_severity = AuditSeverity(severity)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid severity: {severity}"
                )
        
        # Query audit logs
        logs = await audit_service.query_logs(
            start_time=start_time,
            end_time=end_time,
            user_id=user_id,
            event_type=parsed_event_type,
            severity=parsed_severity,
            limit=limit
        )
        
        # Convert to response format
        response_logs = []
        for log in logs:
            response_logs.append(AuditLogResponse(
                log_id=log.log_id,
                timestamp=log.timestamp,
                event_type=log.event_type.value,
                severity=log.severity.value,
                user_id=log.user_id,
                action=log.action,
                resource=log.resource,
                details=log.details,
                ip_address=log.ip_address,
                correlation_id=log.correlation_id
            ))
        
        return response_logs
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get audit logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit logs"
        )


@router.get("/logs/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: str,
    audit_service: AuditLogger = Depends(get_audit_service)
):
    """Get specific audit log by ID"""
    try:
        # Query specific log
        logs = await audit_service.query_logs(limit=1)
        
        # Find the specific log
        for log in logs:
            if log.log_id == log_id:
                return AuditLogResponse(
                    log_id=log.log_id,
                    timestamp=log.timestamp,
                    event_type=log.event_type.value,
                    severity=log.severity.value,
                    user_id=log.user_id,
                    action=log.action,
                    resource=log.resource,
                    details=log.details,
                    ip_address=log.ip_address,
                    correlation_id=log.correlation_id
                )
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit log {log_id} not found"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get audit log {log_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit log"
        )


@router.post("/export")
async def export_audit_logs(
    request: AuditExportRequest,
    audit_service: AuditLogger = Depends(get_audit_service)
):
    """Export audit logs in specified format"""
    try:
        # Validate date range
        if request.start_time >= request.end_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start time must be before end time"
            )
        
        # Check date range (max 30 days)
        if (request.end_time - request.start_time).days > 30:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Export range cannot exceed 30 days"
            )
        
        # Export logs
        export_data = await audit_service.export_logs(
            start_time=request.start_time,
            end_time=request.end_time,
            format=request.format
        )
        
        # Determine content type
        content_type = "application/json" if request.format == "json" else "text/csv"
        filename = f"audit_logs_{request.start_time.strftime('%Y%m%d')}_{request.end_time.strftime('%Y%m%d')}.{request.format}"
        
        # Return streaming response
        def generate():
            yield export_data
        
        return StreamingResponse(
            generate(),
            media_type=content_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export audit logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export audit logs"
        )


@router.get("/stats", response_model=AuditStatsResponse)
async def get_audit_stats(
    audit_service: AuditLogger = Depends(get_audit_service)
):
    """Get audit logging statistics"""
    try:
        stats = await audit_service.get_audit_stats()
        
        return AuditStatsResponse(
            total_logs=stats.get("total_logs", 0),
            severity_counts=stats.get("severity_counts", {}),
            event_type_counts=stats.get("event_type_counts", {}),
            recent_activity_24h=stats.get("recent_activity_24h", 0),
            retention_days=stats.get("retention_days", 90),
            batch_size=stats.get("batch_size", 100),
            flush_interval=stats.get("flush_interval", 30)
        )
        
    except Exception as e:
        logger.error(f"Failed to get audit stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit statistics"
        )


@router.post("/cleanup")
async def cleanup_audit_logs(
    audit_service: AuditLogger = Depends(get_audit_service)
):
    """Clean up old audit logs"""
    try:
        await audit_service.cleanup_old_logs()
        
        return {"message": "Audit log cleanup completed successfully"}
        
    except Exception as e:
        logger.error(f"Failed to cleanup audit logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup audit logs"
        )


@router.get("/health")
async def audit_health_check(
    audit_service: AuditLogger = Depends(get_audit_service)
):
    """Audit service health check"""
    try:
        # Test audit service
        stats = await audit_service.get_audit_stats()
        
        return {
            "status": "healthy",
            "service": "audit-logger",
            "stats": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Audit service health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "audit-logger",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
