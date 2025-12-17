"""
Lucid Service Mesh Controller - Configuration
Environment-based configuration using pydantic-settings

File: service-mesh/config.py
"""

import os
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Service mesh controller settings loaded from environment variables"""
    
    # Service Configuration
    SERVICE_NAME: str = "lucid-service-mesh-controller"
    SERVICE_MESH_HOST: str = "0.0.0.0"
    SERVICE_MESH_PORT: int = 8500
    HTTP_PORT: int = 8088
    
    # Consul Configuration
    CONSUL_HOST: str = "localhost"
    CONSUL_PORT: int = 8500
    CONSUL_DATACENTER: str = "lucid-dc"
    CONSUL_BOOTSTRAP_EXPECT: int = 1
    CONSUL_UI_ENABLED: bool = True
    CONSUL_CONNECT_ENABLED: bool = True
    
    # Certificate Configuration
    CERT_VALIDITY_DAYS: int = 90
    CA_VALIDITY_DAYS: int = 365
    CERT_KEY_SIZE: int = 2048
    CERT_COUNTRY: str = "US"
    CERT_STATE: str = "California"
    CERT_LOCALITY: str = "San Francisco"
    CERT_ORGANIZATION: str = "Lucid"
    
    # Envoy Configuration
    ENVOY_ADMIN_PORT: int = 9901
    ENVOY_CONFIG_PATH: str = "/app/envoy-configs"
    
    # Database Configuration (optional)
    MONGODB_URL: Optional[str] = None
    REDIS_URL: Optional[str] = None
    
    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = False
    LOG_FORMAT: str = "json"
    
    # Environment
    LUCID_ENV: str = "production"
    LUCID_PLATFORM: str = "arm64"
    
    # Paths
    CERTIFICATES_PATH: str = "/app/certificates"
    CONFIG_PATH: str = "/app/config"
    LOGS_PATH: str = "/app/logs"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

