#!/usr/bin/env python3
"""
MongoDB Healthcheck Script for Distroless Container
Checks MongoDB connectivity and authentication
"""

import os
import sys
import subprocess
import logging
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('mongodb-healthcheck')

def check_mongodb_health():
    """Check MongoDB health using mongosh with retries"""
    password = os.getenv('MONGODB_PASSWORD', '')
    username = 'lucid'
    host = '127.0.0.1'
    port = os.getenv('MONGODB_PORT', '27017')

    if not password:
        logger.error("MONGODB_PASSWORD not set")
        return False

    cmd = [
        '/usr/bin/mongosh',
        '--quiet',
        '--host', host,
        '--port', str(port),
        '--eval', 'db.runCommand({ ping: 1 })',
        '-u', username,
        '-p', password,
        '--authenticationDatabase', 'admin'
    ]

    for attempt in range(3):
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info("MongoDB health check passed")
                return True
            else:
                logger.error(f"MongoDB health check failed (attempt {attempt+1}/3): {result.stderr.strip()}")
        except subprocess.TimeoutExpired:
            logger.error(f"MongoDB health check timed out (attempt {attempt+1}/3)")
        except Exception as e:
            logger.error(f"MongoDB health check error (attempt {attempt+1}/3): {e}")
        time.sleep(2)

    return False

if __name__ == '__main__':
    success = check_mongodb_health()
    sys.exit(0 if success else 1)
