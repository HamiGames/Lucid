# Service Mesh Module
# Service mesh components

"""
Service mesh package for Lucid RDP.
Contains service mesh controller and orchestration components.

Modules:
- config: Environment-based configuration
- consul_manager: Consul service discovery integration
- certificate_manager: mTLS certificate management
- envoy_config_generator: Envoy proxy configuration
- main: FastAPI application entry point
- controller: Controller module for Docker CMD
"""

from .config import get_settings, Settings
from .consul_manager import ConsulManager
from .certificate_manager import CertificateManager
from .envoy_config_generator import EnvoyConfigGenerator

__all__ = [
    'get_settings',
    'Settings',
    'ConsulManager',
    'CertificateManager',
    'EnvoyConfigGenerator'
]

__version__ = "1.0.0"
