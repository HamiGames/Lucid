# Path: node/worker/node_worker.py
# Lucid RDP Node Worker - Core RDP session management
# Based on LUCID-STRICT requirements per Spec-1c

from __future__ import annotations

import os
import asyncio
import logging
import uuid
import socket
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
import hashlib

# Import from reorganized structure
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from sessions.core.session_generator import SecureSessionGenerator
from sessions.pipeline.session_processor import SessionPipeline
from sessions.encryption.session_crypto import SessionCrypto
from RDP.server.rdp_server import RDPServer
from RDP.security.trust_controller import TrustController
from blockchain.core.blockchain_engine import PayoutRouter
from payment_systems.tron_node.tron_client import TronNodeSystem

logger = logging.getLogger(__name__)

# Node Worker Constants
RDP_PORT_RANGE = (3389, 4000)  # RDP port range
MAX_CONCURRENT_SESSIONS = int(os.getenv("MAX_CONCURRENT_SESSIONS", "10"))
SESSION_TIMEOUT = int(os.getenv("SESSION_TIMEOUT", "7200"))  # 2 hours
BANDWIDTH_LIMIT_MBPS = float(os.getenv("BANDWIDTH_LIMIT_MBPS", "100.0"))
MIN_STORAGE_GB = float(os.getenv("MIN_STORAGE_GB", "50.0"))


class SessionState(Enum):
    """RDP session states"""
    INITIALIZING = "initializing"
    PENDING_PAYMENT = "pending_payment"
    ACTIVE = "active"
    PAUSED = "paused"
    TERMINATING = "terminating"
    TERMINATED = "terminated"
    ERROR = "error"


class NodeStatus(Enum):
    """Node operational status"""
    STARTING = "starting"
    READY = "ready"
    BUSY = "busy"
    MAINTENANCE = "maintenance"
    OFFLINE = "offline"


@dataclass
class ResourceMetrics:
    """System resource metrics"""
    cpu_percent: float
    memory_percent: float
    storage_used_gb: float
    storage_free_gb: float
    bandwidth_used_mbps: float
    bandwidth_available_mbps: float
    session_count: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "storage_used_gb": self.storage_used_gb,
            "storage_free_gb": self.storage_free_gb,
            "bandwidth_used_mbps": self.bandwidth_used_mbps,
            "bandwidth_available_mbps": self.bandwidth_available_mbps,
            "session_count": self.session_count,
            "timestamp": datetime.now(timezone.utc)
        }


@dataclass
class RDPSession:
    """RDP session instance"""
    session_id: str
    user_address: str
    node_address: str
    rdp_port: int
    state: SessionState
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    terminated_at: Optional[datetime] = None
    payment_tx_id: Optional[str] = None
    data_transferred_gb: float = 0.0
    cost_usdt: float = 0.0
    
    # RDP connection details
    rdp_server: Optional[RDPServer] = None
    client_ip: Optional[str] = None
    trust_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.session_id,
            "user_address": self.user_address,
            "node_address": self.node_address,
            "rdp_port": self.rdp_port,
            "state": self.state.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "terminated_at": self.terminated_at,
            "payment_tx_id": self.payment_tx_id,
            "data_transferred_gb": self.data_transferred_gb,
            "cost_usdt": self.cost_usdt,
            "client_ip": self.client_ip,
            "trust_score": self.trust_score
        }


class NodeWorker:
    """
    Core node worker for Lucid RDP sessions.
    
    Handles:
    - RDP session creation and lifecycle
    - Payment integration with TRON network
    - Resource monitoring and management
    - Trust and security controls
    - Session pipeline processing
    """
    
    def __init__(self, node_address: str, private_key: str):
        self.node_address = node_address
        self.private_key = private_key
        self.node_id = hashlib.sha256(node_address.encode()).hexdigest()[:16]
        
        # Core components
        self.session_generator = SecureSessionGenerator()
        self.session_pipeline = SessionPipeline()
        self.session_crypto = SessionCrypto()
        self.trust_controller = TrustController()
        self.tron_client = TronNodeSystem("mainnet")  # Production network
        self.payout_router = PayoutRouter()
        
        # Session management
        self.active_sessions: Dict[str, RDPSession] = {}
        self.pending_sessions: Dict[str, RDPSession] = {}
        self.session_history: List[RDPSession] = []
        
        # Resource monitoring
        self.status = NodeStatus.STARTING
        self.resource_metrics: Optional[ResourceMetrics] = None
        self.last_metrics_update: Optional[datetime] = None
        
        # Port management
        self.available_ports = set(range(RDP_PORT_RANGE[0], RDP_PORT_RANGE[1] + 1))
        self.used_ports: Dict[int, str] = {}  # port -> session_id
        
        # Event handlers
        self.session_handlers: Dict[str, List[Callable]] = {
            "session_created": [],
            "session_started": [],
            "session_terminated": [],
            "payment_received": []
        }
        
        logger.info(f"Node worker initialized: {self.node_id} ({node_address})")
    
    async def start(self):
        """Start node worker"""
        try:
            logger.info(f"Starting node worker {self.node_id}...")
            
            # Initialize components
            await self.session_generator.initialize()
            await self.session_pipeline.start()
            await self.trust_controller.initialize()
            
            # Start resource monitoring
            asyncio.create_task(self._monitor_resources())
            
            # Start session cleanup
            asyncio.create_task(self._cleanup_expired_sessions())
            
            self.status = NodeStatus.READY
            logger.info(f"Node worker {self.node_id} started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start node worker: {e}")
            self.status = NodeStatus.OFFLINE
            raise
    
    async def stop(self):
        """Stop node worker"""
        try:
            logger.info(f"Stopping node worker {self.node_id}...")
            
            self.status = NodeStatus.OFFLINE
            
            # Terminate all active sessions
            for session_id in list(self.active_sessions.keys()):
                await self.terminate_session(session_id, "node_shutdown")
            
            # Stop components
            await self.session_pipeline.stop()
            
            logger.info(f"Node worker {self.node_id} stopped")
            
        except Exception as e:
            logger.error(f"Error stopping node worker: {e}")
    
    async def create_session(self, user_address: str, session_params: Dict[str, Any]) -> Optional[str]:
        """
        Create new RDP session for user.
        
        Args:
            user_address: User's TRON address
            session_params: Session configuration
            
        Returns:
            Session ID if successful
        """
        try:
            # Check node capacity
            if len(self.active_sessions) >= MAX_CONCURRENT_SESSIONS:
                logger.error("Maximum concurrent sessions reached")
                return None
            
            if self.status != NodeStatus.READY:
                logger.error(f"Node not ready: {self.status}")
                return None
            
            # Check user trust score
            trust_score = await self.trust_controller.get_trust_score(user_address)
            if trust_score < 0.5:  # Minimum trust threshold
                logger.error(f"User trust score too low: {trust_score}")
                return None
            
            # Generate session
            session_data = await self.session_generator.generate_session(
                user_id=user_address,
                node_id=self.node_address,
                metadata=session_params
            )
            
            session_id = session_data["session_id"]
            
            # Allocate RDP port
            rdp_port = self._allocate_port()
            if not rdp_port:
                logger.error("No available RDP ports")
                return None
            
            # Calculate session cost
            cost_usdt = self._calculate_session_cost(session_params)
            
            # Create session instance
            session = RDPSession(
                session_id=session_id,
                user_address=user_address,
                node_address=self.node_address,
                rdp_port=rdp_port,
                state=SessionState.PENDING_PAYMENT,
                cost_usdt=cost_usdt,
                trust_score=trust_score
            )
            
            self.pending_sessions[session_id] = session
            self.used_ports[rdp_port] = session_id
            
            # Trigger session created event
            await self._trigger_event("session_created", session)
            
            logger.info(f"Session created: {session_id} for user {user_address}")
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            return None
    
    async def start_session(self, session_id: str, payment_tx_id: str) -> bool:
        """
        Start RDP session after payment confirmation.
        
        Args:
            session_id: Session identifier
            payment_tx_id: Payment transaction ID
            
        Returns:
            True if session started successfully
        """
        try:
            session = self.pending_sessions.get(session_id)
            if not session:
                logger.error(f"Pending session not found: {session_id}")
                return False
            
            # Verify payment
            payment_verified = await self._verify_payment(payment_tx_id, session.cost_usdt, session.user_address)
            if not payment_verified:
                logger.error(f"Payment verification failed: {payment_tx_id}")
                return False
            
            # Update session
            session.payment_tx_id = payment_tx_id
            session.state = SessionState.ACTIVE
            session.started_at = datetime.now(timezone.utc)
            
            # Start RDP server
            rdp_server = RDPServer(
                port=session.rdp_port,
                session_id=session_id,
                user_address=session.user_address
            )
            
            await rdp_server.start()
            session.rdp_server = rdp_server
            
            # Move to active sessions
            del self.pending_sessions[session_id]
            self.active_sessions[session_id] = session
            
            # Start session monitoring
            asyncio.create_task(self._monitor_session(session_id))
            
            # Trigger session started event
            await self._trigger_event("session_started", session)
            await self._trigger_event("payment_received", {"session_id": session_id, "tx_id": payment_tx_id})
            
            logger.info(f"Session started: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start session: {e}")
            return False
    
    async def terminate_session(self, session_id: str, reason: str = "user_request") -> bool:
        """
        Terminate RDP session.
        
        Args:
            session_id: Session identifier
            reason: Termination reason
            
        Returns:
            True if session terminated successfully
        """
        try:
            session = self.active_sessions.get(session_id)
            if not session:
                logger.error(f"Active session not found: {session_id}")
                return False
            
            session.state = SessionState.TERMINATING
            
            # Stop RDP server
            if session.rdp_server:
                await session.rdp_server.stop()
            
            # Update session
            session.state = SessionState.TERMINATED
            session.terminated_at = datetime.now(timezone.utc)
            
            # Free resources
            if session.rdp_port in self.used_ports:
                del self.used_ports[session.rdp_port]
                self.available_ports.add(session.rdp_port)
            
            # Move to history
            del self.active_sessions[session_id]
            self.session_history.append(session)
            
            # Process final payment if needed
            if session.data_transferred_gb > 0:
                await self._process_final_settlement(session)
            
            # Trigger session terminated event
            await self._trigger_event("session_terminated", session)
            
            logger.info(f"Session terminated: {session_id} ({reason})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to terminate session: {e}")
            return False
    
    async def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session status"""
        try:
            # Check active sessions
            session = self.active_sessions.get(session_id)
            if session:
                return session.to_dict()
            
            # Check pending sessions
            session = self.pending_sessions.get(session_id)
            if session:
                return session.to_dict()
            
            # Check history
            for session in self.session_history:
                if session.session_id == session_id:
                    return session.to_dict()
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get session status: {e}")
            return None
    
    async def get_node_status(self) -> Dict[str, Any]:
        """Get node status and metrics"""
        try:
            # Update resource metrics
            await self._update_resource_metrics()
            
            return {
                "node_id": self.node_id,
                "node_address": self.node_address,
                "status": self.status.value,
                "active_sessions": len(self.active_sessions),
                "pending_sessions": len(self.pending_sessions),
                "max_sessions": MAX_CONCURRENT_SESSIONS,
                "available_ports": len(self.available_ports),
                "resource_metrics": self.resource_metrics.to_dict() if self.resource_metrics else None,
                "last_updated": datetime.now(timezone.utc)
            }
            
        except Exception as e:
            logger.error(f"Failed to get node status: {e}")
            return {"error": str(e)}
    
    def _allocate_port(self) -> Optional[int]:
        """Allocate available RDP port"""
        if not self.available_ports:
            return None
        
        port = min(self.available_ports)
        self.available_ports.remove(port)
        return port
    
    def _calculate_session_cost(self, session_params: Dict[str, Any]) -> float:
        """Calculate session cost based on parameters"""
        try:
            # Base cost
            base_cost = float(session_params.get("base_cost", 0.1))  # $0.10
            
            # Duration-based cost
            duration_hours = float(session_params.get("duration_hours", 1.0))
            duration_cost = duration_hours * 0.05  # $0.05 per hour
            
            # Resource-based cost
            cpu_cores = int(session_params.get("cpu_cores", 1))
            memory_gb = float(session_params.get("memory_gb", 2.0))
            storage_gb = float(session_params.get("storage_gb", 10.0))
            
            resource_cost = (cpu_cores * 0.01) + (memory_gb * 0.005) + (storage_gb * 0.001)
            
            total_cost = base_cost + duration_cost + resource_cost
            
            # Minimum cost
            return max(total_cost, 0.01)  # Minimum $0.01
            
        except Exception as e:
            logger.error(f"Failed to calculate session cost: {e}")
            return 0.1  # Default cost
    
    async def _verify_payment(self, tx_id: str, expected_amount: float, from_address: str) -> bool:
        """Verify TRON payment transaction"""
        try:
            # Get transaction details
            tx_data = await self.tron_client.get_transaction_details(tx_id)
            
            if not tx_data:
                return False
            
            # Verify transaction details
            if (tx_data.get("to_address") == self.node_address and
                tx_data.get("from_address") == from_address and
                float(tx_data.get("amount_usdt", 0)) >= expected_amount and
                tx_data.get("status") == "confirmed"):
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Payment verification failed: {e}")
            return False
    
    async def _process_final_settlement(self, session: RDPSession):
        """Process final payment settlement for data transfer"""
        try:
            if session.data_transferred_gb <= 0:
                return
            
            # Calculate additional cost for data transfer
            data_cost = session.data_transferred_gb * 0.01  # $0.01 per GB
            
            if data_cost > 0:
                logger.info(f"Processing final settlement: {data_cost} USDT for {session.data_transferred_gb}GB")
                
                # This would typically trigger additional payment request
                # For now, just log the settlement
                
        except Exception as e:
            logger.error(f"Final settlement failed: {e}")
    
    async def _monitor_session(self, session_id: str):
        """Monitor session activity and usage"""
        try:
            while session_id in self.active_sessions:
                session = self.active_sessions[session_id]
                
                # Check session timeout
                if session.started_at:
                    elapsed = (datetime.now(timezone.utc) - session.started_at).total_seconds()
                    if elapsed > SESSION_TIMEOUT:
                        logger.warning(f"Session timeout: {session_id}")
                        await self.terminate_session(session_id, "timeout")
                        break
                
                # Update data transfer metrics
                if session.rdp_server:
                    data_transfer = await session.rdp_server.get_data_transfer()
                    session.data_transferred_gb = data_transfer.get("total_gb", 0.0)
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
        except Exception as e:
            logger.error(f"Session monitoring failed: {e}")
    
    async def _monitor_resources(self):
        """Monitor system resources"""
        try:
            while self.status != NodeStatus.OFFLINE:
                await self._update_resource_metrics()
                
                # Check resource constraints
                if self.resource_metrics:
                    if self.resource_metrics.cpu_percent > 90:
                        logger.warning("High CPU usage detected")
                        self.status = NodeStatus.BUSY
                    elif self.resource_metrics.memory_percent > 90:
                        logger.warning("High memory usage detected")
                        self.status = NodeStatus.BUSY
                    elif self.resource_metrics.storage_free_gb < MIN_STORAGE_GB:
                        logger.warning("Low storage space")
                        self.status = NodeStatus.BUSY
                    else:
                        if self.status == NodeStatus.BUSY:
                            self.status = NodeStatus.READY
                
                await asyncio.sleep(60)  # Update every minute
                
        except Exception as e:
            logger.error(f"Resource monitoring failed: {e}")
    
    async def _update_resource_metrics(self):
        """Update system resource metrics"""
        try:
            import psutil
            
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Calculate bandwidth (simplified)
            net_io = psutil.net_io_counters()
            bandwidth_used = 0.0  # Would need historical data for accurate calculation
            
            self.resource_metrics = ResourceMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                storage_used_gb=(disk.used / (1024**3)),
                storage_free_gb=(disk.free / (1024**3)),
                bandwidth_used_mbps=bandwidth_used,
                bandwidth_available_mbps=BANDWIDTH_LIMIT_MBPS - bandwidth_used,
                session_count=len(self.active_sessions)
            )
            
            self.last_metrics_update = datetime.now(timezone.utc)
            
        except Exception as e:
            logger.error(f"Failed to update resource metrics: {e}")
    
    async def _cleanup_expired_sessions(self):
        """Cleanup expired sessions"""
        try:
            while self.status != NodeStatus.OFFLINE:
                now = datetime.now(timezone.utc)
                
                # Check pending sessions (expire after 10 minutes)
                expired_pending = []
                for session_id, session in self.pending_sessions.items():
                    if (now - session.created_at).total_seconds() > 600:  # 10 minutes
                        expired_pending.append(session_id)
                
                for session_id in expired_pending:
                    logger.info(f"Expiring pending session: {session_id}")
                    session = self.pending_sessions[session_id]
                    if session.rdp_port in self.used_ports:
                        del self.used_ports[session.rdp_port]
                        self.available_ports.add(session.rdp_port)
                    del self.pending_sessions[session_id]
                
                # Trim session history (keep last 1000)
                if len(self.session_history) > 1000:
                    self.session_history = self.session_history[-1000:]
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
        except Exception as e:
            logger.error(f"Session cleanup failed: {e}")
    
    async def _trigger_event(self, event_name: str, data: Any):
        """Trigger event handlers"""
        try:
            handlers = self.session_handlers.get(event_name, [])
            for handler in handlers:
                try:
                    await handler(data)
                except Exception as e:
                    logger.error(f"Event handler failed: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to trigger event: {e}")
    
    def add_event_handler(self, event_name: str, handler: Callable):
        """Add event handler"""
        if event_name not in self.session_handlers:
            self.session_handlers[event_name] = []
        self.session_handlers[event_name].append(handler)


# Global node worker instance
_node_worker: Optional[NodeWorker] = None


def get_node_worker() -> Optional[NodeWorker]:
    """Get global node worker instance"""
    global _node_worker
    return _node_worker


def create_node_worker(node_address: str, private_key: str) -> NodeWorker:
    """Create node worker instance"""
    global _node_worker
    _node_worker = NodeWorker(node_address, private_key)
    return _node_worker


async def cleanup_node_worker():
    """Cleanup node worker"""
    global _node_worker
    if _node_worker:
        await _node_worker.stop()
        _node_worker = None


if __name__ == "__main__":
    # Test node worker
    async def test_node_worker():
        print("Testing Lucid Node Worker...")
        
        # Test with sample TRON address
        test_address = "TTestNodeAddress123456789012345"
        test_key = "0123456789abcdef" * 4  # 64 char hex
        
        worker = create_node_worker(test_address, test_key)
        
        try:
            await worker.start()
            
            # Get node status
            status = await worker.get_node_status()
            print(f"Node status: {status}")
            
            # Test session creation
            user_address = "TTestUserAddress123456789012345"
            session_params = {
                "base_cost": 0.1,
                "duration_hours": 1.0,
                "cpu_cores": 1,
                "memory_gb": 2.0,
                "storage_gb": 10.0
            }
            
            session_id = await worker.create_session(user_address, session_params)
            print(f"Created session: {session_id}")
            
            if session_id:
                # Get session status
                session_status = await worker.get_session_status(session_id)
                print(f"Session status: {session_status}")
            
            # Wait a bit
            await asyncio.sleep(2)
            
        finally:
            await worker.stop()
        
        print("Test completed")
    
    asyncio.run(test_node_worker())