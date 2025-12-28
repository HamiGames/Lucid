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
import logging

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

logger = logging.getLogger(__name__)


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
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_file: Optional path to YAML configuration file.
                        If not provided, will look for config.yaml in default locations.
        """
        # load_config handles YAML availability internally
        self.settings = load_config(config_file)
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


def load_config(config_file: Optional[str] = None) -> NodeManagementSettings:
    """
    Load configuration from YAML file and environment variables.
    
    Configuration loading priority (highest to lowest):
    1. Environment variables (highest priority - override everything)
    2. YAML configuration file values (flattened nested structure)
    3. Pydantic field defaults (lowest priority)
    
    Args:
        config_file: Optional path to YAML configuration file. If not provided,
                     will look for 'config.yaml' or 'node-management-config.yaml' 
                     in the node directory.
        
    Returns:
        Loaded NodeManagementSettings object with environment variables overriding YAML values
        
    Raises:
        FileNotFoundError: If config_file is provided but doesn't exist
        ValueError: If configuration validation fails
        ImportError: If PyYAML is not available (should not happen if requirements are installed)
    """
    try:
        yaml_data: Dict[str, Any] = {}
        yaml_file_path: Optional[Path] = None
        
        # Determine YAML file path
        if config_file:
            yaml_file_path = Path(config_file)
        else:
            # Try default locations
            default_locations = [
                Path(__file__).parent / "config.yaml",  # Same directory as config.py
                Path(__file__).parent / "config" / "node-management-config.yaml",  # config directory
                Path(__file__).parent.parent / "node" / "config.yaml",  # Alternative path
            ]
            for loc in default_locations:
                if loc.exists():
                    yaml_file_path = loc
                    break
        
        # Load YAML file if it exists
        if yaml_file_path and yaml_file_path.exists():
            if not YAML_AVAILABLE:
                logger.warning(f"PyYAML not available, skipping YAML file {yaml_file_path}")
            else:
                try:
                    with open(yaml_file_path, 'r', encoding='utf-8') as f:
                        raw_yaml_data = yaml.safe_load(f) or {}
                    logger.info(f"Loaded YAML configuration from {yaml_file_path}")
                    
                    # Flatten nested YAML structure to match Pydantic field names
                    # The YAML has nested structure, but Pydantic uses flat field names
                    # We'll extract relevant values from nested structure
                    flattened_data = {}
                    
                    # Global service configuration
                    if 'global' in raw_yaml_data:
                        global_cfg = raw_yaml_data['global']
                        if 'service_name' in global_cfg:
                            flattened_data['SERVICE_NAME'] = global_cfg['service_name']
                        if 'log_level' in global_cfg:
                            flattened_data['LOG_LEVEL'] = global_cfg['log_level']
                        if 'debug' in global_cfg:
                            flattened_data['DEBUG'] = global_cfg['debug']
                    
                    # Database configuration
                    if 'database' in raw_yaml_data:
                        db_cfg = raw_yaml_data['database']
                        if 'mongodb_url' in db_cfg and db_cfg['mongodb_url']:
                            flattened_data['MONGODB_URL'] = db_cfg['mongodb_url']
                        if 'mongodb_database' in db_cfg:
                            flattened_data['MONGODB_DATABASE'] = db_cfg['mongodb_database']
                        if 'redis_url' in db_cfg and db_cfg['redis_url']:
                            flattened_data['REDIS_URL'] = db_cfg['redis_url']
                    
                    # Monitoring configuration
                    if 'monitoring' in raw_yaml_data:
                        mon_cfg = raw_yaml_data['monitoring']
                        if 'metrics_enabled' in mon_cfg:
                            flattened_data['METRICS_ENABLED'] = mon_cfg['metrics_enabled']
                        if 'metrics_port' in mon_cfg:
                            flattened_data['METRICS_PORT'] = mon_cfg['metrics_port']
                        if 'health_check_interval' in mon_cfg:
                            flattened_data['HEALTH_CHECK_INTERVAL'] = mon_cfg['health_check_interval']
                        if 'health_check_enabled' in mon_cfg:
                            flattened_data['HEALTH_CHECK_ENABLED'] = mon_cfg['health_check_enabled']
                    
                    # Node pool configuration
                    if 'node_pool' in raw_yaml_data:
                        pool_cfg = raw_yaml_data['node_pool']
                        if 'limits' in pool_cfg:
                            limits = pool_cfg['limits']
                            if 'max_nodes_per_pool' in limits:
                                flattened_data['MAX_NODES_PER_POOL'] = limits['max_nodes_per_pool']
                            if 'min_nodes_per_pool' in limits:
                                flattened_data['MIN_NODES_PER_POOL'] = limits['min_nodes_per_pool']
                        if 'management' in pool_cfg:
                            mgmt = pool_cfg['management']
                            if 'pool_health_check_interval_seconds' in mgmt:
                                flattened_data['POOL_HEALTH_CHECK_INTERVAL'] = mgmt['pool_health_check_interval_seconds']
                            if 'pool_sync_interval_seconds' in mgmt:
                                flattened_data['POOL_SYNC_INTERVAL'] = mgmt['pool_sync_interval_seconds']
                    
                    # PoOT configuration
                    if 'poot' in raw_yaml_data:
                        poot_cfg = raw_yaml_data['poot']
                        if 'calculation_interval_seconds' in poot_cfg:
                            flattened_data['POOT_CALCULATION_INTERVAL'] = poot_cfg['calculation_interval_seconds']
                        if 'score_threshold' in poot_cfg:
                            flattened_data['POOT_SCORE_THRESHOLD'] = poot_cfg['score_threshold']
                        if 'challenge_validity_minutes' in poot_cfg:
                            flattened_data['POOT_CHALLENGE_VALIDITY_MINUTES'] = poot_cfg['challenge_validity_minutes']
                        if 'proof_cache_minutes' in poot_cfg:
                            flattened_data['POOT_PROOF_CACHE_MINUTES'] = poot_cfg['proof_cache_minutes']
                        if 'min_token_stake_amount' in poot_cfg:
                            flattened_data['MIN_TOKEN_STAKE_AMOUNT'] = poot_cfg['min_token_stake_amount']
                        if 'max_validation_attempts' in poot_cfg:
                            flattened_data['MAX_VALIDATION_ATTEMPTS'] = poot_cfg['max_validation_attempts']
                        if 'challenge_complexity_bytes' in poot_cfg:
                            flattened_data['CHALLENGE_COMPLEXITY_BYTES'] = poot_cfg['challenge_complexity_bytes']
                        if 'validation_required' in poot_cfg:
                            flattened_data['POOT_VALIDATION_REQUIRED'] = poot_cfg['validation_required']
                    
                    # Payout configuration
                    if 'payout' in raw_yaml_data:
                        payout_cfg = raw_yaml_data['payout']
                        if 'processing_interval_seconds' in payout_cfg:
                            flattened_data['PAYOUT_PROCESSING_INTERVAL'] = payout_cfg['processing_interval_seconds']
                        if 'threshold_usdt' in payout_cfg:
                            flattened_data['PAYOUT_THRESHOLD_USDT'] = payout_cfg['threshold_usdt']
                        if 'minimum_amount_usdt' in payout_cfg:
                            flattened_data['PAYOUT_MIN_AMOUNT_USDT'] = payout_cfg['minimum_amount_usdt']
                        if 'maximum_amount_usdt' in payout_cfg:
                            flattened_data['PAYOUT_MAX_AMOUNT_USDT'] = payout_cfg['maximum_amount_usdt']
                        if 'fees' in payout_cfg and 'fee_percentage' in payout_cfg['fees']:
                            flattened_data['PAYOUT_PROCESSING_FEE_PERCENT'] = payout_cfg['fees']['fee_percentage']
                    
                    # External services
                    if 'external_services' in raw_yaml_data:
                        ext_svc = raw_yaml_data['external_services']
                        if 'api_gateway_url' in ext_svc and ext_svc['api_gateway_url']:
                            flattened_data['API_GATEWAY_URL'] = ext_svc['api_gateway_url']
                        if 'blockchain_engine_url' in ext_svc and ext_svc['blockchain_engine_url']:
                            flattened_data['BLOCKCHAIN_ENGINE_URL'] = ext_svc['blockchain_engine_url']
                    
                    # Filter out empty string values from YAML (they should come from env vars)
                    # Empty strings in YAML indicate "use environment variable", so we remove them
                    yaml_data = {k: v for k, v in flattened_data.items() if v != ""}
                    
                except Exception as e:
                    logger.warning(f"Failed to load YAML configuration from {yaml_file_path}: {str(e)}")
                    logger.warning("Continuing with environment variables and defaults only")
                    yaml_data = {}
        elif config_file:
            # User specified a file but it doesn't exist - this is an error
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
        else:
            logger.debug("No YAML configuration file found, using environment variables and defaults only")
        
        # Create configuration object
        # Priority: Environment variables (highest) > YAML values > Field defaults (lowest)
        # Strategy: Create config from YAML, then override with environment variables
        
        if yaml_data:
            try:
                # Step 1: Create config from YAML data (YAML provides defaults)
                config = NodeManagementSettings.model_validate(yaml_data)
                
                # Step 2: Create config normally to get environment variable values
                env_config = NodeManagementSettings()
                
                # Step 3: Override YAML config with environment variable values
                # Environment variables take highest priority
                env_dict = env_config.model_dump()
                yaml_dict = config.model_dump()
                
                # For each field, if env_config value differs from yaml_config value,
                # use the env value (environment variable was set)
                for key in env_dict.keys():
                    env_value = env_dict[key]
                    yaml_value = yaml_dict.get(key)
                    
                    # If values differ, environment variable was set - use it
                    if env_value != yaml_value:
                        try:
                            setattr(config, key, env_value)
                        except Exception as e:
                            logger.debug(f"Could not override {key} with environment variable: {str(e)}")
                
            except Exception as e:
                logger.warning(f"Error merging YAML with environment variables: {str(e)}")
                logger.warning("Falling back to environment variables and defaults only")
                config = NodeManagementSettings()
        else:
            # Load from environment variables and defaults only
            config = NodeManagementSettings()
        
        logger.info("Configuration loaded successfully")
        return config
        
    except FileNotFoundError:
        # Re-raise file not found errors
        raise
    except Exception as e:
        logger.error(f"Failed to load configuration: {str(e)}")
        raise
