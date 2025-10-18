#!/usr/bin/env python3
"""
Lucid Admin Interface - Emergency API Endpoints
Step 24: Admin Container & Integration

Emergency controls API endpoints for the Lucid admin interface.
Provides emergency response capabilities and system lockdown controls.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field

from admin.emergency.controls import get_emergency_controller, EmergencyController, EmergencyAction, EmergencyStatus
from admin.rbac.manager import get_rbac_manager, RBACManager

logger = logging.getLogger(__name__)

router = APIRouter()


class EmergencyTriggerRequest(BaseModel):
    """Emergency trigger request model"""
    action: str = Field(..., description="Emergency action to trigger")
    reason: str = Field(..., description="Reason for emergency action")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional details")
    severity: str = Field(default="critical", description="Emergency severity level")


class EmergencyResolveRequest(BaseModel):
    """Emergency resolve request model"""
    resolution_notes: str = Field(..., description="Notes about the resolution")


class EmergencyEventResponse(BaseModel):
    """Emergency event response model"""
    event_id: str
    action: str
    status: str
    triggered_by: str
    triggered_at: datetime
    reason: str
    details: Dict[str, Any]
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    metadata: Dict[str, Any] = {}


class EmergencyStatsResponse(BaseModel):
    """Emergency statistics response model"""
    total_emergencies: int
    active_emergencies: int
    status_counts: Dict[str, int]
    action_counts: Dict[str, int]
    current_lockdown_level: str
    config: Dict[str, bool]


# Dependency functions
async def get_emergency_service() -> EmergencyController:
    """Get emergency controller service"""
    try:
        return get_emergency_controller()
    except Exception as e:
        logger.error(f"Failed to get emergency service: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Emergency service not available"
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
@router.post("/trigger", response_model=Dict[str, str])
async def trigger_emergency(
    request: EmergencyTriggerRequest,
    emergency_service: EmergencyController = Depends(get_emergency_service),
    rbac_service: RBACManager = Depends(get_rbac_service)
):
    """Trigger emergency action"""
    try:
        # Check permission
        # Note: In a real implementation, you would get the current user from authentication
        # For now, we'll assume the user has permission
        
        # Validate action
        try:
            action = EmergencyAction(request.action)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid emergency action: {request.action}"
            )
        
        # Validate severity
        try:
            severity = EmergencyStatus(request.severity)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid severity level: {request.severity}"
            )
        
        # Trigger emergency
        event_id = await emergency_service.trigger_emergency(
            action=action,
            triggered_by="admin_user",  # Would be actual user ID in real implementation
            reason=request.reason,
            details=request.details,
            severity=severity
        )
        
        return {
            "event_id": event_id,
            "message": f"Emergency action {action.value} triggered successfully",
            "status": "triggered"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to trigger emergency: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger emergency action"
        )


@router.post("/resolve/{event_id}", response_model=Dict[str, str])
async def resolve_emergency(
    event_id: str,
    request: EmergencyResolveRequest,
    emergency_service: EmergencyController = Depends(get_emergency_service)
):
    """Resolve emergency event"""
    try:
        # Resolve emergency
        success = await emergency_service.resolve_emergency(
            event_id=event_id,
            resolved_by="admin_user",  # Would be actual user ID in real implementation
            resolution_notes=request.resolution_notes
        )
        
        if success:
            return {
                "event_id": event_id,
                "message": "Emergency resolved successfully",
                "status": "resolved"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Emergency event {event_id} not found or already resolved"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resolve emergency {event_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resolve emergency"
        )


@router.get("/active", response_model=List[EmergencyEventResponse])
async def get_active_emergencies(
    emergency_service: EmergencyController = Depends(get_emergency_service)
):
    """Get active emergency events"""
    try:
        emergencies = await emergency_service.get_active_emergencies()
        
        response_emergencies = []
        for emergency in emergencies:
            response_emergencies.append(EmergencyEventResponse(
                event_id=emergency.event_id,
                action=emergency.action.value,
                status=emergency.status.value,
                triggered_by=emergency.triggered_by,
                triggered_at=emergency.triggered_at,
                reason=emergency.reason,
                details=emergency.details,
                resolved_at=emergency.resolved_at,
                resolved_by=emergency.resolved_by,
                metadata=emergency.metadata
            ))
        
        return response_emergencies
        
    except Exception as e:
        logger.error(f"Failed to get active emergencies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve active emergencies"
        )


@router.get("/history", response_model=List[EmergencyEventResponse])
async def get_emergency_history(
    limit: int = 100,
    emergency_service: EmergencyController = Depends(get_emergency_service)
):
    """Get emergency history"""
    try:
        emergencies = await emergency_service.get_emergency_history(limit=limit)
        
        response_emergencies = []
        for emergency in emergencies:
            response_emergencies.append(EmergencyEventResponse(
                event_id=emergency.event_id,
                action=emergency.action.value,
                status=emergency.status.value,
                triggered_by=emergency.triggered_by,
                triggered_at=emergency.triggered_at,
                reason=emergency.reason,
                details=emergency.details,
                resolved_at=emergency.resolved_at,
                resolved_by=emergency.resolved_by,
                metadata=emergency.metadata
            ))
        
        return response_emergencies
        
    except Exception as e:
        logger.error(f"Failed to get emergency history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve emergency history"
        )


@router.get("/stats", response_model=EmergencyStatsResponse)
async def get_emergency_stats(
    emergency_service: EmergencyController = Depends(get_emergency_service)
):
    """Get emergency statistics"""
    try:
        stats = await emergency_service.get_emergency_stats()
        
        return EmergencyStatsResponse(
            total_emergencies=stats.get("total_emergencies", 0),
            active_emergencies=stats.get("active_emergencies", 0),
            status_counts=stats.get("status_counts", {}),
            action_counts=stats.get("action_counts", {}),
            current_lockdown_level=stats.get("current_lockdown_level", "normal"),
            config=stats.get("config", {})
        )
        
    except Exception as e:
        logger.error(f"Failed to get emergency stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve emergency statistics"
        )


@router.get("/actions")
async def get_available_actions():
    """Get available emergency actions"""
    try:
        actions = [
            {
                "action": action.value,
                "description": f"Emergency action: {action.value}",
                "severity_levels": ["alert", "warning", "critical", "lockdown"]
            }
            for action in EmergencyAction
        ]
        
        return {
            "actions": actions,
            "total_actions": len(actions)
        }
        
    except Exception as e:
        logger.error(f"Failed to get available actions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve available actions"
        )


@router.get("/status")
async def get_emergency_status(
    emergency_service: EmergencyController = Depends(get_emergency_service)
):
    """Get current emergency status"""
    try:
        stats = await emergency_service.get_emergency_stats()
        active_emergencies = await emergency_service.get_active_emergencies()
        
        return {
            "status": "operational" if stats.get("active_emergencies", 0) == 0 else "emergency",
            "lockdown_level": stats.get("current_lockdown_level", "normal"),
            "active_emergencies": len(active_emergencies),
            "total_emergencies": stats.get("total_emergencies", 0),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get emergency status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve emergency status"
        )


@router.get("/health")
async def emergency_health_check(
    emergency_service: EmergencyController = Depends(get_emergency_service)
):
    """Emergency service health check"""
    try:
        # Test emergency service
        stats = await emergency_service.get_emergency_stats()
        
        return {
            "status": "healthy",
            "service": "emergency-controller",
            "active_emergencies": stats.get("active_emergencies", 0),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Emergency service health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "emergency-controller",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
