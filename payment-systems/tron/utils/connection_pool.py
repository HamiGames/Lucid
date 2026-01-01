"""
LUCID Payment Systems - TRON Client Connection Pool Module
HTTP connection pool management for TRON network requests
Following architecture patterns from build/docs/
"""

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Optional, Dict, Any
import httpx

logger = logging.getLogger(__name__)


@dataclass
class PoolConfig:
    """Connection pool configuration"""
    max_connections: int = 100
    max_keepalive_connections: int = 20
    keepalive_expiry: float = 5.0
    timeout: float = 30.0
    connect_timeout: float = 10.0
    read_timeout: float = 30.0
    write_timeout: float = 30.0
    pool_timeout: float = 5.0


class ConnectionPoolManager:
    """
    HTTP connection pool manager for TRON network requests
    
    Features:
    - Connection pooling and reuse
    - Keep-alive configuration
    - Connection limits
    - Pool health monitoring
    """
    
    def __init__(self, base_url: str, config: Optional[PoolConfig] = None, headers: Optional[Dict[str, str]] = None):
        self.base_url = base_url
        self.config = config or PoolConfig()
        self.headers = headers or {}
        self._client: Optional[httpx.AsyncClient] = None
        self._lock = asyncio.Lock()
    
    async def get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with connection pool"""
        async with self._lock:
            if self._client is None or self._client.is_closed:
                limits = httpx.Limits(
                    max_connections=self.config.max_connections,
                    max_keepalive_connections=self.config.max_keepalive_connections,
                    keepalive_expiry=self.config.keepalive_expiry
                )
                
                timeout = httpx.Timeout(
                    timeout=self.config.timeout,
                    connect=self.config.connect_timeout,
                    read=self.config.read_timeout,
                    write=self.config.write_timeout,
                    pool=self.config.pool_timeout
                )
                
                self._client = httpx.AsyncClient(
                    base_url=self.base_url,
                    limits=limits,
                    timeout=timeout,
                    headers=self.headers,
                    follow_redirects=True
                )
                
                logger.info(
                    f"Created HTTP client connection pool: "
                    f"max_connections={self.config.max_connections}, "
                    f"max_keepalive={self.config.max_keepalive_connections}"
                )
            
            return self._client
    
    async def close(self):
        """Close connection pool"""
        async with self._lock:
            if self._client and not self._client.is_closed:
                await self._client.aclose()
                self._client = None
                logger.info("Closed HTTP client connection pool")
    
    async def __aenter__(self):
        """Async context manager entry"""
        return await self.get_client()
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        # Don't close on exit - keep pool alive
        pass
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        if self._client is None:
            return {
                "status": "not_initialized",
                "max_connections": self.config.max_connections,
                "max_keepalive_connections": self.config.max_keepalive_connections
            }
        
        # httpx doesn't expose pool stats directly, return config
        return {
            "status": "active" if not self._client.is_closed else "closed",
            "max_connections": self.config.max_connections,
            "max_keepalive_connections": self.config.max_keepalive_connections,
            "base_url": str(self.base_url)
        }


class ConnectionPoolManagerRegistry:
    """Registry for managing multiple connection pools"""
    
    def __init__(self):
        self._pools: Dict[str, ConnectionPoolManager] = {}
        self._lock = asyncio.Lock()
    
    async def get_pool(
        self,
        name: str,
        base_url: str,
        config: Optional[PoolConfig] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> ConnectionPoolManager:
        """Get or create connection pool"""
        async with self._lock:
            if name not in self._pools:
                self._pools[name] = ConnectionPoolManager(base_url, config, headers)
            return self._pools[name]
    
    async def close_all(self):
        """Close all connection pools"""
        async with self._lock:
            for pool in self._pools.values():
                await pool.close()
            self._pools.clear()
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all pools"""
        return {name: pool.get_pool_stats() for name, pool in self._pools.items()}


# Global connection pool registry
_pool_registry: Optional[ConnectionPoolManagerRegistry] = None


def get_pool_registry() -> ConnectionPoolManagerRegistry:
    """Get or create global connection pool registry"""
    global _pool_registry
    if _pool_registry is None:
        _pool_registry = ConnectionPoolManagerRegistry()
    return _pool_registry

