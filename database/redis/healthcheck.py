#!/usr/bin/env python3
"""
Redis Health Check Script for Distroless Container
Provides health check functionality without shell access
"""

import sys
import os
import time
import logging
import redis
from redis.exceptions import ConnectionError, TimeoutError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('redis-healthcheck')

def check_redis_health():
    """Check Redis health using redis-py"""
    try:
        # Get connection parameters from environment
        host = os.getenv('REDIS_HOST', 'localhost')
        port = int(os.getenv('REDIS_PORT', '6379'))
        password = os.getenv('REDIS_PASSWORD', 'changeme')
        
        # Create Redis client
        client = redis.Redis(
            host=host,
            port=port,
            password=password,
            socket_timeout=5,
            socket_connect_timeout=5,
            retry_on_timeout=True
        )
        
        # Test connection with ping
        response = client.ping()
        if not response:
            logger.error("Redis ping failed")
            return False
        
        # Get Redis info
        info = client.info()
        logger.info(f"Redis health check passed. Version: {info.get('redis_version', 'unknown')}")
        return True
        
    except (ConnectionError, TimeoutError) as e:
        logger.error(f"Redis health check failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during health check: {e}")
        return False
    finally:
        try:
            client.close()
        except:
            pass

if __name__ == '__main__':
    if check_redis_health():
        sys.exit(0)
    else:
        sys.exit(1)
