#!/usr/bin/env python3
"""
MongoDB Healthcheck Script for Distroless Container
Checks MongoDB connectivity and authentication
"""

import os
import sys
import subprocess
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('mongodb-healthcheck')

def check_mongodb_health():
    """Check MongoDB health using mongosh"""
    try:
        # Get connection parameters from environment
        password = os.getenv('MONGODB_PASSWORD', '')
        username = 'lucid'
        
        if not password:
            logger.error("MONGODB_PASSWORD not set")
            return False
        
        # Build mongosh command with authentication
        cmd = [
            '/usr/bin/mongosh',
            '--quiet',
            '--eval', 'db.runCommand({ ping: 1 })',
            '-u', username,
            '-p', password,
            '--authenticationDatabase', 'admin'
        ]
        
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
            logger.error(f"MongoDB health check failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("MongoDB health check timed out")
        return False
    except Exception as e:
        logger.error(f"MongoDB health check error: {e}")
        return False

if __name__ == '__main__':
    success = check_mongodb_health()
    sys.exit(0 if success else 1)
