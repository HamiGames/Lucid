"""
LUCID Node Consensus - Uptime Beacon System
Implements uptime monitoring and beacon generation for PoOT consensus
Distroless container: pickme/lucid:node-worker:latest
"""

import asyncio
import json
import logging
import os
import time
import hashlib
import hmac
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
import aiofiles
from dataclasses import dataclass, asdict
from pydantic import BaseModel, Field
import cryptography
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BeaconStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    MAINTENANCE = "maintenance"

class BeaconType(str, Enum):
    HEARTBEAT = "heartbeat"
    HEALTH_CHECK = "health_check"
    PERFORMANCE_METRIC = "performance_metric"
    NETWORK_STATUS = "network_status"
    STORAGE_STATUS = "storage_status"

@dataclass
class UptimeBeacon:
    """Uptime beacon data structure"""
    beacon_id: str
    node_id: str
    beacon_type: BeaconType
    timestamp: datetime
    status: BeaconStatus
    metrics: Dict[str, Any]
    signature: str
    network_latency: Optional[float] = None
    storage_available: Optional[float] = None
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None

@dataclass
class UptimeMetrics:
    """Uptime metrics for a node"""
    node_id: str
    total_beacons: int
    successful_beacons: int
    failed_beacons: int
    uptime_percentage: float
    average_latency: float
    last_beacon_time: datetime
    consecutive_failures: int
    status: BeaconStatus

class BeaconRequest(BaseModel):
    """Pydantic model for beacon requests"""
    node_id: str = Field(..., description="Node sending beacon")
    beacon_type: BeaconType = Field(default=BeaconType.HEARTBEAT, description="Type of beacon")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Node metrics")
    timestamp: Optional[datetime] = Field(default_factory=datetime.now)

class BeaconResponse(BaseModel):
    """Response model for beacon operations"""
    beacon_id: str
    status: str
    message: str
    uptime_percentage: float
    consecutive_failures: int

class UptimeBeaconSystem:
    """Manages uptime beacons and monitoring for PoOT consensus"""
    
    def __init__(self):
        # Use writable volume mount locations (/app/data, /app/cache, and /app/logs are volume mounts)
        self.data_dir = Path("/app/data/node/uptime_beacons")
        self.cache_dir = Path("/app/cache/node")
        self.logs_dir = Path("/app/logs/node")
        
        # Ensure directories exist
        for directory in [self.data_dir, self.cache_dir, self.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Configuration
        self.node_id = os.getenv("LUCID_NODE_ID", "node-001")
        self.mongodb_url = os.getenv("LUCID_MONGODB_URL", "mongodb://lucid:lucid@lucid_mongo:27017/lucid")
        self.consensus_api_url = os.getenv("LUCID_CONSENSUS_API_URL", "http://consensus-api:8080")
        
        # Beacon parameters
        self.beacon_interval = int(os.getenv("LUCID_BEACON_INTERVAL", "60"))  # seconds
        self.beacon_timeout = int(os.getenv("LUCID_BEACON_TIMEOUT", "30"))  # seconds
        self.max_consecutive_failures = int(os.getenv("LUCID_MAX_CONSECUTIVE_FAILURES", "5"))
        self.uptime_threshold = float(os.getenv("LUCID_UPTIME_THRESHOLD", "0.8"))  # 80%
        
        # Node key pair for signing
        self.node_private_key = self._load_or_generate_key()
        self.node_public_key = self.node_private_key.public_key()
        
        # Beacon tracking
        self.beacon_cache: Dict[str, UptimeBeacon] = {}
        self.uptime_metrics: Dict[str, UptimeMetrics] = {}
        self.beacon_tasks: Dict[str, asyncio.Task] = {}
        
        # Note: Async tasks will be started when the service is properly initialized
        # This prevents RuntimeError when creating tasks outside of an event loop
    
    def _load_or_generate_key(self) -> ed25519.Ed25519PrivateKey:
        """Load or generate node private key"""
        try:
            key_file = self.data_dir / "beacon_key.pem"
            
            if key_file.exists():
                with open(key_file, "rb") as f:
                    key_data = f.read()
                return serialization.load_pem_private_key(key_data, password=None)
            else:
                # Generate new key
                private_key = ed25519.Ed25519PrivateKey.generate()
                
                # Save key
                key_data = private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                )
                
                with open(key_file, "wb") as f:
                    f.write(key_data)
                
                logger.info("Generated new beacon private key")
                return private_key
                
        except Exception as e:
            logger.error(f"Error loading/generating beacon key: {e}")
            # Fallback to generating new key
            return ed25519.Ed25519PrivateKey.generate()
    
    async def _load_beacon_data(self):
        """Load existing beacon data from disk"""
        try:
            # Load beacons
            beacons_file = self.data_dir / "beacons.json"
            if beacons_file.exists():
                async with aiofiles.open(beacons_file, "r") as f:
                    data = await f.read()
                    beacons_data = json.loads(data)
                    
                    for beacon_id, beacon_data in beacons_data.items():
                        beacon = UptimeBeacon(**beacon_data)
                        self.beacon_cache[beacon_id] = beacon
                    
                logger.info(f"Loaded {len(self.beacon_cache)} beacons")
            
            # Load metrics
            metrics_file = self.data_dir / "uptime_metrics.json"
            if metrics_file.exists():
                async with aiofiles.open(metrics_file, "r") as f:
                    data = await f.read()
                    metrics_data = json.loads(data)
                    
                    for node_id, metric_data in metrics_data.items():
                        metrics = UptimeMetrics(**metric_data)
                        self.uptime_metrics[node_id] = metrics
                    
                logger.info(f"Loaded {len(self.uptime_metrics)} uptime metrics")
                
        except Exception as e:
            logger.error(f"Error loading beacon data: {e}")
    
    async def _save_beacon_data(self):
        """Save beacon data to disk"""
        try:
            # Save beacons
            beacons_data = {k: asdict(v) for k, v in self.beacon_cache.items()}
            beacons_file = self.data_dir / "beacons.json"
            async with aiofiles.open(beacons_file, "w") as f:
                await f.write(json.dumps(beacons_data, indent=2, default=str))
            
            # Save metrics
            metrics_data = {k: asdict(v) for k, v in self.uptime_metrics.items()}
            metrics_file = self.data_dir / "uptime_metrics.json"
            async with aiofiles.open(metrics_file, "w") as f:
                await f.write(json.dumps(metrics_data, indent=2, default=str))
                
        except Exception as e:
            logger.error(f"Error saving beacon data: {e}")
    
    async def _start_beacon_system(self):
        """Start the beacon system"""
        try:
            logger.info("Starting uptime beacon system")
            
            # Start beacon task for this node
            beacon_task = asyncio.create_task(self._send_periodic_beacons())
            self.beacon_tasks[self.node_id] = beacon_task
            
            # Start metrics calculation task
            metrics_task = asyncio.create_task(self._calculate_uptime_metrics())
            
            # Wait for tasks
            await asyncio.gather(beacon_task, metrics_task)
            
        except Exception as e:
            logger.error(f"Error in beacon system: {e}")
    
    async def _send_periodic_beacons(self):
        """Send periodic beacons"""
        try:
            while True:
                try:
                    # Collect node metrics
                    metrics = await self._collect_node_metrics()
                    
                    # Create beacon request
                    request = BeaconRequest(
                        node_id=self.node_id,
                        beacon_type=BeaconType.HEARTBEAT,
                        metrics=metrics
                    )
                    
                    # Send beacon
                    response = await self.send_beacon(request)
                    
                    if response.status == "success":
                        logger.debug(f"Beacon sent successfully: {response.beacon_id}")
                    else:
                        logger.warning(f"Beacon failed: {response.message}")
                    
                except Exception as e:
                    logger.error(f"Error sending beacon: {e}")
                
                # Wait for next beacon interval
                await asyncio.sleep(self.beacon_interval)
                
        except asyncio.CancelledError:
            logger.info("Beacon system cancelled")
        except Exception as e:
            logger.error(f"Error in periodic beacon sending: {e}")
    
    async def _collect_node_metrics(self) -> Dict[str, Any]:
        """Collect node performance metrics"""
        try:
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "node_id": self.node_id,
                "system_metrics": {}
            }
            
            # Collect system metrics (simulated)
            metrics["system_metrics"] = {
                "cpu_usage": 0.45,  # This would be real CPU usage
                "memory_usage": 0.60,  # This would be real memory usage
                "disk_usage": 0.30,  # This would be real disk usage
                "network_io": {
                    "bytes_in": 1024000,
                    "bytes_out": 2048000
                },
                "load_average": [0.5, 0.6, 0.7]
            }
            
            # Collect network metrics
            metrics["network_metrics"] = {
                "latency_ms": 12.5,  # This would be real network latency
                "bandwidth_mbps": 100.0,  # This would be real bandwidth
                "packet_loss": 0.001,  # This would be real packet loss
                "connections": 50  # This would be real connection count
            }
            
            # Collect storage metrics
            metrics["storage_metrics"] = {
                "total_space_gb": 1000.0,
                "used_space_gb": 300.0,
                "available_space_gb": 700.0,
                "io_operations": 1500  # This would be real IO operations
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting node metrics: {e}")
            return {"timestamp": datetime.now().isoformat(), "error": str(e)}
    
    async def send_beacon(self, request: BeaconRequest) -> BeaconResponse:
        """Send an uptime beacon"""
        try:
            # Validate request
            await self._validate_beacon_request(request)
            
            # Create beacon
            beacon_id = await self._generate_beacon_id(request)
            signature = await self._sign_beacon(beacon_id, request)
            
            # Extract metrics
            system_metrics = request.metrics.get("system_metrics", {})
            network_metrics = request.metrics.get("network_metrics", {})
            storage_metrics = request.metrics.get("storage_metrics", {})
            
            beacon = UptimeBeacon(
                beacon_id=beacon_id,
                node_id=request.node_id,
                beacon_type=request.beacon_type,
                timestamp=request.timestamp or datetime.now(),
                status=BeaconStatus.ACTIVE,
                metrics=request.metrics,
                signature=signature,
                network_latency=network_metrics.get("latency_ms"),
                storage_available=storage_metrics.get("available_space_gb"),
                cpu_usage=system_metrics.get("cpu_usage"),
                memory_usage=system_metrics.get("memory_usage")
            )
            
            # Store beacon
            self.beacon_cache[beacon_id] = beacon
            
            # Update uptime metrics
            await self._update_uptime_metrics(request.node_id, True)
            
            # Save data
            await self._save_beacon_data()
            
            # Log beacon
            await self._log_beacon_event(beacon_id, "beacon_sent", {
                "node_id": request.node_id,
                "beacon_type": request.beacon_type,
                "metrics_count": len(request.metrics)
            })
            
            # Get current uptime percentage
            uptime_metrics = self.uptime_metrics.get(request.node_id)
            uptime_percentage = uptime_metrics.uptime_percentage if uptime_metrics else 0.0
            consecutive_failures = uptime_metrics.consecutive_failures if uptime_metrics else 0
            
            logger.info(f"Beacon sent: {beacon_id} - Uptime: {uptime_percentage:.2%}")
            
            return BeaconResponse(
                beacon_id=beacon_id,
                status="success",
                message="Beacon sent successfully",
                uptime_percentage=uptime_percentage,
                consecutive_failures=consecutive_failures
            )
            
        except Exception as e:
            logger.error(f"Error sending beacon: {e}")
            
            # Update uptime metrics for failure
            await self._update_uptime_metrics(request.node_id, False)
            
            return BeaconResponse(
                beacon_id="",
                status="error",
                message=f"Failed to send beacon: {str(e)}",
                uptime_percentage=0.0,
                consecutive_failures=0
            )
    
    async def _validate_beacon_request(self, request: BeaconRequest):
        """Validate beacon request"""
        if not request.node_id:
            raise ValueError("Node ID is required")
        
        if not request.metrics:
            raise ValueError("Metrics are required")
        
        # Validate timestamp
        if request.timestamp:
            time_diff = abs((datetime.now() - request.timestamp).total_seconds())
            if time_diff > self.beacon_timeout:
                raise ValueError(f"Beacon timestamp too old: {time_diff}s > {self.beacon_timeout}s")
    
    async def _generate_beacon_id(self, request: BeaconRequest) -> str:
        """Generate unique beacon ID"""
        timestamp = int(time.time())
        node_hash = hashlib.sha256(request.node_id.encode()).hexdigest()[:8]
        type_hash = hashlib.sha256(request.beacon_type.value.encode()).hexdigest()[:8]
        metrics_hash = hashlib.sha256(json.dumps(request.metrics, sort_keys=True).encode()).hexdigest()[:8]
        
        return f"beacon_{timestamp}_{node_hash}_{type_hash}_{metrics_hash}"
    
    async def _sign_beacon(self, beacon_id: str, request: BeaconRequest) -> str:
        """Sign beacon"""
        try:
            # Create signature data
            signature_data = {
                "beacon_id": beacon_id,
                "node_id": request.node_id,
                "beacon_type": request.beacon_type.value,
                "timestamp": request.timestamp.isoformat() if request.timestamp else datetime.now().isoformat(),
                "metrics_hash": hashlib.sha256(json.dumps(request.metrics, sort_keys=True).encode()).hexdigest()
            }
            
            # Serialize data
            data_string = json.dumps(signature_data, sort_keys=True)
            data_bytes = data_string.encode()
            
            # Sign data
            signature = self.node_private_key.sign(data_bytes)
            
            return signature.hex()
            
        except Exception as e:
            logger.error(f"Error signing beacon: {e}")
            raise
    
    async def _update_uptime_metrics(self, node_id: str, success: bool):
        """Update uptime metrics for a node"""
        try:
            if node_id not in self.uptime_metrics:
                self.uptime_metrics[node_id] = UptimeMetrics(
                    node_id=node_id,
                    total_beacons=0,
                    successful_beacons=0,
                    failed_beacons=0,
                    uptime_percentage=0.0,
                    average_latency=0.0,
                    last_beacon_time=datetime.now(),
                    consecutive_failures=0,
                    status=BeaconStatus.ACTIVE
                )
            
            metrics = self.uptime_metrics[node_id]
            
            # Update counters
            metrics.total_beacons += 1
            if success:
                metrics.successful_beacons += 1
                metrics.consecutive_failures = 0
            else:
                metrics.failed_beacons += 1
                metrics.consecutive_failures += 1
            
            # Calculate uptime percentage
            if metrics.total_beacons > 0:
                metrics.uptime_percentage = metrics.successful_beacons / metrics.total_beacons
            
            # Update status
            if metrics.consecutive_failures >= self.max_consecutive_failures:
                metrics.status = BeaconStatus.SUSPENDED
            elif metrics.uptime_percentage < self.uptime_threshold:
                metrics.status = BeaconStatus.INACTIVE
            else:
                metrics.status = BeaconStatus.ACTIVE
            
            # Update last beacon time
            metrics.last_beacon_time = datetime.now()
            
            # Calculate average latency
            recent_beacons = [b for b in self.beacon_cache.values() 
                            if b.node_id == node_id and b.network_latency is not None]
            if recent_beacons:
                metrics.average_latency = sum(b.network_latency for b in recent_beacons) / len(recent_beacons)
            
        except Exception as e:
            logger.error(f"Error updating uptime metrics: {e}")
    
    async def _calculate_uptime_metrics(self):
        """Calculate uptime metrics periodically"""
        try:
            while True:
                try:
                    # Calculate metrics for all nodes
                    for node_id in list(self.uptime_metrics.keys()):
                        await self._update_uptime_metrics(node_id, True)  # This will recalculate
                    
                    # Save metrics
                    await self._save_beacon_data()
                    
                    # Log metrics
                    await self._log_uptime_metrics()
                    
                except Exception as e:
                    logger.error(f"Error calculating uptime metrics: {e}")
                
                # Wait for next calculation interval
                await asyncio.sleep(300)  # 5 minutes
                
        except asyncio.CancelledError:
            logger.info("Uptime metrics calculation cancelled")
        except Exception as e:
            logger.error(f"Error in uptime metrics calculation: {e}")
    
    async def _log_uptime_metrics(self):
        """Log current uptime metrics"""
        try:
            for node_id, metrics in self.uptime_metrics.items():
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "node_id": node_id,
                    "uptime_percentage": metrics.uptime_percentage,
                    "total_beacons": metrics.total_beacons,
                    "successful_beacons": metrics.successful_beacons,
                    "failed_beacons": metrics.failed_beacons,
                    "consecutive_failures": metrics.consecutive_failures,
                    "status": metrics.status.value,
                    "average_latency": metrics.average_latency
                }
                
                log_file = self.logs_dir / f"uptime_metrics_{datetime.now().strftime('%Y%m%d')}.log"
                async with aiofiles.open(log_file, "a") as f:
                    await f.write(json.dumps(log_entry) + "\n")
                    
        except Exception as e:
            logger.error(f"Error logging uptime metrics: {e}")
    
    async def get_uptime_metrics(self, node_id: Optional[str] = None) -> Union[UptimeMetrics, List[UptimeMetrics]]:
        """Get uptime metrics for a node or all nodes"""
        try:
            if node_id:
                return self.uptime_metrics.get(node_id)
            else:
                return list(self.uptime_metrics.values())
                
        except Exception as e:
            logger.error(f"Error getting uptime metrics: {e}")
            return [] if not node_id else None
    
    async def get_beacon_history(self, node_id: str, limit: int = 100) -> List[UptimeBeacon]:
        """Get beacon history for a node"""
        try:
            beacons = [b for b in self.beacon_cache.values() if b.node_id == node_id]
            beacons.sort(key=lambda x: x.timestamp, reverse=True)
            return beacons[:limit]
            
        except Exception as e:
            logger.error(f"Error getting beacon history: {e}")
            return []
    
    async def get_node_ranking(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get node ranking by uptime"""
        try:
            ranking = []
            for node_id, metrics in self.uptime_metrics.items():
                ranking.append({
                    "node_id": node_id,
                    "uptime_percentage": metrics.uptime_percentage,
                    "total_beacons": metrics.total_beacons,
                    "successful_beacons": metrics.successful_beacons,
                    "failed_beacons": metrics.failed_beacons,
                    "consecutive_failures": metrics.consecutive_failures,
                    "status": metrics.status.value,
                    "average_latency": metrics.average_latency,
                    "last_beacon_time": metrics.last_beacon_time.isoformat()
                })
            
            # Sort by uptime percentage (descending)
            ranking.sort(key=lambda x: x["uptime_percentage"], reverse=True)
            
            return ranking[:limit]
            
        except Exception as e:
            logger.error(f"Error getting node ranking: {e}")
            return []
    
    async def _log_beacon_event(self, beacon_id: str, event_type: str, data: Dict[str, Any]):
        """Log beacon event"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "beacon_id": beacon_id,
                "event_type": event_type,
                "data": data
            }
            
            log_file = self.logs_dir / f"beacon_events_{datetime.now().strftime('%Y%m%d')}.log"
            async with aiofiles.open(log_file, "a") as f:
                await f.write(json.dumps(log_entry) + "\n")
                
        except Exception as e:
            logger.error(f"Error logging beacon event: {e}")
    
    async def cleanup_old_beacons(self, max_age_days: int = 7):
        """Clean up old beacons"""
        try:
            cutoff_time = datetime.now() - timedelta(days=max_age_days)
            
            to_remove = []
            for beacon_id, beacon in self.beacon_cache.items():
                if beacon.timestamp < cutoff_time:
                    to_remove.append(beacon_id)
            
            for beacon_id in to_remove:
                del self.beacon_cache[beacon_id]
            
            if to_remove:
                await self._save_beacon_data()
                logger.info(f"Cleaned up {len(to_remove)} old beacons")
                
        except Exception as e:
            logger.error(f"Error cleaning up old beacons: {e}")

# Global uptime beacon system instance
uptime_beacon_system = UptimeBeaconSystem()

# Convenience functions for external use
async def send_beacon(request: BeaconRequest) -> BeaconResponse:
    """Send an uptime beacon"""
    return await uptime_beacon_system.send_beacon(request)

async def get_uptime_metrics(node_id: Optional[str] = None) -> Union[UptimeMetrics, List[UptimeMetrics]]:
    """Get uptime metrics for a node or all nodes"""
    return await uptime_beacon_system.get_uptime_metrics(node_id)

async def get_beacon_history(node_id: str, limit: int = 100) -> List[UptimeBeacon]:
    """Get beacon history for a node"""
    return await uptime_beacon_system.get_beacon_history(node_id, limit)

async def get_node_ranking(limit: int = 100) -> List[Dict[str, Any]]:
    """Get node ranking by uptime"""
    return await uptime_beacon_system.get_node_ranking(limit)

if __name__ == "__main__":
    # Example usage
    async def main():
        # Create a beacon request
        request = BeaconRequest(
            node_id="node-001",
            beacon_type=BeaconType.HEARTBEAT,
            metrics={
                "system_metrics": {
                    "cpu_usage": 0.45,
                    "memory_usage": 0.60
                },
                "network_metrics": {
                    "latency_ms": 12.5,
                    "bandwidth_mbps": 100.0
                }
            }
        )
        
        response = await send_beacon(request)
        print(f"Beacon sent: {response}")
        
        # Get uptime metrics
        metrics = await get_uptime_metrics("node-001")
        print(f"Uptime metrics: {metrics}")
    
    asyncio.run(main())
