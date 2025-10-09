# node/tor/__init__.py
# Lucid Node Tor Module
# LUCID-STRICT Layer 1 Core Infrastructure

"""
Tor module for Lucid node operations.

This module provides:
- Onion service management
- SOCKS proxy connections and tunneling
- Tor service management and control

Core Components:
- OnionServiceManager: Manages onion service creation and lifecycle
- SocksProxyManager: Manages SOCKS proxy connections and tunneling
- TorManager: Manages Tor proxy services and onion routing
"""

from .onion_service import (
    OnionServiceManager,
    OnionServiceType,
    OnionKeyType,
    OnionServiceStatus,
    OnionServiceConfig,
    OnionServiceInfo,
    OnionServiceRequest,
    OnionServiceResponse,
    create_onion_service,
    remove_onion_service,
    list_onion_services,
    rotate_onion_service
)

from .socks_proxy import (
    SocksProxyManager,
    SocksVersion,
    SocksAuthMethod,
    ProxyStatus,
    TunnelProtocol,
    SocksProxyConfig,
    ProxyConnection,
    TunnelConfig,
    SocksProxyRequest,
    TunnelRequest,
    create_socks_connection,
    create_tunnel,
    list_proxy_connections,
    list_tunnels
)

from .tor_manager import (
    TorManager,
    TorServiceStatus,
    OnionServiceStatus as TorOnionServiceStatus,
    TorConnectionType,
    OnionService as TorOnionService,
    TorConnection,
    TorServiceRequest,
    TorConnectionRequest,
    TorServiceResponse,
    create_onion_service as create_tor_onion_service,
    create_tor_connection,
    make_tor_request,
    get_tor_status,
    get_onion_services,
    get_tor_connections
)

__all__ = [
    # Onion Service
    'OnionServiceManager',
    'OnionServiceType',
    'OnionKeyType',
    'OnionServiceStatus',
    'OnionServiceConfig',
    'OnionServiceInfo',
    'OnionServiceRequest',
    'OnionServiceResponse',
    'create_onion_service',
    'remove_onion_service',
    'list_onion_services',
    'rotate_onion_service',
    
    # SOCKS Proxy
    'SocksProxyManager',
    'SocksVersion',
    'SocksAuthMethod',
    'ProxyStatus',
    'TunnelProtocol',
    'SocksProxyConfig',
    'ProxyConnection',
    'TunnelConfig',
    'SocksProxyRequest',
    'TunnelRequest',
    'create_socks_connection',
    'create_tunnel',
    'list_proxy_connections',
    'list_tunnels',
    
    # Tor Manager
    'TorManager',
    'TorServiceStatus',
    'TorOnionServiceStatus',
    'TorConnectionType',
    'TorOnionService',
    'TorConnection',
    'TorServiceRequest',
    'TorConnectionRequest',
    'TorServiceResponse',
    'create_tor_onion_service',
    'create_tor_connection',
    'make_tor_request',
    'get_tor_status',
    'get_onion_services',
    'get_tor_connections'
]
