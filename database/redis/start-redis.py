#!/usr/bin/env python3
"""
Redis Distroless Startup Script
Handles Redis initialization and configuration for distroless container
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
logger = logging.getLogger('redis-distroless')

class RedisDistroless:
    def __init__(self):
        self.redis_process = None
        self.data_dir = Path('/data')
        
    def setup_directories(self):
        """Create necessary directories with proper permissions"""
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {self.data_dir}")
        except Exception as e:
            logger.error(f"Failed to create directory: {e}")
            sys.exit(1)
    
    def get_redis_command(self):
        """Build Redis command with security and performance settings"""
        password = os.getenv('REDIS_PASSWORD', 'changeme')
        max_memory = os.getenv('REDIS_MAX_MEMORY', '512mb')
        max_memory_policy = os.getenv('REDIS_MAX_MEMORY_POLICY', 'allkeys-lru')
        
        cmd = [
            '/usr/bin/redis-server',
            '--requirepass', password,
            '--maxmemory', max_memory,
            '--maxmemory-policy', max_memory_policy,
            '--save', '900', '1',
            '--save', '300', '10',
            '--save', '60', '10000',
            '--appendonly', 'yes',
            '--appendfsync', 'everysec',
            '--dir', str(self.data_dir),
            '--daemonize', 'no'
        ]
        
        return cmd
    
    def start_redis(self):
        """Start Redis with proper configuration"""
        try:
            cmd = self.get_redis_command()
            logger.info(f"Starting Redis with command: {' '.join(cmd)}")
            
            # Start Redis process
            self.redis_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid
            )
            
            # Wait for Redis to start
            time.sleep(3)
            
            if self.redis_process.poll() is None:
                logger.info("Redis started successfully")
                return True
            else:
                logger.error("Redis failed to start")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start Redis: {e}")
            return False
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, shutting down Redis...")
        if self.redis_process:
            self.redis_process.terminate()
            self.redis_process.wait(timeout=30)
        sys.exit(0)
    
    def run(self):
        """Main execution loop"""
        # Set up signal handlers
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        
        # Setup directories
        self.setup_directories()
        
        # Start Redis
        if not self.start_redis():
            logger.error("Failed to start Redis")
            sys.exit(1)
        
        # Keep running
        try:
            while True:
                if self.redis_process and self.redis_process.poll() is not None:
                    logger.error("Redis process died unexpectedly")
                    sys.exit(1)
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received interrupt, shutting down...")
            self.signal_handler(signal.SIGTERM, None)

if __name__ == '__main__':
    redis = RedisDistroless()
    redis.run()
