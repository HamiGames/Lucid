# Path: RDP/protocol/__init__.py
# Lucid RDP Protocol Module - RDP protocol implementation
# Implements R-MUST-003: Remote Desktop Host Support with protocol handling
# LUCID-STRICT Layer 1 Core Infrastructure

"""
RDP Protocol Module

This module provides RDP protocol implementation including:
- RDP session protocol handling
- Packet serialization/deserialization
- Protocol negotiation
- Channel management
"""

from .rdp_session import RDPSessionManager, RDPSession, RDPPacket, RDPChannel

__all__ = [
    "RDPSessionManager",
    "RDPSession",
    "RDPPacket", 
    "RDPChannel"
]
