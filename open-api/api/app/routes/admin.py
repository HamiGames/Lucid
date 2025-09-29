# Path: open-api/api/app/routes/admin.py
# Lucid RDP Administration and Monitoring API Blueprint
# Implements system monitoring, administrative functions, and operational oversight

from __future__ import annotations

import logging
import secrets
import psutil
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Literal
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, Header
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field

# Import from our components
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["administration"])
security = HTTPBearer()

# Enums
class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class SystemStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    MAINTENANCE = "maintenance"

class AlertStatus(str, Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"

class MaintenanceStatus(str, Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

# Pydantic Models
class SystemHealth(BaseModel):
    """Overall system health status"""
    status: SystemStatus
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    components: Dict[str, Any] = Field(..., description="Health status of system components")
    metrics: Dict[str, float] = Field(..., description="Key system metrics")
    alerts_count: Dict[str, int] = Field(..., description="Count of alerts by severity")
    uptime_seconds: int = Field(..., description="System uptime in seconds")
    version: str = Field(default="1.0.0", description="System version")

class SystemMetrics(BaseModel):
    """System performance metrics"""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    cpu_usage_percent: float = Field(..., ge=0, le=100)
    memory_usage_percent: float = Field(..., ge=0, le=100)
    disk_usage_percent: float = Field(..., ge=0, le=100)
    network_io: Dict[str, int] = Field(..., description="Network I/O statistics")
    disk_io: Dict[str, int] = Field(..., description="Disk I/O statistics")
    load_average: List[float] = Field(..., description="System load averages")
    active_connections: int = Field(..., description="Number of active network connections")
    database_connections: int = Field(..., description="Number of database connections")

class AlertRule(BaseModel):
    """Alert rule definition"""
    rule_id: str = Field(..., description="Unique rule identifier")
    name: str = Field(..., description="Alert rule name")
    description: str = Field(..., description="Alert rule description")
    metric: str = Field(..., description="Metric to monitor")
    threshold: float = Field(..., description="Alert threshold value")
    operator: str = Field(..., enum=["gt", "lt", "eq", "ne"], description="Comparison operator")
    severity: AlertSeverity
    enabled: bool = Field(default=True)
    cooldown_seconds: int = Field(default=300, description="Cooldown period between alerts")
    recipients: List[str] = Field(default_factory=list, description="Alert recipients")

class Alert(BaseModel):
    """System alert"""
    alert_id: str = Field(..., description="Unique alert identifier")
    rule_id: str = Field(..., description="Associated rule identifier")
    severity: AlertSeverity
    status: AlertStatus
    title: str = Field(..., description="Alert title")
    description: str = Field(..., description="Alert description")
    triggered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_by: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional alert data")

class MaintenanceWindow(BaseModel):
    """Scheduled maintenance window"""
    maintenance_id: str = Field(..., description="Unique maintenance identifier")
    title: str = Field(..., description="Maintenance title")
    description: str = Field(..., description="Maintenance description")
    scheduled_start: datetime = Field(..., description="Scheduled start time")
    scheduled_end: datetime = Field(..., description="Scheduled end time")
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    status: MaintenanceStatus
    affected_services: List[str] = Field(..., description="List of affected services")
    created_by: str = Field(..., description="User who created maintenance window")
    notifications_sent: bool = Field(default=False)

class ServiceStatus(BaseModel):
    """Individual service status"""
    service_name: str = Field(..., description="Service name")
    status: SystemStatus
    version: str = Field(..., description="Service version")
    uptime_seconds: int = Field(..., description="Service uptime")
    last_health_check: datetime = Field(..., description="Last health check timestamp")
    endpoints_healthy: int = Field(..., description="Number of healthy endpoints")
    endpoints_total: int = Field(..., description="Total number of endpoints")
    response_time_ms: float = Field(..., description="Average response time in milliseconds")
    error_rate_percent: float = Field(..., ge=0, le=100, description="Error rate percentage")

class NetworkTopology(BaseModel):
    """Network topology information"""
    total_nodes: int = Field(..., description="Total number of nodes")
    active_nodes: int = Field(..., description="Number of active nodes")
    node_distribution: Dict[str, int] = Field(..., description="Node distribution by region/type")
    network_health_score: float = Field(..., ge=0, le=1, description="Overall network health score")
    consensus_participation: float = Field(..., ge=0, le=1, description="Consensus participation rate")
    average_latency_ms: float = Field(..., description="Average network latency")
    bandwidth_utilization: Dict[str, float] = Field(..., description="Bandwidth utilization statistics")

class AdminUser(BaseModel):
    """Administrative user information"""
    admin_id: str = Field(..., description="Admin user identifier")
    username: str = Field(..., description="Admin username")
    role: str = Field(..., enum=["super_admin", "admin", "operator", "viewer"])
    permissions: List[str] = Field(..., description="Admin permissions")
    created_at: datetime = Field(..., description="Account creation timestamp")
    last_login: Optional[datetime] = None
    is_active: bool = Field(default=True)
    mfa_enabled: bool = Field(default=False)

class AuditLogEntry(BaseModel):
    """Administrative audit log entry"""
    log_id: str = Field(..., description="Unique log identifier")
    admin_id: str = Field(..., description="Admin user identifier")
    action: str = Field(..., description="Administrative action performed")
    resource: str = Field(..., description="Resource affected")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ip_address: str = Field(..., description="Source IP address")
    user_agent: Optional[str] = None
    success: bool = Field(..., description="Action success status")
    details: Dict[str, Any] = Field(default_factory=dict, description="Action details")

class SystemConfiguration(BaseModel):
    """System configuration settings"""
    config_section: str = Field(..., description="Configuration section")
    settings: Dict[str, Any] = Field(..., description="Configuration settings")
    last_updated: datetime = Field(..., description="Last update timestamp")
    updated_by: str = Field(..., description="User who last updated")
    environment: str = Field(..., enum=["development", "staging", "production"])

# Global administrative storage
system_alerts: Dict[str, Alert] = {}
alert_rules: Dict[str, AlertRule] = {}
maintenance_windows: Dict[str, MaintenanceWindow] = {}
admin_users: Dict[str, AdminUser] = {}
audit_logs: List[AuditLogEntry] = []

@router.get("/health/system", response_model=SystemHealth)
async def get_system_health(
    token: str = Depends(security),
    admin_id: str = Header(..., alias="X-Admin-ID")
) -> SystemHealth:
    """
    Get comprehensive system health status.
    
    Requires administrative privileges.
    """
    try:
        logger.info(f"System health check requested by admin: {admin_id}")
        
        # Collect component health statuses
        components = {
            "api_gateway": "healthy",
            "session_manager": "healthy",
            "blockchain_anchoring": "healthy",
            "payment_processor": "healthy",
            "node_network": "healthy",
            "trust_policy_engine": "healthy",
            "database": "healthy",
            "cache": "healthy",
            "message_queue": "healthy"
        }
        
        # Calculate system metrics
        metrics = {
            "cpu_usage": psutil.cpu_percent(),
            "memory_usage": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent,
            "active_sessions": 125,
            "transactions_per_second": 45.7,
            "response_time_ms": 89.5
        }
        
        # Count alerts by severity
        alerts_count = {
            "critical": len([a for a in system_alerts.values() if a.severity == AlertSeverity.CRITICAL and a.status == AlertStatus.ACTIVE]),
            "error": len([a for a in system_alerts.values() if a.severity == AlertSeverity.ERROR and a.status == AlertStatus.ACTIVE]),
            "warning": len([a for a in system_alerts.values() if a.severity == AlertSeverity.WARNING and a.status == AlertStatus.ACTIVE]),
            "info": len([a for a in system_alerts.values() if a.severity == AlertSeverity.INFO and a.status == AlertStatus.ACTIVE])
        }
        
        # Determine overall system status
        if alerts_count["critical"] > 0:
            overall_status = SystemStatus.CRITICAL
        elif alerts_count["error"] > 0:
            overall_status = SystemStatus.DEGRADED
        elif any(status != "healthy" for status in components.values()):
            overall_status = SystemStatus.DEGRADED
        else:
            overall_status = SystemStatus.HEALTHY
        
        health = SystemHealth(
            status=overall_status,
            components=components,
            metrics=metrics,
            alerts_count=alerts_count,
            uptime_seconds=86400 * 30  # Mock 30 days uptime
        )
        
        # Log admin action
        audit_log = AuditLogEntry(
            log_id=f"audit_{secrets.token_hex(8)}",
            admin_id=admin_id,
            action="view_system_health",
            resource="system",
            ip_address="127.0.0.1",
            success=True
        )
        audit_logs.append(audit_log)
        
        logger.info(f"System health status: {overall_status}")
        return health
        
    except Exception as e:
        logger.error(f"System health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"System health check failed: {str(e)}"
        )

@router.get("/metrics", response_model=SystemMetrics)
async def get_system_metrics(
    token: str = Depends(security),
    admin_id: str = Header(..., alias="X-Admin-ID")
) -> SystemMetrics:
    """Get real-time system performance metrics"""
    try:
        # Get system metrics using psutil
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        network_io = psutil.net_io_counters()
        disk_io = psutil.disk_io_counters()
        
        metrics = SystemMetrics(
            cpu_usage_percent=cpu_percent,
            memory_usage_percent=memory.percent,
            disk_usage_percent=(disk.used / disk.total) * 100,
            network_io={
                "bytes_sent": network_io.bytes_sent,
                "bytes_recv": network_io.bytes_recv,
                "packets_sent": network_io.packets_sent,
                "packets_recv": network_io.packets_recv
            },
            disk_io={
                "read_bytes": disk_io.read_bytes,
                "write_bytes": disk_io.write_bytes,
                "read_count": disk_io.read_count,
                "write_count": disk_io.write_count
            },
            load_average=list(psutil.getloadavg()),
            active_connections=len(psutil.net_connections()),
            database_connections=25  # Mock database connections
        )
        
        logger.info(f"System metrics retrieved by admin: {admin_id}")
        return metrics
        
    except Exception as e:
        logger.error(f"System metrics retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"System metrics retrieval failed: {str(e)}"
        )

@router.get("/alerts", response_model=List[Alert])
async def list_alerts(
    severity: Optional[AlertSeverity] = Query(None, description="Filter by severity"),
    status_filter: Optional[AlertStatus] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=500, description="Maximum results"),
    token: str = Depends(security),
    admin_id: str = Header(..., alias="X-Admin-ID")
) -> List[Alert]:
    """List system alerts with optional filtering"""
    try:
        alerts = list(system_alerts.values())
        
        # Apply filters
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        if status_filter:
            alerts = [a for a in alerts if a.status == status_filter]
        
        # Sort by triggered time (newest first)
        alerts.sort(key=lambda a: a.triggered_at, reverse=True)
        
        return alerts[:limit]
        
    except Exception as e:
        logger.error(f"Alert listing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Alert listing failed: {str(e)}"
        )

@router.post("/alerts/rules", response_model=AlertRule, status_code=status.HTTP_201_CREATED)
async def create_alert_rule(
    rule: AlertRule,
    token: str = Depends(security),
    admin_id: str = Header(..., alias="X-Admin-ID")
) -> AlertRule:
    """Create a new alert rule"""
    try:
        rule_id = f"rule_{secrets.token_hex(8)}"
        rule.rule_id = rule_id
        
        # Store alert rule
        alert_rules[rule_id] = rule
        
        # Log admin action
        audit_log = AuditLogEntry(
            log_id=f"audit_{secrets.token_hex(8)}",
            admin_id=admin_id,
            action="create_alert_rule",
            resource=f"alert_rule:{rule_id}",
            ip_address="127.0.0.1",
            success=True,
            details={"rule_name": rule.name, "metric": rule.metric, "threshold": rule.threshold}
        )
        audit_logs.append(audit_log)
        
        logger.info(f"Alert rule created: {rule_id} by admin {admin_id}")
        return rule
        
    except Exception as e:
        logger.error(f"Alert rule creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Alert rule creation failed: {str(e)}"
        )

@router.post("/alerts/{alert_id}/acknowledge", response_model=Alert)
async def acknowledge_alert(
    alert_id: str,
    token: str = Depends(security),
    admin_id: str = Header(..., alias="X-Admin-ID")
) -> Alert:
    """Acknowledge an active alert"""
    try:
        alert = system_alerts.get(alert_id)
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert not found: {alert_id}"
            )
        
        # Update alert status
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = datetime.now(timezone.utc)
        alert.acknowledged_by = admin_id
        
        # Log admin action
        audit_log = AuditLogEntry(
            log_id=f"audit_{secrets.token_hex(8)}",
            admin_id=admin_id,
            action="acknowledge_alert",
            resource=f"alert:{alert_id}",
            ip_address="127.0.0.1",
            success=True,
            details={"alert_severity": alert.severity}
        )
        audit_logs.append(audit_log)
        
        logger.info(f"Alert acknowledged: {alert_id} by admin {admin_id}")
        return alert
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Alert acknowledgment failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Alert acknowledgment failed: {str(e)}"
        )

@router.get("/services", response_model=List[ServiceStatus])
async def list_service_statuses(
    token: str = Depends(security),
    admin_id: str = Header(..., alias="X-Admin-ID")
) -> List[ServiceStatus]:
    """Get status of all system services"""
    try:
        services = [
            ServiceStatus(
                service_name="session-manager",
                status=SystemStatus.HEALTHY,
                version="1.2.3",
                uptime_seconds=86400 * 15,
                last_health_check=datetime.now(timezone.utc) - timedelta(minutes=1),
                endpoints_healthy=8,
                endpoints_total=8,
                response_time_ms=45.2,
                error_rate_percent=0.1
            ),
            ServiceStatus(
                service_name="blockchain-anchoring",
                status=SystemStatus.HEALTHY,
                version="1.1.0",
                uptime_seconds=86400 * 10,
                last_health_check=datetime.now(timezone.utc) - timedelta(minutes=1),
                endpoints_healthy=4,
                endpoints_total=4,
                response_time_ms=120.8,
                error_rate_percent=0.0
            ),
            ServiceStatus(
                service_name="payment-processor",
                status=SystemStatus.DEGRADED,
                version="2.0.1",
                uptime_seconds=86400 * 7,
                last_health_check=datetime.now(timezone.utc) - timedelta(minutes=1),
                endpoints_healthy=5,
                endpoints_total=6,
                response_time_ms=89.1,
                error_rate_percent=2.3
            ),
            ServiceStatus(
                service_name="node-network",
                status=SystemStatus.HEALTHY,
                version="1.0.5",
                uptime_seconds=86400 * 20,
                last_health_check=datetime.now(timezone.utc) - timedelta(minutes=1),
                endpoints_healthy=12,
                endpoints_total=12,
                response_time_ms=67.4,
                error_rate_percent=0.5
            )
        ]
        
        logger.info(f"Service statuses retrieved by admin: {admin_id}")
        return services
        
    except Exception as e:
        logger.error(f"Service status retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Service status retrieval failed: {str(e)}"
        )

@router.get("/network/topology", response_model=NetworkTopology)
async def get_network_topology(
    token: str = Depends(security),
    admin_id: str = Header(..., alias="X-Admin-ID")
) -> NetworkTopology:
    """Get network topology and health information"""
    try:
        topology = NetworkTopology(
            total_nodes=156,
            active_nodes=142,
            node_distribution={
                "north_america": 45,
                "europe": 38,
                "asia_pacific": 32,
                "south_america": 15,
                "africa": 8,
                "oceania": 4
            },
            network_health_score=0.91,
            consensus_participation=0.89,
            average_latency_ms=67.3,
            bandwidth_utilization={
                "total_capacity_gbps": 1250.0,
                "used_capacity_gbps": 387.5,
                "utilization_percent": 31.0
            }
        )
        
        logger.info(f"Network topology retrieved by admin: {admin_id}")
        return topology
        
    except Exception as e:
        logger.error(f"Network topology retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Network topology retrieval failed: {str(e)}"
        )

@router.post("/maintenance", response_model=MaintenanceWindow, status_code=status.HTTP_201_CREATED)
async def schedule_maintenance(
    maintenance: MaintenanceWindow,
    token: str = Depends(security),
    admin_id: str = Header(..., alias="X-Admin-ID")
) -> MaintenanceWindow:
    """Schedule a maintenance window"""
    try:
        maintenance_id = f"maint_{secrets.token_hex(12)}"
        maintenance.maintenance_id = maintenance_id
        maintenance.created_by = admin_id
        maintenance.status = MaintenanceStatus.SCHEDULED
        
        # Store maintenance window
        maintenance_windows[maintenance_id] = maintenance
        
        # Log admin action
        audit_log = AuditLogEntry(
            log_id=f"audit_{secrets.token_hex(8)}",
            admin_id=admin_id,
            action="schedule_maintenance",
            resource=f"maintenance:{maintenance_id}",
            ip_address="127.0.0.1",
            success=True,
            details={
                "scheduled_start": maintenance.scheduled_start.isoformat(),
                "scheduled_end": maintenance.scheduled_end.isoformat(),
                "affected_services": maintenance.affected_services
            }
        )
        audit_logs.append(audit_log)
        
        logger.info(f"Maintenance scheduled: {maintenance_id} by admin {admin_id}")
        return maintenance
        
    except Exception as e:
        logger.error(f"Maintenance scheduling failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Maintenance scheduling failed: {str(e)}"
        )

@router.get("/audit-log", response_model=List[AuditLogEntry])
async def get_audit_log(
    admin_id_filter: Optional[str] = Query(None, description="Filter by admin ID"),
    action_filter: Optional[str] = Query(None, description="Filter by action"),
    start_date: Optional[datetime] = Query(None, description="Filter from date"),
    end_date: Optional[datetime] = Query(None, description="Filter to date"),
    limit: int = Query(100, ge=1, le=500, description="Maximum results"),
    token: str = Depends(security),
    admin_id: str = Header(..., alias="X-Admin-ID")
) -> List[AuditLogEntry]:
    """Get administrative audit log"""
    try:
        filtered_logs = audit_logs.copy()
        
        # Apply filters
        if admin_id_filter:
            filtered_logs = [log for log in filtered_logs if log.admin_id == admin_id_filter]
        if action_filter:
            filtered_logs = [log for log in filtered_logs if action_filter.lower() in log.action.lower()]
        if start_date:
            filtered_logs = [log for log in filtered_logs if log.timestamp >= start_date]
        if end_date:
            filtered_logs = [log for log in filtered_logs if log.timestamp <= end_date]
        
        # Sort by timestamp (newest first)
        filtered_logs.sort(key=lambda log: log.timestamp, reverse=True)
        
        logger.info(f"Audit log retrieved by admin: {admin_id}")
        return filtered_logs[:limit]
        
    except Exception as e:
        logger.error(f"Audit log retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Audit log retrieval failed: {str(e)}"
        )

@router.get("/config/{section}", response_model=SystemConfiguration)
async def get_system_config(
    section: str,
    token: str = Depends(security),
    admin_id: str = Header(..., alias="X-Admin-ID")
) -> SystemConfiguration:
    """Get system configuration for a specific section"""
    try:
        # Mock configuration data
        config_data = {
            "api": {
                "rate_limit_requests_per_minute": 1000,
                "max_request_size_mb": 10,
                "timeout_seconds": 30,
                "cors_enabled": True,
                "debug_mode": False
            },
            "blockchain": {
                "tron_network": "mainnet",
                "confirmation_blocks": 19,
                "gas_price_multiplier": 1.1,
                "anchor_batch_size": 100
            },
            "security": {
                "jwt_expiry_hours": 24,
                "session_timeout_minutes": 60,
                "max_login_attempts": 5,
                "2fa_required": True,
                "password_min_length": 12
            }
        }
        
        if section not in config_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration section not found: {section}"
            )
        
        config = SystemConfiguration(
            config_section=section,
            settings=config_data[section],
            last_updated=datetime.now(timezone.utc) - timedelta(days=5),
            updated_by="admin_system",
            environment="production"
        )
        
        logger.info(f"System config retrieved: {section} by admin {admin_id}")
        return config
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"System config retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"System config retrieval failed: {str(e)}"
        )

@router.put("/config/{section}", response_model=SystemConfiguration)
async def update_system_config(
    section: str,
    config_update: Dict[str, Any] = Body(..., description="Configuration updates"),
    token: str = Depends(security),
    admin_id: str = Header(..., alias="X-Admin-ID")
) -> SystemConfiguration:
    """Update system configuration"""
    try:
        # In a real system, this would validate and apply configuration changes
        
        updated_config = SystemConfiguration(
            config_section=section,
            settings=config_update,
            last_updated=datetime.now(timezone.utc),
            updated_by=admin_id,
            environment="production"
        )
        
        # Log admin action
        audit_log = AuditLogEntry(
            log_id=f"audit_{secrets.token_hex(8)}",
            admin_id=admin_id,
            action="update_system_config",
            resource=f"config:{section}",
            ip_address="127.0.0.1",
            success=True,
            details={"updated_keys": list(config_update.keys())}
        )
        audit_logs.append(audit_log)
        
        logger.info(f"System config updated: {section} by admin {admin_id}")
        return updated_config
        
    except Exception as e:
        logger.error(f"System config update failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"System config update failed: {str(e)}"
        )

# Health check endpoint
@router.get("/health", include_in_schema=False)
async def admin_health() -> Dict[str, Any]:
    """Administration service health check"""
    return {
        "service": "administration",
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {
            "system_monitoring": "operational",
            "alert_system": "operational",
            "audit_logging": "operational",
            "configuration_management": "operational",
            "maintenance_scheduler": "operational"
        },
        "statistics": {
            "active_alerts": len([a for a in system_alerts.values() if a.status == AlertStatus.ACTIVE]),
            "alert_rules_count": len(alert_rules),
            "scheduled_maintenance": len([m for m in maintenance_windows.values() if m.status == MaintenanceStatus.SCHEDULED]),
            "admin_users_count": len(admin_users),
            "audit_entries_today": len([log for log in audit_logs if log.timestamp.date() == datetime.now(timezone.utc).date()])
        }
    }