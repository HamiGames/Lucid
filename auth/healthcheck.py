#!/usr/bin/env python3
"""
Authentication Service Health Check Script for Distroless Container
Provides health check functionality without shell access
"""

import sys
import os
import time
import logging
import requests
from requests.exceptions import ConnectionError, Timeout

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('auth-healthcheck')

def check_auth_service_health():
    """Check Authentication Service health using requests"""
    try:
        # Get connection parameters from environment
        host = os.getenv('AUTH_SERVICE_HOST', 'localhost')
        port = int(os.getenv('AUTH_SERVICE_PORT', '8089'))
        url = f"http://{host}:{port}"
        
        # Test health endpoint
        health_url = f"{url}/health"
        response = requests.get(health_url, timeout=5)
        
        if response.status_code == 200:
            logger.info("Authentication Service health check passed")
            return True
        else:
            logger.error(f"Authentication Service health check failed with status: {response.status_code}")
            return False
        
    except (ConnectionError, Timeout) as e:
        logger.error(f"Authentication Service health check failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during health check: {e}")
        return False

if __name__ == '__main__':
    if check_auth_service_health():
        sys.exit(0)
    else:
        sys.exit(1)
