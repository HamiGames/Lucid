"""
LUCID Payment Systems - TRON Wallet Audit API
Audit logging and security event tracking
Distroless container: lucid-tron-wallet-manager:latest
"""

import logging
import csv
import io
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..services.wallet_audit import (
    WalletAuditService,
    AuditAction,
    AuditSeverity
)

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/tron/audit", tags=["TRON Wallet Audit"])

# Global audit service instance (will be initialized in main app)
audit_service: Optional[WalletAuditService] = None

# Request/Response Models
class AuditLogResponse(BaseModel):
    """Audit log response model"""
    audit_id: str = Field(..., description="Audit log ID")
    action: str = Field(..., description="Action performed")
    wallet_id: str = Field(..., description="Wallet ID")
    user_id: Optional[str] = Field(None, description="User ID")
    severity: str = Field(..., description="Severity level")
    timestamp: str = Field(..., description="Action timestamp")
    success: bool = Field(..., description="Whether action succeeded")
    ip_address: Optional[str] = Field(None, description="IP address")
    user_agent: Optional[str] = Field(None, description="User agent")
    details: Dict[str, Any] = Field(default_factory=dict, description="Action details")
    error_message: Optional[str] = Field(None, description="Error message if failed")

class AuditFilterRequest(BaseModel):
    """Audit filter request"""
    wallet_id: Optional[str] = Field(None, description="Filter by wallet ID")
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    action: Optional[str] = Field(None, description="Filter by action")
    severity: Optional[str] = Field(None, description="Filter by severity")
    start_date: Optional[str] = Field(None, description="Start date (ISO format)")
    end_date: Optional[str] = Field(None, description="End date (ISO format)")
    skip: int = Field(0, description="Skip records")
    limit: int = Field(100, description="Limit records")

class AuditListResponse(BaseModel):
    """Audit list response"""
    logs: List[AuditLogResponse] = Field(..., description="List of audit logs")
    total_count: int = Field(..., description="Total log count")
    skip: int = Field(..., description="Skip value")
    limit: int = Field(..., description="Limit value")
    timestamp: str = Field(..., description="Response timestamp")

class AuditStatsResponse(BaseModel):
    """Audit statistics response"""
    total_logs: int = Field(..., description="Total audit logs")
    by_action: Dict[str, int] = Field(..., description="Log count by action")
    by_severity: Dict[str, int] = Field(..., description="Log count by severity")
    by_wallet: Dict[str, int] = Field(..., description="Log count by wallet")
    failed_actions: int = Field(..., description="Number of failed actions")
    timestamp: str = Field(..., description="Response timestamp")

class SecurityEventResponse(BaseModel):
    """Security event response"""
    events: List[AuditLogResponse] = Field(..., description="Security events")
    total_count: int = Field(..., description="Total event count")
    hours: int = Field(..., description="Time window in hours")
    timestamp: str = Field(..., description="Response timestamp")

def get_audit_service() -> WalletAuditService:
    """Dependency to get audit service"""
    if audit_service is None:
        raise HTTPException(status_code=503, detail="Audit service not initialized")
    return audit_service

@router.get("/logs", response_model=AuditListResponse)
async def get_audit_logs(
    wallet_id: Optional[str] = Query(None, description="Filter by wallet ID"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    action: Optional[str] = Query(None, description="Filter by action"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    skip: int = Query(0, ge=0, description="Skip records"),
    limit: int = Query(100, ge=1, le=1000, description="Limit records"),
    service: WalletAuditService = Depends(get_audit_service)
):
    """Get audit logs with filters"""
    try:
        # Parse dates
        start_dt = None
        end_dt = None
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_date format. Use ISO 8601 format.")
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_date format. Use ISO 8601 format.")
        
        # Parse action and severity enums
        action_enum = None
        if action:
            try:
                action_enum = AuditAction(action.lower())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid action: {action}")
        
        severity_enum = None
        if severity:
            try:
                severity_enum = AuditSeverity(severity.lower())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")
        
        # Get audit logs
        logs_data = await service.get_audit_logs(
            wallet_id=wallet_id,
            user_id=user_id,
            action=action_enum,
            severity=severity_enum,
            start_date=start_dt,
            end_date=end_dt,
            skip=skip,
            limit=limit
        )
        
        # Get total count
        total_count = await service.count_audit_logs(
            wallet_id=wallet_id,
            user_id=user_id,
            action=action_enum,
            severity=severity_enum
        )
        
        # Convert to response format
        logs = []
        for log_data in logs_data:
            logs.append(AuditLogResponse(
                audit_id=log_data.get("_id", ""),
                action=log_data.get("action", ""),
                wallet_id=log_data.get("wallet_id", ""),
                user_id=log_data.get("user_id"),
                severity=log_data.get("severity", "medium"),
                timestamp=log_data.get("timestamp", datetime.now().isoformat()),
                success=log_data.get("success", True),
                ip_address=log_data.get("ip_address"),
                user_agent=log_data.get("user_agent"),
                details=log_data.get("details", {}),
                error_message=log_data.get("error_message")
            ))
        
        return AuditListResponse(
            logs=logs,
            total_count=total_count,
            skip=skip,
            limit=limit,
            timestamp=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting audit logs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get audit logs: {str(e)}")

@router.get("/logs/{wallet_id}", response_model=AuditListResponse)
async def get_wallet_audit_logs(
    wallet_id: str,
    skip: int = Query(0, ge=0, description="Skip records"),
    limit: int = Query(100, ge=1, le=1000, description="Limit records"),
    service: WalletAuditService = Depends(get_audit_service)
):
    """Get wallet-specific audit logs"""
    try:
        # Get audit logs for wallet
        logs_data = await service.get_audit_logs(
            wallet_id=wallet_id,
            skip=skip,
            limit=limit
        )
        
        # Get total count
        total_count = await service.count_audit_logs(wallet_id=wallet_id)
        
        # Convert to response format
        logs = []
        for log_data in logs_data:
            logs.append(AuditLogResponse(
                audit_id=log_data.get("_id", ""),
                action=log_data.get("action", ""),
                wallet_id=wallet_id,
                user_id=log_data.get("user_id"),
                severity=log_data.get("severity", "medium"),
                timestamp=log_data.get("timestamp", datetime.now().isoformat()),
                success=log_data.get("success", True),
                ip_address=log_data.get("ip_address"),
                user_agent=log_data.get("user_agent"),
                details=log_data.get("details", {}),
                error_message=log_data.get("error_message")
            ))
        
        return AuditListResponse(
            logs=logs,
            total_count=total_count,
            skip=skip,
            limit=limit,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error getting audit logs for wallet {wallet_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get audit logs: {str(e)}")

@router.get("/security-events", response_model=SecurityEventResponse)
async def get_security_events(
    wallet_id: Optional[str] = Query(None, description="Filter by wallet ID"),
    hours: int = Query(24, ge=1, le=168, description="Time window in hours"),
    service: WalletAuditService = Depends(get_audit_service)
):
    """Get high/critical severity security events"""
    try:
        # Get security events
        events_data = await service.get_security_events(
            wallet_id=wallet_id,
            hours=hours
        )
        
        # Convert to response format
        events = []
        for event_data in events_data:
            events.append(AuditLogResponse(
                audit_id=event_data.get("_id", ""),
                action=event_data.get("action", ""),
                wallet_id=event_data.get("wallet_id", ""),
                user_id=event_data.get("user_id"),
                severity=event_data.get("severity", "high"),
                timestamp=event_data.get("timestamp", datetime.now().isoformat()),
                success=event_data.get("success", True),
                ip_address=event_data.get("ip_address"),
                user_agent=event_data.get("user_agent"),
                details=event_data.get("details", {}),
                error_message=event_data.get("error_message")
            ))
        
        return SecurityEventResponse(
            events=events,
            total_count=len(events),
            hours=hours,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error getting security events: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get security events: {str(e)}")

@router.get("/stats", response_model=AuditStatsResponse)
async def get_audit_stats(
    service: WalletAuditService = Depends(get_audit_service)
):
    """Get audit statistics"""
    try:
        # Get all logs for statistics
        all_logs = await service.get_audit_logs(limit=10000)
        
        # Calculate statistics
        total_logs = len(all_logs)
        by_action = {}
        by_severity = {}
        by_wallet = {}
        failed_actions = 0
        
        for log in all_logs:
            action = log.get("action", "unknown")
            severity = log.get("severity", "medium")
            wallet = log.get("wallet_id", "unknown")
            success = log.get("success", True)
            
            by_action[action] = by_action.get(action, 0) + 1
            by_severity[severity] = by_severity.get(severity, 0) + 1
            by_wallet[wallet] = by_wallet.get(wallet, 0) + 1
            
            if not success:
                failed_actions += 1
        
        return AuditStatsResponse(
            total_logs=total_logs,
            by_action=by_action,
            by_severity=by_severity,
            by_wallet=by_wallet,
            failed_actions=failed_actions,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error getting audit stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get audit stats: {str(e)}")

@router.post("/export")
async def export_audit_logs(
    request: AuditFilterRequest,
    format: str = Query("json", regex="^(json|csv)$", description="Export format"),
    service: WalletAuditService = Depends(get_audit_service)
):
    """Export audit logs in JSON or CSV format"""
    try:
        # Parse dates
        start_dt = None
        end_dt = None
        if request.start_date:
            try:
                start_dt = datetime.fromisoformat(request.start_date.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_date format")
        if request.end_date:
            try:
                end_dt = datetime.fromisoformat(request.end_date.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_date format")
        
        # Parse enums
        action_enum = None
        if request.action:
            try:
                action_enum = AuditAction(request.action.lower())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid action: {request.action}")
        
        severity_enum = None
        if request.severity:
            try:
                severity_enum = AuditSeverity(request.severity.lower())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid severity: {request.severity}")
        
        # Get audit logs
        logs_data = await service.get_audit_logs(
            wallet_id=request.wallet_id,
            user_id=request.user_id,
            action=action_enum,
            severity=severity_enum,
            start_date=start_dt,
            end_date=end_dt,
            skip=request.skip,
            limit=request.limit
        )
        
        if format == "csv":
            # Generate CSV
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=[
                "audit_id", "action", "wallet_id", "user_id", "severity",
                "timestamp", "success", "ip_address", "user_agent", "error_message"
            ])
            writer.writeheader()
            
            for log in logs_data:
                writer.writerow({
                    "audit_id": str(log.get("_id", "")),
                    "action": log.get("action", ""),
                    "wallet_id": log.get("wallet_id", ""),
                    "user_id": log.get("user_id", ""),
                    "severity": log.get("severity", ""),
                    "timestamp": log.get("timestamp", ""),
                    "success": log.get("success", True),
                    "ip_address": log.get("ip_address", ""),
                    "user_agent": log.get("user_agent", ""),
                    "error_message": log.get("error_message", "")
                })
            
            output.seek(0)
            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
            )
        else:
            # Return JSON
            import json
            return {
                "logs": logs_data,
                "total_count": len(logs_data),
                "exported_at": datetime.now().isoformat(),
                "format": "json"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting audit logs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to export audit logs: {str(e)}")
