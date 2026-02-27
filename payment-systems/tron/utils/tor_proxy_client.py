"""
LUCID TRON Services - Tor Proxy HTTP Client Manager
Configures HTTP client to route external calls through tor-proxy
Supports both httpx and requests libraries
"""

import os
import logging
from typing import Optional
import httpx

logger = logging.getLogger(__name__)


class TorProxyClientManager:
    """Manages HTTP client configuration for tor-proxy integration"""

    def __init__(
        self,
        tor_proxy_host: str = "tor-proxy",
        tor_proxy_socks_port: int = 9050,
        tor_proxy_http_port: int = 8888,
        use_tor_for_external_calls: bool = True,
        tor_route_rpc: bool = True,
        connectivity_timeout: int = 30,
    ):
        """
        Initialize tor-proxy client manager

        Args:
            tor_proxy_host: Tor proxy hostname/IP
            tor_proxy_socks_port: SOCKS5 port (default 9050)
            tor_proxy_http_port: HTTP proxy port (default 8888)
            use_tor_for_external_calls: Enable tor routing for external calls
            tor_route_rpc: Enable tor routing specifically for RPC calls
            connectivity_timeout: Connection timeout in seconds
        """
        self.tor_proxy_host = tor_proxy_host
        self.tor_proxy_socks_port = tor_proxy_socks_port
        self.tor_proxy_http_port = tor_proxy_http_port
        self.use_tor_for_external_calls = use_tor_for_external_calls
        self.tor_route_rpc = tor_route_rpc
        self.connectivity_timeout = connectivity_timeout

        self.socks5_proxy = f"socks5://{tor_proxy_host}:{tor_proxy_socks_port}"
        self.http_proxy = f"http://{tor_proxy_host}:{tor_proxy_http_port}"

        logger.info(
            f"TorProxyClientManager initialized: "
            f"host={tor_proxy_host}, "
            f"socks5_port={tor_proxy_socks_port}, "
            f"http_port={tor_proxy_http_port}, "
            f"use_tor={use_tor_for_external_calls}, "
            f"route_rpc={tor_route_rpc}"
        )

    def create_httpx_client(
        self, timeout: Optional[float] = None, **kwargs
    ) -> httpx.AsyncClient:
        """
        Create httpx AsyncClient configured for tor-proxy

        Args:
            timeout: Request timeout in seconds
            **kwargs: Additional httpx.AsyncClient arguments

        Returns:
            Configured httpx.AsyncClient instance
        """
        if timeout is None:
            timeout = self.connectivity_timeout

        client_config = {
            "timeout": timeout,
            "follow_redirects": True,
            **kwargs,
        }

        # Configure proxy routing
        if self.use_tor_for_external_calls:
            if self.tor_route_rpc:
                # Route all HTTPS through tor for RPC calls
                client_config["proxies"] = {
                    "https://": self.http_proxy,
                    "http://": self.http_proxy,
                }
                logger.debug(f"httpx client configured with HTTP proxy: {self.http_proxy}")
            else:
                # Alternative: use SOCKS5 directly (requires httpx[socks] extra)
                try:
                    client_config["proxies"] = self.socks5_proxy
                    logger.debug(
                        f"httpx client configured with SOCKS5 proxy: {self.socks5_proxy}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to configure SOCKS5 proxy, falling back to HTTP proxy: {e}"
                    )
                    client_config["proxies"] = {
                        "https://": self.http_proxy,
                        "http://": self.http_proxy,
                    }
        else:
            logger.debug("httpx client configured WITHOUT tor proxy")

        return httpx.AsyncClient(**client_config)

    def get_proxy_url(self, protocol: str = "http") -> Optional[str]:
        """
        Get proxy URL for specific protocol

        Args:
            protocol: Protocol type ('http', 'https', or 'socks5')

        Returns:
            Proxy URL or None if tor is disabled
        """
        if not self.use_tor_for_external_calls:
            return None

        if protocol == "socks5":
            return self.socks5_proxy
        else:  # http, https
            return self.http_proxy

    def get_environment_variables(self) -> dict:
        """
        Get environment variables for subprocesses using tor-proxy

        Returns:
            Dictionary of environment variables
        """
        env_vars = {}

        if self.use_tor_for_external_calls:
            env_vars.update(
                {
                    "HTTP_PROXY": self.http_proxy,
                    "HTTPS_PROXY": self.http_proxy,
                    "http_proxy": self.http_proxy,
                    "https_proxy": self.http_proxy,
                    "SOCKS5_PROXY": self.socks5_proxy,
                    "socks5_proxy": self.socks5_proxy,
                }
            )

        return env_vars

    async def test_tor_connectivity(self) -> bool:
        """
        Test connectivity to tor-proxy service

        Returns:
            True if tor-proxy is reachable and healthy
        """
        try:
            async with httpx.AsyncClient(timeout=self.connectivity_timeout) as client:
                # Try to connect to tor-proxy control port
                response = await client.get(
                    f"http://{self.tor_proxy_host}:{self.tor_proxy_http_port}",
                    follow_redirects=True,
                )
                logger.info(
                    f"Tor-proxy connectivity test successful (status={response.status_code})"
                )
                return True
        except Exception as e:
            logger.error(f"Tor-proxy connectivity test failed: {e}")
            return False

    def __repr__(self) -> str:
        return (
            f"TorProxyClientManager("
            f"host={self.tor_proxy_host}, "
            f"socks5_port={self.tor_proxy_socks_port}, "
            f"http_port={self.tor_proxy_http_port}, "
            f"enabled={self.use_tor_for_external_calls})"
        )


# Global instance (can be initialized during app startup)
_tor_client_manager: Optional[TorProxyClientManager] = None


def get_tor_proxy_client_manager() -> TorProxyClientManager:
    """Get or create global tor-proxy client manager"""
    global _tor_client_manager
    if _tor_client_manager is None:
        _tor_client_manager = TorProxyClientManager(
            tor_proxy_host=os.getenv("TOR_PROXY_HOST", "tor-proxy"),
            tor_proxy_socks_port=int(os.getenv("TOR_PROXY_SOCKS_PORT", "9050")),
            tor_proxy_http_port=int(os.getenv("TOR_PROXY_HTTP_PORT", "8888")),
            use_tor_for_external_calls=os.getenv("USE_TOR_FOR_EXTERNAL_CALLS", "true").lower() == "true",
            tor_route_rpc=os.getenv("TOR_ROUTE_RPC", "true").lower() == "true",
            connectivity_timeout=int(os.getenv("TOR_CONNECTIVITY_TIMEOUT", "30")),
        )
    return _tor_client_manager


def initialize_tor_proxy_client(config) -> TorProxyClientManager:
    """Initialize tor-proxy client manager from config object"""
    global _tor_client_manager
    _tor_client_manager = TorProxyClientManager(
        tor_proxy_host=config.tor_proxy_host,
        tor_proxy_socks_port=config.tor_proxy_socks_port,
        tor_proxy_http_port=config.tor_proxy_http_port,
        use_tor_for_external_calls=config.use_tor_for_external_calls,
        tor_route_rpc=config.tor_route_rpc,
        connectivity_timeout=config.tor_connectivity_timeout,
    )
    return _tor_client_manager
