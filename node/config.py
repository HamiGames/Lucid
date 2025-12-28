#!/usr/bin/env python3
"""
Lucid Node Management Configuration Management
Uses Pydantic Settings for environment variable validation
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class NodeManagementSettings(BaseSettings):
    """Base settings for Node Management service"""

    # Service configuration
    NODE_MANAGEMENT_HOST: str = Field(default="0.0.0.0", description="Service host")
    NODE_MANAGEMENT_PORT: int = Field(default=8095, description="Service port")
    NODE_MANAGEMENT_STAGING_PORT: int = Field(default=8099, description="Staging port")
    NODE_MANAGEMENT_URL: str = Field(description="Service URL")
    
    # Database configuration
    MONGODB_URL: str = Field(description="MongoDB connection URL")
    # Support MONGODB_URI as alternative (for compatibility)
    MONGODB_URI: Optional[str] = Field(default=None, description="MongoDB connection URL (alternative)")
    MONGODB_DATABASE: str = Field(default="lucid_node_management", description="MongoDB database name")
    REDIS_URL: str = Field(description="Redis connection URL")
    # Support REDIS_URI as alternative (for compatibility)
    REDIS_URI: Optional[str] = Field(default=None, description="Redis connection URL (alternative)")
    
    # Node pool configuration
    MAX_NODES_PER_POOL: int = Field(default=100, description="Maximum nodes per pool")
    MIN_NODES_PER_POOL: int = Field(default=3, description="Minimum nodes per pool")
    POOL_HEALTH_CHECK_INTERVAL: int = Field(default=300, description="Pool health check interval in seconds")
    POOL_SYNC_INTERVAL: int = Field(default=60, description="Pool synchronization interval in seconds")
    
    # PoOT (Proof of Operational Trust) configuration
    POOT_CALCULATION_INTERVAL: int = Field(default=300, description="PoOT calculation interval in seconds")
    POOT_CHALLENGE_VALIDITY_MINUTES: int = Field(default=15, description="PoOT challenge validity in minutes")
    POOT_PROOF_CACHE_MINUTES: int = Field(default=60, description="PoOT proof cache time in minutes")
    MIN_TOKEN_STAKE_AMOUNT: float = Field(default=100.0, description="Minimum token stake amount")
    MAX_VALIDATION_ATTEMPTS: int = Field(default=3, description="Maximum validation attempts")
    CHALLENGE_COMPLEXITY_BYTES: int = Field(default=32, description="Challenge complexity in bytes")
    POOT_SCORE_THRESHOLD: float = Field(default=0.5, description="PoOT score threshold")
    POOT_VALIDATION_REQUIRED: bool = Field(default=True, description="PoOT validation required")
    
    # Payout configuration
    PAYOUT_THRESHOLD_USDT: float = Field(default=10.0, description="Payout threshold in USDT")
    PAYOUT_PROCESSING_INTERVAL: int = Field(default=3600, description="Payout processing interval in seconds")
    PAYOUT_PROCESSING_FEE_PERCENT: float = Field(default=1.0, description="Payout processing fee percentage")
    PAYOUT_MIN_AMOUNT_USDT: float = Field(default=1.0, description="Minimum payout amount in USDT")
    PAYOUT_MAX_AMOUNT_USDT: float = Field(default=10000.0, description="Maximum payout amount in USDT")
    
    # TRON integration (optional)
    TRON_NETWORK: str = Field(default="mainnet", description="TRON network (mainnet or testnet)")
    TRON_API_URL: str = Field(default="https://api.trongrid.io", description="TRON API URL")
    TRON_API_KEY: Optional[str] = Field(default=None, description="TRON API key")
    USDT_CONTRACT_ADDRESS: Optional[str] = Field(default=None, description="USDT contract address on TRON")
    
    # Integration service URLs (optional)
    API_GATEWAY_URL: Optional[str] = Field(default=None, description="API Gateway URL")
    BLOCKCHAIN_ENGINE_URL: Optional[str] = Field(default=None, description="Blockchain Engine URL")
    NODE_MANAGEMENT_API_URL: Optional[str] = Field(default=None, description="Node Management API URL")
    ELECTRON_GUI_ENDPOINT: Optional[str] = Field(default=None, description="Electron GUI endpoint")
    
    # Node registration configuration
    NODE_REGISTRATION_ENABLED: bool = Field(default=True, description="Node registration enabled")
    NODE_VERIFICATION_REQUIRED: bool = Field(default=True, description="Node verification required")
    NODE_HEALTH_CHECK_INTERVAL: int = Field(default=60, description="Node health check interval in seconds")
    NODE_ID: Optional[str] = Field(default=None, description="Node ID")
    ONION_ADDRESS: Optional[str] = Field(default=None, description="Onion address")
    
    # Environment
    LUCID_ENV: str = Field(default="production")
    LUCID_PLATFORM: str = Field(default="arm64")
    LUCID_CLUSTER: str = Field(default="application")
    PROJECT_ROOT: str = Field(default="/mnt/myssd/Lucid/Lucid")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FORMAT: str = Field(default="json", description="Log format")
    DEBUG: bool = Field(default=False, description="Debug mode")
    
    # Storage paths
    LUCID_DATA_PATH: str = Field(default="/app/data", description="Data storage base path")
    LUCID_LOG_PATH: str = Field(default="/app/logs", description="Log storage path")
    LOG_FILE: str = Field(default="/app/logs/node-management.log", description="Log file path")
    TEMP_STORAGE_PATH: str = Field(default="/tmp/nodes", description="Temporary storage path")
    
    # Monitoring configuration
    METRICS_ENABLED: bool = Field(default=True, description="Metrics enabled")
    METRICS_PORT: int = Field(default=9090, description="Metrics port")
    HEALTH_CHECK_INTERVAL: int = Field(default=30, description="Health check interval in seconds")
    HEALTH_CHECK_ENABLED: bool = Field(default=True, description="Health check enabled")
    
    # Performance configuration
    SERVICE_TIMEOUT_SECONDS: int = Field(default=30, description="Service timeout in seconds")
    SERVICE_RETRY_COUNT: int = Field(default=3, description="Service retry count")
    SERVICE_RETRY_DELAY_SECONDS: float = Field(default=1.0, description="Service retry delay in seconds")
    WORKERS: int = Field(default=1, description="Number of workers")
    
    # Security configuration
    CORS_ORIGINS: str = Field(default="*", description="CORS origins")
    TRUSTED_HOSTS: str = Field(default="*", description="Trusted hosts")
    PRODUCTION: bool = Field(default=False, description="Production mode")
    
    @field_validator('NODE_MANAGEMENT_PORT', 'NODE_MANAGEMENT_STAGING_PORT', 'METRICS_PORT')
    @classmethod
    def validate_port(cls, v):
        if v < 1024 or v > 65535:
            raise ValueError('Port must be between 1024 and 65535')
        return v
    
    @field_validator('MAX_NODES_PER_POOL')
    @classmethod
    def validate_max_nodes(cls, v):
        if v < 1 or v > 1000:
            raise ValueError('MAX_NODES_PER_POOL must be between 1 and 1000')
        return v
    
    @field_validator('MIN_NODES_PER_POOL')
    @classmethod
    def validate_min_nodes(cls, v):
        if v < 1:
            raise ValueError('MIN_NODES_PER_POOL must be at least 1')
        return v
    
    @field_validator('PAYOUT_THRESHOLD_USDT', 'PAYOUT_MIN_AMOUNT_USDT', 'PAYOUT_MAX_AMOUNT_USDT')
    @classmethod
    def validate_payout_amount(cls, v):
        if v < 0:
            raise ValueError('Payout amount must be non-negative')
        return v
    
    @field_validator('LOG_LEVEL')
    @classmethod
    def validate_log_level(cls, v):
        allowed = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in allowed:
            raise ValueError(f'LOG_LEVEL must be one of {allowed}')
        return v.upper()
    
    @field_validator('TRON_NETWORK')
    @classmethod
    def validate_tron_network(cls, v):
        allowed = ['mainnet', 'testnet', 'shasta']
        if v.lower() not in allowed:
            raise ValueError(f'TRON_NETWORK must be one of {allowed}')
        return v.lower()
    
    model_config = SettingsConfigDict(
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )


class NodeManagementConfigManager:
    """Configuration manager for Node Management service"""
    
    def __init__(self):
        self.settings = NodeManagementSettings()
        self._validate_config()
    
    def _validate_config(self):
        """Validate configuration"""
        # Use MONGODB_URI if MONGODB_URL is not set (for compatibility)
        if not self.settings.MONGODB_URL and self.settings.MONGODB_URI:
            self.settings.MONGODB_URL = self.settings.MONGODB_URI
        
        if not self.settings.MONGODB_URL:
            raise ValueError("MONGODB_URL or MONGODB_URI is required")
        
        # Use REDIS_URI if REDIS_URL is not set (for compatibility)
        if not self.settings.REDIS_URL and self.settings.REDIS_URI:
            self.settings.REDIS_URL = self.settings.REDIS_URI
        
        if not self.settings.REDIS_URL:
            raise ValueError("REDIS_URL or REDIS_URI is required")
        
        # Validate node pool configuration
        if self.settings.MIN_NODES_PER_POOL > self.settings.MAX_NODES_PER_POOL:
            raise ValueError("MIN_NODES_PER_POOL must be less than or equal to MAX_NODES_PER_POOL")
        
        # Validate payout configuration
        if self.settings.PAYOUT_MIN_AMOUNT_USDT > self.settings.PAYOUT_MAX_AMOUNT_USDT:
            raise ValueError("PAYOUT_MIN_AMOUNT_USDT must be less than or equal to PAYOUT_MAX_AMOUNT_USDT")
        
        if self.settings.PAYOUT_THRESHOLD_USDT < self.settings.PAYOUT_MIN_AMOUNT_USDT:
            raise ValueError("PAYOUT_THRESHOLD_USDT must be at least PAYOUT_MIN_AMOUNT_USDT")
        
        # Validate MongoDB URL doesn't use localhost
        mongodb_url = self.settings.MONGODB_URL
        if "localhost" in mongodb_url or "127.0.0.1" in mongodb_url:
            raise ValueError("MONGODB_URL must not use localhost - use service name (e.g., lucid-mongodb)")
        
        # Validate Redis URL doesn't use localhost
        if "localhost" in self.settings.REDIS_URL or "127.0.0.1" in self.settings.REDIS_URL:
            raise ValueError("REDIS_URL must not use localhost - use service name (e.g., lucid-redis)")
    
    def get_node_management_config_dict(self) -> dict:
        """Get service configuration as dictionary"""
        return {
            "host": self.settings.NODE_MANAGEMENT_HOST,
            "port": self.settings.NODE_MANAGEMENT_PORT,
            "staging_port": self.settings.NODE_MANAGEMENT_STAGING_PORT,
            "url": self.settings.NODE_MANAGEMENT_URL,
            "max_nodes_per_pool": self.settings.MAX_NODES_PER_POOL,
            "min_nodes_per_pool": self.settings.MIN_NODES_PER_POOL,
            "pool_health_check_interval": self.settings.POOL_HEALTH_CHECK_INTERVAL,
            "pool_sync_interval": self.settings.POOL_SYNC_INTERVAL,
            "poot_calculation_interval": self.settings.POOT_CALCULATION_INTERVAL,
            "payout_threshold_usdt": self.settings.PAYOUT_THRESHOLD_USDT,
            "payout_processing_interval": self.settings.PAYOUT_PROCESSING_INTERVAL,
            "api_gateway_url": self.settings.API_GATEWAY_URL,
            "blockchain_engine_url": self.settings.BLOCKCHAIN_ENGINE_URL,
            "node_id": self.settings.NODE_ID,
            "onion_address": self.settings.ONION_ADDRESS,
        }
    
    def get_mongodb_url(self) -> str:
        """Get MongoDB URL"""
        return self.settings.MONGODB_URL
    
    def get_redis_url(self) -> str:
        """Get Redis URL"""
        return self.settings.REDIS_URL
    
    def get_mongodb_database(self) -> str:
        """Get MongoDB database name"""
        return self.settings.MONGODB_DATABASE
