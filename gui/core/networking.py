# Path: gui/core/networking.py
"""
HTTP client with .onion enforcement for Lucid RDP GUI.
Provides secure networking with Tor-only connectivity and certificate pinning.
"""

import os
import ssl
import time
import hashlib
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass
from enum import Enum
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import socks
import socket

from .tor_client import TorClient, get_tor_client, TorConnectionError

logger = logging.getLogger(__name__)


class OnionEnforcementError(Exception):
    """Onion enforcement related errors"""
    pass


class NetworkSecurityError(Exception):
    """Network security related errors"""
    pass


@dataclass
class OnionEndpoint:
    """Onion endpoint configuration"""
    hostname: str
    port: int = 443
    protocol: str = "https"
    public_key_hash: Optional[str] = None  # SHA-256 hash of public key for pinning
    
    def __post_init__(self):
        if not self.hostname.endswith('.onion'):
            raise OnionEnforcementError(f"Hostname must be .onion: {self.hostname}")
        
        if self.protocol not in ['http', 'https']:
            raise OnionEnforcementError(f"Unsupported protocol: {self.protocol}")
    
    @property
    def url(self) -> str:
        """Get full URL for this endpoint"""
        return f"{self.protocol}://{self.hostname}:{self.port}"
    
    @property
    def base_url(self) -> str:
        """Get base URL without trailing slash"""
        return self.url.rstrip('/')


@dataclass
class SecurityConfig:
    """Network security configuration"""
    allowed_onions: List[str]  # Allowed .onion hostnames
    certificate_pinning: bool = True
    pinning_file: Optional[Path] = None
    connection_timeout: int = 30
    read_timeout: int = 60
    max_retries: int = 3
    retry_backoff_factor: float = 0.3
    verify_ssl: bool = True
    user_agent: str = "Lucid-RDP-GUI/1.0.0"


class TorHttpAdapter(HTTPAdapter):
    """Custom HTTP adapter for Tor SOCKS5 proxy"""
    
    def __init__(self, tor_client: TorClient, *args, **kwargs):
        self.tor_client = tor_client
        super().__init__(*args, **kwargs)
    
    def init_poolmanager(self, *args, **kwargs):
        """Initialize connection pool with Tor SOCKS5 proxy"""
        if not self.tor_client.is_running():
            raise TorConnectionError("Tor is not running")
        
        # Configure SOCKS5 proxy
        socks.set_default_proxy(
            socks.SOCKS5,
            "127.0.0.1",
            self.tor_client.config.socks_port
        )
        socket.socket = socks.socksocket
        
        super().init_poolmanager(*args, **kwargs)


class OnionEnforcer:
    """Enforces .onion-only connectivity and certificate pinning"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.pinned_certificates: Dict[str, str] = {}
        self._load_pinned_certificates()
    
    def _load_pinned_certificates(self) -> None:
        """Load certificate pinning data from file"""
        if not self.config.pinning_file or not self.config.pinning_file.exists():
            return
        
        try:
            with open(self.config.pinning_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split(':', 1)
                        if len(parts) == 2:
                            hostname, cert_hash = parts
                            self.pinned_certificates[hostname] = cert_hash.strip()
            
            logger.debug(f"Loaded {len(self.pinned_certificates)} pinned certificates")
            
        except Exception as e:
            logger.error(f"Failed to load pinned certificates: {e}")
    
    def save_pinned_certificates(self) -> None:
        """Save certificate pinning data to file"""
        if not self.config.pinning_file:
            return
        
        try:
            self.config.pinning_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config.pinning_file, 'w') as f:
                f.write("# Certificate pinning file for Lucid RDP GUI\n")
                f.write("# Format: hostname:sha256_hash\n")
                f.write("# Generated automatically - do not edit manually\n\n")
                
                for hostname, cert_hash in self.pinned_certificates.items():
                    f.write(f"{hostname}:{cert_hash}\n")
            
            logger.debug(f"Saved {len(self.pinned_certificates)} pinned certificates")
            
        except Exception as e:
            logger.error(f"Failed to save pinned certificates: {e}")
    
    def is_allowed_onion(self, hostname: str) -> bool:
        """Check if .onion hostname is allowed"""
        if not hostname.endswith('.onion'):
            return False
        
        # Check against allowed list
        if self.config.allowed_onions:
            return hostname in self.config.allowed_onions
        
        # If no allowed list, allow all .onion addresses
        return True
    
    def verify_certificate_pinning(self, hostname: str, cert_der: bytes) -> bool:
        """Verify certificate pinning for hostname"""
        if not self.config.certificate_pinning:
            return True
        
        # Calculate certificate hash
        cert_hash = hashlib.sha256(cert_der).hexdigest()
        
        # Check if we have a pinned certificate for this hostname
        if hostname in self.pinned_certificates:
            expected_hash = self.pinned_certificates[hostname]
            if cert_hash != expected_hash:
                logger.error(f"Certificate pinning failed for {hostname}")
                logger.error(f"Expected: {expected_hash}")
                logger.error(f"Got: {cert_hash}")
                return False
        else:
            # First time seeing this certificate - pin it (TOFU)
            self.pinned_certificates[hostname] = cert_hash
            self.save_pinned_certificates()
            logger.info(f"Pinned new certificate for {hostname}: {cert_hash}")
        
        return True


class TorHttpClient:
    """
    HTTP client with Tor-only connectivity and .onion enforcement.
    
    Provides secure networking with:
    - Tor SOCKS5 proxy enforcement
    - .onion hostname allowlist
    - Certificate pinning (TOFU)
    - Automatic retries and timeouts
    """
    
    def __init__(self, 
                 security_config: SecurityConfig,
                 tor_client: Optional[TorClient] = None):
        self.security_config = security_config
        self.tor_client = tor_client or get_tor_client()
        self.enforcer = OnionEnforcer(security_config)
        self.session: Optional[requests.Session] = None
        self._setup_session()
    
    def _setup_session(self) -> None:
        """Setup requests session with Tor adapter and security"""
        self.session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.security_config.max_retries,
            backoff_factor=self.security_config.retry_backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"]
        )
        
        # Mount Tor adapter
        tor_adapter = TorHttpAdapter(self.tor_client)
        self.session.mount("http://", tor_adapter)
        self.session.mount("https://", tor_adapter)
        
        # Configure session
        self.session.headers.update({
            'User-Agent': self.security_config.user_agent
        })
        
        # Setup SSL context for certificate pinning
        if self.security_config.certificate_pinning:
            self._setup_ssl_context()
    
    def _setup_ssl_context(self) -> None:
        """Setup SSL context for certificate pinning"""
        class PinningHTTPSAdapter(HTTPAdapter):
            def __init__(self, enforcer, *args, **kwargs):
                self.enforcer = enforcer
                super().__init__(*args, **kwargs)
            
            def init_poolmanager(self, *args, **kwargs):
                context = ssl.create_default_context()
                context.check_hostname = True
                context.verify_mode = ssl.CERT_REQUIRED
                
                # Custom verification for certificate pinning
                def verify_callback(conn, cert, errno, depth, ok):
                    if not ok:
                        return False
                    
                    # Get certificate DER data
                    cert_der = cert.to_cryptography().public_bytes(
                        encoding=serialization.Encoding.DER
                    )
                    
                    # Verify pinning
                    hostname = conn.getpeername()[0]
                    return self.enforcer.verify_certificate_pinning(hostname, cert_der)
                
                context.set_verify(ssl.CERT_REQUIRED, verify_callback)
                kwargs['ssl_context'] = context
                super().init_poolmanager(*args, **kwargs)
        
        # Mount pinning adapter for HTTPS
        pinning_adapter = PinningHTTPSAdapter(self.enforcer)
        self.session.mount("https://", pinning_adapter)
    
    def _validate_url(self, url: str) -> None:
        """Validate URL for .onion enforcement"""
        from urllib.parse import urlparse
        
        parsed = urlparse(url)
        hostname = parsed.hostname
        
        if not hostname:
            raise OnionEnforcementError("No hostname in URL")
        
        if not self.enforcer.is_allowed_onion(hostname):
            raise OnionEnforcementError(f"Onion hostname not allowed: {hostname}")
        
        if parsed.scheme not in ['http', 'https']:
            raise OnionEnforcementError(f"Unsupported scheme: {parsed.scheme}")
    
    def _ensure_tor_running(self) -> None:
        """Ensure Tor is running"""
        if not self.tor_client.is_running():
            raise TorConnectionError("Tor is not running")
    
    def get(self, url: str, **kwargs) -> requests.Response:
        """GET request through Tor"""
        self._ensure_tor_running()
        self._validate_url(url)
        
        kwargs.setdefault('timeout', (
            self.security_config.connection_timeout,
            self.security_config.read_timeout
        ))
        
        try:
            response = self.session.get(url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"GET request failed for {url}: {e}")
            raise
    
    def post(self, url: str, **kwargs) -> requests.Response:
        """POST request through Tor"""
        self._ensure_tor_running()
        self._validate_url(url)
        
        kwargs.setdefault('timeout', (
            self.security_config.connection_timeout,
            self.security_config.read_timeout
        ))
        
        try:
            response = self.session.post(url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"POST request failed for {url}: {e}")
            raise
    
    def put(self, url: str, **kwargs) -> requests.Response:
        """PUT request through Tor"""
        self._ensure_tor_running()
        self._validate_url(url)
        
        kwargs.setdefault('timeout', (
            self.security_config.connection_timeout,
            self.security_config.read_timeout
        ))
        
        try:
            response = self.session.put(url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"PUT request failed for {url}: {e}")
            raise
    
    def delete(self, url: str, **kwargs) -> requests.Response:
        """DELETE request through Tor"""
        self._ensure_tor_running()
        self._validate_url(url)
        
        kwargs.setdefault('timeout', (
            self.security_config.connection_timeout,
            self.security_config.read_timeout
        ))
        
        try:
            response = self.session.delete(url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"DELETE request failed for {url}: {e}")
            raise
    
    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Generic request through Tor"""
        self._ensure_tor_running()
        self._validate_url(url)
        
        kwargs.setdefault('timeout', (
            self.security_config.connection_timeout,
            self.security_config.read_timeout
        ))
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"{method} request failed for {url}: {e}")
            raise
    
    def close(self) -> None:
        """Close HTTP client session"""
        if self.session:
            self.session.close()
            self.session = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Global HTTP client instance
_http_client: Optional[TorHttpClient] = None


def get_http_client(security_config: Optional[SecurityConfig] = None) -> TorHttpClient:
    """Get global HTTP client instance"""
    global _http_client
    
    if _http_client is None:
        if security_config is None:
            # Default security config
            security_config = SecurityConfig(
                allowed_onions=[],  # Allow all .onion addresses
                certificate_pinning=True,
                pinning_file=Path.home() / ".lucid" / "certificates.txt"
            )
        
        _http_client = TorHttpClient(security_config)
    
    return _http_client


def cleanup_http_client() -> None:
    """Cleanup global HTTP client"""
    global _http_client
    
    if _http_client:
        _http_client.close()
        _http_client = None


# Convenience functions for common operations
def get_json(url: str, **kwargs) -> Dict[str, Any]:
    """GET JSON data from .onion endpoint"""
    client = get_http_client()
    response = client.get(url, **kwargs)
    return response.json()


def post_json(url: str, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """POST JSON data to .onion endpoint"""
    client = get_http_client()
    kwargs.setdefault('json', data)
    response = client.post(url, **kwargs)
    return response.json()


def download_file(url: str, filepath: Union[str, Path], **kwargs) -> None:
    """Download file from .onion endpoint"""
    client = get_http_client()
    response = client.get(url, stream=True, **kwargs)
    
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    with open(filepath, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
