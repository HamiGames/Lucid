"""
Envoy configuration generator for service mesh

File: service-mesh/envoy_config_generator.py
"""

import asyncio
import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Optional jinja2 import
try:
    from jinja2 import Template
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False
    logger.warning("jinja2 package not available")


# Envoy configuration template
ENVOY_CONFIG_TEMPLATE = """
static_resources:
  listeners:
  - name: listener_0
    address:
      socket_address:
        address: 0.0.0.0
        port_value: {{ service_port }}
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: ingress_http
          route_config:
            name: local_route
            virtual_hosts:
            - name: local_service
              domains: ["*"]
              routes:
              - match:
                  prefix: "/"
                route:
                  cluster: {{ service_name }}_cluster
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              "@type": type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  clusters:
  - name: {{ service_name }}_cluster
    connect_timeout: 0.25s
    type: LOGICAL_DNS
    lb_policy: ROUND_ROBIN
    load_assignment:
      cluster_name: {{ service_name }}_cluster
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: {{ service_address }}
                port_value: {{ service_port }}
admin:
  address:
    socket_address:
      address: 0.0.0.0
      port_value: {{ admin_port }}
"""


class EnvoyConfigGenerator:
    """Envoy configuration generator"""
    
    def __init__(self, settings):
        self.settings = settings
        self.configs: Dict[str, Dict[str, Any]] = {}
        
    async def initialize(self):
        """Initialize Envoy config generator"""
        try:
            # Create Envoy configs directory
            os.makedirs(self.settings.ENVOY_CONFIG_PATH, exist_ok=True)
            
            logger.info("Envoy config generator initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Envoy config generator: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup Envoy config generator"""
        logger.info("Envoy config generator cleaned up")
    
    async def generate_envoy_config(self, service_name: str, service_address: str, 
                                   service_port: int) -> str:
        """Generate Envoy configuration for service"""
        try:
            if JINJA2_AVAILABLE:
                template = Template(ENVOY_CONFIG_TEMPLATE)
                config = template.render(
                    service_name=service_name,
                    service_address=service_address,
                    service_port=service_port,
                    admin_port=self.settings.ENVOY_ADMIN_PORT
                )
            else:
                # Simple string replacement fallback
                config = ENVOY_CONFIG_TEMPLATE
                config = config.replace("{{ service_name }}", service_name)
                config = config.replace("{{ service_address }}", service_address)
                config = config.replace("{{ service_port }}", str(service_port))
                config = config.replace("{{ admin_port }}", str(self.settings.ENVOY_ADMIN_PORT))
            
            # Save configuration
            config_path = os.path.join(self.settings.ENVOY_CONFIG_PATH, f"{service_name}.yaml")
            with open(config_path, 'w') as f:
                f.write(config)
            
            # Store config info
            self.configs[service_name] = {
                "config_path": config_path,
                "service_address": service_address,
                "service_port": service_port,
                "created_at": datetime.utcnow()
            }
            
            logger.info(f"Envoy configuration generated for service {service_name}")
            
            return config_path
            
        except Exception as e:
            logger.error(f"Failed to generate Envoy config for {service_name}: {e}")
            raise
    
    async def get_envoy_config(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get Envoy configuration for service"""
        if service_name in self.configs:
            config_info = self.configs[service_name]
            return {
                "service_name": service_name,
                "config_path": config_info["config_path"],
                "service_address": config_info["service_address"],
                "service_port": config_info["service_port"],
                "created_at": config_info["created_at"].isoformat()
            }
        return None
    
    async def list_envoy_configs(self) -> List[Dict[str, Any]]:
        """List all Envoy configurations"""
        return [
            {
                "service_name": name,
                "config_path": info["config_path"],
                "service_address": info["service_address"],
                "service_port": info["service_port"],
                "created_at": info["created_at"].isoformat()
            }
            for name, info in self.configs.items()
        ]
    
    async def delete_envoy_config(self, service_name: str) -> bool:
        """Delete Envoy configuration for service"""
        if service_name not in self.configs:
            return False
            
        try:
            config_info = self.configs[service_name]
            
            # Remove config file
            if os.path.exists(config_info["config_path"]):
                os.remove(config_info["config_path"])
            
            # Remove from tracking
            del self.configs[service_name]
            
            logger.info(f"Envoy configuration deleted for service {service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete Envoy config for {service_name}: {e}")
            return False
    
    async def get_config_content(self, service_name: str) -> Optional[str]:
        """Get Envoy configuration content"""
        if service_name not in self.configs:
            return None
            
        config_path = self.configs[service_name]["config_path"]
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return f.read()
        return None
    
    async def check_health(self) -> bool:
        """Check Envoy config generator health"""
        try:
            return os.path.exists(self.settings.ENVOY_CONFIG_PATH)
        except Exception:
            return False

