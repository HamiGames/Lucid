#!/usr/bin/env python3
"""
Lucid Session Management Pipeline Configuration
Configuration management for session processing pipelines
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from pydantic import field_validator
from pydantic_settings import BaseSettings
import logging

logger = logging.getLogger(__name__)

@dataclass
class WorkerConfig:
    """Worker configuration for pipeline stages"""
    count: int = 1
    buffer_size: int = 1000
    timeout_seconds: int = 30
    retry_count: int = 3
    max_memory_mb: int = 512

@dataclass
class StageConfig:
    """Configuration for a pipeline stage"""
    stage_name: str
    stage_type: str
    workers: WorkerConfig = field(default_factory=WorkerConfig)
    enabled: bool = True
    priority: int = 1
    dependencies: list = field(default_factory=list)

class PipelineSettings(BaseSettings):
    """Pipeline configuration settings"""
    
    # Service Configuration
    SERVICE_NAME: str = "lucid-pipeline-manager"
    SERVICE_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # Pipeline Configuration
    MAX_CONCURRENT_SESSIONS: int = 100
    CHUNK_SIZE_MB: int = 10
    COMPRESSION_LEVEL: int = 6
    PIPELINE_TIMEOUT_SECONDS: int = 300
    
    # Worker Configuration (6 states as required by Step 15)
    RECORDER_WORKERS: int = 2
    CHUNK_WORKERS: int = 3
    COMPRESSOR_WORKERS: int = 4
    ENCRYPTOR_WORKERS: int = 4
    MERKLE_WORKERS: int = 2
    STORAGE_WORKERS: int = 2
    
    # Buffer Configuration (6 states)
    RECORDER_BUFFER_SIZE: int = 1000
    CHUNK_BUFFER_SIZE: int = 800
    COMPRESSOR_BUFFER_SIZE: int = 500
    ENCRYPTOR_BUFFER_SIZE: int = 500
    MERKLE_BUFFER_SIZE: int = 300
    STORAGE_BUFFER_SIZE: int = 100
    
    # Timeout Configuration (6 states)
    RECORDER_TIMEOUT: int = 60
    CHUNK_TIMEOUT: int = 45
    COMPRESSOR_TIMEOUT: int = 30
    ENCRYPTOR_TIMEOUT: int = 30
    MERKLE_TIMEOUT: int = 20
    STORAGE_TIMEOUT: int = 60
    
    # Retry Configuration (6 states)
    RECORDER_RETRY_COUNT: int = 3
    CHUNK_RETRY_COUNT: int = 3
    COMPRESSOR_RETRY_COUNT: int = 3
    ENCRYPTOR_RETRY_COUNT: int = 3
    MERKLE_RETRY_COUNT: int = 3
    STORAGE_RETRY_COUNT: int = 3
    
    # Memory Configuration (6 states)
    RECORDER_MAX_MEMORY_MB: int = 1024
    CHUNK_MAX_MEMORY_MB: int = 768
    COMPRESSOR_MAX_MEMORY_MB: int = 512
    ENCRYPTOR_MAX_MEMORY_MB: int = 512
    MERKLE_MAX_MEMORY_MB: int = 256
    STORAGE_MAX_MEMORY_MB: int = 1024
    
    # Database Configuration (from .env.foundation, .env.core)
    MONGODB_URL: str = ""  # Required from environment: MONGODB_URL
    REDIS_URL: str = ""  # Required from environment: REDIS_URL
    ELASTICSEARCH_URL: str = ""  # Optional from environment: ELASTICSEARCH_URL
    
    # Storage Configuration (use volume mount paths from docker-compose)
    CHUNK_STORAGE_PATH: str = "/app/data/chunks"  # Volume: /data/session-pipeline:/app/data
    SESSION_STORAGE_PATH: str = "/app/data/sessions"  # Volume: /data/session-pipeline:/app/data
    TEMP_STORAGE_PATH: str = "/tmp/pipeline"  # tmpfs mount: /tmp:size=200m
    MAX_STORAGE_SIZE_GB: int = 1000
    
    # Network Configuration (from .env.application, docker-compose)
    # Note: SESSION_PIPELINE_HOST and SESSION_PIPELINE_PORT are provided by docker-compose
    # HOST is the bind address (should be 0.0.0.0), PORT is the service port
    HOST: str = "0.0.0.0"  # Bind address (always 0.0.0.0 for container binding)
    PORT: int = 8083  # Default port (overridden by SESSION_PIPELINE_PORT from docker-compose)
    SESSION_PIPELINE_HOST: str = ""  # From docker-compose: SESSION_PIPELINE_HOST (service name, not bind address)
    SESSION_PIPELINE_PORT: str = ""  # From docker-compose: SESSION_PIPELINE_PORT (string, converted to int)
    GRPC_PORT: int = 9083  # Optional, not used currently
    
    # Security Configuration (from .env.secrets, .env.application)
    SECRET_KEY: str = ""  # Required from environment: SECRET_KEY or BLOCKCHAIN_SECRET_KEY or JWT_SECRET_KEY
    ENCRYPTION_KEY: str = ""  # Required from environment: ENCRYPTION_KEY
    JWT_SECRET_KEY: str = ""  # Required from environment: JWT_SECRET_KEY (used instead of JWT_SECRET)
    
    # Monitoring Configuration
    METRICS_ENABLED: bool = True
    METRICS_PORT: int = 9093
    HEALTH_CHECK_INTERVAL: int = 30
    
    # Performance Configuration
    ENABLE_COMPRESSION: bool = True
    ENABLE_ENCRYPTION: bool = True
    ENABLE_DEDUPLICATION: bool = True
    PARALLEL_PROCESSING: bool = True
    
    # Quality Configuration (from .env.application, defaults if not set)
    DEFAULT_QUALITY: str = ""  # From environment: DEFAULT_QUALITY (default: "high")
    DEFAULT_FRAME_RATE: int = 0  # From environment: DEFAULT_FRAME_RATE (default: 30)
    DEFAULT_RESOLUTION: str = ""  # From environment: DEFAULT_RESOLUTION (default: "1920x1080")
    QUALITY_THRESHOLD: float = 0.8
    
    # CORS Configuration (from .env.application)
    CORS_ORIGINS: str = "*"  # From environment: CORS_ORIGINS (comma-separated list, default: "*")
    
    # Integration Service URLs (from .env.application, .env.core)
    BLOCKCHAIN_ENGINE_URL: str = ""  # From environment: BLOCKCHAIN_ENGINE_URL (e.g., http://blockchain-engine:8084)
    NODE_MANAGEMENT_URL: str = ""  # From environment: NODE_MANAGEMENT_URL (e.g., http://node-management:8095)
    API_GATEWAY_URL: str = ""  # From environment: API_GATEWAY_URL (e.g., http://api-gateway:8080)
    AUTH_SERVICE_URL: str = ""  # From environment: AUTH_SERVICE_URL (e.g., http://lucid-auth-service:8089)
    SESSION_RECORDER_URL: str = ""  # From environment: SESSION_RECORDER_URL (e.g., http://session-recorder:8090)
    SESSION_PROCESSOR_URL: str = ""  # From environment: SESSION_PROCESSOR_URL (e.g., http://session-processor:8091)
    SESSION_STORAGE_URL: str = ""  # From environment: SESSION_STORAGE_URL (e.g., http://session-storage:8082)
    SESSION_API_URL: str = ""  # From environment: SESSION_API_URL (e.g., http://session-api:8087)
    
    # Integration Service Timeout Configuration (from .env.application)
    SERVICE_TIMEOUT_SECONDS: int = 30  # Default timeout for service calls
    SERVICE_RETRY_COUNT: int = 3  # Default retry count for service calls
    SERVICE_RETRY_DELAY_SECONDS: float = 1.0  # Default delay between retries
    
    @field_validator('CHUNK_SIZE_MB')
    @classmethod
    def validate_chunk_size(cls, v):
        if v < 1 or v > 100:
            raise ValueError('Chunk size must be between 1 and 100 MB')
        return v
    
    @field_validator('COMPRESSION_LEVEL')
    @classmethod
    def validate_compression_level(cls, v):
        if v < 1 or v > 9:
            raise ValueError('Compression level must be between 1 and 9')
        return v
    
    @field_validator('MAX_CONCURRENT_SESSIONS')
    @classmethod
    def validate_max_sessions(cls, v):
        if v < 1 or v > 1000:
            raise ValueError('Max concurrent sessions must be between 1 and 1000')
        return v
    
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
        if not v or v == "":
            raise ValueError('MONGODB_URL environment variable is required but not set')
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
    

class PipelineConfig:
    """
    Main pipeline configuration class
    Manages all pipeline-related configuration
    """
    
    def __init__(self, settings: Optional[PipelineSettings] = None):
        try:
            self.settings = settings or PipelineSettings()
            self.stage_configs: Dict[str, StageConfig] = {}
            
            # Validate critical environment variables
            self._validate_required_env_vars()
            
            # Override PORT from SESSION_PIPELINE_PORT if provided (HOST always stays 0.0.0.0)
            # SESSION_PIPELINE_HOST is the service name for URLs, not the bind address
            if hasattr(self.settings, 'SESSION_PIPELINE_PORT') and self.settings.SESSION_PIPELINE_PORT:
                try:
                    self.settings.PORT = int(self.settings.SESSION_PIPELINE_PORT)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid SESSION_PIPELINE_PORT value: {self.settings.SESSION_PIPELINE_PORT}, using default {self.settings.PORT}")
            
            # Set default values for quality settings if not provided
            import os
            if not self.settings.DEFAULT_QUALITY:
                self.settings.DEFAULT_QUALITY = os.getenv('DEFAULT_QUALITY', 'high')
            if self.settings.DEFAULT_FRAME_RATE == 0:
                self.settings.DEFAULT_FRAME_RATE = int(os.getenv('DEFAULT_FRAME_RATE', '30'))
            if not self.settings.DEFAULT_RESOLUTION:
                self.settings.DEFAULT_RESOLUTION = os.getenv('DEFAULT_RESOLUTION', '1920x1080')
            
            # Set integration service URLs from environment if not already set
            if not self.settings.BLOCKCHAIN_ENGINE_URL:
                self.settings.BLOCKCHAIN_ENGINE_URL = os.getenv('BLOCKCHAIN_ENGINE_URL', '')
            if not self.settings.NODE_MANAGEMENT_URL:
                self.settings.NODE_MANAGEMENT_URL = os.getenv('NODE_MANAGEMENT_URL', '')
            if not self.settings.API_GATEWAY_URL:
                self.settings.API_GATEWAY_URL = os.getenv('API_GATEWAY_URL', '')
            if not self.settings.AUTH_SERVICE_URL:
                self.settings.AUTH_SERVICE_URL = os.getenv('AUTH_SERVICE_URL', '')
            if not self.settings.SESSION_RECORDER_URL:
                self.settings.SESSION_RECORDER_URL = os.getenv('SESSION_RECORDER_URL', '')
            if not self.settings.SESSION_PROCESSOR_URL:
                self.settings.SESSION_PROCESSOR_URL = os.getenv('SESSION_PROCESSOR_URL', '')
            if not self.settings.SESSION_STORAGE_URL:
                self.settings.SESSION_STORAGE_URL = os.getenv('SESSION_STORAGE_URL', '')
            if not self.settings.SESSION_API_URL:
                self.settings.SESSION_API_URL = os.getenv('SESSION_API_URL', '')
            
            # Parse CORS origins (comma-separated list or "*")
            if self.settings.CORS_ORIGINS == "*":
                self.cors_origins = ["*"]
            else:
                self.cors_origins = [origin.strip() for origin in self.settings.CORS_ORIGINS.split(",") if origin.strip()]
            
            # Initialize stage configurations
            self._initialize_stage_configs()
            
            logger.info("Pipeline configuration initialized")
        except Exception as e:
            logger.error(f"Failed to initialize pipeline configuration: {str(e)}")
            raise
    
    def _validate_required_env_vars(self):
        """Validate that required environment variables are set"""
        import os
        
        # Check SECRET_KEY, ENCRYPTION_KEY, JWT_SECRET_KEY from environment
        if not self.settings.SECRET_KEY:
            # Try to get from alternative env var names
            self.settings.SECRET_KEY = os.getenv('SECRET_KEY') or os.getenv('BLOCKCHAIN_SECRET_KEY') or os.getenv('JWT_SECRET_KEY') or ""
        
        if not self.settings.ENCRYPTION_KEY:
            self.settings.ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY') or ""
        
        if not self.settings.JWT_SECRET_KEY:
            self.settings.JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY') or os.getenv('JWT_SECRET') or ""
        
        # Validate required values
        required_vars = {
            'MONGODB_URL': self.settings.MONGODB_URL,
            'REDIS_URL': self.settings.REDIS_URL,
        }
        
        missing = [name for name, value in required_vars.items() if not value or value == ""]
        
        # Validate secrets (check for placeholders)
        secret_checks = {
            'SECRET_KEY': self.settings.SECRET_KEY,
            'ENCRYPTION_KEY': self.settings.ENCRYPTION_KEY,
            'JWT_SECRET_KEY': self.settings.JWT_SECRET_KEY,
        }
        
        for name, value in secret_checks.items():
            if not value or value == "" or "your-" in str(value).lower() or "placeholder" in str(value).lower():
                missing.append(name)
        
        if missing:
            raise ValueError(f"Required environment variables not set or contain placeholders: {', '.join(missing)}. Please check .env.secrets, .env.core, and .env.application files.")
    
    def _initialize_stage_configs(self):
        """Initialize stage configurations for 6 states as required by Step 15"""
        self.stage_configs = {
            "recorder": StageConfig(
                stage_name="recorder",
                stage_type="recorder",
                workers=WorkerConfig(
                    count=self.settings.RECORDER_WORKERS,
                    buffer_size=self.settings.RECORDER_BUFFER_SIZE,
                    timeout_seconds=self.settings.RECORDER_TIMEOUT,
                    retry_count=self.settings.RECORDER_RETRY_COUNT,
                    max_memory_mb=self.settings.RECORDER_MAX_MEMORY_MB
                ),
                enabled=True,
                priority=1
            ),
            
            "chunk_generator": StageConfig(
                stage_name="chunk_generator",
                stage_type="chunk_generator",
                workers=WorkerConfig(
                    count=self.settings.CHUNK_WORKERS,
                    buffer_size=self.settings.CHUNK_BUFFER_SIZE,
                    timeout_seconds=self.settings.CHUNK_TIMEOUT,
                    retry_count=self.settings.CHUNK_RETRY_COUNT,
                    max_memory_mb=self.settings.CHUNK_MAX_MEMORY_MB
                ),
                enabled=True,
                priority=2,
                dependencies=["recorder"]
            ),
            
            "compressor": StageConfig(
                stage_name="compressor",
                stage_type="compressor",
                workers=WorkerConfig(
                    count=self.settings.COMPRESSOR_WORKERS,
                    buffer_size=self.settings.COMPRESSOR_BUFFER_SIZE,
                    timeout_seconds=self.settings.COMPRESSOR_TIMEOUT,
                    retry_count=self.settings.COMPRESSOR_RETRY_COUNT,
                    max_memory_mb=self.settings.COMPRESSOR_MAX_MEMORY_MB
                ),
                enabled=self.settings.ENABLE_COMPRESSION,
                priority=3,
                dependencies=["chunk_generator"]
            ),
            
            "encryptor": StageConfig(
                stage_name="encryptor",
                stage_type="encryptor",
                workers=WorkerConfig(
                    count=self.settings.ENCRYPTOR_WORKERS,
                    buffer_size=self.settings.ENCRYPTOR_BUFFER_SIZE,
                    timeout_seconds=self.settings.ENCRYPTOR_TIMEOUT,
                    retry_count=self.settings.ENCRYPTOR_RETRY_COUNT,
                    max_memory_mb=self.settings.ENCRYPTOR_MAX_MEMORY_MB
                ),
                enabled=self.settings.ENABLE_ENCRYPTION,
                priority=4,
                dependencies=["compressor"] if self.settings.ENABLE_COMPRESSION else ["chunk_generator"]
            ),
            
            "merkle_builder": StageConfig(
                stage_name="merkle_builder",
                stage_type="merkle_builder",
                workers=WorkerConfig(
                    count=self.settings.MERKLE_WORKERS,
                    buffer_size=self.settings.MERKLE_BUFFER_SIZE,
                    timeout_seconds=self.settings.MERKLE_TIMEOUT,
                    retry_count=self.settings.MERKLE_RETRY_COUNT,
                    max_memory_mb=self.settings.MERKLE_MAX_MEMORY_MB
                ),
                enabled=True,
                priority=5,
                dependencies=["encryptor"] if self.settings.ENABLE_ENCRYPTION else 
                           (["compressor"] if self.settings.ENABLE_COMPRESSION else ["chunk_generator"])
            ),
            
            "storage": StageConfig(
                stage_name="storage",
                stage_type="storage",
                workers=WorkerConfig(
                    count=self.settings.STORAGE_WORKERS,
                    buffer_size=self.settings.STORAGE_BUFFER_SIZE,
                    timeout_seconds=self.settings.STORAGE_TIMEOUT,
                    retry_count=self.settings.STORAGE_RETRY_COUNT,
                    max_memory_mb=self.settings.STORAGE_MAX_MEMORY_MB
                ),
                enabled=True,
                priority=6,
                dependencies=["merkle_builder"]
            )
        }
    
    def get_stage_config(self, stage_name: str) -> Optional[StageConfig]:
        """Get configuration for a specific stage"""
        return self.stage_configs.get(stage_name)
    
    def get_worker_count(self, stage_type: str) -> int:
        """Get worker count for a stage type"""
        for stage_config in self.stage_configs.values():
            if stage_config.stage_type == stage_type:
                return stage_config.workers.count
        return 1
    
    def get_buffer_size(self, stage_type: str) -> int:
        """Get buffer size for a stage type"""
        for stage_config in self.stage_configs.values():
            if stage_config.stage_type == stage_type:
                return stage_config.workers.buffer_size
        return 1000
    
    def get_timeout(self, stage_type: str) -> int:
        """Get timeout for a stage type"""
        for stage_config in self.stage_configs.values():
            if stage_config.stage_type == stage_type:
                return stage_config.workers.timeout_seconds
        return 30
    
    def get_retry_count(self, stage_type: str) -> int:
        """Get retry count for a stage type"""
        for stage_config in self.stage_configs.values():
            if stage_config.stage_type == stage_type:
                return stage_config.workers.retry_count
        return 3
    
    def get_max_memory(self, stage_type: str) -> int:
        """Get max memory for a stage type"""
        for stage_config in self.stage_configs.values():
            if stage_config.stage_type == stage_type:
                return stage_config.workers.max_memory_mb
        return 512
    
    def is_stage_enabled(self, stage_name: str) -> bool:
        """Check if a stage is enabled"""
        stage_config = self.stage_configs.get(stage_name)
        return stage_config.enabled if stage_config else False
    
    def get_stage_dependencies(self, stage_name: str) -> list:
        """Get dependencies for a stage"""
        stage_config = self.stage_configs.get(stage_name)
        return stage_config.dependencies if stage_config else []
    
    def get_stage_priority(self, stage_name: str) -> int:
        """Get priority for a stage"""
        stage_config = self.stage_configs.get(stage_name)
        return stage_config.priority if stage_config else 999
    
    def get_enabled_stages(self) -> list:
        """Get list of enabled stages ordered by priority"""
        enabled_stages = [
            (name, config) for name, config in self.stage_configs.items()
            if config.enabled
        ]
        return sorted(enabled_stages, key=lambda x: x[1].priority)
    
    def get_pipeline_config_dict(self) -> Dict[str, Any]:
        """Get complete pipeline configuration as dictionary"""
        return {
            "service": {
                "name": self.settings.SERVICE_NAME,
                "version": self.settings.SERVICE_VERSION,
                "debug": self.settings.DEBUG,
                "log_level": self.settings.LOG_LEVEL
            },
            "pipeline": {
                "max_concurrent_sessions": self.settings.MAX_CONCURRENT_SESSIONS,
                "chunk_size_mb": self.settings.CHUNK_SIZE_MB,
                "compression_level": self.settings.COMPRESSION_LEVEL,
                "timeout_seconds": self.settings.PIPELINE_TIMEOUT_SECONDS
            },
            "performance": {
                "enable_compression": self.settings.ENABLE_COMPRESSION,
                "enable_encryption": self.settings.ENABLE_ENCRYPTION,
                "enable_deduplication": self.settings.ENABLE_DEDUPLICATION,
                "parallel_processing": self.settings.PARALLEL_PROCESSING
            },
            "stages": {
                name: {
                    "stage_name": config.stage_name,
                    "stage_type": config.stage_type,
                    "enabled": config.enabled,
                    "priority": config.priority,
                    "dependencies": config.dependencies,
                    "workers": {
                        "count": config.workers.count,
                        "buffer_size": config.workers.buffer_size,
                        "timeout_seconds": config.workers.timeout_seconds,
                        "retry_count": config.workers.retry_count,
                        "max_memory_mb": config.workers.max_memory_mb
                    }
                }
                for name, config in self.stage_configs.items()
            },
            "storage": {
                "chunk_storage_path": self.settings.CHUNK_STORAGE_PATH,
                "session_storage_path": self.settings.SESSION_STORAGE_PATH,
                "temp_storage_path": self.settings.TEMP_STORAGE_PATH,
                "max_storage_size_gb": self.settings.MAX_STORAGE_SIZE_GB
            },
            "network": {
                "host": self.settings.HOST,
                "port": self.settings.PORT,
                "grpc_port": self.settings.GRPC_PORT
            },
            "monitoring": {
                "metrics_enabled": self.settings.METRICS_ENABLED,
                "metrics_port": self.settings.METRICS_PORT,
                "health_check_interval": self.settings.HEALTH_CHECK_INTERVAL
            }
        }
    
    def validate_configuration(self) -> bool:
        """Validate the pipeline configuration"""
        try:
            # Validate chunk size
            if self.settings.CHUNK_SIZE_MB < 1 or self.settings.CHUNK_SIZE_MB > 100:
                logger.error(f"Invalid chunk size: {self.settings.CHUNK_SIZE_MB} MB")
                return False
            
            # Validate compression level
            if self.settings.COMPRESSION_LEVEL < 1 or self.settings.COMPRESSION_LEVEL > 9:
                logger.error(f"Invalid compression level: {self.settings.COMPRESSION_LEVEL}")
                return False
            
            # Validate worker counts
            for stage_name, stage_config in self.stage_configs.items():
                if stage_config.workers.count < 1:
                    logger.error(f"Invalid worker count for {stage_name}: {stage_config.workers.count}")
                    return False
                
                if stage_config.workers.buffer_size < 1:
                    logger.error(f"Invalid buffer size for {stage_name}: {stage_config.workers.buffer_size}")
                    return False
                
                if stage_config.workers.timeout_seconds < 1:
                    logger.error(f"Invalid timeout for {stage_name}: {stage_config.workers.timeout_seconds}")
                    return False
            
            # Validate dependencies
            for stage_name, stage_config in self.stage_configs.items():
                for dep in stage_config.dependencies:
                    if dep not in self.stage_configs:
                        logger.error(f"Invalid dependency '{dep}' for stage '{stage_name}'")
                        return False
            
            logger.info("Pipeline configuration validation successful")
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {str(e)}")
            return False
    
    def reload_configuration(self):
        """Reload configuration from environment"""
        try:
            self.settings = PipelineSettings()
            self._initialize_stage_configs()
            logger.info("Pipeline configuration reloaded")
        except Exception as e:
            logger.error(f"Failed to reload configuration: {str(e)}")
            raise
    
    def get_environment_variables(self) -> Dict[str, str]:
        """Get environment variables for configuration"""
        return {
            "SERVICE_NAME": self.settings.SERVICE_NAME,
            "SERVICE_VERSION": self.settings.SERVICE_VERSION,
            "DEBUG": str(self.settings.DEBUG),
            "LOG_LEVEL": self.settings.LOG_LEVEL,
            "MAX_CONCURRENT_SESSIONS": str(self.settings.MAX_CONCURRENT_SESSIONS),
            "CHUNK_SIZE_MB": str(self.settings.CHUNK_SIZE_MB),
            "COMPRESSION_LEVEL": str(self.settings.COMPRESSION_LEVEL),
            "MONGODB_URL": self.settings.MONGODB_URL,
            "REDIS_URL": self.settings.REDIS_URL,
            "HOST": self.settings.HOST,
            "PORT": str(self.settings.PORT),
            "GRPC_PORT": str(self.settings.GRPC_PORT),
            "SECRET_KEY": "***REDACTED***",
            "ENCRYPTION_KEY": "***REDACTED***",
            "JWT_SECRET_KEY": "***REDACTED***"
        }
