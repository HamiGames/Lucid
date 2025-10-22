#!/usr/bin/env python3
"""
Elasticsearch Health Check Script for Distroless Container
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
logger = logging.getLogger('elasticsearch-healthcheck')

def check_elasticsearch_health():
    """Check Elasticsearch health using requests"""
    try:
        # Get connection parameters from environment
        host = os.getenv('ELASTICSEARCH_HOST', 'localhost')
        port = int(os.getenv('ELASTICSEARCH_PORT', '9200'))
        url = f"http://{host}:{port}"
        
        # Test cluster health
        health_url = f"{url}/_cluster/health"
        response = requests.get(health_url, timeout=5)
        
        if response.status_code == 200:
            health_data = response.json()
            status = health_data.get('status', 'unknown')
            logger.info(f"Elasticsearch health check passed. Status: {status}")
            return True
        else:
            logger.error(f"Elasticsearch health check failed with status: {response.status_code}")
            return False
        
    except (ConnectionError, Timeout) as e:
        logger.error(f"Elasticsearch health check failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during health check: {e}")
        return False

if __name__ == '__main__':
    if check_elasticsearch_health():
        sys.exit(0)
    else:
        sys.exit(1)
