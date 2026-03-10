# Network Security Module
# Network security and Tor integration components

"""
Network security package for Lucid RDP.
Contains Tor proxy, onion services, and secure tunneling components.
"""

# Import submodules when they exist
try:
    from .tor import *
except ImportError:
    pass


from .tunnels.tunnel_metrics import get_metrics, TunnelMetrics
from .tunnels.tunnel_status import get_status, TunnelStatus
from .tunnels.entrypoint import main, authenticate, create_onion, rotate_onion, teardown_onion, list_tunnels, refresh_onion


__all__ = [
    "get_metrics",
    "TunnelMetrics",
    "get_status",
    "TunnelStatus",
    "main",
    "authenticate",
    "create_onion",
    "rotate_onion",
    "teardown_onion",
    "list_tunnels",
    "refresh_onion"
]
