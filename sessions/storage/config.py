#!/usr/bin/env python3
"""
Lucid Session Storage Configuration
Configuration management for session storage service
"""

import os
import json
from typing import Dict, Any, Optional
from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings
import logging

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

logger = logging.getLogger(__name__)


class StorageSettings(BaseSettings):
    """Storage configuration settings"""
    
    # Service Configuration
    SERVICE_NAME: str = "lucid-session-storage"
    SERVICE_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # Network Configuration (from docker-compose)
    # Note: SESSION_STORAGE_HOST and SESSION_STORAGE_PORT are provided by docker-compose
    # HOST is the bind address (should be 0.0.0.0), PORT is the service port
    HOST: str = "0.0.0.0"  # Bind address (always 0.0.0.0 for container binding)
    PORT: int = 8082  # Default port (overridden by SESSION_STORAGE_PORT from docker-compose)
    SESSION_STORAGE_HOST: str = ""  # From docker-compose: SESSION_STORAGE_HOST (service name, not bind address)
    SESSION_STORAGE_PORT: str = ""  # From docker-compose: SESSION_STORAGE_PORT (string, converted to int)
    
    # Database Configuration (from .env.foundation, .env.core)
    MONGODB_URL: str = ""  # Required from environment: MONGODB_URL or MONGO_URL
    REDIS_URL: str = ""  # Required from environment: REDIS_URL
    
    # Storage Configuration (use volume mount paths from docker-compose)
    LUCID_STORAGE_PATH: str = "/app/data/sessions"  # Volume: /data/session-storage:/app/data
    LUCID_CHUNK_STORE_PATH: str = "/app/data/chunks"  # Volume: /data/session-storage:/app/data
    TEMP_STORAGE_PATH: str = "/tmp/storage"  # tmpfs mount: /tmp:size=200m
    
    # Chunk Configuration
    LUCID_CHUNK_SIZE_MB: int = 10
    LUCID_COMPRESSION_LEVEL: int = 6
    LUCID_COMPRESSION_ALGORITHM: str = "zstd"  # zstd, lz4, gzip
    LUCID_ENCRYPTION_ENABLED: bool = True
    
    # Session Configuration
    LUCID_RETENTION_DAYS: int = 30
    LUCID_MAX_SESSIONS: int = 1000
    LUCID_MAX_CHUNKS_PER_SESSION: int = 100000
    LUCID_CLEANUP_INTERVAL_HOURS: int = 24
    
    # Backup Configuration
    LUCID_BACKUP_ENABLED: bool = True
    LUCID_BACKUP_RETENTION_DAYS: int = 7
    
    # Performance Configuration
    SESSION_STORAGE_WORKERS: int = 1  # Uvicorn workers
    MAX_STORAGE_SIZE_GB: int = 1000
    
    # Monitoring Configuration
    METRICS_ENABLED: bool = True
    METRICS_PORT: int = 9217
    HEALTH_CHECK_INTERVAL: int = 30
    
    # CORS Configuration (from .env.application)
    CORS_ORIGINS: str = "*"  # From environment: CORS_ORIGINS (comma-separated list, default: "*")
    
    # Configuration File Path (optional - for external config file support)
    SESSION_STORAGE_CONFIG_FILE: str = ""  # Path to YAML/JSON config file (optional)
    
    @field_validator('LUCID_CHUNK_SIZE_MB')
    @classmethod
    def validate_chunk_size(cls, v):
        if v < 1 or v > 100:
            raise ValueError('LUCID_CHUNK_SIZE_MB must be between 1 and 100 MB')
        return v
    
    @field_validator('LUCID_COMPRESSION_LEVEL')
    @classmethod
    def validate_compression_level(cls, v):
        if v < 1 or v > 9:
            raise ValueError('LUCID_COMPRESSION_LEVEL must be between 1 and 9')
        return v
    
    @field_validator('LUCID_COMPRESSION_ALGORITHM')
    @classmethod
    def validate_compression_algorithm(cls, v):
        allowed = ['zstd', 'lz4', 'gzip']
        if v not in allowed:
            raise ValueError(f'LUCID_COMPRESSION_ALGORITHM must be one of {allowed}')
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
        return v
    
    @field_validator('MONGODB_URL')
    @classmethod
    def validate_mongodb_url(cls, v):
        if not v or v == "":
            raise ValueError('MONGODB_URL or MONGO_URL environment variable is required but not set')
        if "localhost" in v or "127.0.0.1" in v:
            raise ValueError('MONGODB_URL must not use localhost - use service name (e.g., lucid-mongodb)')
        return v
    
    @field_validator('REDIS_URL')
    @classmethod
    def validate_redis_url(cls, v):
        if not v or v == "":
            raise ValueError('REDIS_URL environment variable is required but not set')
        if "localhost" in v or "127.0.0.1" in v:
            raise ValueError('REDIS_URL must not use localhost - use service name (e.g., lucid-redis)')
        return v
    
    model_config = {
        # pydantic-settings will read from environment variables
        # docker-compose provides: .env.secrets, .env.core, .env.application, .env.foundation
        "env_file": None,  # Don't read .env file directly - use environment variables from docker-compose
        "case_sensitive": True,
        "env_file_encoding": "utf-8"
    }


class StorageConfig:
    """
    Main storage configuration class
    Manages all storage-related configuration
    """
    
    def __init__(self, settings: Optional[StorageSettings] = None, config_file: Optional[str] = None):
        """
        Initialize StorageConfig.
        
        Args:
            settings: Optional StorageSettings instance. If not provided, will load from YAML/JSON and environment variables.
            config_file: Optional path to YAML/JSON configuration file. Only used if settings is None.
                       If not provided, will check SESSION_STORAGE_CONFIG_FILE environment variable.
        """
        try:
            if settings is None:
                # Determine config file path: explicit parameter > env var > default locations
                if config_file is None:
                    config_file = os.getenv('SESSION_STORAGE_CONFIG_FILE', '')
                    if not config_file:
                        config_file = None
                
                # Load configuration from YAML/JSON and environment variables
                self.settings = load_config(config_file)
            else:
                self.settings = settings
            
            # Validate critical environment variables
            self._validate_required_env_vars()
            
            # Override PORT from SESSION_STORAGE_PORT if provided (HOST always stays 0.0.0.0)
            # SESSION_STORAGE_HOST is the service name for URLs, not the bind address
            if hasattr(self.settings, 'SESSION_STORAGE_PORT') and self.settings.SESSION_STORAGE_PORT:
                try:
                    self.settings.PORT = int(self.settings.SESSION_STORAGE_PORT)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid SESSION_STORAGE_PORT value: {self.settings.SESSION_STORAGE_PORT}, using default {self.settings.PORT}")
            
            # Handle MONGODB_URL vs MONGO_URL
            if not self.settings.MONGODB_URL:
                mongodb_url = os.getenv('MONGODB_URL') or os.getenv('MONGO_URL')
                if mongodb_url:
                    self.settings.MONGODB_URL = mongodb_url
            
            # Parse CORS origins (comma-separated list or "*")
            if self.settings.CORS_ORIGINS == "*":
                self.cors_origins = ["*"]
            else:
                self.cors_origins = [origin.strip() for origin in self.settings.CORS_ORIGINS.split(",") if origin.strip()]
            
            logger.info("Storage configuration initialized")
        except Exception as e:
            logger.error(f"Failed to initialize storage configuration: {str(e)}")
            raise
    
    def _validate_required_env_vars(self):
        """Validate that required environment variables are set"""
        # MONGODB_URL validation is handled by Pydantic validator
        # But we need to check if it's empty and try MONGO_URL as fallback
        if not self.settings.MONGODB_URL:
            mongodb_url = os.getenv('MONGODB_URL') or os.getenv('MONGO_URL')
            if mongodb_url:
                self.settings.MONGODB_URL = mongodb_url
        
        # REDIS_URL validation is handled by Pydantic validator
        # The validator will raise if it's empty
    
    def get_storage_config_dict(self) -> Dict[str, Any]:
        """Get storage configuration as dictionary (for StorageConfig dataclass)"""
        return {
            "base_path": self.settings.LUCID_STORAGE_PATH,
            "chunk_size_mb": self.settings.LUCID_CHUNK_SIZE_MB,
            "compression_level": self.settings.LUCID_COMPRESSION_LEVEL,
            "encryption_enabled": self.settings.LUCID_ENCRYPTION_ENABLED,
            "retention_days": self.settings.LUCID_RETENTION_DAYS,
            "max_sessions": self.settings.LUCID_MAX_SESSIONS,
            "cleanup_interval_hours": self.settings.LUCID_CLEANUP_INTERVAL_HOURS
        }
    
    def get_chunk_store_config_dict(self) -> Dict[str, Any]:
        """Get chunk store configuration as dictionary (for ChunkStoreConfig dataclass)"""
        return {
            "base_path": self.settings.LUCID_CHUNK_STORE_PATH,
            "compression_algorithm": self.settings.LUCID_COMPRESSION_ALGORITHM,
            "compression_level": self.settings.LUCID_COMPRESSION_LEVEL,
            "chunk_size_mb": self.settings.LUCID_CHUNK_SIZE_MB,
            "max_chunks_per_session": self.settings.LUCID_MAX_CHUNKS_PER_SESSION,
            "cleanup_interval_hours": self.settings.LUCID_CLEANUP_INTERVAL_HOURS,
            "backup_enabled": self.settings.LUCID_BACKUP_ENABLED,
            "backup_retention_days": self.settings.LUCID_BACKUP_RETENTION_DAYS
        }
    
    def get_settings(self) -> StorageSettings:
        """Get the underlying settings object"""
        return self.settings
    
    def get_environment_variables(self) -> Dict[str, str]:
        """Get environment variables for configuration"""
        return {
            "SERVICE_NAME": self.settings.SERVICE_NAME,
            "SERVICE_VERSION": self.settings.SERVICE_VERSION,
            "DEBUG": str(self.settings.DEBUG),
            "LOG_LEVEL": self.settings.LOG_LEVEL,
            "HOST": self.settings.HOST,
            "PORT": str(self.settings.PORT),
            "MONGODB_URL": "***REDACTED***",
            "REDIS_URL": "***REDACTED***",
            "LUCID_STORAGE_PATH": self.settings.LUCID_STORAGE_PATH,
            "LUCID_CHUNK_STORE_PATH": self.settings.LUCID_CHUNK_STORE_PATH,
            "LUCID_CHUNK_SIZE_MB": str(self.settings.LUCID_CHUNK_SIZE_MB),
            "LUCID_COMPRESSION_LEVEL": str(self.settings.LUCID_COMPRESSION_LEVEL),
            "LUCID_COMPRESSION_ALGORITHM": self.settings.LUCID_COMPRESSION_ALGORITHM,
            "LUCID_ENCRYPTION_ENABLED": str(self.settings.LUCID_ENCRYPTION_ENABLED),
            "LUCID_RETENTION_DAYS": str(self.settings.LUCID_RETENTION_DAYS),
            "LUCID_MAX_SESSIONS": str(self.settings.LUCID_MAX_SESSIONS),
            "LUCID_MAX_CHUNKS_PER_SESSION": str(self.settings.LUCID_MAX_CHUNKS_PER_SESSION),
            "LUCID_CLEANUP_INTERVAL_HOURS": str(self.settings.LUCID_CLEANUP_INTERVAL_HOURS),
            "LUCID_BACKUP_ENABLED": str(self.settings.LUCID_BACKUP_ENABLED),
            "LUCID_BACKUP_RETENTION_DAYS": str(self.settings.LUCID_BACKUP_RETENTION_DAYS),
        }


def load_config(config_file: Optional[str] = None) -> StorageSettings:
    """
    Load configuration from YAML/JSON file and environment variables.
    
    Configuration loading priority (highest to lowest):
    1. Environment variables (highest priority - override everything)
    2. YAML/JSON configuration file values
    3. Pydantic field defaults (lowest priority)
    
    Supports both YAML (.yaml, .yml) and JSON (.json) configuration files.
    
    Args:
        config_file: Optional path to YAML/JSON configuration file. If not provided,
                     will check SESSION_STORAGE_CONFIG_FILE env var, then look for
                     'config.yaml' or 'config.json' in default locations.
        
    Returns:
        Loaded StorageSettings object with environment variables overriding file values
        
    Raises:
        FileNotFoundError: If config_file is provided but doesn't exist
        ValueError: If configuration validation fails or file format is invalid
        ImportError: If PyYAML is not available for YAML files (JSON always available)
    """
    try:
        config_data: Dict[str, Any] = {}
        config_file_path: Optional[Path] = None
        config_format: Optional[str] = None  # 'yaml', 'json', or None
        
        # Determine config file path
        if config_file:
            config_file_path = Path(config_file)
            # Detect format from extension
            if config_file_path.suffix.lower() in ['.yaml', '.yml']:
                config_format = 'yaml'
            elif config_file_path.suffix.lower() == '.json':
                config_format = 'json'
            else:
                # Try to detect from content or default to YAML
                config_format = 'yaml'
        else:
            # Check environment variable first
            env_config_file = os.getenv('SESSION_STORAGE_CONFIG_FILE', '')
            if env_config_file:
                config_file_path = Path(env_config_file)
                if config_file_path.suffix.lower() in ['.yaml', '.yml']:
                    config_format = 'yaml'
                elif config_file_path.suffix.lower() == '.json':
                    config_format = 'json'
                else:
                    config_format = 'yaml'  # Default to YAML
            else:
                # Try default locations (YAML first, then JSON)
                default_locations = [
                    (Path(__file__).parent / "config.yaml", 'yaml'),
                    (Path(__file__).parent / "config.json", 'json'),
                    (Path(__file__).parent.parent / "storage" / "config.yaml", 'yaml'),
                    (Path(__file__).parent.parent / "storage" / "config.json", 'json'),
                ]
                for loc, fmt in default_locations:
                    if loc.exists():
                        config_file_path = loc
                        config_format = fmt
                        break
        
        # Load config file if it exists
        if config_file_path and config_file_path.exists():
            try:
                if config_format == 'json':
                    # Load JSON file
                    with open(config_file_path, 'r', encoding='utf-8') as f:
                        config_data = json.load(f) or {}
                    logger.info(f"Loaded JSON configuration from {config_file_path}")
                elif config_format == 'yaml':
                    # Load YAML file
                    if not YAML_AVAILABLE:
                        logger.warning(f"PyYAML not available, cannot load YAML file {config_file_path}")
                        logger.warning("Falling back to environment variables and defaults only")
                        config_data = {}
                    else:
                        with open(config_file_path, 'r', encoding='utf-8') as f:
                            config_data = yaml.safe_load(f) or {}
                        logger.info(f"Loaded YAML configuration from {config_file_path}")
                else:
                    # Try to auto-detect format
                    if config_file_path.suffix.lower() in ['.yaml', '.yml']:
                        if YAML_AVAILABLE:
                            with open(config_file_path, 'r', encoding='utf-8') as f:
                                config_data = yaml.safe_load(f) or {}
                            logger.info(f"Loaded YAML configuration from {config_file_path} (auto-detected)")
                        else:
                            logger.warning(f"PyYAML not available, cannot load YAML file {config_file_path}")
                            config_data = {}
                    elif config_file_path.suffix.lower() == '.json':
                        with open(config_file_path, 'r', encoding='utf-8') as f:
                            config_data = json.load(f) or {}
                        logger.info(f"Loaded JSON configuration from {config_file_path} (auto-detected)")
                    else:
                        logger.warning(f"Unknown config file format: {config_file_path.suffix}")
                        config_data = {}
                
                # Filter out empty string values (they should come from env vars)
                # Empty strings in config files indicate "use environment variable"
                config_data = {k: v for k, v in config_data.items() if v != ""}
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in configuration file {config_file_path}: {str(e)}")
                logger.error("JSON syntax error - check file format. Continuing with environment variables and defaults only")
                config_data = {}
            except yaml.YAMLError as e:
                logger.error(f"Invalid YAML in configuration file {config_file_path}: {str(e)}")
                logger.error("YAML syntax error - check file format. Continuing with environment variables and defaults only")
                config_data = {}
            except Exception as e:
                logger.error(f"Failed to load configuration file {config_file_path}: {str(e)}")
                logger.error("Continuing with environment variables and defaults only")
                config_data = {}
        elif config_file or os.getenv('SESSION_STORAGE_CONFIG_FILE'):
            # User specified a file but it doesn't exist - this is an error
            specified_file = config_file or os.getenv('SESSION_STORAGE_CONFIG_FILE')
            raise FileNotFoundError(
                f"Configuration file not found: {specified_file}. "
                f"Please check the path or remove SESSION_STORAGE_CONFIG_FILE environment variable."
            )
        else:
            logger.debug("No configuration file found, using environment variables and defaults only")
        
        # Create configuration object
        # Priority: Environment variables (highest) > File values (YAML/JSON) > Field defaults (lowest)
        # Strategy: Create config from file data, then override with environment variables
        
        if config_data:
            try:
                # Step 1: Create config from file data (file provides defaults)
                config = StorageSettings.model_validate(config_data)
                
                # Step 2: Create config normally to get environment variable values
                env_config = StorageSettings()
                
                # Step 3: Override file config with environment variable values
                # Environment variables take highest priority
                env_dict = env_config.model_dump()
                file_dict = config.model_dump()
                
                # For each field, if env_config value differs from file_config value,
                # use the env value (environment variable was set)
                for key in env_dict.keys():
                    env_value = env_dict[key]
                    file_value = file_dict.get(key)
                    
                    # If values differ, environment variable was set - use it
                    if env_value != file_value:
                        try:
                            setattr(config, key, env_value)
                        except Exception as e:
                            logger.debug(f"Could not override {key} with environment variable: {str(e)}")
                
                file_type = config_format.upper() if config_format else 'CONFIG'
                logger.info(f"Configuration loaded from {file_type} file with environment variable overrides")
                
            except Exception as e:
                file_type = config_format or 'config'
                logger.error(f"Error merging {file_type} file with environment variables: {str(e)}")
                logger.error("Configuration file validation failed. Falling back to environment variables and defaults only")
                logger.debug(f"Validation error details: {str(e)}", exc_info=True)
                config = StorageSettings()
        else:
            # Load from environment variables and defaults only
            config = StorageSettings()
            logger.info("Configuration loaded from environment variables and defaults only")
        
        # Validate final configuration
        try:
            # Additional validation beyond Pydantic validators
            if config.LUCID_STORAGE_PATH and not config.LUCID_STORAGE_PATH.startswith('/'):
                logger.warning(f"LUCID_STORAGE_PATH should be absolute path, got: {config.LUCID_STORAGE_PATH}")
            if config.LUCID_CHUNK_STORE_PATH and not config.LUCID_CHUNK_STORE_PATH.startswith('/'):
                logger.warning(f"LUCID_CHUNK_STORE_PATH should be absolute path, got: {config.LUCID_CHUNK_STORE_PATH}")
        except Exception as e:
            logger.debug(f"Additional validation check failed (non-critical): {str(e)}")
        
        logger.info("Configuration loaded and validated successfully")
        return config
        
    except FileNotFoundError:
        # Re-raise file not found errors with helpful message
        raise
    except ValueError as e:
        # Re-raise validation errors with context
        logger.error(f"Configuration validation failed: {str(e)}")
        logger.error("Please check your configuration file format and values")
        raise ValueError(f"Configuration validation failed: {str(e)}") from e
    except Exception as e:
        logger.error(f"Failed to load configuration: {str(e)}")
        logger.error("This may indicate a problem with the configuration file or environment variables")
        raise


def create_default_config_file(config_path: str = "config.yaml"):
    """
    Create a default configuration file in YAML or JSON format.
    
    Args:
        config_path: Path to create the configuration file (supports .yaml, .yml, or .json extension)
        
    Raises:
        ImportError: If PyYAML is not available for YAML files
        IOError: If file cannot be written
        ValueError: If file extension is not supported
    """
    config_file_path = Path(config_path)
    file_extension = config_file_path.suffix.lower()
    
    if file_extension in ['.yaml', '.yml']:
        if not YAML_AVAILABLE:
            raise ImportError("PyYAML is required to create YAML configuration files. Install it with: pip install PyYAML")
    elif file_extension == '.json':
        # JSON is always available (built-in)
        pass
    else:
        raise ValueError(f"Unsupported configuration file format: {file_extension}. Use .yaml, .yml, or .json")
    
    default_config = {
        "SERVICE_NAME": "lucid-session-storage",
        "SERVICE_VERSION": "1.0.0",
        "DEBUG": False,
        "LOG_LEVEL": "INFO",
        "HOST": "0.0.0.0",
        "PORT": 8082,  # Default port (override with SESSION_STORAGE_PORT env var)
        "SESSION_STORAGE_HOST": "",  # Set via SESSION_STORAGE_HOST env var
        "SESSION_STORAGE_PORT": "",  # Set via SESSION_STORAGE_PORT env var
        "MONGODB_URL": "",  # Must be set from MONGODB_URL or MONGO_URL env var (required)
        "REDIS_URL": "",  # Must be set from REDIS_URL env var (required)
        "LUCID_STORAGE_PATH": "/app/data/sessions",
        "LUCID_CHUNK_STORE_PATH": "/app/data/chunks",
        "TEMP_STORAGE_PATH": "/tmp/storage",
        "LUCID_CHUNK_SIZE_MB": 10,
        "LUCID_COMPRESSION_LEVEL": 6,
        "LUCID_COMPRESSION_ALGORITHM": "zstd",
        "LUCID_ENCRYPTION_ENABLED": True,
        "LUCID_RETENTION_DAYS": 30,
        "LUCID_MAX_SESSIONS": 1000,
        "LUCID_MAX_CHUNKS_PER_SESSION": 100000,
        "LUCID_CLEANUP_INTERVAL_HOURS": 24,
        "LUCID_BACKUP_ENABLED": True,
        "LUCID_BACKUP_RETENTION_DAYS": 7,
        "SESSION_STORAGE_WORKERS": 1,
        "MAX_STORAGE_SIZE_GB": 1000,
        "METRICS_ENABLED": True,
        "METRICS_PORT": 9217,
        "HEALTH_CHECK_INTERVAL": 30,
        "CORS_ORIGINS": "*"
    }
    
    try:
        config_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        if file_extension in ['.yaml', '.yml']:
            with open(config_file_path, 'w', encoding='utf-8') as f:
                yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)
            logger.info(f"Created default YAML configuration file: {config_path}")
        elif file_extension == '.json':
            with open(config_file_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, sort_keys=False)
            logger.info(f"Created default JSON configuration file: {config_path}")
        
    except Exception as e:
        logger.error(f"Failed to create configuration file: {str(e)}")
        raise


# Global configuration instance
_config: Optional[StorageSettings] = None


def get_config() -> StorageSettings:
    """
    Get the global configuration instance.
    
    Returns:
        Global StorageSettings instance
    """
    global _config
    if _config is None:
        _config = load_config()
    return _config


def set_config(new_config: StorageSettings):
    """
    Set the global configuration instance.
    
    Args:
        new_config: New StorageSettings instance
    """
    global _config
    _config = new_config
    logger.info("Global configuration updated")

