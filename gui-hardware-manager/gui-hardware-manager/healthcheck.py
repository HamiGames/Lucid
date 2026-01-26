#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Health check script for GUI Hardware Manager
Can be used standalone for container health verification
"""

import socket
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_health(host: str = "127.0.0.1", port: int = 8099, timeout: int = 2) -> int:
    """
    Check if the service is healthy by attempting a socket connection
    
    Args:
        host: Service host
        port: Service port
        timeout: Connection timeout in seconds
        
    Returns:
        0 if healthy, 1 if unhealthy
    """
    try:
        socket_obj = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket_obj.settimeout(timeout)
        
        result = socket_obj.connect_ex((host, port))
        socket_obj.close()
        
        if result == 0:
            logger.info(f"✓ Service is healthy on {host}:{port}")
            return 0
        else:
            logger.error(f"✗ Service is not responding on {host}:{port}")
            return 1
            
    except socket.timeout:
        logger.error(f"✗ Connection timeout to {host}:{port}")
        return 1
    except socket.error as e:
        logger.error(f"✗ Socket error: {e}")
        return 1
    except Exception as e:
        logger.error(f"✗ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = check_health()
    sys.exit(exit_code)
