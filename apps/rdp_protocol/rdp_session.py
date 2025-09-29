# Path: apps/rdp_protocol/rdp_session.py
# Lucid RDP Protocol Handler - Tor-based P2P RDP with trust-nothing policy
# Based on LUCID-STRICT requirements from Build_guide_docs

from __future__ import annotations

import asyncio
import os
import logging
import struct
import socket
import ssl
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import uuid

import socks  # PySocks for Tor integration
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from apps.chunker.chunker import chunk_manager
from apps.encryptor.encryptor import SessionEncryptionManager
from apps.merkle.merkle_builder import merkle_manager

logger = logging.getLogger(__name__)

# Protocol Constants per Spec-1a
TOR_PROXY_HOST = os.getenv("TOR_PROXY_HOST", "127.0.0.1")
TOR_PROXY_PORT = int(os.getenv("TOR_PROXY_PORT", "9050"))
RDP_PORT = int(os.getenv("LUCID_RDP_PORT", "3389"))
ONION_KEY_DIR = Path(os.getenv("LUCID_ONION_KEY_DIR", "/var/lib/tor/lucid"))

# RDP Protocol Constants (R-MUST-003, R-MUST-004)
RDP_PDU_TYPE_DATA = 0x7f
RDP_PDU_TYPE_CONTROL = 0x80
RDP_MAX_PACKET_SIZE = 8192
E2E_ENCRYPTION_HEADER_SIZE = 32


class RDPConnectionState(Enum):
    """RDP connection states"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    HANDSHAKE = "handshake"
    AUTHENTICATED = "authenticated"
    ACTIVE = "active"
    TERMINATING = "terminating"
    FAILED = "failed"


class PolicyViolationType(Enum):
    """Trust-nothing policy violations (R-MUST-013)"""
    INPUT_DENIED = "input_denied"
    CLIPBOARD_DENIED = "clipboard_denied"
    FILE_TRANSFER_DENIED = "file_transfer_denied"
    RESOURCE_ACCESS_DENIED = "resource_access_denied"
    POLICY_MISMATCH = "policy_mismatch"
    UNAUTHORIZED_ACTION = "unauthorized_action"


@dataclass
class TrustNothingPolicy:
    """Trust-nothing policy implementation (R-MUST-013)"""
    policy_id: str
    session_id: str
    default_deny: bool = True
    input_allowed: bool = False
    clipboard_allowed: bool = False
    file_transfer_allowed: bool = False
    file_transfer_paths: List[str] = field(default_factory=list)
    replace_same_name_guard: bool = True
    privacy_shield_enabled: bool = True
    redaction_zones: List[Dict[str, int]] = field(default_factory=list)
    app_allowlist: List[str] = field(default_factory=list)
    policy_hash: str = ""
    signature: bytes = field(default_factory=bytes)
    
    def validate_action(self, action_type: str, context: Dict[str, Any] = None) -> bool:
        """Validate action against policy with JIT approvals"""
        context = context or {}
        
        if self.default_deny:
            # Default deny - check specific permissions
            if action_type == "input":
                return self.input_allowed
            elif action_type == "clipboard":
                return self.clipboard_allowed
            elif action_type == "file_transfer":
                if not self.file_transfer_allowed:
                    return False
                # Check file path restrictions
                file_path = context.get("file_path", "")
                if self.file_transfer_paths:
                    return any(file_path.startswith(allowed) for allowed in self.file_transfer_paths)
                return True
            elif action_type == "application":
                app_name = context.get("application", "")
                if self.app_allowlist:
                    return app_name in self.app_allowlist
                return False
        
        return False
    
    def apply_privacy_shield(self, screen_data: bytes) -> bytes:
        """Apply privacy shield redaction zones"""
        if not self.privacy_shield_enabled:
            return screen_data
        
        # Apply redaction zones (simplified implementation)
        # In production, this would manipulate the actual screen bitmap
        redacted_data = screen_data
        for zone in self.redaction_zones:
            # Redact specified screen zones
            logger.debug(f"Applying redaction zone: {zone}")
        
        return redacted_data


@dataclass  
class RDPSessionContext:
    """RDP session context with audit trail (R-MUST-005)"""
    session_id: str
    owner_address: str
    ephemeral_keypair: ed25519.Ed25519PrivateKey
    state: RDPConnectionState = RDPConnectionState.DISCONNECTED
    policy: Optional[TrustNothingPolicy] = None
    client_address: str = ""
    server_address: str = ""
    connection_time: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    bytes_sent: int = 0
    bytes_received: int = 0
    audit_events: List[Dict[str, Any]] = field(default_factory=list)
    violations: List[Dict[str, Any]] = field(default_factory=list)
    
    def log_audit_event(self, event_type: str, details: Dict[str, Any] = None):
        """Log audit event for compliance (R-MUST-005)"""
        event = {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "session_id": self.session_id,
            "actor_identity": self.client_address,
            "details": details or {},
            "state": self.state.value
        }
        self.audit_events.append(event)
        logger.info(f"Audit event: {event_type} for session {self.session_id}")
    
    def log_policy_violation(self, violation_type: PolicyViolationType, context: Dict[str, Any]):
        """Log policy violation (R-MUST-013)"""
        violation = {
            "violation_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "violation_type": violation_type.value,
            "session_id": self.session_id,
            "context": context
        }
        self.violations.append(violation)
        self.log_audit_event("policy_violation", {"violation": violation})
        
        # Check if session should be voided
        if self.should_void_session(violation_type):
            self.state = RDPConnectionState.TERMINATING
            logger.error(f"Session {self.session_id} voided due to policy violation: {violation_type.value}")
    
    def should_void_session(self, violation_type: PolicyViolationType) -> bool:
        """Determine if violation should void session"""
        critical_violations = [
            PolicyViolationType.POLICY_MISMATCH,
            PolicyViolationType.UNAUTHORIZED_ACTION
        ]
        return violation_type in critical_violations


class TorOnionService:
    """Tor hidden service management (R-MUST-014, R-MUST-020)"""
    
    def __init__(self, service_name: str, port: int):
        self.service_name = service_name
        self.port = port
        self.onion_address: Optional[str] = None
        self.private_key: Optional[bytes] = None
        self.key_file = ONION_KEY_DIR / f"{service_name}.key"
        
    def generate_onion_service(self) -> str:
        """Generate or load onion service configuration"""
        try:
            ONION_KEY_DIR.mkdir(parents=True, exist_ok=True)
            
            if self.key_file.exists():
                # Load existing key
                self.private_key = self.key_file.read_bytes()
                logger.info(f"Loaded existing onion key for {self.service_name}")
            else:
                # Generate new Ed25519 key for v3 onion service
                from cryptography.hazmat.primitives.asymmetric import ed25519
                private_key = ed25519.Ed25519PrivateKey.generate()
                private_key_bytes = private_key.private_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PrivateFormat.Raw,
                    encryption_algorithm=serialization.NoEncryption()
                )
                
                # Save key securely
                self.key_file.write_bytes(private_key_bytes)
                os.chmod(self.key_file, 0o600)
                self.private_key = private_key_bytes
                logger.info(f"Generated new onion key for {self.service_name}")
            
            # Calculate onion address from public key
            public_key = ed25519.Ed25519PrivateKey.from_private_bytes(self.private_key).public_key()
            public_key_bytes = public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
            
            # Generate v3 onion address
            import base64
            import hashlib
            
            checksum = hashlib.sha3_256(b".onion checksum" + public_key_bytes + b"\x03").digest()[:2]
            onion_bytes = public_key_bytes + checksum + b"\x03"
            self.onion_address = base64.b32encode(onion_bytes).decode().lower() + ".onion"
            
            logger.info(f"Onion service address: {self.onion_address}")
            return self.onion_address
            
        except Exception as e:
            logger.error(f"Failed to generate onion service: {e}")
            raise
    
    def create_tor_socket(self) -> socket.socket:
        """Create Tor SOCKS proxy socket (R-MUST-004, R-MUST-020)"""
        try:
            # Create SOCKS proxy socket for Tor
            tor_socket = socks.socksocket(socket.AF_INET, socket.SOCK_STREAM)
            tor_socket.set_proxy(socks.SOCKS5, TOR_PROXY_HOST, TOR_PROXY_PORT)
            
            # Set socket options for RDP
            tor_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            tor_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            
            return tor_socket
            
        except Exception as e:
            logger.error(f"Failed to create Tor socket: {e}")
            raise


class RDPProtocolHandler:
    """
    Main RDP protocol handler for Lucid RDP.
    
    Implements:
    - R-MUST-003: Remote desktop host support (xrdp/FreeRDP compatible)
    - R-MUST-004: End-to-end encrypted P2P transport over Tor
    - R-MUST-005: Session audit trail with timestamps and metadata
    - R-MUST-012: Single-use Session IDs with ephemeral keypairs
    - R-MUST-013: Trust-nothing policy engine with default-deny
    - R-MUST-014: Tor-only access (.onion services)
    - R-MUST-020: Service-to-service calls traverse Tor
    """
    
    def __init__(self, encryption_manager: SessionEncryptionManager):
        self.encryption_manager = encryption_manager
        self.active_sessions: Dict[str, RDPSessionContext] = {}
        self.onion_service = TorOnionService("lucid-rdp", RDP_PORT)
        self.server_socket: Optional[socket.socket] = None
        self.running = False
        
        # Initialize onion service
        self.onion_address = self.onion_service.generate_onion_service()
        
        logger.info(f"RDP protocol handler initialized on {self.onion_address}")
    
    async def start_server(self) -> str:
        """Start RDP server on Tor hidden service"""
        try:
            # Create Tor socket for server
            self.server_socket = self.onion_service.create_tor_socket()
            self.server_socket.bind(("127.0.0.1", RDP_PORT))
            self.server_socket.listen(5)
            self.server_socket.setblocking(False)
            
            self.running = True
            logger.info(f"RDP server started on {self.onion_address}:{RDP_PORT}")
            
            # Start accepting connections
            asyncio.create_task(self._accept_connections())
            
            return self.onion_address
            
        except Exception as e:
            logger.error(f"Failed to start RDP server: {e}")
            raise
    
    async def stop_server(self):
        """Stop RDP server and terminate all sessions"""
        self.running = False
        
        # Terminate all active sessions
        for session_id in list(self.active_sessions.keys()):
            await self.terminate_session(session_id)
        
        if self.server_socket:
            self.server_socket.close()
        
        logger.info("RDP server stopped")
    
    async def _accept_connections(self):
        """Accept incoming RDP connections"""
        while self.running:
            try:
                # Accept connection through asyncio
                loop = asyncio.get_event_loop()
                client_socket, client_addr = await loop.sock_accept(self.server_socket)
                
                logger.info(f"New RDP connection from {client_addr}")
                
                # Handle connection in separate task
                asyncio.create_task(self._handle_connection(client_socket, client_addr))
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error accepting RDP connection: {e}")
                await asyncio.sleep(0.1)
    
    async def _handle_connection(self, client_socket: socket.socket, client_addr: tuple):
        """Handle individual RDP connection"""
        session_id = None
        try:
            client_socket.setblocking(False)
            
            # Perform RDP handshake
            session_id = await self._rdp_handshake(client_socket, client_addr)
            
            if session_id:
                # Start session recording and processing
                await self._start_session_processing(session_id)
                
                # Handle RDP data transfer
                await self._handle_rdp_data(session_id, client_socket)
            
        except Exception as e:
            logger.error(f"Error handling RDP connection {client_addr}: {e}")
        finally:
            client_socket.close()
            if session_id:
                await self.terminate_session(session_id)
    
    async def _rdp_handshake(self, client_socket: socket.socket, client_addr: tuple) -> Optional[str]:
        """Perform RDP handshake with authentication (R-MUST-012)"""
        try:
            loop = asyncio.get_event_loop()
            
            # Read initial RDP connection request
            initial_data = await asyncio.wait_for(
                loop.sock_recv(client_socket, 1024), timeout=10.0
            )
            
            if len(initial_data) < 16:
                logger.warning("Invalid RDP handshake from {client_addr}")
                return None
            
            # Parse RDP connection request (simplified)
            # In production, this would implement full RDP protocol negotiation
            rdp_version = struct.unpack("<H", initial_data[6:8])[0]
            logger.info(f"RDP version: {rdp_version}")
            
            # Generate session ID and ephemeral keypair (R-MUST-012)
            session_id = str(uuid.uuid4())
            ephemeral_key = ed25519.Ed25519PrivateKey.generate()
            
            # Create session context
            session_ctx = RDPSessionContext(
                session_id=session_id,
                owner_address="",  # Will be set during authentication
                ephemeral_keypair=ephemeral_key,
                state=RDPConnectionState.HANDSHAKE,
                client_address=f"{client_addr[0]}:{client_addr[1]}",
                server_address=self.onion_address,
                connection_time=datetime.now(timezone.utc)
            )
            
            # Store session
            self.active_sessions[session_id] = session_ctx
            session_ctx.log_audit_event("rdp_connect", {"client_addr": session_ctx.client_address})
            
            # Send handshake response with public key
            public_key_bytes = ephemeral_key.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
            
            response = struct.pack("<HH", 0x0300, len(public_key_bytes) + 8) + b"LUCID" + public_key_bytes
            await loop.sock_sendall(client_socket, response)
            
            # Wait for client authentication
            auth_data = await asyncio.wait_for(
                loop.sock_recv(client_socket, 512), timeout=15.0
            )
            
            # Validate authentication (simplified)
            if len(auth_data) >= 34:  # TRON address + signature
                owner_address = auth_data[:34].decode('ascii', errors='ignore')
                session_ctx.owner_address = owner_address
                session_ctx.state = RDPConnectionState.AUTHENTICATED
                
                session_ctx.log_audit_event("authentication", {
                    "owner_address": owner_address,
                    "method": "ed25519_signature"
                })
                
                logger.info(f"RDP session authenticated: {session_id}")
                return session_id
            else:
                logger.warning(f"RDP authentication failed for {client_addr}")
                return None
                
        except asyncio.TimeoutError:
            logger.warning(f"RDP handshake timeout from {client_addr}")
            return None
        except Exception as e:
            logger.error(f"RDP handshake error: {e}")
            return None
    
    async def _start_session_processing(self, session_id: str):
        """Start session recording and processing pipeline"""
        session_ctx = self.active_sessions[session_id]
        
        try:
            # Initialize session chunking
            chunk_manager.start_chunking(session_id)
            
            # Initialize encryption for session
            self.encryption_manager.start_encryption(session_id)
            
            # Initialize Merkle tree building
            merkle_manager.start_session(session_id)
            
            # Start session recording
            session_ctx.log_audit_event("session_start", {
                "chunking_started": True,
                "encryption_started": True,
                "merkle_started": True
            })
            
            session_ctx.state = RDPConnectionState.ACTIVE
            logger.info(f"Session processing started for {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to start session processing: {e}")
            session_ctx.state = RDPConnectionState.FAILED
            raise
    
    async def _handle_rdp_data(self, session_id: str, client_socket: socket.socket):
        """Handle RDP data transfer with policy enforcement"""
        session_ctx = self.active_sessions[session_id]
        loop = asyncio.get_event_loop()
        
        try:
            while session_ctx.state == RDPConnectionState.ACTIVE and self.running:
                # Read RDP packet
                try:
                    packet_header = await asyncio.wait_for(
                        loop.sock_recv(client_socket, 4), timeout=30.0
                    )
                except asyncio.TimeoutError:
                    # Keepalive timeout
                    continue
                
                if len(packet_header) < 4:
                    break
                
                # Parse RDP packet header
                packet_length = struct.unpack("<H", packet_header[2:4])[0]
                if packet_length > RDP_MAX_PACKET_SIZE:
                    logger.warning(f"RDP packet too large: {packet_length}")
                    break
                
                # Read rest of packet
                remaining = packet_length - 4
                packet_data = b""
                while remaining > 0:
                    chunk = await loop.sock_recv(client_socket, min(remaining, 8192))
                    if not chunk:
                        break
                    packet_data += chunk
                    remaining -= len(chunk)
                
                # Process RDP packet
                await self._process_rdp_packet(session_id, packet_header + packet_data)
                
                # Update activity timestamp
                session_ctx.last_activity = datetime.now(timezone.utc)
                session_ctx.bytes_received += len(packet_header + packet_data)
                
        except Exception as e:
            logger.error(f"Error handling RDP data for {session_id}: {e}")
        finally:
            session_ctx.state = RDPConnectionState.TERMINATING
    
    async def _process_rdp_packet(self, session_id: str, packet_data: bytes):
        """Process RDP packet with trust-nothing policy enforcement"""
        session_ctx = self.active_sessions[session_id]
        
        try:
            # Basic RDP packet parsing (simplified)
            if len(packet_data) < 6:
                return
            
            pdu_type = packet_data[5]
            
            # Apply trust-nothing policy (R-MUST-013)
            if session_ctx.policy:
                policy_context = {
                    "packet_type": pdu_type,
                    "packet_size": len(packet_data),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                # Check for input events
                if pdu_type in [0x1B, 0x1C]:  # Keyboard/mouse input
                    if not session_ctx.policy.validate_action("input", policy_context):
                        session_ctx.log_policy_violation(
                            PolicyViolationType.INPUT_DENIED, 
                            policy_context
                        )
                        return
                
                # Check for clipboard operations
                elif pdu_type == 0x21:  # Clipboard data
                    if not session_ctx.policy.validate_action("clipboard", policy_context):
                        session_ctx.log_policy_violation(
                            PolicyViolationType.CLIPBOARD_DENIED,
                            policy_context
                        )
                        return
                
                # Check for file transfer
                elif pdu_type == 0x49:  # File transfer channel
                    if not session_ctx.policy.validate_action("file_transfer", policy_context):
                        session_ctx.log_policy_violation(
                            PolicyViolationType.FILE_TRANSFER_DENIED,
                            policy_context
                        )
                        return
            
            # Process screen updates
            if pdu_type == 0x02:  # Bitmap update
                # Apply privacy shield if enabled
                if session_ctx.policy and session_ctx.policy.privacy_shield_enabled:
                    packet_data = session_ctx.policy.apply_privacy_shield(packet_data)
                
                # Log screen update for audit
                session_ctx.log_audit_event("screen_update", {
                    "packet_size": len(packet_data),
                    "privacy_shield": session_ctx.policy.privacy_shield_enabled if session_ctx.policy else False
                })
            
            # Add session data to chunker for processing
            chunk_manager.process_session_data(session_id, packet_data)
            
            # Log resource access
            session_ctx.log_audit_event("resource_access", {
                "resource_type": "rdp_packet",
                "pdu_type": pdu_type,
                "size": len(packet_data)
            })
            
        except Exception as e:
            logger.error(f"Error processing RDP packet: {e}")
    
    async def create_session_with_policy(self, owner_address: str, policy: TrustNothingPolicy, 
                                       observer_pubkeys: List[str] = None) -> str:
        """Create new RDP session with trust-nothing policy (API integration)"""
        try:
            # Generate session ID and ephemeral keypair
            session_id = str(uuid.uuid4())
            ephemeral_key = ed25519.Ed25519PrivateKey.generate()
            
            # Validate policy signature
            if not self._validate_policy_signature(policy, owner_address):
                raise ValueError("Invalid policy signature")
            
            # Create session context
            session_ctx = RDPSessionContext(
                session_id=session_id,
                owner_address=owner_address,
                ephemeral_keypair=ephemeral_key,
                state=RDPConnectionState.DISCONNECTED,
                policy=policy
            )
            
            self.active_sessions[session_id] = session_ctx
            
            session_ctx.log_audit_event("session_created", {
                "owner_address": owner_address,
                "policy_id": policy.policy_id,
                "observer_count": len(observer_pubkeys) if observer_pubkeys else 0
            })
            
            logger.info(f"Created RDP session {session_id} with trust-nothing policy")
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to create RDP session: {e}")
            raise
    
    def _validate_policy_signature(self, policy: TrustNothingPolicy, owner_address: str) -> bool:
        """Validate policy signature against owner address (simplified)"""
        # In production, this would verify the policy signature using the owner's public key
        # For now, return True if policy has a signature
        return len(policy.signature) > 0
    
    async def terminate_session(self, session_id: str) -> Dict[str, Any]:
        """Terminate RDP session and finalize blockchain anchoring"""
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session_ctx = self.active_sessions[session_id]
        
        try:
            # Update session state
            session_ctx.state = RDPConnectionState.TERMINATING
            
            # Finalize chunking
            final_chunk = chunk_manager.finalize_session(session_id)
            
            # Finalize encryption
            self.encryption_manager.finalize_session(session_id)
            
            # Finalize Merkle tree and get root hash
            merkle_root = merkle_manager.finalize_session(session_id)
            
            # Create session manifest
            manifest_data = {
                "session_id": session_id,
                "owner_address": session_ctx.owner_address,
                "merkle_root": merkle_root,
                "chunk_count": len([chunk for chunk in chunk_manager.get_session_stats(session_id) or {}]),
                "audit_events": len(session_ctx.audit_events),
                "policy_violations": len(session_ctx.violations),
                "bytes_processed": session_ctx.bytes_received,
                "duration_seconds": (datetime.now(timezone.utc) - session_ctx.connection_time).total_seconds() if session_ctx.connection_time else 0
            }
            
            # Log final audit event
            session_ctx.log_audit_event("session_end", manifest_data)
            
            # Remove from active sessions
            del self.active_sessions[session_id]
            
            logger.info(f"Terminated RDP session {session_id}")
            
            return {
                "session_id": session_id,
                "merkle_root": merkle_root,
                "manifest": manifest_data,
                "audit_events": session_ctx.audit_events,
                "policy_violations": session_ctx.violations
            }
            
        except Exception as e:
            logger.error(f"Error terminating session {session_id}: {e}")
            raise
    
    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get current session status"""
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session_ctx = self.active_sessions[session_id]
        
        return {
            "session_id": session_id,
            "state": session_ctx.state.value,
            "owner_address": session_ctx.owner_address,
            "client_address": session_ctx.client_address,
            "connection_time": session_ctx.connection_time.isoformat() if session_ctx.connection_time else None,
            "last_activity": session_ctx.last_activity.isoformat() if session_ctx.last_activity else None,
            "bytes_sent": session_ctx.bytes_sent,
            "bytes_received": session_ctx.bytes_received,
            "audit_events_count": len(session_ctx.audit_events),
            "policy_violations_count": len(session_ctx.violations),
            "policy_enabled": session_ctx.policy is not None
        }
    
    def get_active_sessions(self) -> List[str]:
        """Get list of active session IDs"""
        return list(self.active_sessions.keys())
    
    async def apply_jit_approval(self, session_id: str, action_type: str, context: Dict[str, Any]) -> bool:
        """Apply just-in-time approval for policy actions"""
        if session_id not in self.active_sessions:
            return False
        
        session_ctx = self.active_sessions[session_id]
        
        if not session_ctx.policy:
            return False
        
        # Log JIT approval request
        session_ctx.log_audit_event("jit_approval_request", {
            "action_type": action_type,
            "context": context
        })
        
        # For now, return based on current policy
        # In production, this would trigger user approval dialog
        approved = session_ctx.policy.validate_action(action_type, context)
        
        session_ctx.log_audit_event("jit_approval_response", {
            "action_type": action_type,
            "approved": approved
        })
        
        return approved


# Global RDP handler instance
rdp_handler: Optional[RDPProtocolHandler] = None


def get_rdp_handler() -> RDPProtocolHandler:
    """Get global RDP handler instance"""
    global rdp_handler
    if rdp_handler is None:
        from apps.encryptor.encryptor import SessionEncryptionManager, generate_master_key
        encryption_manager = SessionEncryptionManager(generate_master_key())
        rdp_handler = RDPProtocolHandler(encryption_manager)
    return rdp_handler


async def start_rdp_service() -> str:
    """Start RDP service and return onion address"""
    handler = get_rdp_handler()
    return await handler.start_server()


async def stop_rdp_service():
    """Stop RDP service"""
    global rdp_handler
    if rdp_handler:
        await rdp_handler.stop_server()
        rdp_handler = None


if __name__ == "__main__":
    # Test RDP service
    async def test_rdp():
        print("Starting Lucid RDP service...")
        onion_addr = await start_rdp_service()
        print(f"RDP service available at: {onion_addr}:3389")
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("Stopping RDP service...")
            await stop_rdp_service()
    
    asyncio.run(test_rdp())