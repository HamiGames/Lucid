"""
RDP Connection Manager - Connection Management Service

This module manages RDP connections, including connection creation,
monitoring, and cleanup.
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4
from pathlib import Path

from common.models import RdpConnection, ConnectionStatus

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages RDP connections and their lifecycle"""
    
    def __init__(self, integration_manager: Optional[Any] = None):
        """
        Initialize connection manager
        
        Args:
            integration_manager: Optional integration manager for accessing XRDP client
        """
        self.integration_manager = integration_manager
        self.active_connections: Dict[UUID, RdpConnection] = {}
        # Map connection_id to XRDP process_id (string)
        self.connection_process_ids: Dict[UUID, str] = {}
        
        # Base paths for XRDP (can be overridden via environment variables)
        self.xrdp_base_path = Path(os.getenv('XRDP_BASE_PATH', '/app/data/xrdp'))
        self.xrdp_config_path = Path(os.getenv('XRDP_CONFIG_PATH', '/app/config/xrdp'))
        self.xrdp_log_path = Path(os.getenv('XRDP_LOG_PATH', '/app/logs/xrdp'))
        self.xrdp_session_path = Path(os.getenv('XRDP_SESSION_PATH', '/app/data/xrdp/sessions'))
    
    async def create_connection(
        self, 
        server_id: UUID, 
        session_config: Dict[str, Any]
    ) -> RdpConnection:
        """Create a new RDP connection"""
        try:
            connection_id = uuid4()
            session_id = session_config.get("session_id", uuid4())  # Get from config or generate
            
            # Create connection object using common.models.RdpConnection
            connection = RdpConnection(
                connection_id=connection_id,
                session_id=session_id if isinstance(session_id, UUID) else UUID(session_id),
                server_id=server_id,
                status=ConnectionStatus.CONNECTING,
                created_at=datetime.utcnow(),
                config=session_config,
                metrics={}
            )
            
            # Start XRDP service via API (if XRDP client is available)
            if self.integration_manager and self.integration_manager.xrdp:
                process_id = await self._start_connection_process(connection)
                self.connection_process_ids[connection_id] = process_id
            
            # Update connection status to connected
            connection.status = ConnectionStatus.CONNECTED
            connection.updated_at = datetime.utcnow()
            connection.last_activity = datetime.utcnow()
            self.active_connections[connection_id] = connection
            
            logger.info(f"Connection {connection_id} created for server {server_id}")
            return connection
            
        except Exception as e:
            logger.error(f"Failed to create connection: {e}")
            raise
    
    async def _start_connection_process(self, connection: RdpConnection) -> str:
        """
        Start the XRDP service process via rdp-xrdp API
        
        Returns:
            process_id (str): The XRDP process ID
        """
        try:
            if not self.integration_manager or not self.integration_manager.xrdp:
                raise RuntimeError("XRDP client not available")
            
            xrdp_client = self.integration_manager.xrdp
            
            # Generate process_id from connection_id
            process_id = f"conn-{connection.connection_id}"
            
            # Get port from config or use default
            port = connection.config.get("port", 3389)
            
            # Build paths for this connection
            # Use server_id to create unique directories
            server_id_str = str(connection.server_id)
            config_path = self.xrdp_config_path / server_id_str
            log_path = self.xrdp_log_path / server_id_str
            session_path = self.xrdp_session_path / server_id_str
            
            # Allow override from config
            config_path = Path(connection.config.get("config_path", str(config_path)))
            log_path = Path(connection.config.get("log_path", str(log_path)))
            session_path = Path(connection.config.get("session_path", str(session_path)))
            
            # Start XRDP service via API
            result = await xrdp_client.start_service(
                process_id=process_id,
                port=port,
                config_path=str(config_path),
                log_path=str(log_path),
                session_path=str(session_path)
            )
            
            logger.info(f"Started XRDP service process {process_id} for connection {connection.connection_id}")
            return process_id
            
        except Exception as e:
            logger.error(f"Failed to start XRDP service process: {e}")
            raise
    
    async def close_connection(self, connection_id: UUID) -> bool:
        """Close an RDP connection"""
        try:
            if connection_id not in self.active_connections:
                return False
            
            connection = self.active_connections[connection_id]
            connection.status = ConnectionStatus.DISCONNECTED
            connection.updated_at = datetime.utcnow()
            
            # Stop XRDP service process if running
            if connection_id in self.connection_process_ids:
                process_id = self.connection_process_ids[connection_id]
                
                if self.integration_manager and self.integration_manager.xrdp:
                    try:
                        await self.integration_manager.xrdp.stop_service(process_id)
                        logger.info(f"Stopped XRDP service process {process_id} for connection {connection_id}")
                    except Exception as e:
                        logger.warning(f"Failed to stop XRDP service process {process_id}: {e}")
                        # Continue with connection cleanup even if stop fails
                
                del self.connection_process_ids[connection_id]
            
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
            
            # Check XRDP service process status via API
            process_status = "unknown"
            if connection_id in self.connection_process_ids:
                process_id = self.connection_process_ids[connection_id]
                
                if self.integration_manager and self.integration_manager.xrdp:
                    try:
                        service_status = await self.integration_manager.xrdp.get_service_status(process_id)
                        process_status = service_status.get("status", "unknown")
                    except Exception as e:
                        logger.warning(f"Failed to get XRDP service status for process {process_id}: {e}")
                        process_status = "error"
                else:
                    process_status = "no_client"
            else:
                process_status = "no_process"
            
            return {
                "connection_id": str(connection_id),
                "status": connection.status.value if hasattr(connection.status, 'value') else str(connection.status),
                "process_status": process_status,
                "last_activity": connection.last_activity.isoformat() if connection.last_activity else None,
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
                "last_activity": connection.last_activity.isoformat() if connection.last_activity else None,
                "status": connection.status.value if hasattr(connection.status, 'value') else str(connection.status)
            }
            
            # Add XRDP service metrics if available
            if connection_id in self.connection_process_ids:
                process_id = self.connection_process_ids[connection_id]
                
                if self.integration_manager and self.integration_manager.xrdp:
                    try:
                        service_status = await self.integration_manager.xrdp.get_service_status(process_id)
                        # Add XRDP service metrics from API response
                        if "resource_usage" in service_status:
                            metrics.update(service_status["resource_usage"])
                        if "pid" in service_status:
                            metrics["pid"] = service_status["pid"]
                        if "port" in service_status:
                            metrics["port"] = service_status["port"]
                    except Exception as e:
                        logger.warning(f"Failed to get XRDP service metrics for process {process_id}: {e}")
                        # Continue without service metrics
            
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
