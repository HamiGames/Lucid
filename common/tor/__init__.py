"""
Tor service management module for Lucid RDP.

This module provides comprehensive Tor service management including:
- Tor daemon lifecycle control
- Onion service creation and management
- SOCKS proxy management and routing
- Network security and anonymity features

Components:
- TorManager: Main Tor service controller
- OnionService: .onion service creation and management
- SocksProxy: SOCKS proxy management and connection pooling
"""

from .tor_manager import TorManager, get_tor_manager, create_tor_manager
from .onion_service import OnionService, get_onion_service, create_onion_service
from .socks_proxy import SocksProxy, get_socks_proxy, create_socks_proxy

__all__ = [
    "TorManager",
    "OnionService", 
    "SocksProxy",
    "get_tor_manager",
    "create_tor_manager",
    "get_onion_service",
    "create_onion_service",
    "get_socks_proxy",
    "create_socks_proxy"
]
