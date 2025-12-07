#!/usr/bin/env python3
"""
Redis Distroless Startup Script
Handles Redis initialization and configuration for distroless container
FIXED: Uses REDIS_PASSWORD from environment variables (no hardcoded passwords)
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
        """Build Redis command with security and performance settings from environment"""
        # CRITICAL: Read password from environment variable (from .env.* files)
        password = os.getenv('REDIS_PASSWORD', '')
        if not password:
            logger.error("REDIS_PASSWORD environment variable is not set!")
            logger.error("Please ensure REDIS_PASSWORD is set in .env.secrets or docker-compose environment")
            sys.exit(1)
        
        max_memory = os.getenv('REDIS_MAX_MEMORY', '512mb')
        max_memory_policy = os.getenv('REDIS_MAX_MEMORY_POLICY', 'allkeys-lru')
        port = os.getenv('REDIS_PORT', '6379')
        host = os.getenv('REDIS_HOST', '0.0.0.0')
        
        # Build command using template config and override with command-line args
        cmd = [
            '/usr/local/bin/redis-server',
            '/etc/redis.conf.template',  # Use template config
            '--port', port,
            '--bind', host,
            '--requirepass', password,  # Password from environment
            '--maxmemory', max_memory,
            '--maxmemory-policy', max_memory_policy,
            '--save', '900', '1',
            '--save', '300', '10',
            '--save', '60', '10000',
            '--appendonly', 'yes',
            '--appendfsync', 'everysec',
            '--dir', str(self.data_dir),
            '--daemonize', 'no',
            '--protected-mode', 'yes'  # Enable protected mode with password
        ]
        
        logger.info(f"Redis will start on {host}:{port} with password authentication enabled")
        # Don't log the actual password
        logger.info(f"REDIS_PASSWORD is {'*' * min(len(password), 8)} (hidden)")
        
        return cmd
    
    def start_redis(self):
        """Start Redis with proper configuration"""
        try:
            cmd = self.get_redis_command()
            logger.info(f"Starting Redis server...")
            
            # Start Redis process (foreground, no daemonize)
            self.redis_process = subprocess.Popen(
                cmd,
                stdout=sys.stdout,
                stderr=sys.stderr
            )
            
            # Wait for Redis to start and verify it's listening
            import socket
            port = int(os.getenv('REDIS_PORT', '6379'))
            max_attempts = 10
            for attempt in range(max_attempts):
                time.sleep(1)
                
                # Check if process died
                if self.redis_process.poll() is not None:
                    exit_code = self.redis_process.returncode
                    logger.error(f"Redis process exited with code {exit_code}")
                    return False
                
                # Check if Redis is listening on port
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1)
                    result = sock.connect_ex(('127.0.0.1', port))
                    sock.close()
                    if result == 0:
                        logger.info(f"Redis started successfully and is listening on port {port}")
                        return True
                except Exception as e:
                    logger.debug(f"Connection check attempt {attempt + 1} failed: {e}")
            
            logger.error(f"Redis did not start within {max_attempts} seconds")
            return False
                
        except Exception as e:
            logger.error(f"Failed to start Redis: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, shutting down Redis...")
        if self.redis_process:
            self.redis_process.terminate()
            try:
                self.redis_process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                logger.warning("Redis did not terminate gracefully, forcing...")
                self.redis_process.kill()
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
        
        # Keep running and forward output
        try:
            # Wait for process to exit
            exit_code = self.redis_process.wait()
            logger.error(f"Redis process exited with code {exit_code}")
            sys.exit(exit_code)
        except KeyboardInterrupt:
            logger.info("Received interrupt, shutting down...")
            self.signal_handler(signal.SIGTERM, None)

if __name__ == '__main__':
    redis = RedisDistroless()
    redis.run()
