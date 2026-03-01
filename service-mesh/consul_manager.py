"""
Consul service discovery manager

File: service-mesh/consul_manager.py
"""

import asyncio
import logging
import json
import os
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Optional consul import
try:
    import consul
    CONSUL_AVAILABLE = True
except ImportError:
    CONSUL_AVAILABLE = False
    logger.warning("consul package not available")


class ConsulManager:
    """Consul service discovery manager"""
    
    def __init__(self, settings):
        self.settings = settings
        self.consul_client = None
        self.consul_process = None
        
    async def initialize(self):
        """Initialize Consul manager"""
        try:
            if not CONSUL_AVAILABLE:
                logger.warning("Consul library not available, running in mock mode")
                return
            
            # Start Consul server if binary exists
            consul_binary = "/usr/local/bin/consul"
            if os.path.exists(consul_binary):
                await self._start_consul_server()
            
            # Initialize Consul client
            self.consul_client = consul.Consul(
                host=self.settings.CONSUL_HOST,
                port=self.settings.CONSUL_PORT
            )
            
            # Wait for Consul to be ready
            await self._wait_for_consul_ready()
            
            logger.info("Consul manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Consul manager: {e}")
            # Don't raise - allow service to run without Consul
            logger.warning("Running without Consul integration")
    
    async def cleanup(self):
        """Cleanup Consul manager"""
        if self.consul_process:
            self.consul_process.terminate()
            try:
                await asyncio.wait_for(self.consul_process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.consul_process.kill()
        logger.info("Consul manager cleaned up")
    
    async def _start_consul_server(self):
        """Start Consul server"""
        consul_config = {
            "datacenter": self.settings.CONSUL_DATACENTER,
            "data_dir": "/tmp/consul",
            "log_level": self.settings.LOG_LEVEL,
            "server": True,
            "bootstrap_expect": self.settings.CONSUL_BOOTSTRAP_EXPECT,
            "bind_addr": "0.0.0.0",
            "client_addr": "0.0.0.0",
            "ui_config": {
                "enabled": self.settings.CONSUL_UI_ENABLED
            }
        }
        
        # Write config file
        os.makedirs("/tmp", exist_ok=True)
        config_file = "/tmp/consul.json"
        with open(config_file, 'w') as f:
            json.dump(consul_config, f)
        
        # Start Consul server
        self.consul_process = await asyncio.create_subprocess_exec(
            "/usr/local/bin/consul",
            "agent",
            "-config-file", config_file,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        logger.info("Consul server started")
    
    async def _wait_for_consul_ready(self):
        """Wait for Consul to be ready"""
        if not self.consul_client:
            return
            
        max_attempts = 30
        attempt = 0
        
        while attempt < max_attempts:
            try:
                self.consul_client.agent.self()
                logger.info("Consul is ready")
                return
            except Exception:
                attempt += 1
                await asyncio.sleep(1)
        
        logger.warning("Consul did not become ready within timeout")
    
    async def register_service(self, service_name: str, service_address: str, 
                             service_port: int, health_check_url: str = None) -> bool:
        """Register service with Consul"""
        if not self.consul_client:
            logger.warning("Consul client not available")
            return False
            
        try:
            service_id = f"{service_name}-1"
            
            # Prepare service definition
            service_def = {
                "ID": service_id,
                "Name": service_name,
                "Address": service_address,
                "Port": service_port,
                "Tags": ["lucid", "microservice"]
            }
            
            # Add health check if provided
            if health_check_url:
                service_def["Check"] = {
                    "HTTP": health_check_url,
                    "Interval": "30s",
                    "Timeout": "10s"
                }
            
            # Register service
            self.consul_client.agent.service.register(**service_def)
            
            logger.info(f"Service {service_name} registered with Consul")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register service {service_name}: {e}")
            return False
    
    async def deregister_service(self, service_id: str) -> bool:
        """Deregister service from Consul"""
        if not self.consul_client:
            return False
            
        try:
            self.consul_client.agent.service.deregister(service_id)
            logger.info(f"Service {service_id} deregistered from Consul")
            return True
        except Exception as e:
            logger.error(f"Failed to deregister service {service_id}: {e}")
            return False
    
    async def discover_service(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Discover service from Consul"""
        if not self.consul_client:
            return None
            
        try:
            services = self.consul_client.health.service(service_name, passing=True)[1]
            if services:
                service = services[0]
                return {
                    "address": service["Service"]["Address"],
                    "port": service["Service"]["Port"],
                    "service_id": service["Service"]["ID"],
                    "tags": service["Service"]["Tags"]
                }
            return None
            
        except Exception as e:
            logger.error(f"Failed to discover service {service_name}: {e}")
            return None
    
    async def list_services(self) -> List[Dict[str, Any]]:
        """List all registered services"""
        if not self.consul_client:
            return []
            
        try:
            services = self.consul_client.agent.services()
            return [
                {
                    "name": service["Service"],
                    "address": service["Address"],
                    "port": service["Port"],
                    "tags": service.get("Tags", [])
                }
                for service in services.values()
            ]
        except Exception as e:
            logger.error(f"Failed to list services: {e}")
            return []
    
    async def check_health(self) -> bool:
        """Check Consul health"""
        if not self.consul_client:
            return False
            
        try:
            self.consul_client.agent.self()
            return True
        except Exception:
            return False

