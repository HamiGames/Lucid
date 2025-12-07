#!/usr/bin/env python3
"""
Redis Health Check Script for Distroless Container
FIXED: Uses REDIS_PASSWORD from environment variables (no hardcoded passwords)
"""

import sys
import os
import time
import logging
import redis
from redis.exceptions import ConnectionError, TimeoutError, AuthenticationError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('redis-healthcheck')

def check_redis_health():
    """Check Redis health using redis-py"""
    try:
        # Get connection parameters from environment (from .env.* files)
        host = os.getenv('REDIS_HOST', 'localhost')
        port = int(os.getenv('REDIS_PORT', '6379'))
        password = os.getenv('REDIS_PASSWORD', '')
        
        if not password:
            logger.error("REDIS_PASSWORD environment variable is not set!")
            return False
        
        # Create Redis client with password from environment
        client = redis.Redis(
            host=host,
            port=port,
            password=password,  # Password from environment, not hardcoded
            socket_timeout=5,
            socket_connect_timeout=5,
            retry_on_timeout=True,
            decode_responses=True
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
        
    except AuthenticationError as e:
        logger.error(f"Redis authentication failed: {e}")
        logger.error("Please check REDIS_PASSWORD in .env.secrets matches the Redis configuration")
        return False
    except (ConnectionError, TimeoutError) as e:
        logger.error(f"Redis connection failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during health check: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            if 'client' in locals():
                client.close()
        except:
            pass

if __name__ == '__main__':
    if check_redis_health():
        sys.exit(0)
    else:
        sys.exit(1)
