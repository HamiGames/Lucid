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
import errno

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
        
    def is_port_listening(self, host='127.0.0.1', port=27017, timeout=1):
        """Check if a TCP port is accepting connections"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                result = sock.connect_ex((host, port))
                return result == 0
        except Exception:
            return False

    def cleanup_stale_locks(self):
        """Remove stale mongod locks if no mongod is running"""
        lock_files = [
            self.data_dir / 'mongod.lock',
            self.data_dir / 'WiredTiger.lock'
        ]

        if self.is_port_listening():
            # Another mongod is already listening; do not remove locks
            logger.info("Detected mongod already listening on port 27017; skipping lock cleanup")
            return

        for lock_file in lock_files:
            try:
                if lock_file.exists():
                    lock_file.unlink()
                    logger.warning(f"Removed stale lock file: {lock_file}")
            except Exception as e:
                logger.warning(f"Could not remove lock file {lock_file}: {e}")

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
    
    def wait_for_mongodb(self, max_attempts=60, require_auth=False):
        """Wait for MongoDB to be ready and accepting connections"""
        password = os.getenv('MONGODB_PASSWORD', '')
        host = '127.0.0.1'
        port = int(os.getenv('MONGODB_PORT', '27017'))
        
        logger.info(f"Waiting for MongoDB to be ready (max {max_attempts}s, auth={require_auth})...")
        
        # Track consecutive auth failures for early abort
        consecutive_auth_failures = 0
        max_auth_failures = 5  # Abort after 5 consecutive failures to trigger recovery faster
        
        for attempt in range(max_attempts):
            time.sleep(1)
            
            # Check if process died
            if self.mongod_process and self.mongod_process.poll() is not None:
                exit_code = self.mongod_process.returncode
                logger.error(f"MongoDB process exited with code {exit_code}")
                return False
            
            # First check if port is listening (MongoDB process is running)
            if not self.is_port_listening(host=host, port=port):
                if attempt % 10 == 0:  # Log every 10 seconds
                    logger.info(f"Waiting for MongoDB port {port} to be listening... (attempt {attempt + 1}/{max_attempts})")
                # Reset auth failure counter when port is not listening (MongoDB not started yet)
                consecutive_auth_failures = 0
                continue  # Port not listening yet, keep waiting
            
            # Port is listening, now try to connect
            try:
                if require_auth:
                    if not password:
                        logger.warning("MongoDB requires authentication but MONGODB_PASSWORD is not set")
                        if attempt % 10 == 0:  # Log warning every 10 seconds
                            logger.warning("Waiting for MONGODB_PASSWORD to be set...")
                        continue
                    
                    # Try multiple users (root first, then lucid) - consistent with healthcheck
                    users = ['root', 'lucid']
                    auth_succeeded = False
                    for user in users:
                        try:
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
                            
                            result = subprocess.run(
                                cmd,
                                capture_output=True,
                                text=True,
                                timeout=5
                            )
                            
                            if result.returncode == 0:
                                logger.info(f"MongoDB is ready and accepting connections (user: {user})")
                                return True
                            else:
                                # Log authentication failure details
                                if attempt % 10 == 0:  # Log every 10 seconds to avoid spam
                                    error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()
                                    logger.warning(f"Auth failed for user '{user}': {error_msg}")
                        except subprocess.TimeoutExpired:
                            if attempt % 10 == 0:
                                logger.warning(f"Auth attempt with user {user} timed out")
                            continue  # Try next user
                        except Exception as e:
                            if attempt % 10 == 0:
                                logger.warning(f"Auth attempt with user {user} failed: {e}")
                            continue  # Try next user
                    
                    # If we get here, all auth attempts failed
                    consecutive_auth_failures += 1
                    if consecutive_auth_failures >= max_auth_failures:
                        logger.error(f"Authentication failed {consecutive_auth_failures} times in a row - password mismatch detected")
                        logger.error("MongoDB is running but authentication is failing. This usually means the existing data has a different password.")
                        logger.error("Aborting early to trigger recovery mode to reset password...")
                        return False  # Abort early to trigger recovery
                    
                    if attempt % 10 == 0:
                        logger.warning(f"All authentication attempts failed, retrying... (attempt {attempt + 1}/{max_attempts}, failures: {consecutive_auth_failures}/{max_auth_failures})")
                else:
                    # Connect without authentication
                    cmd = [
                        '/usr/bin/mongosh',
                        '--quiet',
                        '--host', host,
                        '--port', str(port),
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
                        # Reset auth failure counter on successful connection
                        consecutive_auth_failures = 0
                        return True
                    else:
                        # Log connection failure details
                        if attempt % 10 == 0:  # Log every 10 seconds to avoid spam
                            error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()
                            logger.warning(f"Connection failed: {error_msg}")
                        
            except subprocess.TimeoutExpired:
                if attempt % 10 == 0:
                    logger.warning(f"Connection attempt {attempt + 1} timed out")
            except Exception as e:
                if attempt % 10 == 0:
                    logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
        
        logger.error(f"MongoDB did not become ready within {max_attempts} seconds")
        if require_auth and password:
            logger.error("MongoDB may require authentication - check that users exist and password is correct")
        return False
    
    def check_user_exists(self):
        """Check if admin user exists in MongoDB (works with or without auth)"""
        password = os.getenv('MONGODB_PASSWORD', '')
        host = '127.0.0.1'
        port = int(os.getenv('MONGODB_PORT', '27017'))
        
        # First try without auth (if MongoDB was started without --auth)
        try:
            cmd = [
                '/usr/bin/mongosh',
                '--quiet',
                '--host', host,
                '--port', str(port),
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
        except Exception as e:
            logger.debug(f"Check users without auth failed: {e}")
        
        # If that failed, try with auth (MongoDB was started with --auth)
        if password:
            users = ['root', 'lucid']
            for user in users:
                try:
                    cmd = [
                        '/usr/bin/mongosh',
                        '--quiet',
                        '--host', host,
                        '--port', str(port),
                        '--eval', "db.getSiblingDB('admin').getUsers().length",
                        'admin',
                        '-u', user,
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
                        user_count = int(result.stdout.strip())
                        logger.info(f"Found {user_count} user(s) in admin database (via user: {user})")
                        return user_count > 0
                except Exception as e:
                    logger.debug(f"Check users with auth (user: {user}) failed: {e}")
                    continue
        
        return False
    
    def create_admin_user(self):
        """Create admin users (both root and lucid) and ensure lucid_auth database exists"""
        password = os.getenv('MONGODB_PASSWORD', '')
        if not password:
            logger.error("MONGODB_PASSWORD environment variable is not set!")
            logger.error("Please ensure MONGODB_PASSWORD is set in .env.secrets or docker-compose environment")
            return False
        
        host = '127.0.0.1'
        port = int(os.getenv('MONGODB_PORT', '27017'))
        
        logger.info("Creating admin users (root and lucid) in admin database...")
        
        # Escape single quotes in password for JavaScript
        escaped_password = password.replace("'", "\\'").replace("\\", "\\\\")
        
        # Create script that creates both root and lucid users, and ensures lucid_auth database exists
        init_script = f"""
        try {{
            db = db.getSiblingDB('admin');
            
            // Create/update 'root' user (for consistency with healthcheck that tries root first)
            try {{
                var existingRoot = db.getUser('root');
                if (existingRoot) {{
                    print('ℹ️ User root already exists, updating password...');
                    db.changeUserPassword('root', '{escaped_password}');
                    print('✅ User root password updated');
                }} else {{
                    db.createUser({{
                        user: 'root',
                        pwd: '{escaped_password}',
                        roles: [
                            {{ role: 'root', db: 'admin' }}
                        ]
                    }});
                    print('✅ User root created successfully');
                }}
            }} catch (rootError) {{
                // If root user creation fails, try updating password
                try {{
                    db.changeUserPassword('root', '{escaped_password}');
                    print('✅ User root password updated (recovered)');
                }} catch (updateError) {{
                    print('⚠️ Could not create/update root user: ' + rootError.message);
                }}
            }}
            
            // Create/update 'lucid' user (primary user for applications)
            try {{
                var existingLucid = db.getUser('lucid');
                if (existingLucid) {{
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
            }} catch (lucidError) {{
                print('❌ Error creating/updating lucid user: ' + lucidError.message);
                quit(1);
            }}
            
            // Ensure lucid_auth database exists (required by lucid-auth-service)
            // MongoDB creates databases automatically on first write, but we'll create it explicitly
            db = db.getSiblingDB('lucid_auth');
            // Create a dummy collection to ensure database exists
            db.dummy_collection.insertOne({{ _id: 'init', created: new Date() }});
            // Remove the dummy document
            db.dummy_collection.deleteOne({{ _id: 'init' }});
            print('✅ Database lucid_auth ensured to exist');
            
        }} catch (e) {{
            print('❌ Error in initialization script: ' + e.message);
            quit(1);
        }}
        """
        
        try:
            result = subprocess.run(
                [
                    '/usr/bin/mongosh',
                    '--quiet',
                    '--host', host,
                    '--port', str(port),
                    '--eval', init_script
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info("Admin users created/updated successfully")
                if result.stdout:
                    logger.info(result.stdout.strip())
                return True
            else:
                logger.error(f"Failed to create admin users: {result.stderr}")
                if result.stdout:
                    logger.error(f"stdout: {result.stdout}")
                return False
        except Exception as e:
            logger.error(f"Exception while creating admin users: {e}")
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
            # Ensure no stale locks block startup
            self.cleanup_stale_locks()

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
                logger.warning("Failed to start with auth - authentication failures detected")
                logger.warning("This usually means the existing data has a different password than MONGODB_PASSWORD")
                logger.warning("Attempting recovery with localhost bypass to reset password...")
                
                # Start without auth and with localhost bypass to reset password
                if not self.start_mongodb(use_auth=False, bypass_localhost=True):
                    logger.error("Recovery start without auth (localhost bypass) failed")
                    return False
                
                # Create/update user password from MONGODB_PASSWORD
                logger.info("Resetting user passwords to match MONGODB_PASSWORD environment variable...")
                if not self.create_admin_user():
                    logger.error("Failed to reset user passwords during recovery")
                    self.stop_mongodb()
                    return False
                
                # Restart with auth
                logger.info("Restarting MongoDB with authentication enabled after password reset...")
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
