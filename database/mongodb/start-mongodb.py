#!/usr/bin/env python3
"""
MongoDB Distroless Startup Script
Handles MongoDB initialization and configuration for distroless container
CRITICAL: Automatically creates admin user on first run if users don't exist
FIXED: Uses MONGODB_PASSWORD from environment variables (no hardcoded passwords)
"""

import os
import sys
import subprocess
import signal
import time
import logging
import socket
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
        self.log_dir = Path('/var/log/mongodb')
        
    def setup_directories(self):
        """Create necessary directories with proper permissions"""
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self.log_dir.mkdir(parents=True, exist_ok=True)
            # Ensure directories are writable by nonroot user (65532)
            try:
                os.chmod(str(self.data_dir), 0o755)
                os.chmod(str(self.log_dir), 0o755)
            except PermissionError:
                logger.warning(f"Could not set permissions on directories, may cause issues")
            logger.info(f"Created directories: {self.data_dir}, {self.log_dir}")
        except Exception as e:
            logger.error(f"Failed to create directories: {e}")
            sys.exit(1)
    
    def is_data_directory_empty(self):
        """Check if MongoDB data directory is empty (first run)"""
        try:
            if not self.data_dir.exists():
                return True
            # Check if directory has any files (ignore .keep or similar markers)
            contents = list(self.data_dir.iterdir())
            # If only hidden/system files, consider it empty
            meaningful_files = [f for f in contents if not f.name.startswith('.')]
            return len(meaningful_files) == 0
        except Exception as e:
            logger.warning(f"Error checking data directory: {e}")
            return False
    
    def wait_for_mongodb(self, max_attempts=30, require_auth=False):
        """Wait for MongoDB to be ready and accepting connections"""
        password = os.getenv('MONGODB_PASSWORD', '')
        
        for attempt in range(max_attempts):
            time.sleep(1)
            
            # Check if process died
            if self.mongod_process and self.mongod_process.poll() is not None:
                exit_code = self.mongod_process.returncode
                logger.error(f"MongoDB process exited with code {exit_code}")
                return False
            
            # Try to connect with mongosh
            try:
                if require_auth and password:
                    # Connect with authentication
                    cmd = [
                        '/usr/bin/mongosh',
                        '--quiet',
                        '--eval', 'db.runCommand({ ping: 1 })',
                        '-u', 'lucid',
                        '-p', password,
                        '--authenticationDatabase', 'admin'
                    ]
                else:
                    # Connect without authentication
                    cmd = [
                        '/usr/bin/mongosh',
                        '--quiet',
                        '--eval', 'db.runCommand({ ping: 1 })'
                    ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    logger.info("MongoDB is ready and accepting connections")
                    return True
                    
            except subprocess.TimeoutExpired:
                logger.debug(f"Connection attempt {attempt + 1} timed out")
            except Exception as e:
                logger.debug(f"Connection attempt {attempt + 1} failed: {e}")
        
        logger.warning(f"MongoDB did not become ready within {max_attempts} seconds")
        return False
    
    def check_user_exists(self):
        """Check if admin user exists in MongoDB"""
        try:
            # Try to list users (without auth first, then with auth)
            cmd = [
                '/usr/bin/mongosh',
                '--quiet',
                '--eval', "db.getSiblingDB('admin').getUsers().length",
                'admin'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                user_count = int(result.stdout.strip())
                logger.info(f"Found {user_count} user(s) in admin database")
                return user_count > 0
            return False
        except Exception as e:
            logger.debug(f"Error checking users: {e}")
            return False
    
    def create_admin_user(self):
        """Create admin user from environment variables"""
        password = os.getenv('MONGODB_PASSWORD', '')
        if not password:
            logger.error("MONGODB_PASSWORD environment variable is not set!")
            logger.error("Please ensure MONGODB_PASSWORD is set in .env.secrets or docker-compose environment")
            return False
        
        logger.info("Creating admin user 'lucid' in admin database...")
        
        # Escape single quotes in password for JavaScript
        escaped_password = password.replace("'", "\\'").replace("\\", "\\\\")
        
        init_script = f"""
        try {{
            db = db.getSiblingDB('admin');
            
            // Check if user already exists
            var existingUser = db.getUser('lucid');
            if (existingUser) {{
                print('ℹ️ User lucid already exists, updating password...');
                db.changeUserPassword('lucid', '{escaped_password}');
                print('✅ User lucid password updated');
            }} else {{
                db.createUser({{
                    user: 'lucid',
                    pwd: '{escaped_password}',
                    roles: [
                        {{ role: 'userAdminAnyDatabase', db: 'admin' }},
                        {{ role: 'readWriteAnyDatabase', db: 'admin' }},
                        {{ role: 'dbAdminAnyDatabase', db: 'admin' }},
                        {{ role: 'clusterAdmin', db: 'admin' }}
                    ]
                }});
                print('✅ User lucid created successfully');
            }}
        }} catch (e) {{
            print('❌ Error creating/updating user: ' + e.message);
            quit(1);
        }}
        """
        
        try:
            result = subprocess.run(
                ['/usr/bin/mongosh', '--quiet', '--eval', init_script],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info("Admin user created/updated successfully")
                if result.stdout:
                    logger.info(result.stdout.strip())
                return True
            else:
                logger.error(f"Failed to create admin user: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Exception while creating admin user: {e}")
            return False
    
    def get_mongod_command(self, use_auth=True, bypass_localhost=False):
        """Build MongoDB command with security and performance settings"""
        cmd = [
            '/usr/bin/mongod',
            '--bind_ip_all',
            '--dbpath', str(self.data_dir),
            '--logpath', str(self.log_dir / 'mongod.log'),
            '--logappend'
        ]
        
        if use_auth:
            cmd.append('--auth')

        if bypass_localhost:
            # Allow localhost bypass temporarily to reset credentials
            cmd.extend(['--setParameter', 'enableLocalhostAuthBypass=true'])
        
        # Add replica set if enabled (default: false for single-node deployments)
        # MongoDB requires keyFile when using auth + replica sets, which adds complexity
        # For single-node foundation deployments, replica sets are disabled by default
        # For multi-node deployments, enable via MONGODB_REPLICA_SET_ENABLED=true
        if os.getenv('MONGODB_REPLICA_SET_ENABLED', 'false').lower() == 'true':
            repl_set = os.getenv('MONGODB_REPLICA_SET', 'lucid-rs')
            cmd.extend(['--replSet', repl_set])
        
        return cmd
    
    def start_mongodb(self, use_auth=True, bypass_localhost=False):
        """Start MongoDB with proper configuration"""
        try:
            cmd = self.get_mongod_command(use_auth=use_auth, bypass_localhost=bypass_localhost)
            if bypass_localhost and not use_auth:
                auth_status = "without authentication (localhost bypass for recovery)"
            elif use_auth:
                auth_status = "with authentication"
            else:
                auth_status = "without authentication (initialization mode)"
            logger.info(f"Starting MongoDB {auth_status}...")
            logger.debug(f"Command: {' '.join(cmd)}")
            
            # Start MongoDB process (foreground, no fork)
            self.mongod_process = subprocess.Popen(
                cmd,
                stdout=sys.stdout,
                stderr=sys.stderr
            )
            
            # Wait for MongoDB to be ready
            if not self.wait_for_mongodb(require_auth=use_auth):
                logger.error("MongoDB failed to become ready")
                return False
            
            logger.info("MongoDB started successfully")
            return True
                
        except Exception as e:
            logger.error(f"Failed to start MongoDB: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def stop_mongodb(self, timeout=30):
        """Stop MongoDB gracefully"""
        if not self.mongod_process:
            return True
        
        logger.info("Stopping MongoDB...")
        try:
            # Send SIGTERM to mongod process
            self.mongod_process.terminate()
            
            # Wait for process to terminate
            try:
                self.mongod_process.wait(timeout=timeout)
                logger.info("MongoDB stopped gracefully")
                return True
            except subprocess.TimeoutExpired:
                logger.warning("MongoDB did not stop within timeout, forcing...")
                self.mongod_process.kill()
                self.mongod_process.wait()
                return True
        except Exception as e:
            logger.error(f"Error stopping MongoDB: {e}")
            return False
    
    def initialize_mongodb(self):
        """Initialize MongoDB: check if users exist, create if needed, restart with auth"""
        # Check if this is a fresh installation
        is_empty = self.is_data_directory_empty()
        logger.info(f"MongoDB data directory is {'empty' if is_empty else 'populated'}")
        
        # If data is empty, we need to create the user
        if is_empty:
            logger.info("First run detected - initializing MongoDB with admin user...")
            
            # Start MongoDB without auth
            if not self.start_mongodb(use_auth=False):
                logger.error("Failed to start MongoDB without auth for initialization")
                return False
            
            # Wait a bit more to ensure MongoDB is fully ready
            time.sleep(2)
            
            # Create admin user
            if not self.create_admin_user():
                logger.error("Failed to create admin user")
                self.stop_mongodb()
                return False
            
            # Stop MongoDB
            logger.info("Stopping MongoDB to restart with authentication...")
            if not self.stop_mongodb():
                logger.error("Failed to stop MongoDB after initialization")
                return False
            
            # Wait for process to fully stop
            time.sleep(2)
            self.mongod_process = None
            
            # Restart MongoDB with auth
            logger.info("Restarting MongoDB with authentication enabled...")
            return self.start_mongodb(use_auth=True)
        
        else:
            # Data exists - check if users exist
            logger.info("Existing data detected - checking if users exist...")
            
            # Try starting with auth first
            if self.start_mongodb(use_auth=True):
                # Check if we can connect (users exist)
                time.sleep(2)
                if self.check_user_exists():
                    logger.info("Users exist - MongoDB started successfully with authentication")
                    return True
                else:
                    logger.warning("No users found in existing data - initializing users...")
                    # Stop and restart without auth to create users
                    self.stop_mongodb()
                    time.sleep(2)
                    self.mongod_process = None
                    
                    # Start without auth
                    if not self.start_mongodb(use_auth=False):
                        return False
                    
                    # Create user
                    if not self.create_admin_user():
                        self.stop_mongodb()
                        return False
                    
                    # Restart with auth
                    self.stop_mongodb()
                    time.sleep(2)
                    self.mongod_process = None
                    return self.start_mongodb(use_auth=True)
            else:
                # Couldn't start with auth - likely password mismatch in existing data
                logger.warning("Failed to start with auth - attempting recovery with localhost bypass...")
                
                # Start without auth and with localhost bypass to reset password
                if not self.start_mongodb(use_auth=False, bypass_localhost=True):
                    logger.error("Recovery start without auth (localhost bypass) failed")
                    return False
                
                # Create/update user password from MONGODB_PASSWORD
                if not self.create_admin_user():
                    self.stop_mongodb()
                    return False
                
                # Restart with auth
                self.stop_mongodb()
                time.sleep(2)
                self.mongod_process = None
                return self.start_mongodb(use_auth=True)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, shutting down MongoDB...")
        self.stop_mongodb()
        sys.exit(0)
    
    def run(self):
        """Main execution loop"""
        # Set up signal handlers
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        
        # Setup directories
        self.setup_directories()
        
        # Initialize MongoDB (create users if needed)
        if not self.initialize_mongodb():
            logger.error("Failed to initialize MongoDB")
            sys.exit(1)
        
        # Keep running and forward output
        try:
            # Wait for process to exit
            exit_code = self.mongod_process.wait()
            logger.error(f"MongoDB process exited with code {exit_code}")
            sys.exit(exit_code)
        except KeyboardInterrupt:
            logger.info("Received interrupt, shutting down...")
            self.signal_handler(signal.SIGTERM, None)

if __name__ == '__main__':
    mongodb = MongoDBDistroless()
    mongodb.run()
