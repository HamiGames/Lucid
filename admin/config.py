#!/usr/bin/env python3
"""
Lucid Admin Interface - Configuration Management
Step 23: Admin Backend APIs Implementation

Configuration management for the Lucid admin interface service.
Handles environment variables, service settings, and security configuration.
"""

import os
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Database configuration"""
    mongodb_uri: str = ""
    mongodb_database: str = "lucid"
    redis_url: str = "redis://redis-distroless:6379/0"
    elasticsearch_url: str = "http://elasticsearch-distroless:9200"
    connection_timeout: int = 30
    max_pool_size: int = 100
    min_pool_size: int = 10


@dataclass
class SecurityConfig:
    """Security configuration"""
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7
    password_min_length: int = 12
    password_require_special_chars: bool = True
    session_timeout_hours: int = 8
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 30
    totp_issuer: str = "Lucid Admin"
    totp_window: int = 1


@dataclass
class ServiceConfig:
    """Service configuration"""
    service_name: str = "lucid-admin-interface"
    version: str = "1.0.0"
    host: str = "0.0.0.0"
    port: int = 8083
    debug: bool = False
    log_level: str = "INFO"
    workers: int = 1
    max_connections: int = 1000
    keep_alive_timeout: int = 5
    api_docs_path: str = "/admin/docs"
    api_redoc_path: str = "/admin/redoc"
    api_openapi_path: str = "/admin/openapi.json"
    api_prefix: str = "/admin/api/v1"


@dataclass
class RBACConfig:
    """Role-based access control configuration"""
    default_role: str = "read_only"
    super_admin_role: str = "super_admin"
    admin_role: str = "admin"
    operator_role: str = "operator"
    read_only_role: str = "read_only"
    permission_cache_ttl: int = 300  # 5 minutes
    role_hierarchy: Dict[str, List[str]] = field(default_factory=lambda: {
        "super_admin": ["admin", "operator", "read_only"],
        "admin": ["operator", "read_only"],
        "operator": ["read_only"],
        "read_only": []
    })
    
    # Admin Controller specific
    key_rotation_interval_days: int = 30
    admin_session_timeout_hours: int = 8
    governance_quorum_pct: float = 0.67
    policy_cache_ttl_sec: int = 300
    multisig_threshold: int = 3
    multisig_total: int = 5


@dataclass
class MonitoringConfig:
    """Monitoring and metrics configuration"""
    metrics_enabled: bool = True
    metrics_port: int = 9090
    health_check_interval: int = 30
    system_metrics_interval: int = 60
    log_retention_days: int = 30
    audit_log_retention_days: int = 90
    performance_monitoring: bool = True


@dataclass
class EmergencyConfig:
    """Emergency controls configuration"""
    emergency_lockdown_enabled: bool = True
    emergency_shutdown_enabled: bool = True
    session_termination_enabled: bool = True
    node_maintenance_enabled: bool = True
    blockchain_pause_enabled: bool = True
    emergency_notification_emails: List[str] = field(default_factory=list)


@dataclass
class AdminConfig:
    """Main admin interface configuration"""
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    service: ServiceConfig = field(default_factory=ServiceConfig)
    rbac: RBACConfig = field(default_factory=RBACConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    emergency: EmergencyConfig = field(default_factory=EmergencyConfig)
    
    # External service URLs
    api_gateway_url: str = "http://api-gateway:8080"
    blockchain_url: str = "http://blockchain-engine:8084"
    session_management_url: str = "http://session-api:8113"
    node_management_url: str = "http://node-management:8095"
    auth_service_url: str = "http://lucid-auth-service:8089"
    # tron_payment_url removed for TRON isolation compliance
    
    # CORS settings
    cors_origins: List[str] = field(default_factory=lambda: [
        "https://admin.lucid.local",
        "http://localhost:3000",
        "http://localhost:8083"
    ])
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = field(default_factory=lambda: ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
    cors_allow_headers: List[str] = field(default_factory=lambda: ["*"])
    
    # Trusted hosts
    trusted_hosts: List[str] = field(default_factory=lambda: ["admin.lucid.local", "localhost", "127.0.0.1"])
    
    # Rate limiting
    rate_limit_requests: int = 1000
    rate_limit_window: int = 60  # seconds
    rate_limit_burst: int = 100
    
    # File upload limits
    max_upload_size: int = 100 * 1024 * 1024  # 100MB
    allowed_file_types: List[str] = field(default_factory=lambda: [
        "application/json",
        "text/csv",
        "application/pdf"
    ])
    
    def __post_init__(self):
        """Post-initialization processing"""
        self._load_from_environment()
        self._validate_config()
    
    def _load_from_environment(self):
        """Load configuration from environment variables"""
        # Database configuration
        self.database.mongodb_uri = os.getenv("MONGODB_URI") or os.getenv("MONGO_URI") or self.database.mongodb_uri
        self.database.mongodb_database = os.getenv("MONGODB_DATABASE", self.database.mongodb_database)
        self.database.redis_url = os.getenv("REDIS_URL", self.database.redis_url)
        self.database.elasticsearch_url = os.getenv("ELASTICSEARCH_URL", self.database.elasticsearch_url)
        try:
            self.database.connection_timeout = int(os.getenv("DATABASE_CONNECTION_TIMEOUT", str(self.database.connection_timeout)))
            self.database.max_pool_size = int(os.getenv("DATABASE_MAX_POOL_SIZE", str(self.database.max_pool_size)))
            self.database.min_pool_size = int(os.getenv("DATABASE_MIN_POOL_SIZE", str(self.database.min_pool_size)))
        except ValueError:
            pass
        
        # Security configuration
        self.security.jwt_secret_key = os.getenv("JWT_SECRET_KEY", self.security.jwt_secret_key)
        self.security.jwt_algorithm = os.getenv("JWT_ALGORITHM", self.security.jwt_algorithm)
        try:
            self.security.jwt_access_token_expire_minutes = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", str(self.security.jwt_access_token_expire_minutes)))
            self.security.jwt_refresh_token_expire_days = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", str(self.security.jwt_refresh_token_expire_days)))
            self.security.password_min_length = int(os.getenv("PASSWORD_MIN_LENGTH", str(self.security.password_min_length)))
            self.security.session_timeout_hours = int(os.getenv("SESSION_TIMEOUT_HOURS", str(self.security.session_timeout_hours)))
            self.security.max_login_attempts = int(os.getenv("MAX_LOGIN_ATTEMPTS", str(self.security.max_login_attempts)))
            self.security.lockout_duration_minutes = int(os.getenv("LOCKOUT_DURATION_MINUTES", str(self.security.lockout_duration_minutes)))
            self.security.totp_window = int(os.getenv("TOTP_WINDOW", str(self.security.totp_window)))
        except ValueError:
            pass
        self.security.password_require_special_chars = os.getenv("PASSWORD_REQUIRE_SPECIAL_CHARS", "true").lower() == "true"
        self.security.totp_issuer = os.getenv("TOTP_ISSUER", self.security.totp_issuer)
        
        # Service configuration
        self.service.service_name = os.getenv("ADMIN_INTERFACE_SERVICE_NAME", self.service.service_name)
        self.service.version = os.getenv("ADMIN_INTERFACE_VERSION", self.service.version)
        self.service.host = os.getenv("ADMIN_INTERFACE_HOST", os.getenv("ADMIN_HOST", self.service.host))
        try:
            port_str = os.getenv("ADMIN_INTERFACE_PORT", os.getenv("ADMIN_PORT", str(self.service.port)))
            self.service.port = int(port_str)
            if not (1 <= self.service.port <= 65535):
                raise ValueError(f"Port {self.service.port} out of range")
        except ValueError as e:
            logger.warning(f"Invalid ADMIN_INTERFACE_PORT/ADMIN_PORT, using default: {self.service.port}: {e}")
        self.service.debug = os.getenv("ADMIN_INTERFACE_DEBUG", os.getenv("ADMIN_DEBUG", "false")).lower() == "true"
        self.service.log_level = os.getenv("ADMIN_INTERFACE_LOG_LEVEL", os.getenv("LOG_LEVEL", self.service.log_level))
        try:
            self.service.workers = int(os.getenv("ADMIN_INTERFACE_WORKERS", str(self.service.workers)))
            self.service.max_connections = int(os.getenv("ADMIN_INTERFACE_MAX_CONNECTIONS", str(self.service.max_connections)))
            self.service.keep_alive_timeout = int(os.getenv("ADMIN_INTERFACE_KEEP_ALIVE_TIMEOUT", str(self.service.keep_alive_timeout)))
        except ValueError:
            pass
        self.service.api_docs_path = os.getenv("API_DOCS_PATH", self.service.api_docs_path)
        self.service.api_redoc_path = os.getenv("API_REDOC_PATH", self.service.api_redoc_path)
        self.service.api_openapi_path = os.getenv("API_OPENAPI_PATH", self.service.api_openapi_path)
        self.service.api_prefix = os.getenv("API_PREFIX", self.service.api_prefix)
        
        # RBAC configuration
        self.rbac.default_role = os.getenv("RBAC_DEFAULT_ROLE", self.rbac.default_role)
        self.rbac.super_admin_role = os.getenv("RBAC_SUPER_ADMIN_ROLE", self.rbac.super_admin_role)
        self.rbac.admin_role = os.getenv("RBAC_ADMIN_ROLE", self.rbac.admin_role)
        self.rbac.operator_role = os.getenv("RBAC_OPERATOR_ROLE", self.rbac.operator_role)
        self.rbac.read_only_role = os.getenv("RBAC_READ_ONLY_ROLE", self.rbac.read_only_role)
        try:
            self.rbac.permission_cache_ttl = int(os.getenv("RBAC_PERMISSION_CACHE_TTL", str(self.rbac.permission_cache_ttl)))
            self.rbac.key_rotation_interval_days = int(os.getenv("KEY_ROTATION_INTERVAL_DAYS", str(self.rbac.key_rotation_interval_days)))
            self.rbac.admin_session_timeout_hours = int(os.getenv("ADMIN_SESSION_TIMEOUT_HOURS", str(self.rbac.admin_session_timeout_hours)))
            self.rbac.governance_quorum_pct = float(os.getenv("GOVERNANCE_QUORUM_PCT", str(self.rbac.governance_quorum_pct)))
            self.rbac.policy_cache_ttl_sec = int(os.getenv("POLICY_CACHE_TTL_SEC", str(self.rbac.policy_cache_ttl_sec)))
            self.rbac.multisig_threshold = int(os.getenv("MULTISIG_THRESHOLD", str(self.rbac.multisig_threshold)))
            self.rbac.multisig_total = int(os.getenv("MULTISIG_TOTAL", str(self.rbac.multisig_total)))
        except ValueError:
            pass
        
        # Monitoring configuration
        self.monitoring.metrics_enabled = os.getenv("METRICS_ENABLED", "true").lower() == "true"
        self.monitoring.performance_monitoring = os.getenv("PERFORMANCE_MONITORING", "true").lower() == "true"
        try:
            self.monitoring.metrics_port = int(os.getenv("METRICS_PORT", str(self.monitoring.metrics_port)))
            self.monitoring.health_check_interval = int(os.getenv("HEALTH_CHECK_INTERVAL", str(self.monitoring.health_check_interval)))
            self.monitoring.system_metrics_interval = int(os.getenv("SYSTEM_METRICS_INTERVAL", str(self.monitoring.system_metrics_interval)))
            self.monitoring.log_retention_days = int(os.getenv("LOG_RETENTION_DAYS", str(self.monitoring.log_retention_days)))
            self.monitoring.audit_log_retention_days = int(os.getenv("AUDIT_LOG_RETENTION_DAYS", str(self.monitoring.audit_log_retention_days)))
        except ValueError:
            pass
        
        # Emergency configuration
        self.emergency.emergency_lockdown_enabled = os.getenv("EMERGENCY_LOCKDOWN_ENABLED", "true").lower() == "true"
        self.emergency.emergency_shutdown_enabled = os.getenv("EMERGENCY_SHUTDOWN_ENABLED", "true").lower() == "true"
        self.emergency.session_termination_enabled = os.getenv("SESSION_TERMINATION_ENABLED", "true").lower() == "true"
        self.emergency.node_maintenance_enabled = os.getenv("NODE_MAINTENANCE_ENABLED", "true").lower() == "true"
        self.emergency.blockchain_pause_enabled = os.getenv("BLOCKCHAIN_PAUSE_ENABLED", "true").lower() == "true"
        emergency_emails_env = os.getenv("EMERGENCY_NOTIFICATION_EMAILS")
        if emergency_emails_env:
            self.emergency.emergency_notification_emails = [
                email.strip() for email in emergency_emails_env.split(",") if email.strip()
            ]
        
        # External service URLs
        self.api_gateway_url = os.getenv("API_GATEWAY_URL", self.api_gateway_url)
        self.blockchain_url = os.getenv("BLOCKCHAIN_ENGINE_URL", os.getenv("BLOCKCHAIN_URL", self.blockchain_url))
        self.session_management_url = os.getenv("SESSION_API_URL", os.getenv("SESSION_MANAGEMENT_URL", self.session_management_url))
        self.node_management_url = os.getenv("NODE_MANAGEMENT_URL", self.node_management_url)
        self.auth_service_url = os.getenv("AUTH_SERVICE_URL", self.auth_service_url)
        # self.tron_payment_url removed for TRON isolation compliance
        
        # CORS configuration
        cors_origins_env = os.getenv("CORS_ORIGINS")
        if cors_origins_env:
            self.cors_origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]
        self.cors_allow_credentials = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"
        cors_methods_env = os.getenv("CORS_ALLOW_METHODS")
        if cors_methods_env:
            self.cors_allow_methods = [method.strip() for method in cors_methods_env.split(",") if method.strip()]
        cors_headers_env = os.getenv("CORS_ALLOW_HEADERS")
        if cors_headers_env:
            self.cors_allow_headers = [header.strip() for header in cors_headers_env.split(",") if header.strip()]
        
        # Trusted hosts
        trusted_hosts_env = os.getenv("TRUSTED_HOSTS")
        if trusted_hosts_env:
            self.trusted_hosts = [host.strip() for host in trusted_hosts_env.split(",") if host.strip()]
        
        # Rate limiting
        try:
            self.rate_limit_requests = int(os.getenv("RATE_LIMIT_REQUESTS", str(self.rate_limit_requests)))
            self.rate_limit_window = int(os.getenv("RATE_LIMIT_WINDOW", str(self.rate_limit_window)))
            self.rate_limit_burst = int(os.getenv("RATE_LIMIT_BURST", str(self.rate_limit_burst)))
        except ValueError:
            pass
        
        # File upload limits
        try:
            self.max_upload_size = int(os.getenv("MAX_UPLOAD_SIZE", str(self.max_upload_size)))
        except ValueError:
            pass
        allowed_types_env = os.getenv("ALLOWED_FILE_TYPES")
        if allowed_types_env:
            self.allowed_file_types = [ftype.strip() for ftype in allowed_types_env.split(",") if ftype.strip()]
    
    def _validate_config(self):
        """Validate configuration values"""
        # Validate port numbers
        if not (1 <= self.service.port <= 65535):
            raise ValueError(f"Invalid port number: {self.service.port}")
        
        # Validate JWT secret key
        if len(self.security.jwt_secret_key) < 32:
            logger.warning("JWT secret key is too short, consider using a longer key")
        
        # Validate database URIs
        if not self.database.mongodb_uri or not self.database.mongodb_uri.startswith(("mongodb://", "mongodb+srv://")):
            logger.warning("Invalid MongoDB URI format, using default")
            self.database.mongodb_uri = os.getenv("MONGODB_URI") or os.getenv("MONGO_URI") or ""
        
        if not self.database.redis_url.startswith(("redis://", "rediss://")):
            raise ValueError("Invalid Redis URL format")
        
        # Validate external service URLs
        external_urls = [
            self.api_gateway_url,
            self.blockchain_url,
            self.session_management_url,
            self.node_management_url,
            self.auth_service_url
            # self.tron_payment_url removed for TRON isolation compliance
        ]
        
        for url in external_urls:
            if not url.startswith(("http://", "https://")):
                raise ValueError(f"Invalid service URL format: {url}")
        
        # Validate CORS origins
        for origin in self.cors_origins:
            if not origin.startswith(("http://", "https://")):
                raise ValueError(f"Invalid CORS origin format: {origin}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            "database": {
                "mongodb_uri": self.database.mongodb_uri,
                "mongodb_database": self.database.mongodb_database,
                "redis_url": self.database.redis_url,
                "elasticsearch_url": self.database.elasticsearch_url,
                "connection_timeout": self.database.connection_timeout,
                "max_pool_size": self.database.max_pool_size,
                "min_pool_size": self.database.min_pool_size
            },
            "security": {
                "jwt_algorithm": self.security.jwt_algorithm,
                "jwt_access_token_expire_minutes": self.security.jwt_access_token_expire_minutes,
                "jwt_refresh_token_expire_days": self.security.jwt_refresh_token_expire_days,
                "password_min_length": self.security.password_min_length,
                "password_require_special_chars": self.security.password_require_special_chars,
                "session_timeout_hours": self.security.session_timeout_hours,
                "max_login_attempts": self.security.max_login_attempts,
                "lockout_duration_minutes": self.security.lockout_duration_minutes,
                "totp_issuer": self.security.totp_issuer,
                "totp_window": self.security.totp_window
            },
            "service": {
                "service_name": self.service.service_name,
                "version": self.service.version,
                "host": self.service.host,
                "port": self.service.port,
                "debug": self.service.debug,
                "log_level": self.service.log_level,
                "workers": self.service.workers,
                "max_connections": self.service.max_connections,
                "keep_alive_timeout": self.service.keep_alive_timeout
            },
            "rbac": {
                "default_role": self.rbac.default_role,
                "super_admin_role": self.rbac.super_admin_role,
                "admin_role": self.rbac.admin_role,
                "operator_role": self.rbac.operator_role,
                "read_only_role": self.rbac.read_only_role,
                "permission_cache_ttl": self.rbac.permission_cache_ttl,
                "role_hierarchy": self.rbac.role_hierarchy
            },
            "monitoring": {
                "metrics_enabled": self.monitoring.metrics_enabled,
                "metrics_port": self.monitoring.metrics_port,
                "health_check_interval": self.monitoring.health_check_interval,
                "system_metrics_interval": self.monitoring.system_metrics_interval,
                "log_retention_days": self.monitoring.log_retention_days,
                "audit_log_retention_days": self.monitoring.audit_log_retention_days,
                "performance_monitoring": self.monitoring.performance_monitoring
            },
            "emergency": {
                "emergency_lockdown_enabled": self.emergency.emergency_lockdown_enabled,
                "emergency_shutdown_enabled": self.emergency.emergency_shutdown_enabled,
                "session_termination_enabled": self.emergency.session_termination_enabled,
                "node_maintenance_enabled": self.emergency.node_maintenance_enabled,
                "blockchain_pause_enabled": self.emergency.blockchain_pause_enabled,
                "emergency_notification_emails": self.emergency.emergency_notification_emails
            },
            "external_services": {
                "api_gateway_url": self.api_gateway_url,
                "blockchain_url": self.blockchain_url,
                "session_management_url": self.session_management_url,
                "node_management_url": self.node_management_url,
                "auth_service_url": self.auth_service_url
                # "tron_payment_url" removed for TRON isolation compliance
            },
            "cors_origins": self.cors_origins,
            "rate_limiting": {
                "rate_limit_requests": self.rate_limit_requests,
                "rate_limit_window": self.rate_limit_window,
                "rate_limit_burst": self.rate_limit_burst
            },
            "file_upload": {
                "max_upload_size": self.max_upload_size,
                "allowed_file_types": self.allowed_file_types
            }
        }
    
    def get_database_url(self) -> str:
        """Get database connection URL"""
        return self.database.mongodb_uri
    
    def get_redis_url(self) -> str:
        """Get Redis connection URL"""
        return self.database.redis_url
    
    def get_elasticsearch_url(self) -> str:
        """Get Elasticsearch connection URL"""
        return self.database.elasticsearch_url
    
    def is_debug_mode(self) -> bool:
        """Check if running in debug mode"""
        return self.service.debug
    
    def get_log_level(self) -> str:
        """Get logging level"""
        return self.service.log_level.upper()


# Global configuration instance
_admin_config: Optional[AdminConfig] = None


def get_admin_config() -> AdminConfig:
    """Get global admin configuration instance"""
    global _admin_config
    if _admin_config is None:
        _admin_config = AdminConfig()
        logger.info("Admin configuration initialized")
    return _admin_config


def reload_admin_config():
    """Reload admin configuration from environment"""
    global _admin_config
    _admin_config = AdminConfig()
    logger.info("Admin configuration reloaded")


def get_config_dict() -> Dict[str, Any]:
    """Get configuration as dictionary"""
    return get_admin_config().to_dict()


# Environment-specific configurations
def get_development_config() -> AdminConfig:
    """Get development configuration"""
    config = AdminConfig()
    config.service.debug = True
    config.service.log_level = "DEBUG"
    config.security.jwt_access_token_expire_minutes = 60
    config.database.connection_timeout = 10
    return config


def get_production_config() -> AdminConfig:
    """Get production configuration"""
    config = AdminConfig()
    config.service.debug = False
    config.service.log_level = "INFO"
    config.security.jwt_access_token_expire_minutes = 15
    config.database.connection_timeout = 30
    config.monitoring.performance_monitoring = True
    return config


def get_testing_config() -> AdminConfig:
    """Get testing configuration"""
    config = AdminConfig()
    config.service.debug = True
    config.service.log_level = "DEBUG"
    config.database.mongodb_uri = "mongodb://localhost:27017/lucid_test"
    config.database.redis_url = "redis://localhost:6379/1"
    config.security.jwt_access_token_expire_minutes = 1
    return config


if __name__ == "__main__":
    # Test configuration loading
    config = get_admin_config()
    print("Admin Configuration:")
    print(f"Service: {config.service.service_name} v{config.service.version}")
    print(f"Host: {config.service.host}:{config.service.port}")
    print(f"Debug: {config.service.debug}")
    print(f"Database: {config.database.mongodb_uri}")
    print(f"Security: JWT {config.security.jwt_algorithm}")
    print(f"RBAC: {len(config.rbac.role_hierarchy)} roles configured")
    print(f"Emergency: {len(config.emergency.emergency_notification_emails)} notification emails")
