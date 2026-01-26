"""
Health Check Logic for GUI Tor Manager
Provides comprehensive health status of the service and its dependencies
"""

from typing import Dict, Any, Optional
from enum import Enum
import asyncio
import socket
from datetime import datetime

from config import get_config


class HealthStatus(str, Enum):
    """Health status enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class HealthCheckManager:
    """Manages health check logic for the GUI Tor Manager service"""
    
    def __init__(self):
        """Initialize health check manager"""
        self.config = get_config().settings
        self._tor_proxy_healthy: Optional[bool] = None
        self._last_check: Optional[datetime] = None
    
    async def check_tor_proxy_connection(self) -> bool:
        """Check if Tor proxy service is reachable"""
        try:
            # Extract host and port from TOR_PROXY_URL
            # URL format: http://tor-proxy:9051
            url = self.config.TOR_PROXY_URL
            
            # Parse host and port
            if "://" in url:
                _, url_part = url.split("://", 1)
            else:
                url_part = url
            
            if ":" in url_part:
                host, port_str = url_part.rsplit(":", 1)
                port = int(port_str)
            else:
                host = url_part
                port = 9051
            
            # Test connection with socket
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, self._socket_test, host, port
            )
            return result
        except Exception as e:
            print(f"Tor proxy connection check failed: {e}")
            return False
    
    @staticmethod
    def _socket_test(host: str, port: int, timeout: int = 2) -> bool:
        """Test socket connection to host:port"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    async def check_api_health(self) -> bool:
        """Check if API itself is healthy"""
        # Basic check: ensure configuration is valid
        try:
            self.config.verify_critical_settings()
            return True
        except Exception as e:
            print(f"API health check failed: {e}")
            return False
    
    async def get_overall_status(self) -> Dict[str, Any]:
        """Get overall health status"""
        api_healthy = await self.check_api_health()
        tor_proxy_healthy = await self.check_tor_proxy_connection()
        
        self._last_check = datetime.utcnow()
        
        # Determine overall status
        if api_healthy and tor_proxy_healthy:
            status = HealthStatus.HEALTHY
        elif api_healthy:
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.UNHEALTHY
        
        return {
            "status": status.value,
            "timestamp": self._last_check.isoformat(),
            "service": self.config.SERVICE_NAME,
            "components": {
                "api": "healthy" if api_healthy else "unhealthy",
                "tor_proxy": "healthy" if tor_proxy_healthy else "unhealthy",
            },
            "version": "1.0.0",
        }


# Create singleton instance
_health_check_manager: Optional[HealthCheckManager] = None


def get_health_check() -> HealthCheckManager:
    """Get or create health check manager singleton"""
    global _health_check_manager
    if _health_check_manager is None:
        _health_check_manager = HealthCheckManager()
    return _health_check_manager
