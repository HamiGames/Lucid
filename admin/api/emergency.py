
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

from admin.emergency.controls import get_emergency_controls, EmergencyControls, EmergencyAction, EmergencyStatus, EmergencySeverity
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
async def get_emergency_service() -> EmergencyControls:
    """Get emergency controller service"""
    try:
        return get_emergency_controls()
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
    emergency_service: EmergencyControls = Depends(get_emergency_service),
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
            severity = EmergencySeverity(request.severity)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid severity level: {request.severity}"
            )
        
        # Trigger emergency by activating the control
        result = await emergency_service.activate_emergency_control(
            control_id=f"emergency_{action.value}",
            admin_id="admin_user",  # Would be actual user ID in real implementation
            admin_username="admin_user",
            force=True,
            details=request.details
        )
        
        return {
            "status": result.get("status", "triggered"),
            "message": f"Emergency action {action.value} triggered successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to trigger emergency: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger emergency action"
        )


@router.post("/resolve/{control_id}", response_model=Dict[str, str])
async def resolve_emergency(
    control_id: str,
    request: EmergencyResolveRequest,
    emergency_service: EmergencyControls = Depends(get_emergency_service)
):
    """Resolve emergency event"""
    try:
        # Deactivate emergency control
        result = await emergency_service.deactivate_emergency_control(
            control_id=control_id,
            admin_id="admin_user",  # Would be actual user ID in real implementation
            admin_username="admin_user",
            details={"resolution_notes": request.resolution_notes}
        )
        
        if result.get("status") in ["deactivated", "already_inactive"]:
            return {
                "control_id": control_id,
                "message": "Emergency resolved successfully",
                "status": "resolved"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Emergency control {control_id} not found"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resolve emergency {control_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resolve emergency"
        )


@router.get("/active", response_model=List[Dict[str, Any]])
async def get_active_emergencies(
    emergency_service: EmergencyControls = Depends(get_emergency_service)
):
    """Get active emergency events"""
    try:
        status = await emergency_service.get_emergency_status()
        
        return status.get("controls", [])
        
    except Exception as e:
        logger.error(f"Failed to get active emergencies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve active emergencies"
        )


@router.get("/history", response_model=Dict[str, Any])
async def get_emergency_history(
    limit: int = 100,
    offset: int = 0,
    emergency_service: EmergencyControls = Depends(get_emergency_service)
):
    """Get emergency history"""
    try:
        from datetime import datetime, timezone
        events = await emergency_service.get_emergency_events(
            limit=limit,
            offset=offset
        )
        
        return events
        
    except Exception as e:
        logger.error(f"Failed to get emergency history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve emergency history"
        )


@router.get("/stats", response_model=Dict[str, Any])
async def get_emergency_stats(
    emergency_service: EmergencyControls = Depends(get_emergency_service)
):
    """Get emergency statistics"""
    try:
        status = await emergency_service.get_emergency_status()
        
        # Get event counts
        events = await emergency_service.get_emergency_events(limit=1000)
        
        status_counts = {}
        action_counts = {}
        
        for event in events.get("events", []):
            status_val = event.get("status", "unknown")
            action_val = event.get("action", "unknown")
            
            status_counts[status_val] = status_counts.get(status_val, 0) + 1
            action_counts[action_val] = action_counts.get(action_val, 0) + 1
        
        return {
            "total_emergencies": events.get("total", 0),
            "active_emergencies": status.get("active_controls", 0),
            "status_counts": status_counts,
            "action_counts": action_counts,
            "current_lockdown_level": "lockdown" if status.get("is_locked_down", False) else "normal",
            "config": {
                "new_sessions_enabled": status.get("new_sessions_enabled", True)
            }
        }
        
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
                "severity_levels": ["low", "medium", "high", "critical"]
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
    emergency_service: EmergencyControls = Depends(get_emergency_service)
):
    """Get current emergency status"""
    try:
        status = await emergency_service.get_emergency_status()
        
        return {
            "status": "operational" if status.get("active_controls", 0) == 0 else "emergency",
            "lockdown_level": "lockdown" if status.get("is_locked_down", False) else "normal",
            "active_emergencies": status.get("active_controls", 0),
            "new_sessions_enabled": status.get("new_sessions_enabled", True),
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
    emergency_service: EmergencyControls = Depends(get_emergency_service)
):
    """Emergency service health check"""
    try:
        # Test emergency service
        status = await emergency_service.get_emergency_status()
        
        return {
            "status": "healthy",
            "service": "emergency-controls",
            "active_emergencies": status.get("active_controls", 0),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Emergency service health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "emergency-controls",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }