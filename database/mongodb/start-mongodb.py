#!/usr/bin/env python3
"""
MongoDB Distroless Startup Script
Handles MongoDB initialization and configuration for distroless container
"""

import os
import sys
import subprocess
import signal
import time
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('mongodb-distroless')

class MongoDBDistroless:
    def __init__(self):
        self.mongod_process = None
        self.data_dir = Path('/data/db')
        self.config_dir = Path('/data/configdb')
        
    def setup_directories(self):
        """Create necessary directories with proper permissions"""
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self.config_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directories: {self.data_dir}, {self.config_dir}")
        except Exception as e:
            logger.error(f"Failed to create directories: {e}")
            sys.exit(1)
    
    def get_mongod_command(self):
        """Build MongoDB command with security and performance settings"""
        cmd = [
            '/usr/bin/mongod',
            '--auth',
            '--bind_ip_all',
            '--replSet', 'rs0',
            '--oplogSize', '128',
            '--wiredTigerCacheSizeGB', '0.5',
            '--dbpath', str(self.data_dir),
            '--configdb', str(self.config_dir),
            '--logpath', '/var/log/mongodb/mongod.log',
            '--fork'
        ]
        
        # Add environment-based configuration
        if os.getenv('MONGODB_REPLICA_SET_ENABLED', 'true').lower() == 'true':
            cmd.extend(['--replSet', os.getenv('MONGODB_REPLICA_SET', 'rs0')])
        
        return cmd
    
    def start_mongodb(self):
        """Start MongoDB with proper configuration"""
        try:
            cmd = self.get_mongod_command()
            logger.info(f"Starting MongoDB with command: {' '.join(cmd)}")
            
            # Start MongoDB process
            self.mongod_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid
            )
            
            # Wait for MongoDB to start
            time.sleep(5)
            
            if self.mongod_process.poll() is None:
                logger.info("MongoDB started successfully")
                return True
            else:
                logger.error("MongoDB failed to start")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start MongoDB: {e}")
            return False
    
    def initialize_replica_set(self):
        """Initialize MongoDB replica set if needed"""
        try:
            # Wait for MongoDB to be ready
            time.sleep(10)
            
            # Initialize replica set
            init_script = """
            rs.initiate({
                _id: "rs0",
                members: [
                    { _id: 0, host: "localhost:27017" }
                ]
            })
            """
            
            result = subprocess.run(
                ['/usr/bin/mongosh', '--eval', init_script],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info("Replica set initialized successfully")
            else:
                logger.warning(f"Replica set initialization warning: {result.stderr}")
                
        except Exception as e:
            logger.warning(f"Replica set initialization failed: {e}")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, shutting down MongoDB...")
        if self.mongod_process:
            self.mongod_process.terminate()
            self.mongod_process.wait(timeout=30)
        sys.exit(0)
    
    def run(self):
        """Main execution loop"""
        # Set up signal handlers
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        
        # Setup directories
        self.setup_directories()
        
        # Start MongoDB
        if not self.start_mongodb():
            logger.error("Failed to start MongoDB")
            sys.exit(1)
        
        # Initialize replica set
        self.initialize_replica_set()
        
        # Keep running
        try:
            while True:
                if self.mongod_process and self.mongod_process.poll() is not None:
                    logger.error("MongoDB process died unexpectedly")
                    sys.exit(1)
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received interrupt, shutting down...")
            self.signal_handler(signal.SIGTERM, None)

if __name__ == '__main__':
    mongodb = MongoDBDistroless()
    mongodb.run()
