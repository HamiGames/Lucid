# Path: RDP/client/connection_manager.py
# Lucid RDP Connection Manager - Connection pooling and management
# Implements R-MUST-003: Remote Desktop Host Support with connection pooling
# LUCID-STRICT Layer 2 Service Integration

from __future__ import annotations

import asyncio
import logging
import os
import time
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import threading
import socket
import ssl
import hashlib

# Import existing project modules
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from RDP.client.rdp_client import RDPClient, ClientConfig, ClientConnectionState, ConnectionMetrics

logger = logging.getLogger(__name__)

# Configuration from environment
MAX_POOL_SIZE = int(os.getenv("MAX_POOL_SIZE", "10"))
MIN_POOL_SIZE = int(os.getenv("MIN_POOL_SIZE", "2"))
CONNECTION_IDLE_TIMEOUT = int(os.getenv("CONNECTION_IDLE_TIMEOUT", "300"))  # 5 minutes
CONNECTION_LIFETIME = int(os.getenv("CONNECTION_LIFETIME", "3600"))  # 1 hour
POOL_CLEANUP_INTERVAL = int(os.getenv("POOL_CLEANUP_INTERVAL", "60"))  # 1 minute
HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "30"))  # 30 seconds


class ConnectionPoolState(Enum):
    """Connection pool states"""
    INITIALIZING = "initializing"
    RUNNING = "running"
    DRAINING = "draining"
    STOPPED = "stopped"
    ERROR = "error"


class ConnectionPriority(Enum):
    """Connection priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PooledConnection:
    """Pooled RDP connection"""
    connection_id: str
    client: RDPClient
    config: ClientConfig
    session_id: Optional[str]
    priority: ConnectionPriority
    created_at: datetime
    last_used_at: datetime
    usage_count: int = 0
    total_usage_time: float = 0.0
    error_count: int = 0
    is_active: bool = False
    is_available: bool = True
    health_score: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConnectionPoolConfig:
    """Connection pool configuration"""
    max_pool_size: int = MAX_POOL_SIZE
    min_pool_size: int = MIN_POOL_SIZE
    connection_idle_timeout: int = CONNECTION_IDLE_TIMEOUT
    connection_lifetime: int = CONNECTION_LIFETIME
    cleanup_interval: int = POOL_CLEANUP_INTERVAL
    health_check_interval: int = HEALTH_CHECK_INTERVAL
    auto_cleanup_enabled: bool = True
    health_monitoring_enabled: bool = True
    load_balancing_enabled: bool = True
    connection_reuse_enabled: bool = True


@dataclass
class ConnectionRequest:
    """Connection request"""
    request_id: str
    config: ClientConfig
    session_id: str
    priority: ConnectionPriority
    timeout: int
    created_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PoolMetrics:
    """Connection pool metrics"""
    total_connections: int
    active_connections: int
    available_connections: int
    idle_connections: int
    failed_connections: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_wait_time: float
    average_connection_time: float
    pool_utilization: float
    timestamp: datetime


class ConnectionManager:
    """
    Manages a pool of RDP connections for efficient connection reuse
    and load balancing across multiple sessions.
    """
    
    def __init__(self, config: Optional[ConnectionPoolConfig] = None):
        self.config = config or ConnectionPoolConfig()
        self.connection_pool: Dict[str, PooledConnection] = {}
        self.pending_requests: List[ConnectionRequest] = []
        self.pool_state = ConnectionPoolState.INITIALIZING
        self.pool_metrics: List[PoolMetrics] = []
        
        # Management
        self._running = False
        self._cleanup_task: Optional[asyncio.Task] = None
        self._health_check_task: Optional[asyncio.Task] = None
        self._metrics_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        
        # Callbacks
        self.connection_callbacks: List[Callable] = []
        self.metrics_callbacks: List[Callable] = []
        
        logger.info(f"ConnectionManager initialized with config: {self.config}")
    
    async def start(self) -> None:
        """Start the connection manager"""
        if self._running:
            logger.warning("ConnectionManager is already running")
            return
        
        try:
            self._running = True
            self.pool_state = ConnectionPoolState.RUNNING
            
            # Start background tasks
            if self.config.auto_cleanup_enabled:
                self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            if self.config.health_monitoring_enabled:
                self._health_check_task = asyncio.create_task(self._health_check_loop())
            
            self._metrics_task = asyncio.create_task(self._metrics_loop())
            
            # Initialize minimum pool size
            await self._initialize_pool()
            
            logger.info("ConnectionManager started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start ConnectionManager: {e}")
            await self.stop()
            raise
    
    async def stop(self) -> None:
        """Stop the connection manager"""
        if not self._running:
            return
        
        logger.info("Stopping ConnectionManager...")
        self._running = False
        self.pool_state = ConnectionPoolState.DRAINING
        
        # Cancel background tasks
        tasks = [self._cleanup_task, self._health_check_task, self._metrics_task]
        for task in tasks:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Close all connections
        await self._close_all_connections()
        
        self.pool_state = ConnectionPoolState.STOPPED
        logger.info("ConnectionManager stopped")
    
    async def get_connection(
        self,
        config: ClientConfig,
        session_id: str,
        priority: ConnectionPriority = ConnectionPriority.NORMAL,
        timeout: int = 30
    ) -> Optional[RDPClient]:
        """Get a connection from the pool"""
        async with self._lock:
            request_id = str(uuid.uuid4())
            request = ConnectionRequest(
                request_id=request_id,
                config=config,
                session_id=session_id,
                priority=priority,
                timeout=timeout,
                created_at=datetime.now(timezone.utc)
            )
            
            try:
                # Try to find an available connection
                connection = await self._find_available_connection(config)
                
                if connection:
                    # Use existing connection
                    await self._assign_connection(connection, session_id)
                    logger.info(f"Reused connection {connection.connection_id} for session {session_id}")
                    return connection.client
                else:
                    # Create new connection if pool not full
                    if len(self.connection_pool) < self.config.max_pool_size:
                        connection = await self._create_new_connection(config, priority)
                        if connection:
                            await self._assign_connection(connection, session_id)
                            logger.info(f"Created new connection {connection.connection_id} for session {session_id}")
                            return connection.client
                    
                    # Add to pending requests if pool is full
                    self.pending_requests.append(request)
                    logger.info(f"Added request {request_id} to pending queue")
                    
                    # Wait for connection to become available
                    return await self._wait_for_connection(request)
                
            except Exception as e:
                logger.error(f"Failed to get connection for session {session_id}: {e}")
                return None
    
    async def return_connection(
        self,
        client: RDPClient,
        session_id: str,
        force_close: bool = False
    ) -> bool:
        """Return a connection to the pool"""
        async with self._lock:
            try:
                # Find the connection
                connection = None
                for conn in self.connection_pool.values():
                    if conn.client == client:
                        connection = conn
                        break
                
                if not connection:
                    logger.error(f"Connection not found in pool for session {session_id}")
                    return False
                
                # Update connection metrics
                connection.last_used_at = datetime.now(timezone.utc)
                connection.usage_count += 1
                
                if force_close or not self.config.connection_reuse_enabled:
                    # Close the connection
                    await self._close_connection(connection)
                    logger.info(f"Closed connection {connection.connection_id} for session {session_id}")
                else:
                    # Return to pool
                    connection.is_active = False
                    connection.is_available = True
                    connection.session_id = None
                    
                    # Disconnect from current session
                    await client.disconnect()
                    
                    logger.info(f"Returned connection {connection.connection_id} to pool")
                
                # Process pending requests
                await self._process_pending_requests()
                
                return True
                
            except Exception as e:
                logger.error(f"Failed to return connection for session {session_id}: {e}")
                return False
    
    async def close_connection(self, client: RDPClient) -> bool:
        """Close a specific connection"""
        async with self._lock:
            connection = None
            for conn in self.connection_pool.values():
                if conn.client == client:
                    connection = conn
                    break
            
            if connection:
                await self._close_connection(connection)
                return True
            
            return False
    
    async def get_pool_status(self) -> Dict[str, Any]:
        """Get connection pool status"""
        async with self._lock:
            current_time = datetime.now(timezone.utc)
            
            active_connections = sum(1 for conn in self.connection_pool.values() if conn.is_active)
            available_connections = sum(1 for conn in self.connection_pool.values() if conn.is_available)
            idle_connections = sum(1 for conn in self.connection_pool.values() if not conn.is_active)
            failed_connections = sum(1 for conn in self.connection_pool.values() if conn.error_count > 0)
            
            # Calculate pool utilization
            pool_utilization = (active_connections / self.config.max_pool_size) * 100 if self.config.max_pool_size > 0 else 0
            
            return {
                "pool_state": self.pool_state.value,
                "total_connections": len(self.connection_pool),
                "active_connections": active_connections,
                "available_connections": available_connections,
                "idle_connections": idle_connections,
                "failed_connections": failed_connections,
                "pending_requests": len(self.pending_requests),
                "pool_utilization": pool_utilization,
                "config": {
                    "max_pool_size": self.config.max_pool_size,
                    "min_pool_size": self.config.min_pool_size,
                    "connection_idle_timeout": self.config.connection_idle_timeout,
                    "connection_lifetime": self.config.connection_lifetime
                },
                "timestamp": current_time.isoformat()
            }
    
    async def get_pool_metrics(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get connection pool metrics history"""
        metrics_list = self.pool_metrics[-limit:] if self.pool_metrics else []
        return [metrics.__dict__ for metrics in metrics_list]
    
    async def _initialize_pool(self) -> None:
        """Initialize the connection pool with minimum connections"""
        logger.info(f"Initializing connection pool with {self.config.min_pool_size} connections...")
        
        for i in range(self.config.min_pool_size):
            try:
                # Create default config
                config = ClientConfig(
                    server_host="localhost",
                    server_port=3389
                )
                
                connection = await self._create_new_connection(config, ConnectionPriority.NORMAL)
                if connection:
                    logger.info(f"Initialized connection {connection.connection_id}")
                
            except Exception as e:
                logger.error(f"Failed to initialize connection {i}: {e}")
    
    async def _create_new_connection(
        self,
        config: ClientConfig,
        priority: ConnectionPriority
    ) -> Optional[PooledConnection]:
        """Create a new pooled connection"""
        try:
            connection_id = str(uuid.uuid4())
            
            # Create RDP client
            client = RDPClient(config)
            await client.start()
            
            # Create pooled connection
            connection = PooledConnection(
                connection_id=connection_id,
                client=client,
                config=config,
                session_id=None,
                priority=priority,
                created_at=datetime.now(timezone.utc),
                last_used_at=datetime.now(timezone.utc),
                is_active=False,
                is_available=True
            )
            
            # Add to pool
            self.connection_pool[connection_id] = connection
            
            logger.info(f"Created new pooled connection {connection_id}")
            return connection
            
        except Exception as e:
            logger.error(f"Failed to create new connection: {e}")
            return None
    
    async def _find_available_connection(self, config: ClientConfig) -> Optional[PooledConnection]:
        """Find an available connection matching the config"""
        current_time = datetime.now(timezone.utc)
        
        # Find connections that match the config and are available
        available_connections = []
        for connection in self.connection_pool.values():
            if (connection.is_available and
                not connection.is_active and
                self._configs_match(connection.config, config) and
                connection.error_count < 3):  # Skip connections with too many errors
                
                # Check if connection is not expired
                age = (current_time - connection.created_at).total_seconds()
                if age < self.config.connection_lifetime:
                    available_connections.append(connection)
        
        if not available_connections:
            return None
        
        # Select best connection based on load balancing
        if self.config.load_balancing_enabled:
            # Select connection with lowest usage count and highest health score
            available_connections.sort(key=lambda c: (c.usage_count, -c.health_score))
        
        return available_connections[0]
    
    async def _assign_connection(self, connection: PooledConnection, session_id: str) -> None:
        """Assign a connection to a session"""
        connection.is_active = True
        connection.is_available = False
        connection.session_id = session_id
        connection.last_used_at = datetime.now(timezone.utc)
        
        # Connect to the session
        try:
            success = await connection.client.connect(session_id, connection.config)
            if not success:
                connection.is_active = False
                connection.is_available = True
                connection.session_id = None
                connection.error_count += 1
                logger.error(f"Failed to connect session {session_id} to connection {connection.connection_id}")
        except Exception as e:
            connection.is_active = False
            connection.is_available = True
            connection.session_id = None
            connection.error_count += 1
            logger.error(f"Error connecting session {session_id} to connection {connection.connection_id}: {e}")
    
    async def _wait_for_connection(self, request: ConnectionRequest) -> Optional[RDPClient]:
        """Wait for a connection to become available"""
        try:
            # Wait for connection with timeout
            start_time = time.time()
            while time.time() - start_time < request.timeout:
                await asyncio.sleep(1)
                
                # Check if request is still in pending list
                if request not in self.pending_requests:
                    break
                
                # Try to find an available connection
                connection = await self._find_available_connection(request.config)
                if connection:
                    await self._assign_connection(connection, request.session_id)
                    self.pending_requests.remove(request)
                    return connection.client
            
            # Timeout reached
            if request in self.pending_requests:
                self.pending_requests.remove(request)
                logger.warning(f"Connection request {request.request_id} timed out")
            
            return None
            
        except Exception as e:
            logger.error(f"Error waiting for connection: {e}")
            if request in self.pending_requests:
                self.pending_requests.remove(request)
            return None
    
    async def _process_pending_requests(self) -> None:
        """Process pending connection requests"""
        if not self.pending_requests:
            return
        
        # Sort requests by priority
        self.pending_requests.sort(key=lambda r: r.priority.value, reverse=True)
        
        # Process high priority requests first
        processed_requests = []
        for request in self.pending_requests:
            connection = await self._find_available_connection(request.config)
            if connection:
                await self._assign_connection(connection, request.session_id)
                processed_requests.append(request)
                logger.info(f"Processed pending request {request.request_id}")
        
        # Remove processed requests
        for request in processed_requests:
            self.pending_requests.remove(request)
    
    async def _close_connection(self, connection: PooledConnection) -> None:
        """Close a pooled connection"""
        try:
            # Stop the client
            await connection.client.stop()
            
            # Remove from pool
            if connection.connection_id in self.connection_pool:
                del self.connection_pool[connection.connection_id]
            
            logger.info(f"Closed pooled connection {connection.connection_id}")
            
        except Exception as e:
            logger.error(f"Error closing connection {connection.connection_id}: {e}")
    
    async def _close_all_connections(self) -> None:
        """Close all connections in the pool"""
        connections_to_close = list(self.connection_pool.values())
        for connection in connections_to_close:
            await self._close_connection(connection)
        
        self.connection_pool.clear()
        logger.info("Closed all connections in pool")
    
    async def _cleanup_loop(self) -> None:
        """Background cleanup loop"""
        while self._running:
            try:
                await asyncio.sleep(self.config.cleanup_interval)
                
                if not self._running:
                    break
                
                await self._cleanup_expired_connections()
                await self._cleanup_idle_connections()
                
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _cleanup_expired_connections(self) -> None:
        """Clean up expired connections"""
        current_time = datetime.now(timezone.utc)
        expired_connections = []
        
        for connection in self.connection_pool.values():
            age = (current_time - connection.created_at).total_seconds()
            if age > self.config.connection_lifetime:
                expired_connections.append(connection)
        
        for connection in expired_connections:
            logger.info(f"Cleaning up expired connection {connection.connection_id}")
            await self._close_connection(connection)
    
    async def _cleanup_idle_connections(self) -> None:
        """Clean up idle connections if pool size exceeds minimum"""
        if len(self.connection_pool) <= self.config.min_pool_size:
            return
        
        current_time = datetime.now(timezone.utc)
        idle_connections = []
        
        for connection in self.connection_pool.values():
            if (connection.is_available and
                not connection.is_active and
                connection.error_count == 0):
                
                idle_time = (current_time - connection.last_used_at).total_seconds()
                if idle_time > self.config.connection_idle_timeout:
                    idle_connections.append(connection)
        
        # Sort by last used time (oldest first)
        idle_connections.sort(key=lambda c: c.last_used_at)
        
        # Close excess idle connections
        excess_count = len(self.connection_pool) - self.config.min_pool_size
        connections_to_close = idle_connections[:excess_count]
        
        for connection in connections_to_close:
            logger.info(f"Cleaning up idle connection {connection.connection_id}")
            await self._close_connection(connection)
    
    async def _health_check_loop(self) -> None:
        """Background health check loop"""
        while self._running:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                
                if not self._running:
                    break
                
                await self._check_connection_health()
                
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(30)  # Wait before retrying
    
    async def _check_connection_health(self) -> None:
        """Check health of all connections"""
        for connection in list(self.connection_pool.values()):
            try:
                # Get connection status
                status = connection.client.get_connection_status()
                
                if status:
                    # Update health score based on status
                    if status["state"] == "connected":
                        connection.health_score = min(1.0, connection.health_score + 0.1)
                    else:
                        connection.health_score = max(0.0, connection.health_score - 0.1)
                    
                    # Mark as failed if health score is too low
                    if connection.health_score < 0.3:
                        connection.error_count += 1
                        logger.warning(f"Connection {connection.connection_id} health score low: {connection.health_score}")
                
            except Exception as e:
                logger.error(f"Error checking health for connection {connection.connection_id}: {e}")
                connection.error_count += 1
    
    async def _metrics_loop(self) -> None:
        """Background metrics collection loop"""
        while self._running:
            try:
                await asyncio.sleep(60)  # Collect metrics every minute
                
                if not self._running:
                    break
                
                await self._collect_pool_metrics()
                
            except Exception as e:
                logger.error(f"Error in metrics loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _collect_pool_metrics(self) -> None:
        """Collect pool metrics"""
        try:
            current_time = datetime.now(timezone.utc)
            
            active_connections = sum(1 for conn in self.connection_pool.values() if conn.is_active)
            available_connections = sum(1 for conn in self.connection_pool.values() if conn.is_available)
            idle_connections = sum(1 for conn in self.connection_pool.values() if not conn.is_active)
            failed_connections = sum(1 for conn in self.connection_pool.values() if conn.error_count > 0)
            
            # Calculate utilization
            pool_utilization = (active_connections / self.config.max_pool_size) * 100 if self.config.max_pool_size > 0 else 0
            
            metrics = PoolMetrics(
                total_connections=len(self.connection_pool),
                active_connections=active_connections,
                available_connections=available_connections,
                idle_connections=idle_connections,
                failed_connections=failed_connections,
                total_requests=0,  # Would be tracked in a real implementation
                successful_requests=0,  # Would be tracked in a real implementation
                failed_requests=0,  # Would be tracked in a real implementation
                average_wait_time=0.0,  # Would be calculated in a real implementation
                average_connection_time=0.0,  # Would be calculated in a real implementation
                pool_utilization=pool_utilization,
                timestamp=current_time
            )
            
            self.pool_metrics.append(metrics)
            
            # Keep only last 1000 metrics
            if len(self.pool_metrics) > 1000:
                self.pool_metrics = self.pool_metrics[-1000:]
            
        except Exception as e:
            logger.error(f"Error collecting pool metrics: {e}")
    
    def _configs_match(self, config1: ClientConfig, config2: ClientConfig) -> bool:
        """Check if two configs are compatible for connection reuse"""
        return (config1.server_host == config2.server_host and
                config1.server_port == config2.server_port and
                config1.username == config2.username and
                config1.domain == config2.domain)
    
    def add_connection_callback(self, callback: Callable) -> None:
        """Add a callback for connection events"""
        self.connection_callbacks.append(callback)
    
    def add_metrics_callback(self, callback: Callable) -> None:
        """Add a callback for metrics events"""
        self.metrics_callbacks.append(callback)
    
    def remove_connection_callback(self, callback: Callable) -> None:
        """Remove a connection callback"""
        try:
            self.connection_callbacks.remove(callback)
        except ValueError:
            pass
    
    def remove_metrics_callback(self, callback: Callable) -> None:
        """Remove a metrics callback"""
        try:
            self.metrics_callbacks.remove(callback)
        except ValueError:
            pass


# Global connection manager instance
_connection_manager: Optional[ConnectionManager] = None


def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager instance"""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager


async def start_connection_manager():
    """Start the global connection manager"""
    manager = get_connection_manager()
    await manager.start()


async def stop_connection_manager():
    """Stop the global connection manager"""
    global _connection_manager
    if _connection_manager:
        await _connection_manager.stop()
        _connection_manager = None


if __name__ == "__main__":
    async def test_connection_manager():
        """Test the connection manager"""
        manager = ConnectionManager()
        
        try:
            await manager.start()
            
            # Create test config
            config = ClientConfig(
                server_host="localhost",
                server_port=3389,
                username="test_user"
            )
            
            # Get connection
            session_id = "test_session_123"
            client = await manager.get_connection(config, session_id)
            
            if client:
                print(f"Got connection for session: {session_id}")
                
                # Get pool status
                status = await manager.get_pool_status()
                print(f"Pool status: {status}")
                
                # Wait a bit
                await asyncio.sleep(5)
                
                # Return connection
                await manager.return_connection(client, session_id)
                
            else:
                print("Failed to get connection")
                
        finally:
            await manager.stop()
    
    # Run test
    asyncio.run(test_connection_manager())
