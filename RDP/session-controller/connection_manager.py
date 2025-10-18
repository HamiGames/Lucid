"""
RDP Connection Manager - Connection Management Service

This module manages RDP connections, including connection creation,
monitoring, and cleanup.
"""

import asyncio
import logging
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4
import json

logger = logging.getLogger(__name__)

class RdpConnection:
    """Represents an RDP connection"""
    
    def __init__(self, connection_id: UUID, server_id: UUID, config: Dict[str, Any]):
        self.connection_id = connection_id
        self.server_id = server_id
        self.config = config
        self.status = "connecting"
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        self.metrics = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert connection to dictionary"""
        return {
            "connection_id": str(self.connection_id),
            "server_id": str(self.server_id),
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "metrics": self.metrics
        }

class ConnectionManager:
    """Manages RDP connections and their lifecycle"""
    
    def __init__(self):
        self.active_connections: Dict[UUID, RdpConnection] = {}
        self.connection_processes: Dict[UUID, subprocess.Popen] = {}
    
    async def create_connection(
        self, 
        server_id: UUID, 
        session_config: Dict[str, Any]
    ) -> RdpConnection:
        """Create a new RDP connection"""
        try:
            connection_id = uuid4()
            
            # Create connection object
            connection = RdpConnection(
                connection_id=connection_id,
                server_id=server_id,
                config=session_config
            )
            
            # Start connection process
            process = await self._start_connection_process(connection)
            self.connection_processes[connection_id] = process
            
            connection.status = "active"
            self.active_connections[connection_id] = connection
            
            logger.info(f"Connection {connection_id} created for server {server_id}")
            return connection
            
        except Exception as e:
            logger.error(f"Failed to create connection: {e}")
            raise
    
    async def _start_connection_process(self, connection: RdpConnection) -> subprocess.Popen:
        """Start the RDP connection process"""
        try:
            # Build xrdp connection command
            cmd = [
                "xrdp-sesman",
                "--config", connection.config.get("xrdp_config_path", "/etc/xrdp/sesman.ini"),
                "--port", str(connection.config.get("port", 3389)),
                "--server", connection.config.get("server_host", "localhost")
            ]
            
            # Start process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            return process
            
        except Exception as e:
            logger.error(f"Failed to start connection process: {e}")
            raise
    
    async def close_connection(self, connection_id: UUID) -> bool:
        """Close an RDP connection"""
        try:
            if connection_id not in self.active_connections:
                return False
            
            connection = self.active_connections[connection_id]
            connection.status = "closing"
            
            # Terminate process if running
            if connection_id in self.connection_processes:
                process = self.connection_processes[connection_id]
                process.terminate()
                
                # Wait for process to terminate
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                
                del self.connection_processes[connection_id]
            
            connection.status = "closed"
            del self.active_connections[connection_id]
            
            logger.info(f"Connection {connection_id} closed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to close connection: {e}")
            return False
    
    async def get_connection(self, connection_id: UUID) -> Optional[RdpConnection]:
        """Get connection by ID"""
        return self.active_connections.get(connection_id)
    
    async def list_connections(self, server_id: Optional[UUID] = None) -> List[RdpConnection]:
        """List connections, optionally filtered by server"""
        if server_id:
            return [
                conn for conn in self.active_connections.values()
                if conn.server_id == server_id
            ]
        return list(self.active_connections.values())
    
    async def check_connection_health(self, connection_id: UUID) -> Dict[str, Any]:
        """Check connection health"""
        try:
            if connection_id not in self.active_connections:
                return {"status": "not_found"}
            
            connection = self.active_connections[connection_id]
            
            # Check if process is still running
            if connection_id in self.connection_processes:
                process = self.connection_processes[connection_id]
                if process.poll() is None:
                    process_status = "running"
                else:
                    process_status = "stopped"
            else:
                process_status = "no_process"
            
            return {
                "connection_id": str(connection_id),
                "status": connection.status,
                "process_status": process_status,
                "last_activity": connection.last_activity.isoformat(),
                "uptime": (datetime.utcnow() - connection.created_at).total_seconds()
            }
            
        except Exception as e:
            logger.error(f"Failed to check connection health: {e}")
            return {"status": "error", "error": str(e)}
    
    async def get_connection_metrics(self, connection_id: UUID) -> Dict[str, Any]:
        """Get connection metrics"""
        try:
            if connection_id not in self.active_connections:
                return {}
            
            connection = self.active_connections[connection_id]
            
            # Get process metrics if available
            metrics = {
                "connection_id": str(connection_id),
                "uptime": (datetime.utcnow() - connection.created_at).total_seconds(),
                "last_activity": connection.last_activity.isoformat(),
                "status": connection.status
            }
            
            # Add process-specific metrics
            if connection_id in self.connection_processes:
                process = self.connection_processes[connection_id]
                if process.poll() is None:
                    # Process is running, get additional metrics
                    try:
                        # Get process memory usage
                        import psutil
                        process_obj = psutil.Process(process.pid)
                        metrics.update({
                            "memory_usage": process_obj.memory_info().rss,
                            "cpu_percent": process_obj.cpu_percent(),
                            "num_threads": process_obj.num_threads()
                        })
                    except Exception:
                        pass  # Metrics not available
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get connection metrics: {e}")
            return {}
    
    async def update_connection_activity(self, connection_id: UUID):
        """Update connection last activity timestamp"""
        if connection_id in self.active_connections:
            self.active_connections[connection_id].last_activity = datetime.utcnow()
    
    async def cleanup_stale_connections(self) -> int:
        """Clean up stale connections"""
        try:
            current_time = datetime.utcnow()
            stale_connections = []
            
            for connection_id, connection in self.active_connections.items():
                # Check if connection is stale (no activity for 1 hour)
                if (current_time - connection.last_activity).total_seconds() > 3600:
                    stale_connections.append(connection_id)
            
            # Close stale connections
            for connection_id in stale_connections:
                await self.close_connection(connection_id)
            
            logger.info(f"Cleaned up {len(stale_connections)} stale connections")
            return len(stale_connections)
            
        except Exception as e:
            logger.error(f"Failed to cleanup stale connections: {e}")
            return 0
    
    async def start_connection_monitoring(self):
        """Start background connection monitoring"""
        while True:
            try:
                # Clean up stale connections
                await self.cleanup_stale_connections()
                
                # Update activity for active connections
                for connection_id in self.active_connections:
                    await self.update_connection_activity(connection_id)
                
                # Wait 60 seconds before next check
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Connection monitoring error: {e}")
                await asyncio.sleep(120)  # Wait longer on error
