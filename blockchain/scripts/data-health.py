#!/usr/bin/env python3
"""
Data Health Check Script for Session-Anchoring and Data-Chain Services
Provides comprehensive health checking that bypasses basic socket checks
and verifies actual service operational status via HTTP endpoints.

Usage:
    - Standalone: python3 data-health.py [service_name]
    - Docker healthcheck: python3 data-health.py
    - Check specific service: python3 data-health.py session-anchoring|data-chain

Exit Codes:
    0 - All services healthy
    1 - Service unhealthy or error
"""

import sys
import os
import time
import socket
import urllib.request
import urllib.error
from typing import Dict, Optional, Tuple

# Configure service endpoints
SERVICES = {
    "session-anchoring": {
        "host": os.getenv("SESSION_ANCHORING_HOST", "127.0.0.1"),
        "port": int(os.getenv("SESSION_ANCHORING_PORT", "8085")),
        "path": os.getenv("SESSION_ANCHORING_HEALTH_PATH", "/health"),
        "timeout": float(os.getenv("SESSION_ANCHORING_HEALTH_CHECK_TIMEOUT", "10")),
    },
    "data-chain": {
        "host": os.getenv("DATA_CHAIN_HOST", "127.0.0.1"),
        "port": int(os.getenv("DATA_CHAIN_PORT", "8087")),
        "path": os.getenv("DATA_CHAIN_HEALTH_PATH", "/health"),
        "timeout": float(os.getenv("DATA_CHAIN_HEALTH_CHECK_TIMEOUT", "10")),
    },
}


def check_port_listening(host: str, port: int, timeout: float = 2.0) -> bool:
    """
    Check if a port is listening (basic connectivity check).
    
    Args:
        host: Hostname or IP address
        port: Port number
        timeout: Connection timeout in seconds
        
    Returns:
        True if port is listening, False otherwise
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def check_http_health(host: str, port: int, path: str, timeout: float = 10.0) -> Tuple[bool, Optional[str]]:
    """
    Check service health via HTTP endpoint.
    
    Args:
        host: Hostname or IP address
        port: Port number
        path: Health check endpoint path
        timeout: Request timeout in seconds
        
    Returns:
        Tuple of (is_healthy, error_message)
    """
    try:
        url = f"http://{host}:{port}{path}"
        
        # Create request with timeout
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Lucid-HealthCheck/1.0")
        
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status_code = response.getcode()
            
            if status_code == 200:
                # Try to read response to ensure service is fully operational
                try:
                    response.read(1)  # Read at least 1 byte to verify connection
                except Exception:
                    pass  # Some services may close connection immediately
                
                return True, None
            else:
                return False, f"HTTP {status_code}"
                
    except urllib.error.HTTPError as e:
        # HTTP error (4xx, 5xx) - service responded but with error
        if e.code == 200:
            return True, None
        return False, f"HTTP {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        # URL error (connection refused, timeout, etc.)
        return False, f"Connection error: {str(e)}"
    except socket.timeout:
        return False, "Connection timeout"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


def check_service_health(service_name: str, fallback_to_socket: bool = True) -> Tuple[bool, Optional[str]]:
    """
    Check health of a specific service.
    
    Args:
        service_name: Name of the service to check
        fallback_to_socket: If HTTP check fails, fall back to socket check
        
    Returns:
        Tuple of (is_healthy, error_message)
    """
    if service_name not in SERVICES:
        return False, f"Unknown service: {service_name}"
    
    config = SERVICES[service_name]
    
    # First, check if port is listening (quick check)
    if not check_port_listening(config["host"], config["port"], timeout=2.0):
        return False, f"Port {config['port']} not listening"
    
    # Then, check HTTP health endpoint (comprehensive check)
    is_healthy, error = check_http_health(
        config["host"],
        config["port"],
        config["path"],
        timeout=config["timeout"]
    )
    
    if is_healthy:
        return True, None
    
    # If HTTP check fails but fallback is enabled, verify port is still listening
    if fallback_to_socket:
        if check_port_listening(config["host"], config["port"], timeout=2.0):
            # Port is listening but HTTP failed - service might be starting
            return False, f"Port listening but HTTP check failed: {error}"
        else:
            return False, f"Port {config['port']} not listening"
    
    return False, error


def check_all_services() -> Tuple[bool, Dict[str, Tuple[bool, Optional[str]]]]:
    """
    Check health of all configured services.
    
    Returns:
        Tuple of (all_healthy, service_results_dict)
    """
    results = {}
    all_healthy = True
    
    for service_name in SERVICES.keys():
        is_healthy, error = check_service_health(service_name)
        results[service_name] = (is_healthy, error)
        
        if not is_healthy:
            all_healthy = False
    
    return all_healthy, results


def main():
    """Main entry point for health check script."""
    # Get service name from command line if provided
    service_name = None
    if len(sys.argv) > 1:
        service_name = sys.argv[1].lower()
    
    # Check specific service or all services
    if service_name:
        if service_name not in SERVICES:
            print(f"Error: Unknown service '{service_name}'", file=sys.stderr)
            print(f"Available services: {', '.join(SERVICES.keys())}", file=sys.stderr)
            sys.exit(1)
        
        is_healthy, error = check_service_health(service_name)
        
        if is_healthy:
            print(f"Service '{service_name}' is healthy")
            sys.exit(0)
        else:
            print(f"Service '{service_name}' is unhealthy: {error}", file=sys.stderr)
            sys.exit(1)
    else:
        # Check all services
        all_healthy, results = check_all_services()
        
        if all_healthy:
            print("All services are healthy")
            sys.exit(0)
        else:
            # Print detailed results
            for svc_name, (healthy, error) in results.items():
                status = "healthy" if healthy else f"unhealthy: {error}"
                print(f"  {svc_name}: {status}", file=sys.stderr)
            
            sys.exit(1)


if __name__ == "__main__":
    main()

