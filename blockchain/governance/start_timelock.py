#!/usr/bin/env python3
"""
Timelock Governance Service Startup Script

This script starts the timelock governance service with proper configuration
and integration with the Lucid RDP blockchain system.

Usage:
    python start_timelock.py [--config CONFIG_FILE] [--output-dir OUTPUT_DIR]

Author: Lucid RDP Team
Version: 1.0.0
"""

import asyncio
import argparse
import logging
import os
import signal
import sys
from pathlib import Path
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient
from timelock import (
    TimelockGovernance,
    TimelockConfig,
    create_timelock_governance,
    cleanup_timelock_governance
)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/data/timelock/timelock.log')
    ]
)

logger = logging.getLogger(__name__)


class TimelockService:
    """Timelock governance service manager"""
    
    def __init__(
        self,
        mongo_uri: str = "mongodb://lucid:lucid@mongo-distroless:27019/lucid?authSource=admin",
        output_dir: str = "/data/timelock",
        config: Optional[TimelockConfig] = None
    ):
        self.mongo_uri = mongo_uri
        self.output_dir = Path(output_dir)
        self.config = config
        self.client: Optional[AsyncIOMotorClient] = None
        self.timelock: Optional[TimelockGovernance] = None
        self.is_running = False
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def start(self) -> bool:
        """Start the timelock service"""
        try:
            logger.info("Starting Timelock Governance Service...")
            
            # Connect to MongoDB
            self.client = AsyncIOMotorClient(self.mongo_uri)
            db = self.client.lucid
            
            # Test connection
            await self.client.admin.command('ping')
            logger.info("Connected to MongoDB successfully")
            
            # Create timelock governance
            self.timelock = create_timelock_governance(
                db=db,
                config=self.config,
                output_dir=str(self.output_dir)
            )
            
            # Start timelock system
            success = await self.timelock.start()
            if not success:
                logger.error("Failed to start timelock governance system")
                return False
            
            self.is_running = True
            logger.info("Timelock Governance Service started successfully")
            
            # Log system stats
            stats = await self.timelock.get_system_stats()
            logger.info(f"System stats: {stats}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start timelock service: {e}")
            return False
    
    async def stop(self) -> None:
        """Stop the timelock service"""
        try:
            logger.info("Stopping Timelock Governance Service...")
            
            self.is_running = False
            
            if self.timelock:
                await self.timelock.stop()
                logger.info("Timelock governance system stopped")
            
            if self.client:
                self.client.close()
                logger.info("MongoDB connection closed")
            
            logger.info("Timelock Governance Service stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping timelock service: {e}")
    
    async def run(self) -> None:
        """Run the service indefinitely"""
        try:
            # Start the service
            if not await self.start():
                return
            
            # Keep running until interrupted
            while self.is_running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Service error: {e}")
        finally:
            await self.stop()


def load_config(config_file: Optional[str]) -> Optional[TimelockConfig]:
    """Load timelock configuration from file"""
    if not config_file or not Path(config_file).exists():
        return None
    
    try:
        import json
        with open(config_file, 'r') as f:
            config_data = json.load(f)
        
        return TimelockConfig(
            min_delay_seconds=config_data.get('min_delay_seconds', 3600),
            max_delay_seconds=config_data.get('max_delay_seconds', 2592000),
            default_grace_period=config_data.get('default_grace_period', 604800),
            max_grace_period=config_data.get('max_grace_period', 2592000),
            admin_addresses=set(config_data.get('admin_addresses', [])),
            emergency_addresses=set(config_data.get('emergency_addresses', [])),
            required_signatures=config_data.get('required_signatures', {})
        )
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return None


def setup_signal_handlers(service: TimelockService) -> None:
    """Setup signal handlers for graceful shutdown"""
    
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        asyncio.create_task(service.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Timelock Governance Service")
    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="/data/timelock",
        help="Output directory for timelock data"
    )
    parser.add_argument(
        "--mongo-uri",
        type=str,
        default=os.getenv(
            "MONGO_URI",
            "mongodb://lucid:lucid@mongo-distroless:27019/lucid?authSource=admin"
        ),
        help="MongoDB connection URI"
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Create service
    service = TimelockService(
        mongo_uri=args.mongo_uri,
        output_dir=args.output_dir,
        config=config
    )
    
    # Setup signal handlers
    setup_signal_handlers(service)
    
    # Run service
    await service.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Service interrupted by user")
    except Exception as e:
        logger.error(f"Service failed: {e}")
        sys.exit(1)
