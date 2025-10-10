# Path: gui/core/tor_client.py
"""
Tor integration and SOCKS5 proxy management for Lucid RDP GUI.
Provides secure Tor connectivity with health checks and process management.
"""

import os
import sys
import time
import signal
import subprocess
import threading
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import socket
import requests
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class TorStatus(Enum):
    """Tor process status"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    FAILED = "failed"
    STOPPING = "stopping"


@dataclass
class TorConfig:
    """Tor configuration parameters"""
    socks_port: int = 9150
    control_port: int = 9151
    data_directory: Optional[Path] = None
    torrc_path: Optional[Path] = None
    tor_binary_path: Optional[Path] = None
    cookie_auth: bool = True
    isolate_socks_auth: bool = True
    allow_single_hop_exits: bool = False
    exit_nodes: Optional[List[str]] = None
    strict_nodes: bool = False
    enforce_distinct_subnets: bool = True


class TorConnectionError(Exception):
    """Tor connection related errors"""
    pass


class TorClient:
    """
    Tor client manager for GUI applications.
    
    Handles Tor process lifecycle, health checks, and SOCKS5 proxy management.
    Enforces Tor-only connectivity with fail-closed behavior.
    """
    
    def __init__(self, config: Optional[TorConfig] = None):
        self.config = config or TorConfig()
        self.process: Optional[subprocess.Popen] = None
        self.status = TorStatus.STOPPED
        self._status_lock = threading.Lock()
        self._startup_timeout = 30  # seconds
        self._health_check_interval = 5  # seconds
        self._health_check_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        
        # Setup data directory
        if not self.config.data_directory:
            self.config.data_directory = Path.home() / ".lucid" / "tor"
        
        self.config.data_directory.mkdir(parents=True, exist_ok=True)
        
        # Setup torrc
        if not self.config.torrc_path:
            self.config.torrc_path = self.config.data_directory / "torrc"
        
        logger.info(f"Tor client initialized with data directory: {self.config.data_directory}")
    
    def start(self) -> bool:
        """
        Start Tor process with configured parameters.
        
        Returns:
            True if Tor started successfully, False otherwise
        """
        with self._status_lock:
            if self.status in [TorStatus.RUNNING, TorStatus.STARTING]:
                logger.warning("Tor is already running or starting")
                return self.status == TorStatus.RUNNING
            
            self.status = TorStatus.STARTING
        
        try:
            # Find Tor binary
            tor_binary = self._find_tor_binary()
            if not tor_binary:
                raise TorConnectionError("Tor binary not found")
            
            # Create torrc configuration
            self._create_torrc()
            
            # Start Tor process
            self._start_tor_process(tor_binary)
            
            # Wait for startup
            if self._wait_for_startup():
                self._start_health_monitoring()
                logger.info("Tor started successfully")
                return True
            else:
                self._stop_tor_process()
                return False
                
        except Exception as e:
            logger.error(f"Failed to start Tor: {e}")
            with self._status_lock:
                self.status = TorStatus.FAILED
            return False
    
    def stop(self) -> bool:
        """
        Stop Tor process gracefully.
        
        Returns:
            True if Tor stopped successfully, False otherwise
        """
        with self._status_lock:
            if self.status == TorStatus.STOPPED:
                return True
            
            self.status = TorStatus.STOPPING
        
        try:
            # Signal health monitoring to stop
            self._shutdown_event.set()
            
            # Stop Tor process
            self._stop_tor_process()
            
            with self._status_lock:
                self.status = TorStatus.STOPPED
            
            logger.info("Tor stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop Tor: {e}")
            with self._status_lock:
                self.status = TorStatus.FAILED
            return False
    
    def is_running(self) -> bool:
        """Check if Tor is running and healthy"""
        with self._status_lock:
            return self.status == TorStatus.RUNNING
    
    def get_socks_proxy(self) -> str:
        """
        Get SOCKS5 proxy string for Tor connection.
        
        Returns:
            SOCKS5 proxy string in format 'socks5://127.0.0.1:port'
        """
        if not self.is_running():
            raise TorConnectionError("Tor is not running")
        
        return f"socks5://127.0.0.1:{self.config.socks_port}"
    
    def test_connection(self) -> bool:
        """
        Test Tor connection by making a request through SOCKS5 proxy.
        
        Returns:
            True if connection test successful, False otherwise
        """
        try:
            if not self.is_running():
                return False
            
            # Test with a simple HTTP request through Tor
            proxies = {
                'http': self.get_socks_proxy(),
                'https': self.get_socks_proxy()
            }
            
            # Use a test endpoint that should work through Tor
            response = requests.get(
                'https://httpbin.org/ip',
                proxies=proxies,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.debug("Tor connection test successful")
                return True
            else:
                logger.warning(f"Tor connection test failed: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.warning(f"Tor connection test failed: {e}")
            return False
    
    def _find_tor_binary(self) -> Optional[Path]:
        """Find Tor binary on the system"""
        if self.config.tor_binary_path and self.config.tor_binary_path.exists():
            return self.config.tor_binary_path
        
        # Common Tor binary locations
        possible_paths = [
            Path("tor"),  # In PATH
            Path("/usr/bin/tor"),
            Path("/usr/local/bin/tor"),
            Path("/opt/homebrew/bin/tor"),  # macOS Homebrew
            Path("C:/Program Files/Tor/tor.exe"),  # Windows
            Path("C:/Program Files (x86)/Tor/tor.exe"),  # Windows 32-bit
        ]
        
        for path in possible_paths:
            try:
                if path.name == "tor" and not path.is_absolute():
                    # Check if tor is in PATH
                    result = subprocess.run(
                        ["which", "tor"] if sys.platform != "win32" else ["where", "tor"],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        return Path(result.stdout.strip())
                elif path.exists():
                    return path
            except Exception:
                continue
        
        return None
    
    def _create_torrc(self) -> None:
        """Create Tor configuration file"""
        torrc_content = f"""# Lucid RDP Tor Configuration
# Generated automatically - do not edit manually

# Network settings
SOCKSPort {self.config.socks_port}
ControlPort {self.config.control_port}

# Authentication
CookieAuthentication {'1' if self.config.cookie_auth else '0'}
CookieAuthFile {self.config.data_directory / 'control_auth_cookie'}

# Security settings
IsolateSOCKSAuth {'1' if self.config.isolate_socks_auth else '0'}
AllowSingleHopExits {'1' if self.config.allow_single_hop_exits else '0'}
EnforceDistinctSubnets {'1' if self.config.enforce_distinct_subnets else '0'}

# Data directory
DataDirectory {self.config.data_directory}

# Logging
Log notice file {self.config.data_directory / 'tor.log'}

# Exit policy
ExitPolicy reject *:*

# Circuit build timeout
CircuitBuildTimeout 10
LearnCircuitBuildTimeout 0
"""

        # Add exit nodes if specified
        if self.config.exit_nodes:
            torrc_content += f"\n# Exit nodes\nExitNodes {','.join(self.config.exit_nodes)}\n"
            if self.config.strict_nodes:
                torrc_content += "StrictNodes 1\n"
        
        # Write torrc file
        with open(self.config.torrc_path, 'w') as f:
            f.write(torrc_content)
        
        logger.debug(f"Created torrc at: {self.config.torrc_path}")
    
    def _start_tor_process(self, tor_binary: Path) -> None:
        """Start Tor process"""
        cmd = [
            str(tor_binary),
            "-f", str(self.config.torrc_path)
        ]
        
        # Start process
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(self.config.data_directory)
        )
        
        logger.debug(f"Started Tor process with PID: {self.process.pid}")
    
    def _stop_tor_process(self) -> None:
        """Stop Tor process"""
        if self.process:
            try:
                # Try graceful shutdown first
                self.process.terminate()
                
                # Wait for graceful shutdown
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    # Force kill if graceful shutdown fails
                    logger.warning("Tor process did not stop gracefully, forcing kill")
                    self.process.kill()
                    self.process.wait()
                
                logger.debug("Tor process stopped")
                
            except Exception as e:
                logger.error(f"Error stopping Tor process: {e}")
            finally:
                self.process = None
    
    def _wait_for_startup(self) -> bool:
        """Wait for Tor to start up and become ready"""
        start_time = time.time()
        
        while time.time() - start_time < self._startup_timeout:
            if self.process and self.process.poll() is not None:
                # Process has terminated
                logger.error("Tor process terminated during startup")
                return False
            
            # Check if SOCKS port is listening
            if self._check_socks_port():
                with self._status_lock:
                    self.status = TorStatus.RUNNING
                return True
            
            time.sleep(1)
        
        logger.error("Tor startup timeout")
        return False
    
    def _check_socks_port(self) -> bool:
        """Check if SOCKS port is listening"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', self.config.socks_port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    def _start_health_monitoring(self) -> None:
        """Start background health monitoring thread"""
        self._health_check_thread = threading.Thread(
            target=self._health_monitor_loop,
            daemon=True
        )
        self._health_check_thread.start()
    
    def _health_monitor_loop(self) -> None:
        """Background health monitoring loop"""
        while not self._shutdown_event.is_set():
            try:
                if not self._check_socks_port():
                    logger.warning("Tor SOCKS port not responding")
                    with self._status_lock:
                        if self.status == TorStatus.RUNNING:
                            self.status = TorStatus.FAILED
                    break
                
                # Test connection periodically
                if not self.test_connection():
                    logger.warning("Tor connection test failed")
                    with self._status_lock:
                        if self.status == TorStatus.RUNNING:
                            self.status = TorStatus.FAILED
                    break
                
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
            
            # Wait for next check or shutdown signal
            if self._shutdown_event.wait(self._health_check_interval):
                break
        
        logger.debug("Health monitoring stopped")
    
    @contextmanager
    def ensure_running(self):
        """Context manager to ensure Tor is running"""
        was_running = self.is_running()
        
        if not was_running:
            if not self.start():
                raise TorConnectionError("Failed to start Tor")
        
        try:
            yield self
        finally:
            if not was_running:
                self.stop()


# Global Tor client instance
_tor_client: Optional[TorClient] = None


def get_tor_client(config: Optional[TorConfig] = None) -> TorClient:
    """Get global Tor client instance"""
    global _tor_client
    
    if _tor_client is None:
        _tor_client = TorClient(config)
    
    return _tor_client


def cleanup_tor_client() -> None:
    """Cleanup global Tor client"""
    global _tor_client
    
    if _tor_client:
        _tor_client.stop()
        _tor_client = None


# Signal handlers for graceful shutdown
def _signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down Tor client")
    cleanup_tor_client()
    sys.exit(0)


# Register signal handlers
if sys.platform != "win32":
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)
