"""
Lucid Service Mesh Controller
Cluster: Infrastructure
Port: 8090

Features:
- Service discovery and registration
- Policy enforcement and governance
- Health monitoring and diagnostics
- Configuration management and updates
- Cross-cluster service integration
- Service mesh orchestration
"""

from .config_manager import ConfigManager
from .policy_engine import PolicyEngine
from .health_checker import HealthChecker

__all__ = [
    'ConfigManager',
    'PolicyEngine', 
    'HealthChecker'
]

# HTTP server is conditionally available (requires FastAPI)
try:
    from .http_server import HTTPServer
    __all__.append('HTTPServer')
except ImportError:
    pass

__version__ = "1.0.0"
__cluster__ = "infrastructure"
__port__ = 8090
