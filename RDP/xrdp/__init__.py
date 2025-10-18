# LUCID XRDP Service Package
# LUCID-STRICT Layer 2 Service Integration
# Multi-platform support for Pi 5 ARM64
# Distroless container implementation

"""
Lucid XRDP Service Package

This package provides XRDP service management for the Lucid system,
including process lifecycle management, configuration generation,
and service monitoring.

Components:
- xrdp_service: XRDP process management and monitoring
- xrdp_config: Configuration generation and validation
- main: FastAPI application and service endpoints
"""

__version__ = "1.0.0"
__author__ = "Lucid Development Team"
__description__ = "XRDP service management for Lucid system"

# Import main components
from .xrdp_service import XRDPServiceManager, XRDPProcess, ServiceStatus
from .xrdp_config import XRDPConfigManager, XRDPConfig, SecurityLevel

__all__ = [
    "XRDPServiceManager",
    "XRDPProcess", 
    "ServiceStatus",
    "XRDPConfigManager",
    "XRDPConfig",
    "SecurityLevel"
]
