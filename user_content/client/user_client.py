# Path: user_content/client/user_client.py
# Lucid RDP User Client - Main user interface for RDP connections
# Based on LUCID-STRICT requirements per Spec-1a, Spec-1c

from __future__ import annotations

import os
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json

import httpx
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

# Import from reorganized structure
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from sessions.core.session_generator import SessionType, generate_session_id, validate_session_id
from RDP.protocol.rdp_session import RDPSessionHandler, RDPConnectionState
from RDP.security.trust_controller import TrustController, SessionControlMode, ThreatLevel
from user_content.wallet.user_wallet import get_user_wallet

logger = logging.getLogger(__name__)

# User Client Constants
DEFAULT_API_BASE = os.getenv("LUCID_API_BASE", "http://lucid-api.onion")
CONNECTION_TIMEOUT = int(os.getenv("CONNECTION_TIMEOUT_SEC", "30"))
SESSION_POLL_INTERVAL = int(os.getenv("SESSION_POLL_INTERVAL_SEC", "5"))


class ConnectionStatus(Enum):
    """RDP connection status"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    AUTHENTICATING = "authenticating"
    CONNECTED = "connected"
    FAILED = "failed"


@dataclass
class UserSession:
    """User session information"""
    session_id: str
    session_type: SessionType
    owner_address: str
    target_node: Optional[str]
    connection_status: ConnectionStatus
    created_at: datetime
    rdp_handler: Optional[RDPSessionHandler] = None
    trust_profile: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "session_type": self.session_type.value,
            "owner_address": self.owner_address,
            "target_node": self.target_node,
            "status": self.connection_status.value,
            "created_at": self.created_at.isoformat(),
            "trust_profile": self.trust_profile
        }


class LucidUserClient:
    """
    Main Lucid RDP User Client.
    
    Provides user interface for:
    - Connecting to remote desktops via RDP
    - Managing sessions and trust policies
    - Wallet integration for payments
    - Tor-only connectivity per R-MUST-014
    """
    
    def __init__(self, user_address: str, api_base: str = DEFAULT_API_BASE):
        self.user_address = user_address
        self.api_base = api_base
        self.active_sessions: Dict[str, UserSession] = {}
        
        # Initialize HTTP client for Tor connectivity
        self.http_client = httpx.AsyncClient(
            timeout=CONNECTION_TIMEOUT,
            follow_redirects=True
        )
        
        # Initialize wallet integration
        self.user_wallet = get_user_wallet(user_address)
        
        # Initialize trust controller
        self.trust_controller = TrustController()
        
        logger.info(f"Lucid user client initialized for address: {user_address}")
    
    async def create_rdp_session(self, 
                                target_node: str,
                                control_mode: SessionControlMode = SessionControlMode.GUIDED,
                                threat_level: ThreatLevel = ThreatLevel.MEDIUM,
                                custom_policies: Optional[Dict[str, Any]] = None) -> UserSession:
        """
        Create new RDP session with trust-nothing policies.
        
        Args:
            target_node: Target node identifier
            control_mode: Session control mode
            threat_level: Assessed threat level
            custom_policies: Custom trust policies
            
        Returns:
            Created user session
        """
        try:
            # Generate secure session ID
            session_meta = generate_session_id(
                SessionType.RDP_USER,
                owner_address=self.user_address
            )
            
            # Create trust profile
            trust_profile_id = await self.trust_controller.create_session_profile(
                session_meta.session_id,
                control_mode,
                threat_level,
                custom_policies
            )
            
            # Initialize RDP handler
            rdp_handler = RDPSessionHandler(
                session_meta.session_id,
                self.user_address,
                session_meta.ephemeral_keypair
            )
            
            # Create user session
            user_session = UserSession(
                session_id=session_meta.session_id,
                session_type=SessionType.RDP_USER,
                owner_address=self.user_address,
                target_node=target_node,
                connection_status=ConnectionStatus.DISCONNECTED,
                created_at=datetime.now(timezone.utc),
                rdp_handler=rdp_handler,
                trust_profile=trust_profile_id
            )
            
            # Store active session
            self.active_sessions[session_meta.session_id] = user_session
            
            logger.info(f"Created RDP session: {session_meta.session_id}")
            return user_session
            
        except Exception as e:
            logger.error(f"Failed to create RDP session: {e}")
            raise
    
    async def connect_to_node(self, session_id: str) -> bool:
        """
        Connect to target node via RDP.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if connection successful
        """
        try:
            user_session = self.active_sessions.get(session_id)
            if not user_session:
                logger.error(f"Session not found: {session_id}")
                return False
            
            user_session.connection_status = ConnectionStatus.CONNECTING
            
            # Get node connection info from API
            node_info = await self._get_node_info(user_session.target_node)
            if not node_info:
                logger.error(f"Node info not found: {user_session.target_node}")
                user_session.connection_status = ConnectionStatus.FAILED
                return False
            
            # Initialize RDP connection
            if user_session.rdp_handler:
                user_session.connection_status = ConnectionStatus.AUTHENTICATING
                
                # Connect via Tor to node's onion address
                onion_address = node_info.get("onion_address")
                rdp_port = node_info.get("rdp_port", 3389)
                
                success = await user_session.rdp_handler.connect_to_server(
                    onion_address, rdp_port
                )
                
                if success:
                    user_session.connection_status = ConnectionStatus.CONNECTED
                    logger.info(f"Connected to node: {user_session.target_node}")
                    
                    # Start session monitoring
                    asyncio.create_task(self._monitor_session(session_id))
                    
                    return True
                else:
                    user_session.connection_status = ConnectionStatus.FAILED
                    return False
            
            return False
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            if session_id in self.active_sessions:
                self.active_sessions[session_id].connection_status = ConnectionStatus.FAILED
            return False
    
    async def disconnect_session(self, session_id: str, reason: str = "user_disconnect") -> bool:
        """
        Disconnect RDP session.
        
        Args:
            session_id: Session identifier
            reason: Disconnection reason
            
        Returns:
            True if disconnection successful
        """
        try:
            user_session = self.active_sessions.get(session_id)
            if not user_session:
                logger.warning(f"Session not found for disconnect: {session_id}")
                return False
            
            # Disconnect RDP handler
            if user_session.rdp_handler:
                await user_session.rdp_handler.disconnect(reason)
            
            # Update status
            user_session.connection_status = ConnectionStatus.DISCONNECTED
            
            # Process final session data for payment
            await self._finalize_session_payment(user_session)
            
            # Remove from active sessions
            del self.active_sessions[session_id]
            
            logger.info(f"Disconnected session: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Disconnect failed: {e}")
            return False
    
    async def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current session status.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session status information
        """
        try:
            user_session = self.active_sessions.get(session_id)
            if not user_session:
                return None
            
            status_data = user_session.to_dict()
            
            # Add RDP handler status if available
            if user_session.rdp_handler:
                rdp_context = user_session.rdp_handler.get_session_context()
                if rdp_context:
                    status_data.update({
                        "rdp_state": rdp_context.state.value,
                        "bytes_sent": rdp_context.bytes_sent,
                        "bytes_received": rdp_context.bytes_received,
                        "policy_violations": len(rdp_context.violations)
                    })
            
            # Add trust controller status
            if user_session.trust_profile:
                security_summary = await self.trust_controller.get_session_security_summary(session_id)
                status_data.update({
                    "security_events": security_summary.get("security_events", {}),
                    "privacy_events": security_summary.get("privacy_events", {}),
                    "jit_approvals": security_summary.get("jit_approvals", {})
                })
            
            return status_data
            
        except Exception as e:
            logger.error(f"Failed to get session status: {e}")
            return None
    
    async def list_available_nodes(self) -> List[Dict[str, Any]]:
        """
        List available nodes for connection.
        
        Returns:
            List of available nodes
        """
        try:
            response = await self.http_client.get(f"{self.api_base}/api/nodes/available")
            response.raise_for_status()
            
            nodes = response.json().get("nodes", [])
            logger.debug(f"Found {len(nodes)} available nodes")
            
            return nodes
            
        except Exception as e:
            logger.error(f"Failed to list nodes: {e}")
            return []
    
    async def get_session_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get user's session history.
        
        Args:
            limit: Maximum number of sessions to return
            
        Returns:
            List of historical sessions
        """
        try:
            params = {
                "owner_address": self.user_address,
                "limit": limit
            }
            
            response = await self.http_client.get(
                f"{self.api_base}/api/sessions/history", 
                params=params
            )
            response.raise_for_status()
            
            sessions = response.json().get("sessions", [])
            logger.debug(f"Retrieved {len(sessions)} historical sessions")
            
            return sessions
            
        except Exception as e:
            logger.error(f"Failed to get session history: {e}")
            return []
    
    async def _get_node_info(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get node connection information"""
        try:
            response = await self.http_client.get(f"{self.api_base}/api/nodes/{node_id}")
            response.raise_for_status()
            
            return response.json().get("node")
            
        except Exception as e:
            logger.error(f"Failed to get node info: {e}")
            return None
    
    async def _monitor_session(self, session_id: str):
        """Monitor active session for status changes"""
        try:
            user_session = self.active_sessions.get(session_id)
            if not user_session:
                return
            
            while (user_session.connection_status == ConnectionStatus.CONNECTED and 
                   session_id in self.active_sessions):
                
                # Check RDP handler status
                if user_session.rdp_handler:
                    rdp_context = user_session.rdp_handler.get_session_context()
                    
                    # Check for disconnection
                    if rdp_context and rdp_context.state == RDPConnectionState.FAILED:
                        user_session.connection_status = ConnectionStatus.FAILED
                        await self.disconnect_session(session_id, "rdp_failure")
                        break
                    
                    # Check for policy violations
                    if rdp_context and len(rdp_context.violations) > 0:
                        logger.warning(f"Session {session_id} has {len(rdp_context.violations)} policy violations")
                
                # Wait before next poll
                await asyncio.sleep(SESSION_POLL_INTERVAL)
                
        except Exception as e:
            logger.error(f"Session monitoring failed: {e}")
    
    async def _finalize_session_payment(self, user_session: UserSession):
        """Finalize session payment processing"""
        try:
            if user_session.rdp_handler:
                rdp_context = user_session.rdp_handler.get_session_context()
                
                if rdp_context:
                    # Calculate session costs based on data transferred
                    session_cost = self._calculate_session_cost(rdp_context)
                    
                    if session_cost > 0:
                        # Process payment via user wallet
                        payment_result = await self.user_wallet.process_session_payment(
                            user_session.session_id,
                            session_cost,
                            user_session.target_node
                        )
                        
                        logger.info(f"Session payment processed: {session_cost} USDT ({payment_result})")
                    
        except Exception as e:
            logger.error(f"Session payment finalization failed: {e}")
    
    def _calculate_session_cost(self, rdp_context) -> float:
        """Calculate session cost based on usage"""
        try:
            # Simple cost calculation based on data transfer
            # In production, this would be more sophisticated
            total_bytes = rdp_context.bytes_sent + rdp_context.bytes_received
            gb_transferred = total_bytes / (1024 * 1024 * 1024)
            
            # $0.01 per GB (example rate)
            cost = gb_transferred * 0.01
            
            return round(cost, 4)
            
        except Exception as e:
            logger.error(f"Cost calculation failed: {e}")
            return 0.0
    
    async def close(self):
        """Close user client and cleanup resources"""
        try:
            # Disconnect all active sessions
            session_ids = list(self.active_sessions.keys())
            for session_id in session_ids:
                await self.disconnect_session(session_id, "client_shutdown")
            
            # Close HTTP client
            await self.http_client.aclose()
            
            # Close trust controller
            await self.trust_controller.close()
            
            logger.info("User client closed")
            
        except Exception as e:
            logger.error(f"Client close failed: {e}")


# Global user client instances
_user_clients: Dict[str, LucidUserClient] = {}


def get_user_client(user_address: str, api_base: str = DEFAULT_API_BASE) -> LucidUserClient:
    """Get user client instance for address"""
    global _user_clients
    
    if user_address not in _user_clients:
        _user_clients[user_address] = LucidUserClient(user_address, api_base)
    
    return _user_clients[user_address]


async def cleanup_user_clients():
    """Cleanup all user client instances"""
    global _user_clients
    
    for client in _user_clients.values():
        await client.close()
    
    _user_clients.clear()


if __name__ == "__main__":
    # Test user client
    async def test_user_client():
        print("Testing Lucid User Client...")
        
        client = get_user_client("TTestUserAddress123456789012345")
        
        # List available nodes
        nodes = await client.list_available_nodes()
        print(f"Available nodes: {len(nodes)}")
        
        if nodes:
            # Create test session
            session = await client.create_rdp_session(
                target_node=nodes[0].get("node_id", "test_node"),
                control_mode=SessionControlMode.GUIDED
            )
            
            print(f"Created session: {session.session_id}")
            
            # Get session status
            status = await client.get_session_status(session.session_id)
            print(f"Session status: {status}")
        
        # Cleanup
        await client.close()
        print("Test completed")
    
    asyncio.run(test_user_client())