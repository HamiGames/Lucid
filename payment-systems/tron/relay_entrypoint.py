#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LUCID TRON Relay Service Entrypoint
UTF-8 encoded entrypoint script for distroless container

This service provides READ-ONLY blockchain relay and caching functionality.
It has NO private key access and only serves read operations and verification.

Relay modes:
  - full:      Full relay with all features (default)
  - cache:     Cache-only mode (minimal features)
  - validator: Validation-only mode (transaction verification)
  - monitor:   Monitoring-only mode (observation)
"""

import os
import sys
import logging

# Ensure site-packages and app directory are in Python path
site_packages = '/opt/venv/lib/python3.11/site-packages'
app_dir = '/app'

if site_packages not in sys.path:
    sys.path.insert(0, site_packages)
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def validate_environment():
    """Validate required environment variables for relay service."""
    required_vars = [
        'SERVICE_PORT',
        'TRON_NETWORK',
        'TRON_RPC_URL',
    ]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        return False
    
    return True


def get_relay_config():
    """Extract relay configuration from environment variables."""
    return {
        'port': int(os.getenv('SERVICE_PORT', os.getenv('TRON_RELAY_PORT', '8098'))),
        'host': os.getenv('SERVICE_HOST', '0.0.0.0'),
        'workers': int(os.getenv('WORKERS', '1')),
        'relay_id': os.getenv('RELAY_ID', 'relay-001'),
        'relay_mode': os.getenv('RELAY_MODE', 'full'),
        'tron_network': os.getenv('TRON_NETWORK', 'mainnet'),
        'tron_rpc_url': os.getenv('TRON_RPC_URL', 'https://api.trongrid.io'),
        'cache_enabled': os.getenv('CACHE_ENABLED', 'true').lower() == 'true',
        'cache_ttl': int(os.getenv('CACHE_TTL', '3600')),
        'max_cache_size': int(os.getenv('MAX_CACHE_SIZE', '10000')),
    }


if __name__ == "__main__":
    try:
        # Set SERVICE_NAME for service detection
        os.environ['SERVICE_NAME'] = 'lucid-tron-relay'
        
        # Validate environment
        if not validate_environment():
            sys.exit(1)
        
        # Get relay configuration
        config = get_relay_config()
        
        logger.info(f"Starting LUCID TRON Relay Service")
        logger.info(f"  Relay ID: {config['relay_id']}")
        logger.info(f"  Mode: {config['relay_mode']}")
        logger.info(f"  Network: {config['tron_network']}")
        logger.info(f"  Host: {config['host']}:{config['port']}")
        logger.info(f"  Workers: {config['workers']}")
        logger.info(f"  Cache: {'enabled' if config['cache_enabled'] else 'disabled'}")
        
        # Import required modules
        try:
            import uvicorn
            from main import app
        except ImportError as e:
            logger.error(f"Failed to import required modules: {e}", file=sys.stderr)
            sys.exit(1)
        
        # Start the relay service
        logger.info(f"Binding relay to {config['host']}:{config['port']}")
        uvicorn.run(
            app,
            host=config['host'],
            port=config['port'],
            workers=config['workers'],
            log_level=os.getenv('LOG_LEVEL', 'info').lower()
        )
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
