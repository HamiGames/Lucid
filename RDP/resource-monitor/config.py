#!/usr/bin/env python3
"""
Lucid RDP Resource Monitor Configuration
Configuration management for RDP resource monitoring service
"""

import os
from typing import Dict, Any, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings
import logging

logger = logging.getLogger(__name__)


class MonitorSettings(BaseSettings):
    """RDP Resource Monitor configuration settings"""
    
    # Service Configuration
    SERVICE_NAME: str = "lucid-rdp-monitor"
    SERVICE_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # Network Configuration (from docker-compose.application.yml)
    # Note: RDP_MONITOR_HOST is service name, RDP_MONITOR_PORT is service port
    HOST: str = "0.0.0.0"  # Bind address (always 0.0.0.0 for container binding)
    PORT: int = 8093  # Default port (overridden by RDP_MONITOR_PORT from docker-compose)
    RDP_MONITOR_HOST: str = ""  # From docker-compose: RDP_MONITOR_HOST (service name, not bind address)
    RDP_MONITOR_PORT: str = ""  # From docker-compose: RDP_MONITOR_PORT (string, converted to int)
    RDP_MONITOR_URL: str = ""  # From docker-compose: RDP_MONITOR_URL (e.g., http://rdp-monitor:8093)
    
    # Database Configuration (from .env.foundation, .env.core)
    MONGODB_URL: str = ""  # Required from environment: MONGODB_URL
    REDIS_URL: str = ""  # Optional from environment: REDIS_URL
    
    # Storage Configuration (use volume mount paths from docker-compose)
    LOG_STORAGE_PATH: str = "/app/logs"  # Volume: /logs/rdp-monitor:/app/logs:rw
    TEMP_STORAGE_PATH: str = "/tmp/monitor"  # tmpfs mount: /tmp:size=100m
    
    # Monitoring Configuration
    MONITORING_INTERVAL: int = 30  # seconds - interval for collecting metrics
    COLLECTION_INTERVAL: int = 30  # seconds - interval for metrics collection
    METRICS_HISTORY_LIMIT: int = 100  # Maximum number of metrics per session to keep in memory
    METRICS_CLEANUP_HOURS: int = 24  # Hours of metrics history to keep
    
    # Alert Thresholds Configuration
    CPU_THRESHOLD_PERCENT: float = 80.0  # CPU usage alert threshold
    MEMORY_THRESHOLD_PERCENT: float = 80.0  # Memory usage alert threshold
    DISK_THRESHOLD_PERCENT: float = 90.0  # Disk usage alert threshold
    NETWORK_BANDWIDTH_THRESHOLD_MB: float = 1000.0  # Network bandwidth alert threshold (MB/s)
    
    # Metrics Configuration
    METRICS_ENABLED: bool = True
    PROMETHEUS_ENABLED: bool = True
    EXPORT_METRICS_ENDPOINT: bool = True
    
    # Performance Configuration
    MAX_CONCURRENT_SESSIONS: int = 100  # Maximum number of sessions to monitor concurrently
    SESSION_METRICS_CACHE_SIZE: int = 1000  # Maximum cached metrics per session
    
    # Health Check Configuration
    HEALTH_CHECK_INTERVAL: int = 30  # seconds
    HEALTH_CHECK_ENABLED: bool = True
    
    # Integration Service URLs (from .env.application, .env.core)
    RDP_SERVER_MANAGER_URL: str = ""  # From environment: RDP_SERVER_MANAGER_URL (e.g., http://rdp-server-manager:8081)
    RDP_XRDP_URL: str = ""  # From environment: RDP_XRDP_URL (e.g., http://rdp-xrdp:3389)
    RDP_CONTROLLER_URL: str = ""  # From environment: RDP_CONTROLLER_URL (e.g., http://rdp-controller:8092)
    
    # Integration Service Timeout Configuration
    SERVICE_TIMEOUT_SECONDS: int = 30  # Default timeout for service calls
    SERVICE_RETRY_COUNT: int = 3  # Default retry count for service calls
    SERVICE_RETRY_DELAY_SECONDS: float = 1.0  # Default delay between retries
    
    # CORS Configuration (from .env.application)
    CORS_ORIGINS: str = "*"  # From environment: CORS_ORIGINS (comma-separated list, default: "*")
    
    @field_validator('MONITORING_INTERVAL')
    @classmethod
    def validate_monitoring_interval(cls, v):
        if v < 1 or v > 3600:
            raise ValueError('Monitoring interval must be between 1 and 3600 seconds')
        return v
    
    @field_validator('COLLECTION_INTERVAL')
    @classmethod
    def validate_collection_interval(cls, v):
        if v < 1 or v > 3600:
            raise ValueError('Collection interval must be between 1 and 3600 seconds')
        return v
    
    @field_validator('CPU_THRESHOLD_PERCENT', 'MEMORY_THRESHOLD_PERCENT', 'DISK_THRESHOLD_PERCENT')
    @classmethod
    def validate_threshold_percent(cls, v):
        if v < 0 or v > 100:
            raise ValueError('Threshold percentage must be between 0 and 100')
        return v
    
    @field_validator('MAX_CONCURRENT_SESSIONS')
    @classmethod
    def validate_max_sessions(cls, v):
        if v < 1 or v > 1000:
            raise ValueError('Max concurrent sessions must be between 1 and 1000')
        return v
    
    @field_validator('HEALTH_CHECK_INTERVAL', mode='before')
    @classmethod
    def validate_health_check_interval(cls, v):
        """Convert '30s' format to integer seconds"""
        if isinstance(v, int):
            return v
        if isinstance(v, str):
            # Strip 's' suffix if present (e.g., '30s' -> '30')
            v = v.rstrip('s').strip()
            try:
                return int(v)
            except ValueError:
                raise ValueError(f'HEALTH_CHECK_INTERVAL must be an integer or integer string (e.g., "30" or "30s"), got: {v}')
        raise ValueError(f'HEALTH_CHECK_INTERVAL must be an integer or string, got: {type(v)}')
    
    model_config = {
        # pydantic-settings will read from environment variables
        # docker-compose provides: .env.secrets, .env.core, .env.application, .env.foundation
        "env_file": None,  # Don't read .env file directly - use environment variables from docker-compose
        "case_sensitive": True,
        "env_file_encoding": "utf-8"
    }
    
    @field_validator('MONGODB_URL')
    @classmethod
    def validate_mongodb_url(cls, v):
        # MongoDB is optional for rdp-monitor, but if provided, validate it
        if v and v != "":
            if "localhost" in v or "127.0.0.1" in v:
                raise ValueError('MONGODB_URL must not use localhost - use service name (e.g., lucid-mongodb)')
        return v
    
    @field_validator('REDIS_URL')
    @classmethod
    def validate_redis_url(cls, v):
        # Redis is optional for rdp-monitor, but if provided, validate it
        if v and v != "":
            if "localhost" in v or "127.0.0.1" in v:
                raise ValueError('REDIS_URL must not use localhost - use service name (e.g., lucid-redis)')
        return v


class MonitorConfig:
    """
    Main monitor configuration class
    Manages all monitor-related configuration
    """
    
    def __init__(self, settings: Optional[MonitorSettings] = None):
        try:
            self.settings = settings or MonitorSettings()
            
            # Validate critical environment variables (if required)
            self._validate_required_env_vars()
            
            # Override PORT from RDP_MONITOR_PORT if provided (HOST always stays 0.0.0.0)
            # RDP_MONITOR_HOST is the service name for URLs, not the bind address
            if hasattr(self.settings, 'RDP_MONITOR_PORT') and self.settings.RDP_MONITOR_PORT:
                try:
                    self.settings.PORT = int(self.settings.RDP_MONITOR_PORT)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid RDP_MONITOR_PORT value: {self.settings.RDP_MONITOR_PORT}, using default {self.settings.PORT}")
            
            # Set integration service URLs from environment if not already set
            if not self.settings.RDP_SERVER_MANAGER_URL:
                self.settings.RDP_SERVER_MANAGER_URL = os.getenv('RDP_SERVER_MANAGER_URL', 'http://rdp-server-manager:8081')
            if not self.settings.RDP_XRDP_URL:
                self.settings.RDP_XRDP_URL = os.getenv('RDP_XRDP_URL', 'http://rdp-xrdp:3389')
            if not self.settings.RDP_CONTROLLER_URL:
                self.settings.RDP_CONTROLLER_URL = os.getenv('RDP_CONTROLLER_URL', 'http://rdp-controller:8092')
            
            logger.info("Monitor configuration initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize monitor configuration: {e}", exc_info=True)
            raise
    
    def _validate_required_env_vars(self):
        """Validate that required environment variables are set"""
        # MongoDB and Redis are optional for rdp-monitor
        # Only validate if they're provided
        if self.settings.MONGODB_URL and self.settings.MONGODB_URL != "":
            if "localhost" in self.settings.MONGODB_URL or "127.0.0.1" in self.settings.MONGODB_URL:
                raise ValueError("MONGODB_URL must not use localhost - use service name (e.g., lucid-mongodb)")
        
        if self.settings.REDIS_URL and self.settings.REDIS_URL != "":
            if "localhost" in self.settings.REDIS_URL or "127.0.0.1" in self.settings.REDIS_URL:
                raise ValueError("REDIS_URL must not use localhost - use service name (e.g., lucid-redis)")
    
    def get_alert_thresholds(self) -> Dict[str, float]:
        """Get alert thresholds as a dictionary"""
        return {
            "cpu_percent": self.settings.CPU_THRESHOLD_PERCENT,
            "memory_percent": self.settings.MEMORY_THRESHOLD_PERCENT,
            "disk_percent": self.settings.DISK_THRESHOLD_PERCENT,
            "network_bandwidth": self.settings.NETWORK_BANDWIDTH_THRESHOLD_MB
        }
    
    def get_service_config(self) -> Dict[str, Any]:
        """Get service configuration as a dictionary"""
        return {
            "name": self.settings.SERVICE_NAME,
            "version": self.settings.SERVICE_VERSION,
            "debug": self.settings.DEBUG,
            "log_level": self.settings.LOG_LEVEL,
            "host": self.settings.HOST,
            "port": self.settings.PORT
        }
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get monitoring configuration as a dictionary"""
        return {
            "monitoring_interval": self.settings.MONITORING_INTERVAL,
            "collection_interval": self.settings.COLLECTION_INTERVAL,
            "metrics_history_limit": self.settings.METRICS_HISTORY_LIMIT,
            "metrics_cleanup_hours": self.settings.METRICS_CLEANUP_HOURS,
            "max_concurrent_sessions": self.settings.MAX_CONCURRENT_SESSIONS,
            "session_metrics_cache_size": self.settings.SESSION_METRICS_CACHE_SIZE
        }

