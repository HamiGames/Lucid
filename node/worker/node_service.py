# Path: node/worker/node_service.py
# Lucid Node Service - Node lifecycle management
# Based on LUCID-STRICT requirements per Spec-1c

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database_adapter import DatabaseAdapter

logger = logging.getLogger(__name__)


class NodeStatus(Enum):
    """Node operational status"""
    STARTING = "starting"
    READY = "ready"
    BUSY = "busy"
    MAINTENANCE = "maintenance"
    OFFLINE = "offline"
    ERROR = "error"


class NodeRole(Enum):
    """Node role in the network"""
    WORKER = "worker"
    LEADER = "leader"
    COORDINATOR = "coordinator"
    OBSERVER = "observer"


@dataclass
class NodeInfo:
    """Node information"""
    node_id: str
    node_address: str
    status: NodeStatus
    role: NodeRole
    created_at: datetime
    last_seen: datetime
    capabilities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.node_id,
            "node_address": self.node_address,
            "status": self.status.value if hasattr(self.status, 'value') else self.status,
            "role": self.role.value if hasattr(self.role, 'value') else self.role,
            "created_at": self.created_at,
            "last_seen": self.last_seen,
            "capabilities": self.capabilities,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NodeInfo':
        return cls(
            node_id=data["_id"],
            node_address=data["node_address"],
            status=NodeStatus(data["status"]),
            role=NodeRole(data["role"]),
            created_at=data["created_at"],
            last_seen=data["last_seen"],
            capabilities=data.get("capabilities", []),
            metadata=data.get("metadata", {})
        )


@dataclass
class NodeMetrics:
    """Node performance metrics"""
    node_id: str
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_bandwidth_mbps: float
    active_sessions: int
    total_sessions: int
    uptime_seconds: int
    poot_score: float = 0.0
    work_credits: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "timestamp": self.timestamp,
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "disk_percent": self.disk_percent,
            "network_bandwidth_mbps": self.network_bandwidth_mbps,
            "active_sessions": self.active_sessions,
            "total_sessions": self.total_sessions,
            "uptime_seconds": self.uptime_seconds,
            "poot_score": self.poot_score,
            "work_credits": self.work_credits
        }


class NodeService:
    """
    Node service for managing node lifecycle and status.
    
    Handles:
    - Node registration and discovery
    - Status monitoring and updates
    - Capability management
    - Health checks and maintenance
    - Metrics collection and reporting
    """
    
    def __init__(self, db: DatabaseAdapter, node_id: str, node_address: str):
        self.db = db
        self.node_id = node_id
        self.node_address = node_address
        self.running = False
        
        # Node information
        self.node_info: Optional[NodeInfo] = None
        self.metrics_history: List[NodeMetrics] = []
        
        # Background tasks
        self._tasks: List[asyncio.Task] = []
        
        logger.info(f"Node service initialized: {node_id}")
    
    async def start(self):
        """Start node service"""
        try:
            logger.info(f"Starting node service {self.node_id}...")
            self.running = True
            
            # Register node
            await self._register_node()
            
            # Start background tasks
            self._tasks.append(asyncio.create_task(self._status_update_loop()))
            self._tasks.append(asyncio.create_task(self._health_check_loop()))
            self._tasks.append(asyncio.create_task(self._metrics_collection_loop()))
            
            logger.info(f"Node service {self.node_id} started")
            
        except Exception as e:
            logger.error(f"Failed to start node service: {e}")
            raise
    
    async def stop(self):
        """Stop node service"""
        try:
            logger.info(f"Stopping node service {self.node_id}...")
            self.running = False
            
            # Cancel background tasks
            for task in self._tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for tasks to complete
            if self._tasks:
                await asyncio.gather(*self._tasks, return_exceptions=True)
            
            # Update node status to offline
            if self.node_info:
                await self._update_node_status(NodeStatus.OFFLINE)
            
            logger.info(f"Node service {self.node_id} stopped")
            
        except Exception as e:
            logger.error(f"Error stopping node service: {e}")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get node service status"""
        try:
            if not self.node_info:
                return {"error": "Node not registered"}
            
            # Get recent metrics
            recent_metrics = None
            if self.metrics_history:
                recent_metrics = self.metrics_history[-1].to_dict()
            
            return {
                "node_id": self.node_id,
                "node_address": self.node_address,
                "status": self.node_info.status.value if hasattr(self.node_info.status, 'value') else self.node_info.status,
                "role": self.node_info.role.value if hasattr(self.node_info.role, 'value') else self.node_info.role,
                "capabilities": self.node_info.capabilities,
                "created_at": self.node_info.created_at,
                "last_seen": self.node_info.last_seen,
                "metrics": recent_metrics,
                "running": self.running
            }
            
        except Exception as e:
            logger.error(f"Failed to get node status: {e}")
            return {"error": str(e)}
    
    async def update_status(self, status: NodeStatus):
        """Update node status"""
        try:
            await self._update_node_status(status)
            logger.info(f"Node status updated: {status.value if hasattr(status, 'value') else status}")
            
        except Exception as e:
            logger.error(f"Failed to update node status: {e}")
    
    async def update_capabilities(self, capabilities: List[str]):
        """Update node capabilities"""
        try:
            if self.node_info:
                self.node_info.capabilities = capabilities
                await self._save_node_info()
                logger.info(f"Node capabilities updated: {capabilities}")
            
        except Exception as e:
            logger.error(f"Failed to update capabilities: {e}")
    
    async def update_metadata(self, metadata: Dict[str, Any]):
        """Update node metadata"""
        try:
            if self.node_info:
                self.node_info.metadata.update(metadata)
                await self._save_node_info()
                logger.info(f"Node metadata updated")
            
        except Exception as e:
            logger.error(f"Failed to update metadata: {e}")
    
    async def update_poot_scores(self, poot_scores: Dict[str, float]):
        """Update PoOT scores for the node"""
        try:
            if self.node_id in poot_scores:
                # Update latest metrics with PoOT score
                if self.metrics_history:
                    self.metrics_history[-1].poot_score = poot_scores[self.node_id]
                
                # Update node metadata
                await self.update_metadata({
                    "poot_score": poot_scores[self.node_id],
                    "poot_updated": datetime.now(timezone.utc)
                })
                
                logger.info(f"PoOT score updated: {poot_scores[self.node_id]}")
            
        except Exception as e:
            logger.error(f"Failed to update PoOT scores: {e}")
    
    async def get_metrics(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get node metrics for specified time period"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            # Filter metrics by time
            recent_metrics = [
                metric for metric in self.metrics_history
                if metric.timestamp >= cutoff_time
            ]
            
            return [metric.to_dict() for metric in recent_metrics]
            
        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return []
    
    async def _register_node(self):
        """Register node in the database"""
        try:
            # Check if node already exists
            existing_node = await self.db["nodes"].find_one({"_id": self.node_id})
            
            if existing_node:
                # Load existing node info
                self.node_info = NodeInfo.from_dict(existing_node)
                logger.info(f"Loaded existing node: {self.node_id}")
            else:
                # Create new node
                self.node_info = NodeInfo(
                    node_id=self.node_id,
                    node_address=self.node_address,
                    status=NodeStatus.STARTING,
                    role=NodeRole.WORKER,
                    created_at=datetime.now(timezone.utc),
                    last_seen=datetime.now(timezone.utc),
                    capabilities=["session_processing", "resource_monitoring"],
                    metadata={}
                )
                
                await self._save_node_info()
                logger.info(f"Registered new node: {self.node_id}")
            
        except Exception as e:
            logger.error(f"Failed to register node: {e}")
            raise
    
    async def _update_node_status(self, status: NodeStatus):
        """Update node status in database"""
        try:
            if self.node_info:
                self.node_info.status = status
                self.node_info.last_seen = datetime.now(timezone.utc)
                await self._save_node_info()
            
        except Exception as e:
            logger.error(f"Failed to update node status: {e}")
    
    async def _save_node_info(self):
        """Save node information to database"""
        try:
            if self.node_info:
                await self.db["nodes"].replace_one(
                    {"_id": self.node_id},
                    self.node_info.to_dict(),
                    upsert=True
                )
            
        except Exception as e:
            logger.error(f"Failed to save node info: {e}")
    
    async def _status_update_loop(self):
        """Periodic status update loop"""
        while self.running:
            try:
                # Update last seen timestamp
                if self.node_info:
                    self.node_info.last_seen = datetime.now(timezone.utc)
                    await self._save_node_info()
                
                await asyncio.sleep(60)  # Update every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Status update loop error: {e}")
                await asyncio.sleep(30)
    
    async def _health_check_loop(self):
        """Periodic health check loop"""
        while self.running:
            try:
                # Perform health checks
                health_status = await self._perform_health_check()
                
                # Update node status based on health
                if health_status["healthy"]:
                    if self.node_info and self.node_info.status == NodeStatus.ERROR:
                        await self._update_node_status(NodeStatus.READY)
                else:
                    await self._update_node_status(NodeStatus.ERROR)
                
                await asyncio.sleep(120)  # Check every 2 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(60)
    
    async def _metrics_collection_loop(self):
        """Periodic metrics collection loop"""
        while self.running:
            try:
                # Collect current metrics
                metrics = await self._collect_metrics()
                
                if metrics:
                    self.metrics_history.append(metrics)
                    
                    # Keep only last 1000 metrics
                    if len(self.metrics_history) > 1000:
                        self.metrics_history = self.metrics_history[-1000:]
                    
                    # Save metrics to database
                    await self.db["node_metrics"].insert_one(metrics.to_dict())
                
                await asyncio.sleep(300)  # Collect every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Metrics collection loop error: {e}")
                await asyncio.sleep(60)
    
    async def _perform_health_check(self) -> Dict[str, Any]:
        """Perform node health check"""
        try:
            # Basic health checks
            health_status = {
                "healthy": True,
                "checks": {},
                "timestamp": datetime.now(timezone.utc)
            }
            
            # Check database connection
            try:
                await self.db["nodes"].find_one({"_id": self.node_id})
                health_status["checks"]["database"] = "ok"
            except Exception as e:
                health_status["checks"]["database"] = f"error: {e}"
                health_status["healthy"] = False
            
            # Check resource usage (simplified)
            try:
                import psutil
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                
                if cpu_percent > 90:
                    health_status["checks"]["cpu"] = f"high: {cpu_percent}%"
                    health_status["healthy"] = False
                else:
                    health_status["checks"]["cpu"] = f"ok: {cpu_percent}%"
                
                if memory.percent > 90:
                    health_status["checks"]["memory"] = f"high: {memory.percent}%"
                    health_status["healthy"] = False
                else:
                    health_status["checks"]["memory"] = f"ok: {memory.percent}%"
                    
            except ImportError:
                health_status["checks"]["resources"] = "psutil not available"
            except Exception as e:
                health_status["checks"]["resources"] = f"error: {e}"
                health_status["healthy"] = False
            
            return health_status
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "healthy": False,
                "checks": {"error": str(e)},
                "timestamp": datetime.now(timezone.utc)
            }
    
    async def _collect_metrics(self) -> Optional[NodeMetrics]:
        """Collect current node metrics"""
        try:
            import psutil
            
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Calculate uptime (simplified)
            uptime_seconds = 0
            if self.node_info:
                uptime_seconds = int((datetime.now(timezone.utc) - self.node_info.created_at).total_seconds())
            
            # Get network bandwidth (simplified)
            net_io = psutil.net_io_counters()
            network_bandwidth = 0.0  # Would need historical data for accurate calculation
            
            metrics = NodeMetrics(
                node_id=self.node_id,
                timestamp=datetime.now(timezone.utc),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_percent=(disk.used / disk.total) * 100,
                network_bandwidth_mbps=network_bandwidth,
                active_sessions=0,  # Would be updated by node worker
                total_sessions=0,  # Would be updated by node worker
                uptime_seconds=uptime_seconds
            )
            
            return metrics
            
        except ImportError:
            logger.warning("psutil not available for metrics collection")
            return None
        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
            return None


# Global node service instance
_node_service: Optional[NodeService] = None


def get_node_service() -> Optional[NodeService]:
    """Get global node service instance"""
    global _node_service
    return _node_service


def create_node_service(db: DatabaseAdapter, node_id: str, node_address: str) -> NodeService:
    """Create node service instance"""
    global _node_service
    _node_service = NodeService(db, node_id, node_address)
    return _node_service


async def cleanup_node_service():
    """Cleanup node service"""
    global _node_service
    if _node_service:
        await _node_service.stop()
        _node_service = None


if __name__ == "__main__":
    # Test node service
    async def test_node_service():
        print("Testing Lucid Node Service...")
        
        # This would normally be initialized with real components
        # For testing purposes, we'll create mock instances
        
        print("Test completed - node service ready")
    
    asyncio.run(test_node_service())
