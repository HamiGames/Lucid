"""
Lucid Service Mesh Controller - Configuration Manager
Manages service mesh configuration and dynamic updates.

File: infrastructure/service-mesh/controller/config_manager.py
Lines: ~300
Purpose: Configuration management
Dependencies: asyncio, yaml, consul
"""

import asyncio
import logging
import yaml
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Service mesh configuration manager.
    
    Handles:
    - Configuration loading and validation
    - Dynamic configuration updates
    - Service mesh topology management
    - Policy configuration
    """
    
    def __init__(self):
        self.config: Dict[str, Any] = {}
        self.config_path = os.getenv("SERVICE_MESH_CONFIG_PATH", "/config")
        self.watch_paths: List[str] = []
        self.last_modified: Dict[str, float] = {}
        
    async def load_config(self):
        """Load service mesh configuration."""
        try:
            logger.info("Loading service mesh configuration...")
            
            # Load main configuration
            main_config_path = os.path.join(self.config_path, "service-mesh.yaml")
            if os.path.exists(main_config_path):
                await self._load_yaml_config(main_config_path)
            else:
                # Use default configuration
                self._load_default_config()
                
            # Load service configurations
            services_config_path = os.path.join(self.config_path, "services")
            if os.path.exists(services_config_path):
                await self._load_service_configs(services_config_path)
                
            # Load policy configurations
            policies_config_path = os.path.join(self.config_path, "policies")
            if os.path.exists(policies_config_path):
                await self._load_policy_configs(policies_config_path)
                
            # Setup watch paths
            self._setup_watch_paths()
            
            logger.info("Configuration loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
            
    def _load_default_config(self):
        """Load default service mesh configuration."""
        self.config = {
            "service_mesh": {
                "name": "lucid-service-mesh",
                "version": "1.0.0",
                "namespace": "lucid",
                "controller": {
                    "port": 8600,
                    "admin_port": 8601,
                    "log_level": "INFO"
                },
                "discovery": {
                    "backend": "consul",
                    "consul_host": "consul:8500",
                    "service_ttl": 60,
                    "health_check_interval": 30
                },
                "sidecar": {
                    "envoy": {
                        "admin_port": 15000,
                        "proxy_port": 15001,
                        "config_path": "/etc/envoy"
                    }
                },
                "security": {
                    "mtls": {
                        "enabled": True,
                        "cert_validity_days": 90,
                        "auto_rotate": True
                    }
                },
                "networking": {
                    "default_timeout": 30,
                    "retry_attempts": 3,
                    "circuit_breaker": {
                        "failure_threshold": 5,
                        "recovery_timeout": 30
                    }
                }
            },
            "services": {},
            "policies": {}
        }
        
    async def _load_yaml_config(self, config_path: str):
        """Load YAML configuration file."""
        try:
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
                
            if config_data:
                self.config.update(config_data)
                logger.info(f"Loaded configuration from {config_path}")
                
        except Exception as e:
            logger.error(f"Failed to load YAML config from {config_path}: {e}")
            raise
            
    async def _load_service_configs(self, services_path: str):
        """Load service-specific configurations."""
        try:
            services_dir = Path(services_path)
            for config_file in services_dir.glob("*.yaml"):
                service_name = config_file.stem
                
                with open(config_file, 'r') as f:
                    service_config = yaml.safe_load(f)
                    
                if service_config:
                    self.config["services"][service_name] = service_config
                    logger.info(f"Loaded service config: {service_name}")
                    
        except Exception as e:
            logger.error(f"Failed to load service configs: {e}")
            raise
            
    async def _load_policy_configs(self, policies_path: str):
        """Load policy configurations."""
        try:
            policies_dir = Path(policies_path)
            for config_file in policies_dir.glob("*.yaml"):
                policy_name = config_file.stem
                
                with open(config_file, 'r') as f:
                    policy_config = yaml.safe_load(f)
                    
                if policy_config:
                    self.config["policies"][policy_name] = policy_config
                    logger.info(f"Loaded policy config: {policy_name}")
                    
        except Exception as e:
            logger.error(f"Failed to load policy configs: {e}")
            raise
            
    def _setup_watch_paths(self):
        """Setup file paths to watch for changes."""
        self.watch_paths = [
            os.path.join(self.config_path, "service-mesh.yaml"),
            os.path.join(self.config_path, "services"),
            os.path.join(self.config_path, "policies")
        ]
        
        # Initialize last modified times
        for path in self.watch_paths:
            if os.path.exists(path):
                if os.path.isfile(path):
                    self.last_modified[path] = os.path.getmtime(path)
                else:
                    # For directories, check all files
                    for root, dirs, files in os.walk(path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            self.last_modified[file_path] = os.path.getmtime(file_path)
                            
    async def watch_for_changes(self):
        """Watch for configuration changes."""
        try:
            for path in self.watch_paths:
                if os.path.exists(path):
                    if os.path.isfile(path):
                        await self._check_file_changes(path)
                    else:
                        # Check directory changes
                        for root, dirs, files in os.walk(path):
                            for file in files:
                                file_path = os.path.join(root, file)
                                await self._check_file_changes(file_path)
                                
        except Exception as e:
            logger.error(f"Error watching for config changes: {e}")
            
    async def _check_file_changes(self, file_path: str):
        """Check if a file has been modified."""
        try:
            if not os.path.exists(file_path):
                return
                
            current_mtime = os.path.getmtime(file_path)
            last_mtime = self.last_modified.get(file_path, 0)
            
            if current_mtime > last_mtime:
                logger.info(f"Configuration file changed: {file_path}")
                self.last_modified[file_path] = current_mtime
                
                # Reload configuration
                await self._reload_config_file(file_path)
                
        except Exception as e:
            logger.error(f"Error checking file changes for {file_path}: {e}")
            
    async def _reload_config_file(self, file_path: str):
        """Reload a specific configuration file."""
        try:
            if file_path.endswith("service-mesh.yaml"):
                await self._load_yaml_config(file_path)
            elif "services" in file_path:
                service_name = Path(file_path).stem
                with open(file_path, 'r') as f:
                    service_config = yaml.safe_load(f)
                if service_config:
                    self.config["services"][service_name] = service_config
            elif "policies" in file_path:
                policy_name = Path(file_path).stem
                with open(file_path, 'r') as f:
                    policy_config = yaml.safe_load(f)
                if policy_config:
                    self.config["policies"][policy_name] = policy_config
                    
            logger.info(f"Reloaded configuration: {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to reload config file {file_path}: {e}")
            
    def get_config(self, path: str = None) -> Any:
        """Get configuration value by path."""
        if path is None:
            return self.config
            
        keys = path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
                
        return value
        
    def get_service_config(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific service."""
        return self.config.get("services", {}).get(service_name)
        
    def get_policy_config(self, policy_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific policy."""
        return self.config.get("policies", {}).get(policy_name)
        
    def update_config(self, path: str, value: Any):
        """Update configuration value."""
        keys = path.split('.')
        config = self.config
        
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
            
        config[keys[-1]] = value
        
    def get_status(self) -> Dict[str, Any]:
        """Get configuration manager status."""
        return {
            "config_loaded": bool(self.config),
            "watch_paths": len(self.watch_paths),
            "services_configured": len(self.config.get("services", {})),
            "policies_configured": len(self.config.get("policies", {})),
            "last_update": datetime.utcnow().isoformat()
        }
        
    async def cleanup(self):
        """Cleanup configuration manager."""
        logger.info("Cleaning up configuration manager...")
        # No specific cleanup needed
