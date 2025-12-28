# LUCID RDP Config Manager - Configuration Management
# LUCID-STRICT Layer 2 Service Integration
# Multi-platform support for Pi 5 ARM64
# Distroless container implementation

from __future__ import annotations

import asyncio
import logging
import os
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

class ConfigType(Enum):
    """Configuration types"""
    SERVER = "server"
    XRDP = "xrdp"
    SESSION = "session"
    SECURITY = "security"
    RESOURCE = "resource"
    DISPLAY = "display"

@dataclass
class ConfigTemplate:
    """Configuration template"""
    name: str
    config_type: ConfigType
    template: Dict[str, Any]
    variables: List[str] = field(default_factory=list)
    description: str = ""

class ConfigManager:
    """
    Configuration manager for RDP servers.
    
    Manages server configurations, templates, and environment-specific settings.
    Implements LUCID-STRICT Layer 2 Service Integration requirements.
    """
    
    def __init__(self):
        """Initialize config manager"""
        # Use writable volume mount location (/app/data is mounted as volume)
        self.config_path = Path("/app/data/config")
        self.templates_path = self.config_path / "templates"
        self.active_configs: Dict[str, Dict[str, Any]] = {}
        
        # Default configuration templates
        self.templates: Dict[str, ConfigTemplate] = {}
        
        # Initialize default templates
        self._initialize_templates()
        
        # Create directories
        self._create_directories()
    
    def _create_directories(self) -> None:
        """Create required directories"""
        for path in [self.config_path, self.templates_path]:
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {path}")
    
    def _initialize_templates(self) -> None:
        """Initialize default configuration templates"""
        
        # XRDP Server Template
        xrdp_template = ConfigTemplate(
            name="xrdp_server",
            config_type=ConfigType.XRDP,
            template={
                "globals": {
                    "bitmap_cache": True,
                    "bitmap_compression": True,
                    "port": "{port}",
                    "crypt_level": "high",
                    "channel_code": 1,
                    "max_bpp": 24,
                    "use_fastpath": "both"
                },
                "security": {
                    "allow_root_login": False,
                    "max_login_attempts": 3,
                    "login_timeout": 60,
                    "ssl_protocols": "TLSv1.2,TLSv1.3",
                    "certificate_path": "{cert_path}",
                    "key_path": "{key_path}"
                },
                "channels": {
                    "rdpdr": True,
                    "rdpsnd": True,
                    "drdynvc": True,
                    "cliprdr": True,
                    "rail": True
                },
                "logging": {
                    "log_file": "{log_file}",
                    "log_level": "INFO",
                    "enable_syslog": False
                },
                "display": {
                    "display_server": "wayland",
                    "session_path": "{session_path}"
                }
            },
            variables=["port", "cert_path", "key_path", "log_file", "session_path"],
            description="XRDP server configuration template"
        )
        
        # Session Template
        session_template = ConfigTemplate(
            name="session_config",
            config_type=ConfigType.SESSION,
            template={
                "session": {
                    "server_id": "{server_id}",
                    "user_id": "{user_id}",
                    "session_id": "{session_id}",
                    "port": "{port}",
                    "created_at": "{created_at}"
                },
                "environment": {
                    "DISPLAY": ":0",
                    "WAYLAND_DISPLAY": "wayland-0",
                    "XDG_RUNTIME_DIR": "/tmp/runtime-{server_id}"
                },
                "security": {
                    "session_timeout": 3600,
                    "idle_timeout": 1800,
                    "max_connections": 1
                }
            },
            variables=["server_id", "user_id", "session_id", "port", "created_at"],
            description="Session configuration template"
        )
        
        # Display Template
        display_template = ConfigTemplate(
            name="display_config",
            config_type=ConfigType.DISPLAY,
            template={
                "display_config": {
                    "resolution": "{resolution}",
                    "color_depth": "{color_depth}",
                    "refresh_rate": "{refresh_rate}",
                    "hardware_acceleration": "{hardware_acceleration}"
                },
                "wayland": {
                    "enable": True,
                    "compositor": "weston",
                    "backend": "drm"
                }
            },
            variables=["resolution", "color_depth", "refresh_rate", "hardware_acceleration"],
            description="Display configuration template"
        )
        
        # Resource Limits Template
        resource_template = ConfigTemplate(
            name="resource_limits",
            config_type=ConfigType.RESOURCE,
            template={
                "resource_limits": {
                    "max_cpu": "{max_cpu}",
                    "max_memory": "{max_memory}",
                    "max_bandwidth": "{max_bandwidth}",
                    "max_disk": "{max_disk}"
                },
                "monitoring": {
                    "enabled": True,
                    "interval": 30,
                    "alert_threshold": 80
                }
            },
            variables=["max_cpu", "max_memory", "max_bandwidth", "max_disk"],
            description="Resource limits configuration template"
        )
        
        # Security Template
        security_template = ConfigTemplate(
            name="security_config",
            config_type=ConfigType.SECURITY,
            template={
                "authentication": {
                    "method": "password",
                    "require_2fa": False,
                    "session_timeout": 3600
                },
                "encryption": {
                    "tls_version": "1.3",
                    "cipher_suites": ["TLS_AES_256_GCM_SHA384", "TLS_CHACHA20_POLY1305_SHA256"],
                    "certificate_validation": True
                },
                "access_control": {
                    "allowed_ips": "{allowed_ips}",
                    "blocked_ips": "{blocked_ips}",
                    "rate_limiting": True
                }
            },
            variables=["allowed_ips", "blocked_ips"],
            description="Security configuration template"
        )
        
        # Store templates
        self.templates = {
            "xrdp_server": xrdp_template,
            "session_config": session_template,
            "display_config": display_template,
            "resource_limits": resource_template,
            "security_config": security_template
        }
    
    async def initialize(self) -> None:
        """Initialize config manager"""
        logger.info("Initializing Config Manager...")
        
        # Load existing configurations
        await self._load_configurations()
        
        logger.info("Config Manager initialized")
    
    async def _load_configurations(self) -> None:
        """Load existing configurations"""
        try:
            config_file = self.config_path / "active_configs.json"
            if config_file.exists():
                with open(config_file, 'r') as f:
                    self.active_configs = json.load(f)
                logger.info(f"Loaded {len(self.active_configs)} active configurations")
        except Exception as e:
            logger.error(f"Failed to load configurations: {e}")
    
    async def save_configurations(self) -> None:
        """Save active configurations"""
        try:
            config_file = self.config_path / "active_configs.json"
            with open(config_file, 'w') as f:
                json.dump(self.active_configs, f, indent=2)
            logger.info("Configurations saved")
        except Exception as e:
            logger.error(f"Failed to save configurations: {e}")
    
    async def generate_config(self, 
                            template_name: str, 
                            variables: Dict[str, Any],
                            output_path: Optional[Path] = None) -> Dict[str, Any]:
        """Generate configuration from template"""
        try:
            if template_name not in self.templates:
                raise ValueError(f"Template '{template_name}' not found")
            
            template = self.templates[template_name]
            config = self._substitute_variables(template.template, variables)
            
            # Save to file if output path provided
            if output_path:
                await self._save_config_to_file(config, output_path)
            
            return config
            
        except Exception as e:
            logger.error(f"Config generation failed: {e}")
            raise
    
    def _substitute_variables(self, template: Dict[str, Any], variables: Dict[str, Any]) -> Dict[str, Any]:
        """Substitute variables in template"""
        import copy
        config = copy.deepcopy(template)
        
        def substitute_recursive(obj):
            if isinstance(obj, dict):
                return {k: substitute_recursive(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [substitute_recursive(item) for item in obj]
            elif isinstance(obj, str):
                for var, value in variables.items():
                    obj = obj.replace(f"{{{var}}}", str(value))
                return obj
            else:
                return obj
        
        return substitute_recursive(config)
    
    async def _save_config_to_file(self, config: Dict[str, Any], output_path: Path) -> None:
        """Save configuration to file"""
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Determine file format
            if output_path.suffix == '.json':
                with open(output_path, 'w') as f:
                    json.dump(config, f, indent=2)
            elif output_path.suffix == '.ini':
                await self._save_ini_config(config, output_path)
            else:
                # Default to JSON
                with open(output_path, 'w') as f:
                    json.dump(config, f, indent=2)
            
            logger.info(f"Configuration saved to: {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to save config to file: {e}")
            raise
    
    async def _save_ini_config(self, config: Dict[str, Any], output_path: Path) -> None:
        """Save configuration as INI format"""
        with open(output_path, 'w') as f:
            for section_name, section_data in config.items():
                f.write(f"[{section_name}]\n")
                for key, value in section_data.items():
                    if isinstance(value, bool):
                        value = str(value).lower()
                    elif isinstance(value, (list, tuple)):
                        value = ','.join(map(str, value))
                    f.write(f"{key}={value}\n")
                f.write("\n")
    
    async def get_template(self, template_name: str) -> Optional[ConfigTemplate]:
        """Get configuration template"""
        return self.templates.get(template_name)
    
    async def list_templates(self) -> List[str]:
        """List available templates"""
        return list(self.templates.keys())
    
    async def create_custom_template(self, 
                                    name: str, 
                                    config_type: ConfigType,
                                    template: Dict[str, Any],
                                    variables: List[str],
                                    description: str = "") -> bool:
        """Create custom configuration template"""
        try:
            custom_template = ConfigTemplate(
                name=name,
                config_type=config_type,
                template=template,
                variables=variables,
                description=description
            )
            
            self.templates[name] = custom_template
            
            # Save template to file
            template_file = self.templates_path / f"{name}.json"
            template_data = {
                "name": name,
                "config_type": config_type.value,
                "template": template,
                "variables": variables,
                "description": description
            }
            
            with open(template_file, 'w') as f:
                json.dump(template_data, f, indent=2)
            
            logger.info(f"Created custom template: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Custom template creation failed: {e}")
            return False
    
    async def validate_config(self, config: Dict[str, Any], config_type: ConfigType) -> bool:
        """Validate configuration"""
        try:
            # Basic validation rules
            if config_type == ConfigType.XRDP:
                required_sections = ["globals", "security", "channels", "logging", "display"]
                for section in required_sections:
                    if section not in config:
                        logger.error(f"Missing required section: {section}")
                        return False
            
            elif config_type == ConfigType.SESSION:
                required_sections = ["session", "environment", "security"]
                for section in required_sections:
                    if section not in config:
                        logger.error(f"Missing required section: {section}")
                        return False
            
            # Additional validation can be added here
            
            return True
            
        except Exception as e:
            logger.error(f"Config validation failed: {e}")
            return False
    
    async def get_default_variables(self, template_name: str) -> Dict[str, Any]:
        """Get default variables for template"""
        if template_name not in self.templates:
            return {}
        
        template = self.templates[template_name]
        defaults = {}
        
        # Set default values based on template type
        if template.config_type == ConfigType.XRDP:
            defaults.update({
                "port": 3389,
                "cert_path": "/etc/ssl/certs/server.crt",
                "key_path": "/etc/ssl/private/server.key",
                "log_file": "/var/log/xrdp/xrdp.log",
                "session_path": "/data/sessions"
            })
        
        elif template.config_type == ConfigType.DISPLAY:
            defaults.update({
                "resolution": "1920x1080",
                "color_depth": "24",
                "refresh_rate": "60",
                "hardware_acceleration": "true"
            })
        
        elif template.config_type == ConfigType.RESOURCE:
            defaults.update({
                "max_cpu": "80",
                "max_memory": "1024",
                "max_bandwidth": "1000",
                "max_disk": "5000"
            })
        
        return defaults
    
    async def get_configuration_statistics(self) -> Dict[str, Any]:
        """Get configuration statistics"""
        return {
            "total_templates": len(self.templates),
            "active_configs": len(self.active_configs),
            "template_types": {
                template.config_type.value: sum(1 for t in self.templates.values() if t.config_type == template.config_type)
                for template in self.templates.values()
            },
            "config_path": str(self.config_path),
            "templates_path": str(self.templates_path)
        }
