# Path: gui/core/__init__.py
"""
Core GUI infrastructure for Lucid RDP.
Provides shared components for Tor integration, networking, security, and configuration management.
"""

from .tor_client import TorClient, TorConnectionError
from .networking import TorHttpClient, OnionEnforcementError
from .config_manager import ConfigManager, GuiConfig, get_config_manager
from .security import SecurityValidator, CertificatePinner, OnionValidator, get_security_validator

__all__ = [
    "TorClient",
    "TorConnectionError", 
    "TorHttpClient",
    "OnionEnforcementError",
    "ConfigManager",
    "GuiConfig",
    "get_config_manager",
    "SecurityValidator",
    "CertificatePinner",
    "OnionValidator",
    "get_security_validator"
]
