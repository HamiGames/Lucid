"""
Lucid Authentication Service - Endpoint Configuration Manager
Manages customizable HTTP endpoint configuration from YAML files

File: auth/api/endpoint_config.py
Purpose: Load and manage endpoint configuration for customizable HTTP endpoints
Dependencies: yaml, pathlib, typing
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class EndpointConfig:
    """
    Manages endpoint configuration for customizable HTTP endpoints.
    
    Loads configuration from YAML files and provides methods to:
    - Check if endpoints are enabled
    - Get endpoint rate limits
    - Get endpoint authentication requirements
    - Get endpoint customization options
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize endpoint configuration manager.
        
        Args:
            config_path: Path to endpoints.yaml file (default: auth/config/endpoints.yaml)
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "endpoints.yaml"
        
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self):
        """Load endpoint configuration from YAML file."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    self.config = yaml.safe_load(f) or {}
                logger.info(f"Loaded endpoint configuration from {self.config_path}")
            else:
                logger.warning(f"Endpoint configuration file not found: {self.config_path}, using defaults")
                self.config = self._get_default_config()
        except Exception as e:
            logger.error(f"Failed to load endpoint configuration: {e}, using defaults")
            self.config = self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default endpoint configuration."""
        return {
            "endpoints": {
                "health": {"enabled": True, "authentication_required": False},
                "meta": {"enabled": True, "authentication_required": False},
                "auth": {"enabled": True, "authentication_required": False},
                "users": {"enabled": True, "authentication_required": True},
                "sessions": {"enabled": True, "authentication_required": True},
                "hardware_wallet": {"enabled": True, "authentication_required": True}
            },
            "customization": {
                "cors": {"enabled": True},
                "rate_limiting": {"enabled": True, "default_limit": 60}
            }
        }
    
    def is_endpoint_enabled(self, endpoint_name: str) -> bool:
        """
        Check if an endpoint is enabled.
        
        Args:
            endpoint_name: Name of the endpoint (e.g., "auth", "users", "sessions")
        
        Returns:
            True if endpoint is enabled, False otherwise
        """
        endpoints = self.config.get("endpoints", {})
        endpoint = endpoints.get(endpoint_name, {})
        return endpoint.get("enabled", True)
    
    def get_endpoint_rate_limit(self, endpoint_name: str) -> Optional[int]:
        """
        Get rate limit for an endpoint.
        
        Args:
            endpoint_name: Name of the endpoint
        
        Returns:
            Rate limit in requests per minute, or None if no limit
        """
        endpoints = self.config.get("endpoints", {})
        endpoint = endpoints.get(endpoint_name, {})
        rate_limit = endpoint.get("rate_limit")
        
        if rate_limit is None:
            # Check default rate limit
            customization = self.config.get("customization", {})
            rate_limiting = customization.get("rate_limiting", {})
            return rate_limiting.get("default_limit", 60)
        
        return rate_limit
    
    def is_authentication_required(self, endpoint_name: str) -> bool:
        """
        Check if authentication is required for an endpoint.
        
        Args:
            endpoint_name: Name of the endpoint
        
        Returns:
            True if authentication is required, False otherwise
        """
        endpoints = self.config.get("endpoints", {})
        endpoint = endpoints.get(endpoint_name, {})
        return endpoint.get("authentication_required", False)
    
    def get_sub_endpoint_config(self, endpoint_name: str, sub_endpoint_name: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a sub-endpoint.
        
        Args:
            endpoint_name: Parent endpoint name (e.g., "auth")
            sub_endpoint_name: Sub-endpoint name (e.g., "login")
        
        Returns:
            Sub-endpoint configuration dictionary, or None if not found
        """
        endpoints = self.config.get("endpoints", {})
        endpoint = endpoints.get(endpoint_name, {})
        sub_endpoints = endpoint.get("sub_endpoints", {})
        return sub_endpoints.get(sub_endpoint_name)
    
    def get_cors_config(self) -> Dict[str, Any]:
        """Get CORS configuration."""
        customization = self.config.get("customization", {})
        cors = customization.get("cors", {})
        return {
            "enabled": cors.get("enabled", True),
            "allow_origins": cors.get("allow_origins", ["*"]),
            "allow_credentials": cors.get("allow_credentials", True),
            "allow_methods": cors.get("allow_methods", ["GET", "POST", "PUT", "DELETE", "OPTIONS"]),
            "allow_headers": cors.get("allow_headers", ["*"]),
            "max_age": cors.get("max_age", 3600)
        }
    
    def get_rate_limiting_config(self) -> Dict[str, Any]:
        """Get rate limiting configuration."""
        customization = self.config.get("customization", {})
        rate_limiting = customization.get("rate_limiting", {})
        return {
            "enabled": rate_limiting.get("enabled", True),
            "default_limit": rate_limiting.get("default_limit", 60),
            "storage": rate_limiting.get("storage", "redis"),
            "key_prefix": rate_limiting.get("key_prefix", "auth:rate_limit:")
        }
    
    def get_validation_config(self) -> Dict[str, Any]:
        """Get request validation configuration."""
        customization = self.config.get("customization", {})
        validation = customization.get("validation", {})
        return {
            "strict_mode": validation.get("strict_mode", False),
            "max_request_size": validation.get("max_request_size", 1048576),
            "timeout": validation.get("timeout", 30)
        }
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        customization = self.config.get("customization", {})
        logging_config = customization.get("logging", {})
        return {
            "log_requests": logging_config.get("log_requests", True),
            "log_responses": logging_config.get("log_responses", False),
            "log_errors": logging_config.get("log_errors", True),
            "log_level": logging_config.get("log_level", "INFO")
        }
    
    def reload_config(self):
        """Reload configuration from file."""
        self._load_config()
        logger.info("Endpoint configuration reloaded")
    
    def get_all_endpoints(self) -> Dict[str, Any]:
        """Get all endpoint configurations."""
        return self.config.get("endpoints", {})
    
    def get_all_customization(self) -> Dict[str, Any]:
        """Get all customization options."""
        return self.config.get("customization", {})


# Global endpoint configuration instance
_endpoint_config: Optional[EndpointConfig] = None


def get_endpoint_config() -> EndpointConfig:
    """Get global endpoint configuration instance."""
    global _endpoint_config
    if _endpoint_config is None:
        _endpoint_config = EndpointConfig()
    return _endpoint_config

