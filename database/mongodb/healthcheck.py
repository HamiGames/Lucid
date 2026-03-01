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
    """Check MongoDB health using mongosh with retries and user fallback"""
    password = os.getenv('MONGODB_PASSWORD', '')
    host = '127.0.0.1'
    port = os.getenv('MONGODB_PORT', '27017')
    users = ['root', 'lucid']  # try root first, then lucid

    if not password:
        logger.error("MONGODB_PASSWORD not set")
        return False

    for user in users:
        cmd = [
            '/usr/bin/mongosh',
            '--quiet',
            '--host', host,
            '--port', str(port),
            '--eval', 'db.runCommand({ ping: 1 })',
            '-u', user,
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
                    logger.info(f"MongoDB health check passed with user '{user}'")
                    return True
                else:
                    logger.error(f"MongoDB health check failed (user {user}, attempt {attempt+1}/3): {result.stderr.strip()}")
            except subprocess.TimeoutExpired:
                logger.error(f"MongoDB health check timed out (user {user}, attempt {attempt+1}/3)")
            except Exception as e:
                logger.error(f"MongoDB health check error (user {user}, attempt {attempt+1}/3): {e}")
            time.sleep(2)

    return False

if __name__ == '__main__':
    success = check_mongodb_health()
    sys.exit(0 if success else 1)
