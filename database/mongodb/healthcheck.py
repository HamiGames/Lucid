#!/usr/bin/env python3
"""
MongoDB Health Check Script for Distroless Container
Provides health check functionality without shell access
"""

import sys
import os
import time
import logging
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('mongodb-healthcheck')

def check_mongodb_health():
    """Check MongoDB health using PyMongo"""
    try:
        # Get connection parameters from environment
        host = os.getenv('MONGODB_HOST', 'localhost')
        port = int(os.getenv('MONGODB_PORT', '27017'))
        username = os.getenv('MONGODB_USER', 'lucid')
        password = os.getenv('MONGODB_PASSWORD', 'changeme')
        database = os.getenv('MONGODB_DATABASE', 'lucid')
        
        # Build connection URI
        uri = f"mongodb://{username}:{password}@{host}:{port}/{database}?authSource=admin"
        
        # Create client with timeout
        client = MongoClient(
            uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=5000
        )
        
        # Test connection
        client.admin.command('ping')
        
        # Check if we can read from the database
        db = client[database]
        collections = db.list_collection_names()
        
        logger.info(f"MongoDB health check passed. Collections: {len(collections)}")
        return True
        
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        logger.error(f"MongoDB health check failed: {e}")
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
    if check_mongodb_health():
        sys.exit(0)
    else:
        sys.exit(1)
