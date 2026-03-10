"""
URL and Data Validation Utilities for GUI Tor Manager
"""

from typing import Tuple
import re
from urllib.parse import urlparse


def validate_url(url: str, allowed_schemes: list[str] = None) -> bool:
    """
    Validate URL format
    
    Args:
        url: URL to validate
        allowed_schemes: List of allowed schemes (default: ['http', 'https'])
    
    Returns:
        True if valid, False otherwise
    """
    if allowed_schemes is None:
        allowed_schemes = ["http", "https"]
    
    try:
        result = urlparse(url)
        
        # Check scheme
        if result.scheme not in allowed_schemes:
            return False
        
        # Check netloc (host)
        if not result.netloc:
            return False
        
        # Reject localhost
        if "localhost" in result.netloc or "127.0.0.1" in result.netloc:
            return False
        
        return True
    except Exception:
        return False


def validate_port(port: int) -> bool:
    """
    Validate port number
    
    Args:
        port: Port number to validate
    
    Returns:
        True if valid, False otherwise
    """
    return 1 <= port <= 65535


def validate_host(host: str) -> bool:
    """
    Validate hostname
    
    Args:
        host: Hostname to validate
    
    Returns:
        True if valid, False otherwise
    """
    if not host or len(host) > 255:
        return False
    
    # Reject localhost
    if host in ("localhost", "127.0.0.1", "::1"):
        return False
    
    # Check for valid hostname pattern
    pattern = r"^(?!-)(?:[a-zA-Z0-9-]{1,63}(?<!-)\.)*(?!-)(?:[a-zA-Z0-9-]{1,63}(?<!-))$"
    return bool(re.match(pattern, host))


def parse_host_port(url: str) -> Tuple[str, int]:
    """
    Parse host and port from URL
    
    Args:
        url: URL to parse (e.g., 'http://host:port')
    
    Returns:
        Tuple of (host, port)
    
    Raises:
        ValueError: If URL format is invalid
    """
    try:
        parsed = urlparse(url)
        
        if not parsed.netloc:
            raise ValueError(f"Invalid URL format: {url}")
        
        # Split host and port
        if ":" in parsed.netloc:
            host, port_str = parsed.netloc.rsplit(":", 1)
            try:
                port = int(port_str)
            except ValueError:
                raise ValueError(f"Invalid port in URL: {parsed.netloc}")
        else:
            host = parsed.netloc
            # Default port based on scheme
            port = 443 if parsed.scheme == "https" else 80
        
        return host, port
    except Exception as e:
        raise ValueError(f"Failed to parse URL '{url}': {e}")


def validate_onion_address(address: str) -> bool:
    """
    Validate Tor onion address format
    
    Args:
        address: Onion address to validate (e.g., 'xxxx...xxxx.onion')
    
    Returns:
        True if valid, False otherwise
    """
    # v2 onion: 16 chars + .onion
    # v3 onion: 56 chars + .onion
    pattern = r"^[a-z0-9]{16}\.onion$|^[a-z0-9]{56}\.onion$"
    return bool(re.match(pattern, address.lower()))


def validate_tor_control_response(response: str) -> bool:
    """
    Validate Tor control protocol response format
    
    Args:
        response: Response from Tor control port
    
    Returns:
        True if valid response format, False otherwise
    """
    # Tor control responses start with numeric code (e.g., "250", "650")
    pattern = r"^\d{3}(\s|[-+]|$)"
    return bool(re.match(pattern, response.strip()))
