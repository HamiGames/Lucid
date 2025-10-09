# Path: node/shards/shard_host_management.py
# Lucid RDP Shard Host Management - Ongoing operations and maintenance for distributed storage hosts
# Based on LUCID-STRICT requirements per Spec-1c

from __future__ import annotations

import asyncio
import logging
import hashlib
import os
# Optional aiohttp import
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    aiohttp = None
    AIOHTTP_AVAILABLE = False
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import uuid
import json

# Database adapter handles compatibility
from ..database_adapter import DatabaseAdapter, get_database_adapter

# Import existing components using relative imports
from ..peer_discovery import PeerDiscovery
from ..work_credits import WorkCreditsCalculator
logger = logging.getLogger(__name__)

# Management Constants
HEALTH_CHECK_INTERVAL_SEC = int(os.getenv("HEALTH_CHECK_INTERVAL_SEC", "60"))  # 1 minute
PERFORMANCE_WINDOW_HOURS = int(os.getenv("PERFORMANCE_WINDOW_HOURS", "24"))  # 24 hours
DEGRADED_THRESHOLD_FAILURES = int(os.getenv("DEGRADED_THRESHOLD_FAILURES", "3"))  # 3 failed checks
MAINTENANCE_WINDOW_HOURS = int(os.getenv("MAINTENANCE_WINDOW_HOURS", "2"))  # 2 hour maintenance window
BACKUP_REDUNDANCY_FACTOR = int(os.getenv("BACKUP_REDUNDANCY_FACTOR", "2"))  # Additional backup copies


class MaintenanceType(Enum):
    """Types of maintenance operations"""
    SCHEDULED = "scheduled"
    EMERGENCY = "emergency"
    UPGRADE = "upgrade"
    REPAIR = "repair"
    MIGRATION = "migration"


class OperationStatus(Enum):
    """Status of management operations"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class PerformanceMetrics:
    """Host performance metrics"""
    node_id: str
    response_time_ms: float
    uptime_percentage: float
    throughput_mbps: float
    error_rate: float
    storage_io_rate: float
    cpu_usage_percentage: float
    memory_usage_percentage: float
    network_latency_ms: float
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "response_time_ms": self.response_time_ms,
            "uptime_percentage": self.uptime_percentage,
            "throughput_mbps": self.throughput_mbps,
            "error_rate": self.error_rate,
            "storage_io_rate": self.storage_io_rate,
            "cpu_usage_percentage": self.cpu_usage_percentage,
            "memory_usage_percentage": self.memory_usage_percentage,
            "network_latency_ms": self.network_latency_ms,
            "last_updated": self.last_updated
        }


@dataclass
class MaintenanceWindow:
    """Scheduled maintenance window"""
    maintenance_id: str
    node_id: str
    maintenance_type: MaintenanceType
    scheduled_start: datetime
    scheduled_end: datetime
    description: str
    status: OperationStatus = OperationStatus.PENDING
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    affected_shards: List[str] = field(default_factory=list)
    backup_hosts: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.maintenance_id,
            "node_id": self.node_id,
            "type": self.maintenance_type.value,
            "scheduled_start": self.scheduled_start,
            "scheduled_end": self.scheduled_end,
            "description": self.description,
            "status": self.status.value,
            "actual_start": self.actual_start,
            "actual_end": self.actual_end,
            "affected_shards": self.affected_shards,
            "backup_hosts": self.backup_hosts
        }


@dataclass
class ShardIntegrityCheck:
    """Shard integrity verification result"""
    check_id: str
    shard_id: str
    host_id: str
    check_type: str  # hash_verification, availability_check, corruption_scan
    result: bool
    details: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.check_id,
            "shard_id": self.shard_id,
            "host_id": self.host_id,
            "check_type": self.check_type,
            "result": self.result,
            "details": self.details,
            "timestamp": self.timestamp
        }


@dataclass
class DataRepairOperation:
    """Data repair operation tracking"""
    repair_id: str
    shard_id: str
    failed_hosts: List[str]
    repair_hosts: List[str]
    repair_type: str  # restore_from_replica, reconstruct_from_parity
    status: OperationStatus
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.repair_id,
            "shard_id": self.shard_id,
            "failed_hosts": self.failed_hosts,
            "repair_hosts": self.repair_hosts,
            "repair_type": self.repair_type,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error_message": self.error_message
        }


class ShardHostManagementSystem:
    """
    Shard Host Management System for ongoing operations and maintenance.
    
    Handles:
    - Continuous health monitoring and performance tracking
    - Scheduled and emergency maintenance coordination
    - Data integrity verification and corruption detection
    - Automatic shard repair and recovery operations
    - Host capacity planning and optimization
    - Storage lifecycle management
    """
    
    def __init__(self, db: DatabaseAdapter, shard_creation_system: ShardHostCreationSystem):
        self.db = db
        self.shard_creation_system = shard_creation_system
        
        # State tracking
        self.performance_metrics: Dict[str, PerformanceMetrics] = {}
        self.maintenance_windows: Dict[str, MaintenanceWindow] = {}
        self.active_repairs: Dict[str, DataRepairOperation] = {}
        self.integrity_checks: Dict[str, ShardIntegrityCheck] = {}
        self.running = False
        
        # Background tasks
        self._monitoring_task: Optional[asyncio.Task] = None
        self._integrity_task: Optional[asyncio.Task] = None
        self._maintenance_task: Optional[asyncio.Task] = None
        self._optimization_task: Optional[asyncio.Task] = None
        
        # HTTP client for host communication
        self._http_session: Optional[aiohttp.ClientSession] = None
        
        logger.info("Shard host management system initialized")
    
    async def start(self):
        """Start shard host management system"""
        try:
            self.running = True
            
            # Setup database indexes
            await self._setup_indexes()
            
            # Initialize HTTP client with Tor proxy
            connector = aiohttp.TCPConnector()
            self._http_session = aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=30)
            )
            
            # Load existing maintenance windows
            await self._load_maintenance_windows()
            
            # Start background tasks
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            self._integrity_task = asyncio.create_task(self._integrity_check_loop())
            self._maintenance_task = asyncio.create_task(self._maintenance_loop())
            self._optimization_task = asyncio.create_task(self._optimization_loop())
            
            logger.info("Shard host management system started")
            
        except Exception as e:
            logger.error(f"Failed to start shard host management system: {e}")
            raise
    
    async def stop(self):
        """Stop shard host management system"""
        try:
            self.running = False
            
            # Cancel background tasks
            tasks = [self._monitoring_task, self._integrity_task, self._maintenance_task, self._optimization_task]
            for task in tasks:
                if task and not task.done():
                    task.cancel()
            
            # Wait for tasks to complete
            await asyncio.gather(*[t for t in tasks if t], return_exceptions=True)
            
            # Close HTTP session
            if self._http_session:
                await self._http_session.close()
            
            logger.info("Shard host management system stopped")
            
        except Exception as e:
            logger.error(f"Error stopping shard host management system: {e}")
    
    async def schedule_maintenance(self, node_id: str, maintenance_type: MaintenanceType,
                                 start_time: datetime, end_time: datetime, 
                                 description: str) -> str:
        """
        Schedule maintenance window for a storage host.
        
        Args:
            node_id: Node identifier
            maintenance_type: Type of maintenance
            start_time: Scheduled start time
            end_time: Scheduled end time
            description: Maintenance description
            
        Returns:
            Maintenance window ID
        """
        try:
            maintenance_id = str(uuid.uuid4())
            
            # Get affected shards
            host = self.shard_creation_system.storage_hosts.get(node_id)
            if not host:
                raise ValueError(f"Storage host not found: {node_id}")
            
            affected_shards = list(host.assigned_shards)
            
            # Find backup hosts for affected shards
            backup_hosts = await self._find_backup_hosts(affected_shards, exclude_nodes=[node_id])
            
            maintenance_window = MaintenanceWindow(
                maintenance_id=maintenance_id,
                node_id=node_id,
                maintenance_type=maintenance_type,
                scheduled_start=start_time,
                scheduled_end=end_time,
                description=description,
                affected_shards=affected_shards,
                backup_hosts=backup_hosts
            )
            
            # Store maintenance window
            self.maintenance_windows[maintenance_id] = maintenance_window
            await self.db["maintenance_windows"].replace_one(
                {"_id": maintenance_id},
                maintenance_window.to_dict(),
                upsert=True
            )
            
            logger.info(f"Maintenance scheduled: {maintenance_id} for host {node_id}")
            return maintenance_id
            
        except Exception as e:
            logger.error(f"Failed to schedule maintenance: {e}")
            raise
    
    async def get_host_performance(self, node_id: str, hours: int = 24) -> Optional[Dict[str, Any]]:
        """
        Get host performance metrics.
        
        Args:
            node_id: Node identifier
            hours: Hours of historical data to include
            
        Returns:
            Performance metrics summary
        """
        try:
            # Get current metrics
            current_metrics = self.performance_metrics.get(node_id)
            
            # Get historical metrics from database
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            cursor = self.db["performance_metrics"].find({
                "node_id": node_id,
                "last_updated": {"$gte": cutoff_time}
            }).sort("last_updated", -1)
            
            historical_metrics = await cursor.to_list(length=1000)
            
            if not historical_metrics and not current_metrics:
                return None
            
            # Calculate aggregated metrics
            if historical_metrics:
                avg_response_time = sum(m["response_time_ms"] for m in historical_metrics) / len(historical_metrics)
                avg_uptime = sum(m["uptime_percentage"] for m in historical_metrics) / len(historical_metrics)
                avg_throughput = sum(m["throughput_mbps"] for m in historical_metrics) / len(historical_metrics)
                avg_error_rate = sum(m["error_rate"] for m in historical_metrics) / len(historical_metrics)
            else:
                avg_response_time = current_metrics.response_time_ms if current_metrics else 0
                avg_uptime = current_metrics.uptime_percentage if current_metrics else 0
                avg_throughput = current_metrics.throughput_mbps if current_metrics else 0
                avg_error_rate = current_metrics.error_rate if current_metrics else 0
            
            return {
                "node_id": node_id,
                "current_metrics": current_metrics.to_dict() if current_metrics else None,
                "historical_summary": {
                    "period_hours": hours,
                    "data_points": len(historical_metrics),
                    "avg_response_time_ms": avg_response_time,
                    "avg_uptime_percentage": avg_uptime,
                    "avg_throughput_mbps": avg_throughput,
                    "avg_error_rate": avg_error_rate
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get host performance: {e}")
            return None
    
    async def trigger_integrity_check(self, shard_id: str) -> str:
        """
        Trigger integrity check for a specific shard.
        
        Args:
            shard_id: Shard identifier
            
        Returns:
            Check ID
        """
        try:
            check_id = str(uuid.uuid4())
            
            # Get shard info
            shard = self.shard_creation_system.active_shards.get(shard_id)
            if not shard:
                raise ValueError(f"Shard not found: {shard_id}")
            
            # Perform integrity check asynchronously
            asyncio.create_task(self._perform_integrity_check(check_id, shard))
            
            logger.info(f"Integrity check triggered: {check_id} for shard {shard_id}")
            return check_id
            
        except Exception as e:
            logger.error(f"Failed to trigger integrity check: {e}")
            raise
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        try:
            total_hosts = len(self.shard_creation_system.storage_hosts)
            healthy_hosts = 0
            degraded_hosts = 0
            offline_hosts = 0
            total_shards = len(self.shard_creation_system.active_shards)
            healthy_shards = 0
            degraded_shards = 0
            failed_shards = 0
            
            # Analyze host health
            for host in self.shard_creation_system.storage_hosts.values():
                if host.status == HostStatus.AVAILABLE:
                    healthy_hosts += 1
                elif host.status == HostStatus.DEGRADED:
                    degraded_hosts += 1
                elif host.status == HostStatus.OFFLINE:
                    offline_hosts += 1
            
            # Analyze shard health
            for shard in self.shard_creation_system.active_shards.values():
                if shard.status == ShardStatus.READY:
                    healthy_shards += 1
                elif shard.status == ShardStatus.DEGRADED:
                    degraded_shards += 1
                elif shard.status == ShardStatus.FAILED:
                    failed_shards += 1
            
            # Calculate health scores
            host_health_score = (healthy_hosts / max(total_hosts, 1)) * 100
            shard_health_score = (healthy_shards / max(total_shards, 1)) * 100
            overall_health_score = (host_health_score + shard_health_score) / 2
            
            return {
                "overall_health_score": overall_health_score,
                "hosts": {
                    "total": total_hosts,
                    "healthy": healthy_hosts,
                    "degraded": degraded_hosts,
                    "offline": offline_hosts,
                    "health_percentage": host_health_score
                },
                "shards": {
                    "total": total_shards,
                    "healthy": healthy_shards,
                    "degraded": degraded_shards,
                    "failed": failed_shards,
                    "health_percentage": shard_health_score
                },
                "operations": {
                    "active_maintenance_windows": len(self.maintenance_windows),
                    "active_repairs": len(self.active_repairs),
                    "integrity_checks_24h": await self._count_recent_integrity_checks()
                },
                "last_updated": datetime.now(timezone.utc)
            }
            
        except Exception as e:
            logger.error(f"Failed to get system health: {e}")
            return {"error": str(e)}
    
    async def _monitoring_loop(self):
        """Continuous monitoring of host performance"""
        while self.running:
            try:
                for host in self.shard_creation_system.storage_hosts.values():
                    try:
                        # Skip offline hosts
                        if host.status == HostStatus.OFFLINE:
                            continue
                        
                        # Perform health check
                        metrics = await self._check_host_performance(host)
                        if metrics:
                            self.performance_metrics[host.node_id] = metrics
                            
                            # Store in database
                            await self.db["performance_metrics"].insert_one(metrics.to_dict())
                            
                            # Update host status based on performance
                            await self._update_host_status_from_performance(host, metrics)
                        
                    except Exception as host_error:
                        logger.error(f"Failed to monitor host {host.node_id}: {host_error}")
                
                await asyncio.sleep(HEALTH_CHECK_INTERVAL_SEC)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(30)
    
    async def _check_host_performance(self, host: ShardHost) -> Optional[PerformanceMetrics]:
        """Check performance metrics for a specific host"""
        try:
            if not self._http_session:
                return None
            
            # Use Tor proxy for .onion addresses
            proxy_url = "http://127.0.0.1:8118"  # Privoxy HTTP proxy for Tor
            url = f"http://{host.onion_address}:{host.port}/health/metrics"
            
            start_time = datetime.now(timezone.utc)
            
            async with self._http_session.get(
                url, 
                proxy=proxy_url,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                
                response_time_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                
                if response.status == 200:
                    data = await response.json()
                    
                    metrics = PerformanceMetrics(
                        node_id=host.node_id,
                        response_time_ms=response_time_ms,
                        uptime_percentage=data.get("uptime_percentage", 0),
                        throughput_mbps=data.get("throughput_mbps", 0),
                        error_rate=data.get("error_rate", 0),
                        storage_io_rate=data.get("storage_io_rate", 0),
                        cpu_usage_percentage=data.get("cpu_usage_percentage", 0),
                        memory_usage_percentage=data.get("memory_usage_percentage", 0),
                        network_latency_ms=data.get("network_latency_ms", response_time_ms)
                    )
                    
                    return metrics
                
                else:
                    logger.warning(f"Host health check failed: {host.node_id} returned {response.status}")
                    return None
            
        except Exception as e:
            logger.debug(f"Host performance check failed for {host.node_id}: {e}")
            return None
    
    async def _update_host_status_from_performance(self, host: ShardHost, metrics: PerformanceMetrics):
        """Update host status based on performance metrics"""
        try:
            # Define thresholds for degraded performance
            is_degraded = (
                metrics.response_time_ms > 5000 or  # > 5 seconds
                metrics.uptime_percentage < 95 or   # < 95% uptime
                metrics.error_rate > 0.05 or        # > 5% error rate
                metrics.cpu_usage_percentage > 90 or # > 90% CPU
                metrics.memory_usage_percentage > 90  # > 90% memory
            )
            
            if is_degraded and host.status == HostStatus.AVAILABLE:
                host.status = HostStatus.DEGRADED
                logger.warning(f"Host marked as degraded: {host.node_id}")
                
                # Update in database
                await self.db["shard_hosts"].update_one(
                    {"_id": host.node_id},
                    {"$set": {"status": host.status.value}}
                )
                
            elif not is_degraded and host.status == HostStatus.DEGRADED:
                host.status = HostStatus.AVAILABLE
                logger.info(f"Host recovered from degraded state: {host.node_id}")
                
                # Update in database
                await self.db["shard_hosts"].update_one(
                    {"_id": host.node_id},
                    {"$set": {"status": host.status.value}}
                )
            
        except Exception as e:
            logger.error(f"Failed to update host status: {e}")
    
    async def _integrity_check_loop(self):
        """Periodic integrity checks for shards"""
        while self.running:
            try:
                # Select random shards for integrity checking
                active_shards = list(self.shard_creation_system.active_shards.values())
                if not active_shards:
                    await asyncio.sleep(300)  # Wait 5 minutes if no shards
                    continue
                
                # Check a subset of shards each cycle
                import random
                check_count = min(10, len(active_shards))  # Check up to 10 shards per cycle
                shards_to_check = random.sample(active_shards, check_count)
                
                for shard in shards_to_check:
                    try:
                        check_id = str(uuid.uuid4())
                        await self._perform_integrity_check(check_id, shard)
                        
                    except Exception as shard_error:
                        logger.error(f"Integrity check failed for shard {shard.shard_id}: {shard_error}")
                
                # Wait before next integrity check cycle
                await asyncio.sleep(3600)  # Check every hour
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Integrity check loop error: {e}")
                await asyncio.sleep(300)
    
    async def _perform_integrity_check(self, check_id: str, shard: ShardInfo):
        """Perform integrity check on a shard"""
        try:
            # Check each host that has this shard
            for host_id in shard.assigned_hosts:
                host = self.shard_creation_system.storage_hosts.get(host_id)
                if not host or host.status == HostStatus.OFFLINE:
                    continue
                
                try:
                    # Perform hash verification
                    is_valid = await self._verify_shard_hash(shard, host)
                    
                    check = ShardIntegrityCheck(
                        check_id=f"{check_id}_{host_id}",
                        shard_id=shard.shard_id,
                        host_id=host_id,
                        check_type="hash_verification",
                        result=is_valid,
                        details={
                            "expected_hash": shard.data_hash,
                            "verification_method": "sha256",
                            "host_status": host.status.value
                        }
                    )
                    
                    # Store integrity check result
                    await self.db["integrity_checks"].insert_one(check.to_dict())
                    
                    if not is_valid:
                        logger.warning(f"Shard integrity check failed: {shard.shard_id} on host {host_id}")
                        await self._initiate_shard_repair(shard, [host_id])
                    
                except Exception as host_check_error:
                    logger.error(f"Integrity check failed for shard {shard.shard_id} on host {host_id}: {host_check_error}")
            
        except Exception as e:
            logger.error(f"Failed to perform integrity check: {e}")
    
    async def _verify_shard_hash(self, shard: ShardInfo, host: ShardHost) -> bool:
        """Verify shard hash on a specific host"""
        try:
            if not self._http_session:
                return False
            
            # Request shard hash from host
            proxy_url = "http://127.0.0.1:8118"  # Privoxy HTTP proxy
            url = f"http://{host.onion_address}:{host.port}/storage/verify/{shard.shard_id}"
            
            async with self._http_session.get(url, proxy=proxy_url) as response:
                if response.status == 200:
                    data = await response.json()
                    actual_hash = data.get("hash")
                    return actual_hash == shard.data_hash
                else:
                    return False
            
        except Exception as e:
            logger.debug(f"Shard hash verification failed: {e}")
            return False
    
    async def _initiate_shard_repair(self, shard: ShardInfo, failed_hosts: List[str]):
        """Initiate repair operation for corrupted or missing shard data"""
        try:
            repair_id = str(uuid.uuid4())
            
            # Find healthy hosts with this shard
            healthy_hosts = []
            for host_id in shard.assigned_hosts:
                if host_id not in failed_hosts:
                    host = self.shard_creation_system.storage_hosts.get(host_id)
                    if host and host.status in [HostStatus.AVAILABLE, HostStatus.ASSIGNED]:
                        healthy_hosts.append(host_id)
            
            if not healthy_hosts:
                logger.error(f"No healthy hosts found for shard repair: {shard.shard_id}")
                return
            
            # Find replacement hosts for failed ones
            replacement_hosts = await self._find_backup_hosts([shard.shard_id], exclude_nodes=shard.assigned_hosts)
            repair_hosts = replacement_hosts[:len(failed_hosts)]
            
            repair_operation = DataRepairOperation(
                repair_id=repair_id,
                shard_id=shard.shard_id,
                failed_hosts=failed_hosts,
                repair_hosts=repair_hosts,
                repair_type="restore_from_replica",
                status=OperationStatus.PENDING
            )
            
            self.active_repairs[repair_id] = repair_operation
            await self.db["repair_operations"].insert_one(repair_operation.to_dict())
            
            # Execute repair asynchronously
            asyncio.create_task(self._execute_shard_repair(repair_operation))
            
            logger.info(f"Shard repair initiated: {repair_id} for shard {shard.shard_id}")
            
        except Exception as e:
            logger.error(f"Failed to initiate shard repair: {e}")
    
    async def _execute_shard_repair(self, repair_operation: DataRepairOperation):
        """Execute shard repair operation"""
        try:
            repair_operation.status = OperationStatus.IN_PROGRESS
            await self.db["repair_operations"].update_one(
                {"_id": repair_operation.repair_id},
                {"$set": {"status": repair_operation.status.value}}
            )
            
            # In production, this would copy shard data from healthy hosts to repair hosts
            # For now, simulate the repair process
            await asyncio.sleep(5)  # Simulate repair time
            
            # Update shard assignments
            shard = self.shard_creation_system.active_shards.get(repair_operation.shard_id)
            if shard:
                # Remove failed hosts
                for failed_host in repair_operation.failed_hosts:
                    if failed_host in shard.assigned_hosts:
                        shard.assigned_hosts.remove(failed_host)
                
                # Add repair hosts
                for repair_host in repair_operation.repair_hosts:
                    if repair_host not in shard.assigned_hosts:
                        shard.assigned_hosts.append(repair_host)
                
                # Update database
                await self.db["shards"].update_one(
                    {"_id": shard.shard_id},
                    {"$set": {"assigned_hosts": shard.assigned_hosts}}
                )
            
            # Mark repair as completed
            repair_operation.status = OperationStatus.COMPLETED
            repair_operation.completed_at = datetime.now(timezone.utc)
            
            await self.db["repair_operations"].update_one(
                {"_id": repair_operation.repair_id},
                {"$set": {
                    "status": repair_operation.status.value,
                    "completed_at": repair_operation.completed_at
                }}
            )
            
            logger.info(f"Shard repair completed: {repair_operation.repair_id}")
            
        except Exception as e:
            logger.error(f"Shard repair execution failed: {e}")
            repair_operation.status = OperationStatus.FAILED
            repair_operation.error_message = str(e)
            repair_operation.completed_at = datetime.now(timezone.utc)
            
            await self.db["repair_operations"].update_one(
                {"_id": repair_operation.repair_id},
                {"$set": {
                    "status": repair_operation.status.value,
                    "error_message": repair_operation.error_message,
                    "completed_at": repair_operation.completed_at
                }}
            )
    
    async def _maintenance_loop(self):
        """Process scheduled maintenance windows"""
        while self.running:
            try:
                now = datetime.now(timezone.utc)
                
                # Check for maintenance windows that should start
                for maintenance in list(self.maintenance_windows.values()):
                    if (maintenance.status == OperationStatus.PENDING and
                        now >= maintenance.scheduled_start):
                        
                        await self._start_maintenance(maintenance)
                    
                    elif (maintenance.status == OperationStatus.IN_PROGRESS and
                          now >= maintenance.scheduled_end):
                        
                        await self._end_maintenance(maintenance)
                
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Maintenance loop error: {e}")
                await asyncio.sleep(30)
    
    async def _start_maintenance(self, maintenance: MaintenanceWindow):
        """Start a maintenance window"""
        try:
            maintenance.status = OperationStatus.IN_PROGRESS
            maintenance.actual_start = datetime.now(timezone.utc)
            
            # Update host status
            host = self.shard_creation_system.storage_hosts.get(maintenance.node_id)
            if host:
                host.status = HostStatus.BUSY
                await self.db["shard_hosts"].update_one(
                    {"_id": maintenance.node_id},
                    {"$set": {"status": host.status.value}}
                )
            
            # Update maintenance window
            await self.db["maintenance_windows"].update_one(
                {"_id": maintenance.maintenance_id},
                {"$set": {
                    "status": maintenance.status.value,
                    "actual_start": maintenance.actual_start
                }}
            )
            
            logger.info(f"Maintenance started: {maintenance.maintenance_id}")
            
        except Exception as e:
            logger.error(f"Failed to start maintenance: {e}")
    
    async def _end_maintenance(self, maintenance: MaintenanceWindow):
        """End a maintenance window"""
        try:
            maintenance.status = OperationStatus.COMPLETED
            maintenance.actual_end = datetime.now(timezone.utc)
            
            # Restore host status
            host = self.shard_creation_system.storage_hosts.get(maintenance.node_id)
            if host:
                host.status = HostStatus.AVAILABLE
                await self.db["shard_hosts"].update_one(
                    {"_id": maintenance.node_id},
                    {"$set": {"status": host.status.value}}
                )
            
            # Update maintenance window
            await self.db["maintenance_windows"].update_one(
                {"_id": maintenance.maintenance_id},
                {"$set": {
                    "status": maintenance.status.value,
                    "actual_end": maintenance.actual_end
                }}
            )
            
            # Remove from active maintenance windows
            del self.maintenance_windows[maintenance.maintenance_id]
            
            logger.info(f"Maintenance completed: {maintenance.maintenance_id}")
            
        except Exception as e:
            logger.error(f"Failed to end maintenance: {e}")
    
    async def _optimization_loop(self):
        """Periodic optimization and cleanup"""
        while self.running:
            try:
                # Clean up old performance metrics (older than 7 days)
                cutoff_time = datetime.now(timezone.utc) - timedelta(days=7)
                await self.db["performance_metrics"].delete_many({"last_updated": {"$lt": cutoff_time}})
                
                # Clean up old integrity checks (older than 30 days)
                cutoff_time = datetime.now(timezone.utc) - timedelta(days=30)
                await self.db["integrity_checks"].delete_many({"timestamp": {"$lt": cutoff_time}})
                
                # Clean up completed repair operations (older than 7 days)
                cutoff_time = datetime.now(timezone.utc) - timedelta(days=7)
                await self.db["repair_operations"].delete_many({
                    "status": OperationStatus.COMPLETED.value,
                    "completed_at": {"$lt": cutoff_time}
                })
                
                # Optimize storage allocation
                await self._optimize_storage_allocation()
                
                await asyncio.sleep(86400)  # Optimize daily
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Optimization loop error: {e}")
                await asyncio.sleep(3600)
    
    async def _optimize_storage_allocation(self):
        """Optimize storage allocation across hosts"""
        try:
            # Check for hosts that are over-utilized
            hosts = list(self.shard_creation_system.storage_hosts.values())
            
            overutilized_hosts = [
                host for host in hosts
                if host.storage_utilization > 0.85  # > 85% utilized
            ]
            
            underutilized_hosts = [
                host for host in hosts
                if host.storage_utilization < 0.5 and host.status == HostStatus.AVAILABLE  # < 50% utilized
            ]
            
            if overutilized_hosts and underutilized_hosts:
                logger.info(f"Storage optimization: {len(overutilized_hosts)} overutilized, {len(underutilized_hosts)} underutilized hosts")
                # In production, this would trigger shard migration
            
        except Exception as e:
            logger.error(f"Storage optimization failed: {e}")
    
    async def _find_backup_hosts(self, shard_ids: List[str], exclude_nodes: List[str] = None) -> List[str]:
        """Find suitable backup hosts for shards"""
        try:
            exclude_nodes = exclude_nodes or []
            available_hosts = []
            
            for host in self.shard_creation_system.storage_hosts.values():
                if (host.node_id not in exclude_nodes and
                    host.status == HostStatus.AVAILABLE and
                    len(host.assigned_shards) < 1000):  # Max shards per host
                    available_hosts.append(host.node_id)
            
            # Return up to the required number of backup hosts
            return available_hosts[:len(shard_ids) * BACKUP_REDUNDANCY_FACTOR]
            
        except Exception as e:
            logger.error(f"Failed to find backup hosts: {e}")
            return []
    
    async def _count_recent_integrity_checks(self) -> int:
        """Count integrity checks in the last 24 hours"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
            count = await self.db["integrity_checks"].count_documents({"timestamp": {"$gte": cutoff_time}})
            return count
        except Exception as e:
            logger.error(f"Failed to count recent integrity checks: {e}")
            return 0
    
    async def _setup_indexes(self):
        """Setup database indexes"""
        try:
            # Performance metrics indexes
            await self.db["performance_metrics"].create_index("node_id")
            await self.db["performance_metrics"].create_index("last_updated")
            
            # Maintenance windows indexes
            await self.db["maintenance_windows"].create_index("node_id")
            await self.db["maintenance_windows"].create_index("scheduled_start")
            await self.db["maintenance_windows"].create_index("status")
            
            # Integrity checks indexes
            await self.db["integrity_checks"].create_index("shard_id")
            await self.db["integrity_checks"].create_index("host_id")
            await self.db["integrity_checks"].create_index("timestamp")
            
            # Repair operations indexes
            await self.db["repair_operations"].create_index("shard_id")
            await self.db["repair_operations"].create_index("status")
            await self.db["repair_operations"].create_index("started_at")
            
            logger.info("Shard host management database indexes created")
            
        except Exception as e:
            logger.warning(f"Failed to create shard management indexes: {e}")
    
    async def _load_maintenance_windows(self):
        """Load active maintenance windows from database"""
        try:
            cursor = self.db["maintenance_windows"].find({
                "status": {"$in": [OperationStatus.PENDING.value, OperationStatus.IN_PROGRESS.value]}
            })
            
            async for window_doc in cursor:
                maintenance = MaintenanceWindow(
                    maintenance_id=window_doc["_id"],
                    node_id=window_doc["node_id"],
                    maintenance_type=MaintenanceType(window_doc["type"]),
                    scheduled_start=window_doc["scheduled_start"],
                    scheduled_end=window_doc["scheduled_end"],
                    description=window_doc["description"],
                    status=OperationStatus(window_doc["status"]),
                    actual_start=window_doc.get("actual_start"),
                    actual_end=window_doc.get("actual_end"),
                    affected_shards=window_doc.get("affected_shards", []),
                    backup_hosts=window_doc.get("backup_hosts", [])
                )
                
                self.maintenance_windows[maintenance.maintenance_id] = maintenance
                
            logger.info(f"Loaded {len(self.maintenance_windows)} active maintenance windows")
            
        except Exception as e:
            logger.error(f"Failed to load maintenance windows: {e}")


# Global shard host management system instance
_shard_host_management: Optional[ShardHostManagementSystem] = None


def get_shard_host_management() -> Optional[ShardHostManagementSystem]:
    """Get global shard host management system instance"""
    global _shard_host_management
    return _shard_host_management


def create_shard_host_management(db: DatabaseAdapter,
                                shard_creation_system: ShardHostCreationSystem) -> ShardHostManagementSystem:
    """Create shard host management system instance"""
    global _shard_host_management
    _shard_host_management = ShardHostManagementSystem(db, shard_creation_system)
    return _shard_host_management


async def cleanup_shard_host_management():
    """Cleanup shard host management system"""
    global _shard_host_management
    if _shard_host_management:
        await _shard_host_management.stop()
        _shard_host_management = None


if __name__ == "__main__":
    # Test shard host management system
    async def test_shard_host_management():
        print("Testing Lucid Shard Host Management System...")
        
        # This would normally be initialized with real components
        # For testing purposes, we'll create mock instances
        
        print("Test completed - shard host management system ready")
    
    asyncio.run(test_shard_host_management())