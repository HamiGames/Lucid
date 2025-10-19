"""
LUCID Payment Systems - TRON Payment Services Configuration
Configuration management for TRON payment services
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from pydantic_settings import BaseSettings
from pydantic import Field
from enum import Enum

class NetworkType(str, Enum):
    """TRON network types"""
    MAINNET = "mainnet"
    TESTNET = "testnet"
    SHASTA = "shasta"

class LogLevel(str, Enum):
    """Log levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class TRONPaymentConfig(BaseSettings):
    """TRON Payment Services Configuration"""
    
    # Network Configuration
    tron_network: NetworkType = Field(default=NetworkType.MAINNET, description="TRON network")
    tron_http_endpoint: Optional[str] = Field(default=None, description="Custom TRON HTTP endpoint")
    trongrid_api_key: Optional[str] = Field(default=None, description="TronGrid API key")
    
    # Service URLs
    tron_client_url: str = Field(default="http://localhost:8085", description="TRON client service URL")
    wallet_manager_url: str = Field(default="http://localhost:8086", description="Wallet manager service URL")
    usdt_manager_url: str = Field(default="http://localhost:8087", description="USDT manager service URL")
    payout_router_url: str = Field(default="http://localhost:8088", description="Payout router service URL")
    payment_gateway_url: str = Field(default="http://localhost:8089", description="Payment gateway service URL")
    trx_staking_url: str = Field(default="http://localhost:8090", description="TRX staking service URL")
    
    # Database Configuration
    mongodb_url: str = Field(default="mongodb://localhost:27017", description="MongoDB connection URL")
    mongodb_database: str = Field(default="lucid_payments", description="MongoDB database name")
    redis_url: str = Field(default="redis://localhost:6379", description="Redis connection URL")
    redis_database: int = Field(default=0, description="Redis database number")
    
    # Security Configuration
    wallet_encryption_key: str = Field(default="default_encryption_key_change_in_production", description="Wallet encryption key")
    jwt_secret_key: str = Field(default="default_jwt_secret_change_in_production", description="JWT secret key")
    api_key: Optional[str] = Field(default=None, description="API key for service authentication")
    
    # Payment Configuration
    max_payment_amount: float = Field(default=10000.0, description="Maximum payment amount")
    min_payment_amount: float = Field(default=0.01, description="Minimum payment amount")
    daily_payment_limit: float = Field(default=100000.0, description="Daily payment limit")
    payment_timeout: int = Field(default=300, description="Payment timeout in seconds")
    
    # Staking Configuration
    min_staking_amount: float = Field(default=1.0, description="Minimum staking amount in TRX")
    max_staking_amount: float = Field(default=1000000.0, description="Maximum staking amount in TRX")
    staking_duration_min: int = Field(default=1, description="Minimum staking duration in days")
    staking_duration_max: int = Field(default=365, description="Maximum staking duration in days")
    
    # USDT Configuration
    usdt_contract_address: str = Field(default="TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t", description="USDT contract address")
    usdt_decimals: int = Field(default=6, description="USDT decimals")
    
    # Wallet Configuration
    max_wallets_per_user: int = Field(default=10, description="Maximum wallets per user")
    wallet_backup_enabled: bool = Field(default=True, description="Enable wallet backup")
    wallet_encryption_enabled: bool = Field(default=True, description="Enable wallet encryption")
    
    # Monitoring Configuration
    health_check_interval: int = Field(default=60, description="Health check interval in seconds")
    metrics_enabled: bool = Field(default=True, description="Enable metrics collection")
    log_level: LogLevel = Field(default=LogLevel.INFO, description="Log level")
    
    # Data Storage Configuration
    data_directory: str = Field(default="/data/payment-systems", description="Data directory")
    backup_enabled: bool = Field(default=True, description="Enable data backup")
    backup_interval: int = Field(default=3600, description="Backup interval in seconds")
    retention_days: int = Field(default=30, description="Data retention in days")
    
    # Rate Limiting Configuration
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests: int = Field(default=100, description="Rate limit requests per minute")
    rate_limit_burst: int = Field(default=200, description="Rate limit burst requests")
    
    # Circuit Breaker Configuration
    circuit_breaker_enabled: bool = Field(default=True, description="Enable circuit breaker")
    circuit_breaker_failure_threshold: int = Field(default=5, description="Circuit breaker failure threshold")
    circuit_breaker_timeout: int = Field(default=60, description="Circuit breaker timeout in seconds")
    circuit_breaker_recovery_timeout: int = Field(default=300, description="Circuit breaker recovery timeout in seconds")
    
    # Notification Configuration
    notification_enabled: bool = Field(default=True, description="Enable notifications")
    email_notifications: bool = Field(default=False, description="Enable email notifications")
    webhook_notifications: bool = Field(default=True, description="Enable webhook notifications")
    webhook_url: Optional[str] = Field(default=None, description="Webhook URL for notifications")
    
    # Development Configuration
    debug_mode: bool = Field(default=False, description="Enable debug mode")
    mock_transactions: bool = Field(default=False, description="Enable mock transactions")
    test_mode: bool = Field(default=False, description="Enable test mode")
    
    class Config:
        env_prefix = "TRON_PAYMENT_"
        case_sensitive = False
        env_file = ".env"
        env_file_encoding = "utf-8"

# Global configuration instance
config = TRONPaymentConfig()

# Network-specific configurations
NETWORK_CONFIGS = {
    NetworkType.MAINNET: {
        "tron_http_endpoint": "https://api.trongrid.io",
        "usdt_contract_address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
        "chain_id": "0x2b6653dc",
        "network_name": "TRON Mainnet"
    },
    NetworkType.TESTNET: {
        "tron_http_endpoint": "https://api.shasta.trongrid.io",
        "usdt_contract_address": "TG3XXyExBkPJ4D8sYv7cL6Lf4n9W4iZ1C",  # Testnet USDT
        "chain_id": "0x94a9059e",
        "network_name": "TRON Testnet"
    },
    NetworkType.SHASTA: {
        "tron_http_endpoint": "https://api.shasta.trongrid.io",
        "usdt_contract_address": "TG3XXyExBkPJ4D8sYv7cL6Lf4n9W4iZ1C",  # Shasta USDT
        "chain_id": "0x94a9059e",
        "network_name": "TRON Shasta"
    }
}

# Service configurations
SERVICE_CONFIGS = {
    "tron_client": {
        "port": 8085,
        "host": "0.0.0.0",
        "workers": 4,
        "timeout": 30,
        "max_connections": 1000
    },
    "wallet_manager": {
        "port": 8086,
        "host": "0.0.0.0",
        "workers": 2,
        "timeout": 60,
        "max_connections": 500
    },
    "usdt_manager": {
        "port": 8087,
        "host": "0.0.0.0",
        "workers": 2,
        "timeout": 60,
        "max_connections": 500
    },
    "payout_router": {
        "port": 8088,
        "host": "0.0.0.0",
        "workers": 4,
        "timeout": 120,
        "max_connections": 1000
    },
    "payment_gateway": {
        "port": 8089,
        "host": "0.0.0.0",
        "workers": 4,
        "timeout": 60,
        "max_connections": 1000
    },
    "trx_staking": {
        "port": 8090,
        "host": "0.0.0.0",
        "workers": 2,
        "timeout": 90,
        "max_connections": 500
    }
}

# API endpoint configurations
API_ENDPOINTS = {
    "tron_client": {
        "network_info": "/api/v1/network/info",
        "account_info": "/api/v1/account/{address}",
        "transaction": "/api/v1/transaction/{txid}",
        "broadcast": "/api/v1/transaction/broadcast"
    },
    "wallet_manager": {
        "create_wallet": "/api/v1/wallets",
        "get_wallet": "/api/v1/wallets/{wallet_id}",
        "update_wallet": "/api/v1/wallets/{wallet_id}",
        "delete_wallet": "/api/v1/wallets/{wallet_id}",
        "list_wallets": "/api/v1/wallets",
        "wallet_balance": "/api/v1/wallets/{wallet_id}/balance"
    },
    "usdt_manager": {
        "register_token": "/api/v1/tokens",
        "token_balance": "/api/v1/tokens/balance",
        "transfer_token": "/api/v1/tokens/transfer",
        "token_info": "/api/v1/tokens/{token_address}",
        "list_tokens": "/api/v1/tokens"
    },
    "payout_router": {
        "create_payout": "/api/v1/payouts",
        "payout_status": "/api/v1/payouts/{payout_id}",
        "list_payouts": "/api/v1/payouts",
        "payout_stats": "/api/v1/payouts/stats"
    },
    "payment_gateway": {
        "create_payment": "/api/v1/payments",
        "process_payment": "/api/v1/payments/{payment_id}/process",
        "payment_status": "/api/v1/payments/{payment_id}",
        "list_payments": "/api/v1/payments",
        "payment_stats": "/api/v1/payments/stats"
    },
    "trx_staking": {
        "stake_trx": "/api/v1/staking/stake",
        "unstake_trx": "/api/v1/staking/unstake",
        "resource_info": "/api/v1/staking/resources/{address}",
        "staking_records": "/api/v1/staking/records",
        "staking_stats": "/api/v1/staking/stats"
    }
}

# Validation rules
VALIDATION_RULES = {
    "address": {
        "trx": {
            "pattern": r"^T[A-Za-z1-9]{33}$",
            "length": 34,
            "prefix": "T"
        }
    },
    "amount": {
        "min_trx": 0.000001,  # 1 SUN
        "max_trx": 1000000.0,
        "min_usdt": 0.000001,
        "max_usdt": 1000000.0
    },
    "duration": {
        "min_days": 1,
        "max_days": 365
    }
}

# Error codes
ERROR_CODES = {
    "INVALID_ADDRESS": "E001",
    "INVALID_AMOUNT": "E002",
    "INSUFFICIENT_BALANCE": "E003",
    "TRANSACTION_FAILED": "E004",
    "NETWORK_ERROR": "E005",
    "SERVICE_UNAVAILABLE": "E006",
    "RATE_LIMIT_EXCEEDED": "E007",
    "INVALID_SIGNATURE": "E008",
    "WALLET_NOT_FOUND": "E009",
    "PAYMENT_NOT_FOUND": "E010"
}

# Success codes
SUCCESS_CODES = {
    "PAYMENT_CREATED": "S001",
    "PAYMENT_PROCESSED": "S002",
    "PAYMENT_COMPLETED": "S003",
    "WALLET_CREATED": "S004",
    "WALLET_UPDATED": "S005",
    "TRANSACTION_BROADCAST": "S006",
    "STAKING_SUCCESS": "S007",
    "UNSTAKING_SUCCESS": "S008"
}

def get_network_config(network: NetworkType) -> Dict[str, Any]:
    """Get network-specific configuration"""
    return NETWORK_CONFIGS.get(network, {})

def get_service_config(service_name: str) -> Dict[str, Any]:
    """Get service-specific configuration"""
    return SERVICE_CONFIGS.get(service_name, {})

def get_api_endpoints(service_name: str) -> Dict[str, str]:
    """Get API endpoints for a service"""
    return API_ENDPOINTS.get(service_name, {})

def get_validation_rules() -> Dict[str, Any]:
    """Get validation rules"""
    return VALIDATION_RULES

def get_error_code(error_name: str) -> str:
    """Get error code by name"""
    return ERROR_CODES.get(error_name, "E999")

def get_success_code(success_name: str) -> str:
    """Get success code by name"""
    return SUCCESS_CODES.get(success_name, "S999")

def is_development_mode() -> bool:
    """Check if running in development mode"""
    return config.debug_mode or config.test_mode

def is_production_mode() -> bool:
    """Check if running in production mode"""
    return not is_development_mode()

def get_data_directory() -> Path:
    """Get data directory path"""
    return Path(config.data_directory)

def get_log_level() -> str:
    """Get log level"""
    return config.log_level.value

def get_network_endpoint() -> str:
    """Get TRON network endpoint"""
    if config.tron_http_endpoint:
        return config.tron_http_endpoint
    
    network_config = get_network_config(config.tron_network)
    return network_config.get("tron_http_endpoint", "https://api.trongrid.io")

def get_usdt_contract_address() -> str:
    """Get USDT contract address"""
    if config.usdt_contract_address:
        return config.usdt_contract_address
    
    network_config = get_network_config(config.tron_network)
    return network_config.get("usdt_contract_address", "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t")

def validate_config() -> List[str]:
    """Validate configuration and return any errors"""
    errors = []
    
    # Validate network configuration
    if config.tron_network not in NetworkType:
        errors.append(f"Invalid TRON network: {config.tron_network}")
    
    # Validate amounts
    if config.min_payment_amount <= 0:
        errors.append("Minimum payment amount must be greater than 0")
    
    if config.max_payment_amount <= config.min_payment_amount:
        errors.append("Maximum payment amount must be greater than minimum")
    
    if config.daily_payment_limit <= 0:
        errors.append("Daily payment limit must be greater than 0")
    
    # Validate staking configuration
    if config.min_staking_amount <= 0:
        errors.append("Minimum staking amount must be greater than 0")
    
    if config.max_staking_amount <= config.min_staking_amount:
        errors.append("Maximum staking amount must be greater than minimum")
    
    if config.staking_duration_min <= 0:
        errors.append("Minimum staking duration must be greater than 0")
    
    if config.staking_duration_max <= config.staking_duration_min:
        errors.append("Maximum staking duration must be greater than minimum")
    
    # Validate security configuration
    if config.wallet_encryption_key == "default_encryption_key_change_in_production":
        if is_production_mode():
            errors.append("Wallet encryption key must be changed in production")
    
    if config.jwt_secret_key == "default_jwt_secret_change_in_production":
        if is_production_mode():
            errors.append("JWT secret key must be changed in production")
    
    # Validate URLs
    if not config.tron_client_url.startswith(("http://", "https://")):
        errors.append("TRON client URL must start with http:// or https://")
    
    # Validate data directory
    data_dir = get_data_directory()
    if not data_dir.exists():
        try:
            data_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors.append(f"Cannot create data directory: {e}")
    
    return errors

# Initialize configuration validation
config_errors = validate_config()
if config_errors:
    print("Configuration errors:")
    for error in config_errors:
        print(f"  - {error}")
    if is_production_mode():
        raise ValueError("Configuration validation failed in production mode")

# Export commonly used configurations
__all__ = [
    "config",
    "TRONPaymentConfig",
    "NetworkType",
    "LogLevel",
    "get_network_config",
    "get_service_config",
    "get_api_endpoints",
    "get_validation_rules",
    "get_error_code",
    "get_success_code",
    "is_development_mode",
    "is_production_mode",
    "get_data_directory",
    "get_log_level",
    "get_network_endpoint",
    "get_usdt_contract_address",
    "validate_config"
]