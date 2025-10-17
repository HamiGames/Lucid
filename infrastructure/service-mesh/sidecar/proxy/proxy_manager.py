"""
Lucid Service Mesh - Sidecar Proxy Manager
Manages Envoy sidecar proxy lifecycle and configuration.

File: infrastructure/service-mesh/sidecar/proxy/proxy_manager.py
Lines: ~350
Purpose: Proxy management
Dependencies: asyncio, subprocess, yaml
"""

import asyncio
import logging
import subprocess
import yaml
import os
import signal
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class ProxyStatus(Enum):
    """Proxy status enumeration."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    FAILED = "failed"


class ProxyManager:
    """
    Envoy sidecar proxy manager.
    
    Handles:
    - Proxy lifecycle management
    - Configuration updates
    - Health monitoring
    - Log management
    """
    
    def __init__(self):
        self.proxy_process: Optional[subprocess.Popen] = None
        self.proxy_status = ProxyStatus.STOPPED
        self.config_path = "/etc/envoy"
        self.log_path = "/var/log/envoy"
        self.admin_port = 15000
        self.proxy_port = 15001
        
        # Proxy configuration
        self.current_config: Dict[str, Any] = {}
        self.config_version = 0
        
    async def initialize(self):
        """Initialize proxy manager."""
        try:
            logger.info("Initializing Proxy Manager...")
            
            # Create necessary directories
            os.makedirs(self.config_path, exist_ok=True)
            os.makedirs(self.log_path, exist_ok=True)
            
            # Load initial configuration
            await self._load_initial_config()
            
            logger.info("Proxy Manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Proxy Manager: {e}")
            raise
            
    async def _load_initial_config(self):
        """Load initial proxy configuration."""
        bootstrap_config_path = os.path.join(self.config_path, "bootstrap.yaml")
        
        if os.path.exists(bootstrap_config_path):
            with open(bootstrap_config_path, 'r') as f:
                self.current_config = yaml.safe_load(f)
        else:
            # Use default configuration
            self._create_default_config()
            
    def _create_default_config(self):
        """Create default proxy configuration."""
        self.current_config = {
            "admin": {
                "address": {
                    "socket_address": {
                        "address": "0.0.0.0",
                        "port_value": self.admin_port
                    }
                }
            },
            "static_resources": {
                "listeners": [],
                "clusters": []
            }
        }
        
    async def start_proxy(self) -> bool:
        """Start the Envoy proxy."""
        try:
            if self.proxy_status == ProxyStatus.RUNNING:
                logger.warning("Proxy is already running")
                return True
                
            logger.info("Starting Envoy proxy...")
            self.proxy_status = ProxyStatus.STARTING
            
            # Write configuration
            await self._write_config()
            
            # Start proxy process
            cmd = [
                "envoy",
                "-c", os.path.join(self.config_path, "bootstrap.yaml"),
                "--log-level", "info",
                "--log-format", "[%Y-%m-%d %T.%e][%t][%l] %v",
                "--log-path", os.path.join(self.log_path, "envoy.log")
            ]
            
            self.proxy_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid
            )
            
            # Wait for proxy to start
            await self._wait_for_proxy_ready()
            
            self.proxy_status = ProxyStatus.RUNNING
            logger.info("Envoy proxy started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start proxy: {e}")
            self.proxy_status = ProxyStatus.FAILED
            return False
            
    async def stop_proxy(self) -> bool:
        """Stop the Envoy proxy."""
        try:
            if self.proxy_status == ProxyStatus.STOPPED:
                logger.warning("Proxy is already stopped")
                return True
                
            logger.info("Stopping Envoy proxy...")
            self.proxy_status = ProxyStatus.STOPPING
            
            if self.proxy_process:
                # Send SIGTERM to process group
                os.killpg(os.getpgid(self.proxy_process.pid), signal.SIGTERM)
                
                # Wait for graceful shutdown
                try:
                    self.proxy_process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    # Force kill if graceful shutdown fails
                    os.killpg(os.getpgid(self.proxy_process.pid), signal.SIGKILL)
                    self.proxy_process.wait()
                    
                self.proxy_process = None
                
            self.proxy_status = ProxyStatus.STOPPED
            logger.info("Envoy proxy stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop proxy: {e}")
            self.proxy_status = ProxyStatus.FAILED
            return False
            
    async def restart_proxy(self) -> bool:
        """Restart the Envoy proxy."""
        logger.info("Restarting Envoy proxy...")
        
        # Stop proxy
        if not await self.stop_proxy():
            return False
            
        # Wait a moment
        await asyncio.sleep(2)
        
        # Start proxy
        return await self.start_proxy()
        
    async def update_config(self, new_config: Dict[str, Any]) -> bool:
        """Update proxy configuration."""
        try:
            logger.info("Updating proxy configuration...")
            
            # Validate configuration
            if not self._validate_config(new_config):
                logger.error("Invalid configuration provided")
                return False
                
            # Update configuration
            self.current_config = new_config
            self.config_version += 1
            
            # Write new configuration
            await self._write_config()
            
            # Reload proxy if running
            if self.proxy_status == ProxyStatus.RUNNING:
                await self._reload_proxy()
                
            logger.info("Proxy configuration updated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update configuration: {e}")
            return False
            
    def _validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate proxy configuration."""
        try:
            # Basic validation
            if not isinstance(config, dict):
                return False
                
            # Check required sections
            if "static_resources" not in config:
                return False
                
            return True
            
        except Exception:
            return False
            
    async def _write_config(self):
        """Write configuration to file."""
        config_file = os.path.join(self.config_path, "bootstrap.yaml")
        
        with open(config_file, 'w') as f:
            yaml.dump(self.current_config, f, default_flow_style=False)
            
    async def _reload_proxy(self):
        """Reload proxy configuration."""
        try:
            # Send SIGHUP to reload configuration
            if self.proxy_process:
                os.kill(self.proxy_process.pid, signal.SIGHUP)
                logger.info("Proxy configuration reloaded")
                
        except Exception as e:
            logger.error(f"Failed to reload proxy: {e}")
            
    async def _wait_for_proxy_ready(self, timeout: int = 30):
        """Wait for proxy to be ready."""
        start_time = datetime.utcnow()
        
        while (datetime.utcnow() - start_time).total_seconds() < timeout:
            try:
                # Check if process is still running
                if self.proxy_process and self.proxy_process.poll() is not None:
                    raise Exception("Proxy process exited unexpectedly")
                    
                # Check admin endpoint
                if await self._check_admin_endpoint():
                    return
                    
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error waiting for proxy ready: {e}")
                raise
                
        raise Exception("Timeout waiting for proxy to be ready")
        
    async def _check_admin_endpoint(self) -> bool:
        """Check if admin endpoint is responding."""
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"http://localhost:{self.admin_port}/ready",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    return response.status == 200
                    
        except Exception:
            return False
            
    async def get_proxy_stats(self) -> Dict[str, Any]:
        """Get proxy statistics."""
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"http://localhost:{self.admin_port}/stats",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        stats_text = await response.text()
                        return self._parse_stats(stats_text)
                        
        except Exception as e:
            logger.error(f"Failed to get proxy stats: {e}")
            
        return {}
        
    def _parse_stats(self, stats_text: str) -> Dict[str, Any]:
        """Parse Envoy stats text into dictionary."""
        stats = {}
        
        for line in stats_text.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                stats[key.strip()] = value.strip()
                
        return stats
        
    async def get_proxy_config(self) -> Dict[str, Any]:
        """Get current proxy configuration."""
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"http://localhost:{self.admin_port}/config_dump",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                        
        except Exception as e:
            logger.error(f"Failed to get proxy config: {e}")
            
        return {}
        
    def get_proxy_status(self) -> Dict[str, Any]:
        """Get proxy status information."""
        return {
            "status": self.proxy_status.value,
            "pid": self.proxy_process.pid if self.proxy_process else None,
            "config_version": self.config_version,
            "admin_port": self.admin_port,
            "proxy_port": self.proxy_port,
            "config_path": self.config_path,
            "log_path": self.log_path,
            "last_update": datetime.utcnow().isoformat()
        }
        
    async def cleanup(self):
        """Cleanup proxy manager."""
        logger.info("Cleaning up Proxy Manager...")
        
        if self.proxy_status == ProxyStatus.RUNNING:
            await self.stop_proxy()
