"""
Configuration validation logic for Lucid project.

This module provides comprehensive configuration validation functionality including:
- Configuration schema validation
- Environment variable validation
- File path validation
- Network configuration validation
- Service configuration validation
- Database configuration validation
- Security configuration validation
"""

import os
import re
import json
import yaml
import logging
from typing import Any, Dict, List, Optional, Union, Tuple, Callable
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime, timezone
from enum import Enum
from dataclasses import dataclass, field
import ipaddress
import socket
import ssl
from pydantic import BaseModel, Field, validator, root_validator
from pydantic.types import SecretStr
import jsonschema
from jsonschema import validate, ValidationError

logger = logging.getLogger(__name__)


class ConfigValidationLevel(Enum):
    """Configuration validation severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ConfigValidationResult(Enum):
    """Configuration validation result enumeration."""
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"
    ERROR = "error"


class ConfigurationValidationError(Exception):
    """Base exception for configuration validation errors."""
    pass


class SchemaValidationError(ConfigurationValidationError):
    """Raised when schema validation fails."""
    pass


class EnvironmentValidationError(ConfigurationValidationError):
    """Raised when environment variable validation fails."""
    pass


class FilePathValidationError(ConfigurationValidationError):
    """Raised when file path validation fails."""
    pass


class NetworkValidationError(ConfigurationValidationError):
    """Raised when network configuration validation fails."""
    pass


class ServiceValidationError(ConfigurationValidationError):
    """Raised when service configuration validation fails."""
    pass


class DatabaseValidationError(ConfigurationValidationError):
    """Raised when database configuration validation fails."""
    pass


class SecurityConfigValidationError(ConfigurationValidationError):
    """Raised when security configuration validation fails."""
    pass


@dataclass
class ValidationResult:
    """Result of a configuration validation operation."""
    is_valid: bool
    result: ConfigValidationResult
    level: ConfigValidationLevel
    message: str
    field: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ConfigSchema:
    """Configuration schema definition."""
    name: str
    description: str
    schema: Dict[str, Any]
    required_fields: List[str] = field(default_factory=list)
    optional_fields: List[str] = field(default_factory=list)
    validation_rules: List[Dict[str, Any]] = field(default_factory=list)


class EnvironmentValidator:
    """Environment variable validation utility."""
    
    @staticmethod
    def validate_required_env_vars(required_vars: List[str]) -> List[ValidationResult]:
        """Validate that required environment variables are set."""
        results = []
        
        for var in required_vars:
            if var not in os.environ:
                results.append(ValidationResult(
                    is_valid=False,
                    result=ConfigValidationResult.ERROR,
                    level=ConfigValidationLevel.ERROR,
                    message=f"Required environment variable '{var}' is not set",
                    field=var
                ))
            else:
                results.append(ValidationResult(
                    is_valid=True,
                    result=ConfigValidationResult.VALID,
                    level=ConfigValidationLevel.INFO,
                    message=f"Environment variable '{var}' is set",
                    field=var
                ))
        
        return results
    
    @staticmethod
    def validate_env_var_format(var_name: str, pattern: str) -> ValidationResult:
        """Validate environment variable format using regex pattern."""
        if var_name not in os.environ:
            return ValidationResult(
                is_valid=False,
                result=ConfigValidationResult.ERROR,
                level=ConfigValidationLevel.ERROR,
                message=f"Environment variable '{var_name}' is not set",
                field=var_name
            )
        
        value = os.environ[var_name]
        if re.match(pattern, value):
            return ValidationResult(
                is_valid=True,
                result=ConfigValidationResult.VALID,
                level=ConfigValidationLevel.INFO,
                message=f"Environment variable '{var_name}' format is valid",
                field=var_name
            )
        else:
            return ValidationResult(
                is_valid=False,
                result=ConfigValidationResult.INVALID,
                level=ConfigValidationLevel.ERROR,
                message=f"Environment variable '{var_name}' format is invalid",
                field=var_name,
                details={'value': value, 'expected_pattern': pattern}
            )
    
    @staticmethod
    def validate_numeric_env_var(var_name: str, min_value: Optional[float] = None, 
                                max_value: Optional[float] = None) -> ValidationResult:
        """Validate numeric environment variable."""
        if var_name not in os.environ:
            return ValidationResult(
                is_valid=False,
                result=ConfigValidationResult.ERROR,
                level=ConfigValidationLevel.ERROR,
                message=f"Environment variable '{var_name}' is not set",
                field=var_name
            )
        
        try:
            value = float(os.environ[var_name])
            
            if min_value is not None and value < min_value:
                return ValidationResult(
                    is_valid=False,
                    result=ConfigValidationResult.INVALID,
                    level=ConfigValidationLevel.ERROR,
                    message=f"Environment variable '{var_name}' value {value} is below minimum {min_value}",
                    field=var_name,
                    details={'value': value, 'min_value': min_value}
                )
            
            if max_value is not None and value > max_value:
                return ValidationResult(
                    is_valid=False,
                    result=ConfigValidationResult.INVALID,
                    level=ConfigValidationLevel.ERROR,
                    message=f"Environment variable '{var_name}' value {value} exceeds maximum {max_value}",
                    field=var_name,
                    details={'value': value, 'max_value': max_value}
                )
            
            return ValidationResult(
                is_valid=True,
                result=ConfigValidationResult.VALID,
                level=ConfigValidationLevel.INFO,
                message=f"Environment variable '{var_name}' value {value} is valid",
                field=var_name
            )
            
        except ValueError:
            return ValidationResult(
                is_valid=False,
                result=ConfigValidationResult.INVALID,
                level=ConfigValidationLevel.ERROR,
                message=f"Environment variable '{var_name}' is not a valid number",
                field=var_name,
                details={'value': os.environ[var_name]}
            )


class FilePathValidator:
    """File path validation utility."""
    
    @staticmethod
    def validate_file_exists(file_path: Union[str, Path]) -> ValidationResult:
        """Validate that a file exists."""
        path = Path(file_path)
        
        if not path.exists():
            return ValidationResult(
                is_valid=False,
                result=ConfigValidationResult.ERROR,
                level=ConfigValidationLevel.ERROR,
                message=f"File does not exist: {path}",
                field=str(path)
            )
        
        if not path.is_file():
            return ValidationResult(
                is_valid=False,
                result=ConfigValidationResult.ERROR,
                level=ConfigValidationLevel.ERROR,
                message=f"Path is not a file: {path}",
                field=str(path)
            )
        
        return ValidationResult(
            is_valid=True,
            result=ConfigValidationResult.VALID,
            level=ConfigValidationLevel.INFO,
            message=f"File exists: {path}",
            field=str(path)
        )
    
    @staticmethod
    def validate_directory_exists(dir_path: Union[str, Path]) -> ValidationResult:
        """Validate that a directory exists."""
        path = Path(dir_path)
        
        if not path.exists():
            return ValidationResult(
                is_valid=False,
                result=ConfigValidationResult.ERROR,
                level=ConfigValidationLevel.ERROR,
                message=f"Directory does not exist: {path}",
                field=str(path)
            )
        
        if not path.is_dir():
            return ValidationResult(
                is_valid=False,
                result=ConfigValidationResult.ERROR,
                level=ConfigValidationLevel.ERROR,
                message=f"Path is not a directory: {path}",
                field=str(path)
            )
        
        return ValidationResult(
            is_valid=True,
            result=ConfigValidationResult.VALID,
            level=ConfigValidationLevel.INFO,
            message=f"Directory exists: {path}",
            field=str(path)
        )
    
    @staticmethod
    def validate_file_writable(file_path: Union[str, Path]) -> ValidationResult:
        """Validate that a file is writable."""
        path = Path(file_path)
        
        # Check if parent directory exists and is writable
        parent = path.parent
        if not parent.exists():
            return ValidationResult(
                is_valid=False,
                result=ConfigValidationResult.ERROR,
                level=ConfigValidationLevel.ERROR,
                message=f"Parent directory does not exist: {parent}",
                field=str(path)
            )
        
        if not os.access(parent, os.W_OK):
            return ValidationResult(
                is_valid=False,
                result=ConfigValidationResult.ERROR,
                level=ConfigValidationLevel.ERROR,
                message=f"Parent directory is not writable: {parent}",
                field=str(path)
            )
        
        return ValidationResult(
            is_valid=True,
            result=ConfigValidationResult.VALID,
            level=ConfigValidationLevel.INFO,
            message=f"File path is writable: {path}",
            field=str(path)
        )


class NetworkConfigValidator:
    """Network configuration validation utility."""
    
    @staticmethod
    def validate_hostname(hostname: str) -> ValidationResult:
        """Validate hostname format."""
        if len(hostname) > 253:
            return ValidationResult(
                is_valid=False,
                result=ConfigValidationResult.INVALID,
                level=ConfigValidationLevel.ERROR,
                message="Hostname too long (max 253 characters)",
                field="hostname"
            )
        
        if hostname.endswith('.'):
            hostname = hostname[:-1]
        
        if not hostname:
            return ValidationResult(
                is_valid=False,
                result=ConfigValidationResult.INVALID,
                level=ConfigValidationLevel.ERROR,
                message="Empty hostname",
                field="hostname"
            )
        
        # Check each label
        for label in hostname.split('.'):
            if not label or len(label) > 63:
                return ValidationResult(
                    is_valid=False,
                    result=ConfigValidationResult.INVALID,
                    level=ConfigValidationLevel.ERROR,
                    message="Invalid hostname label length",
                    field="hostname"
                )
            
            if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$', label):
                return ValidationResult(
                    is_valid=False,
                    result=ConfigValidationResult.INVALID,
                    level=ConfigValidationLevel.ERROR,
                    message="Invalid hostname characters",
                    field="hostname"
                )
        
        return ValidationResult(
            is_valid=True,
            result=ConfigValidationResult.VALID,
            level=ConfigValidationLevel.INFO,
            message="Valid hostname",
            field="hostname"
        )
    
    @staticmethod
    def validate_ip_address(ip: str) -> ValidationResult:
        """Validate IP address format."""
        try:
            ipaddress.ip_address(ip)
            return ValidationResult(
                is_valid=True,
                result=ConfigValidationResult.VALID,
                level=ConfigValidationLevel.INFO,
                message="Valid IP address",
                field="ip_address"
            )
        except ValueError:
            return ValidationResult(
                is_valid=False,
                result=ConfigValidationResult.INVALID,
                level=ConfigValidationLevel.ERROR,
                message="Invalid IP address format",
                field="ip_address"
            )
    
    @staticmethod
    def validate_port(port: Union[int, str]) -> ValidationResult:
        """Validate port number."""
        try:
            port_num = int(port)
            if 1 <= port_num <= 65535:
                return ValidationResult(
                    is_valid=True,
                    result=ConfigValidationResult.VALID,
                    level=ConfigValidationLevel.INFO,
                    message="Valid port number",
                    field="port"
                )
            else:
                return ValidationResult(
                    is_valid=False,
                    result=ConfigValidationResult.INVALID,
                    level=ConfigValidationLevel.ERROR,
                    message="Port number must be between 1 and 65535",
                    field="port"
                )
        except ValueError:
            return ValidationResult(
                is_valid=False,
                result=ConfigValidationResult.INVALID,
                level=ConfigValidationLevel.ERROR,
                message="Invalid port number format",
                field="port"
            )
    
    @staticmethod
    def validate_url(url: str) -> ValidationResult:
        """Validate URL format."""
        try:
            result = urlparse(url)
            if all([result.scheme, result.netloc]):
                return ValidationResult(
                    is_valid=True,
                    result=ConfigValidationResult.VALID,
                    level=ConfigValidationLevel.INFO,
                    message="Valid URL",
                    field="url"
                )
            else:
                return ValidationResult(
                    is_valid=False,
                    result=ConfigValidationResult.INVALID,
                    level=ConfigValidationLevel.ERROR,
                    message="Invalid URL format",
                    field="url"
                )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                result=ConfigValidationResult.INVALID,
                level=ConfigValidationLevel.ERROR,
                message=f"URL validation error: {str(e)}",
                field="url"
            )
    
    @staticmethod
    def test_connection(host: str, port: int, timeout: int = 5) -> ValidationResult:
        """Test network connection to host:port."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                return ValidationResult(
                    is_valid=True,
                    result=ConfigValidationResult.VALID,
                    level=ConfigValidationLevel.INFO,
                    message=f"Connection successful to {host}:{port}",
                    field="connection"
                )
            else:
                return ValidationResult(
                    is_valid=False,
                    result=ConfigValidationResult.INVALID,
                    level=ConfigValidationLevel.WARNING,
                    message=f"Connection failed to {host}:{port}",
                    field="connection"
                )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                result=ConfigValidationResult.ERROR,
                level=ConfigValidationLevel.ERROR,
                message=f"Connection test error: {str(e)}",
                field="connection"
            )


class ServiceConfigValidator:
    """Service configuration validation utility."""
    
    @staticmethod
    def validate_service_config(config: Dict[str, Any], required_fields: List[str]) -> List[ValidationResult]:
        """Validate service configuration."""
        results = []
        
        # Check required fields
        for field in required_fields:
            if field not in config:
                results.append(ValidationResult(
                    is_valid=False,
                    result=ConfigValidationResult.ERROR,
                    level=ConfigValidationLevel.ERROR,
                    message=f"Required field '{field}' is missing",
                    field=field
                ))
        
        # Validate service-specific configurations
        if 'port' in config:
            results.append(NetworkConfigValidator.validate_port(config['port']))
        
        if 'host' in config:
            # Try IP address validation first, then hostname
            ip_result = NetworkConfigValidator.validate_ip_address(config['host'])
            if not ip_result.is_valid:
                results.append(NetworkConfigValidator.validate_hostname(config['host']))
            else:
                results.append(ip_result)
        
        if 'url' in config:
            results.append(NetworkConfigValidator.validate_url(config['url']))
        
        return results


class DatabaseConfigValidator:
    """Database configuration validation utility."""
    
    @staticmethod
    def validate_database_url(url: str) -> ValidationResult:
        """Validate database connection URL."""
        try:
            result = urlparse(url)
            
            # Check if it's a valid database URL
            valid_schemes = ['mysql', 'postgresql', 'mongodb', 'sqlite', 'redis']
            if result.scheme not in valid_schemes:
                return ValidationResult(
                    is_valid=False,
                    result=ConfigValidationResult.INVALID,
                    level=ConfigValidationLevel.ERROR,
                    message=f"Invalid database scheme: {result.scheme}",
                    field="database_url"
                )
            
            if not result.netloc:
                return ValidationResult(
                    is_valid=False,
                    result=ConfigValidationResult.INVALID,
                    level=ConfigValidationLevel.ERROR,
                    message="Missing database host",
                    field="database_url"
                )
            
            return ValidationResult(
                is_valid=True,
                result=ConfigValidationResult.VALID,
                level=ConfigValidationLevel.INFO,
                message="Valid database URL",
                field="database_url"
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                result=ConfigValidationResult.ERROR,
                level=ConfigValidationLevel.ERROR,
                message=f"Database URL validation error: {str(e)}",
                field="database_url"
            )
    
    @staticmethod
    def validate_mongodb_config(config: Dict[str, Any]) -> List[ValidationResult]:
        """Validate MongoDB configuration."""
        results = []
        required_fields = ['host', 'port', 'database']
        
        for field in required_fields:
            if field not in config:
                results.append(ValidationResult(
                    is_valid=False,
                    result=ConfigValidationResult.ERROR,
                    level=ConfigValidationLevel.ERROR,
                    message=f"Required MongoDB field '{field}' is missing",
                    field=field
                ))
        
        if 'port' in config:
            results.append(NetworkConfigValidator.validate_port(config['port']))
        
        if 'host' in config:
            results.append(NetworkConfigValidator.validate_hostname(config['host']))
        
        return results


class SecurityConfigValidator:
    """Security configuration validation utility."""
    
    @staticmethod
    def validate_ssl_config(config: Dict[str, Any]) -> List[ValidationResult]:
        """Validate SSL/TLS configuration."""
        results = []
        
        if 'enabled' in config and config['enabled']:
            if 'cert_file' in config:
                results.append(FilePathValidator.validate_file_exists(config['cert_file']))
            
            if 'key_file' in config:
                results.append(FilePathValidator.validate_file_exists(config['key_file']))
            
            if 'ca_file' in config:
                results.append(FilePathValidator.validate_file_exists(config['ca_file']))
        
        return results
    
    @staticmethod
    def validate_cors_config(config: Dict[str, Any]) -> List[ValidationResult]:
        """Validate CORS configuration."""
        results = []
        
        if 'allowed_origins' in config:
            origins = config['allowed_origins']
            if isinstance(origins, list):
                for origin in origins:
                    results.append(NetworkConfigValidator.validate_url(origin))
            else:
                results.append(ValidationResult(
                    is_valid=False,
                    result=ConfigValidationResult.INVALID,
                    level=ConfigValidationLevel.ERROR,
                    message="allowed_origins must be a list",
                    field="cors.allowed_origins"
                ))
        
        return results


class ConfigSchemaValidator:
    """Configuration schema validation utility."""
    
    @staticmethod
    def validate_json_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> List[ValidationResult]:
        """Validate data against JSON schema."""
        results = []
        
        try:
            validate(instance=data, schema=schema)
            results.append(ValidationResult(
                is_valid=True,
                result=ConfigValidationResult.VALID,
                level=ConfigValidationLevel.INFO,
                message="Configuration matches schema",
                field="schema"
            ))
        except ValidationError as e:
            results.append(ValidationResult(
                is_valid=False,
                result=ConfigValidationResult.INVALID,
                level=ConfigValidationLevel.ERROR,
                message=f"Schema validation error: {e.message}",
                field=e.path[0] if e.path else "schema",
                details={'error_path': list(e.path), 'error_message': e.message}
            ))
        except Exception as e:
            results.append(ValidationResult(
                is_valid=False,
                result=ConfigValidationResult.ERROR,
                level=ConfigValidationLevel.ERROR,
                message=f"Schema validation error: {str(e)}",
                field="schema"
            ))
        
        return results
    
    @staticmethod
    def load_schema_from_file(schema_path: Union[str, Path]) -> Dict[str, Any]:
        """Load JSON schema from file."""
        path = Path(schema_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Schema file not found: {path}")
        
        with open(path, 'r') as f:
            if path.suffix.lower() == '.json':
                return json.load(f)
            elif path.suffix.lower() in ['.yml', '.yaml']:
                return yaml.safe_load(f)
            else:
                raise ValueError(f"Unsupported schema file format: {path.suffix}")


class ConfigurationValidator:
    """Main configuration validation class."""
    
    def __init__(self):
        self.env_validator = EnvironmentValidator()
        self.file_validator = FilePathValidator()
        self.network_validator = NetworkConfigValidator()
        self.service_validator = ServiceConfigValidator()
        self.db_validator = DatabaseConfigValidator()
        self.security_validator = SecurityConfigValidator()
        self.schema_validator = ConfigSchemaValidator()
    
    def validate_config_file(self, config_path: Union[str, Path]) -> List[ValidationResult]:
        """Validate configuration file."""
        results = []
        path = Path(config_path)
        
        # Check if file exists
        file_result = self.file_validator.validate_file_exists(path)
        results.append(file_result)
        
        if not file_result.is_valid:
            return results
        
        # Load and validate configuration
        try:
            with open(path, 'r') as f:
                if path.suffix.lower() == '.json':
                    config = json.load(f)
                elif path.suffix.lower() in ['.yml', '.yaml']:
                    config = yaml.safe_load(f)
                else:
                    results.append(ValidationResult(
                        is_valid=False,
                        result=ConfigValidationResult.ERROR,
                        level=ConfigValidationLevel.ERROR,
                        message=f"Unsupported configuration file format: {path.suffix}",
                        field="file_format"
                    ))
                    return results
            
            # Basic validation
            if not isinstance(config, dict):
                results.append(ValidationResult(
                    is_valid=False,
                    result=ConfigValidationResult.ERROR,
                    level=ConfigValidationLevel.ERROR,
                    message="Configuration must be a dictionary",
                    field="config_structure"
                ))
                return results
            
            results.append(ValidationResult(
                is_valid=True,
                result=ConfigValidationResult.VALID,
                level=ConfigValidationLevel.INFO,
                message="Configuration file loaded successfully",
                field="config_file"
            ))
            
        except Exception as e:
            results.append(ValidationResult(
                is_valid=False,
                result=ConfigValidationResult.ERROR,
                level=ConfigValidationLevel.ERROR,
                message=f"Error loading configuration file: {str(e)}",
                field="config_file"
            ))
        
        return results
    
    def validate_environment_config(self, required_vars: List[str]) -> List[ValidationResult]:
        """Validate environment configuration."""
        return self.env_validator.validate_required_env_vars(required_vars)
    
    def validate_network_config(self, config: Dict[str, Any]) -> List[ValidationResult]:
        """Validate network configuration."""
        results = []
        
        if 'host' in config:
            results.append(self.network_validator.validate_hostname(config['host']))
        
        if 'port' in config:
            results.append(self.network_validator.validate_port(config['port']))
        
        if 'url' in config:
            results.append(self.network_validator.validate_url(config['url']))
        
        return results
    
    def validate_service_config(self, config: Dict[str, Any], service_type: str = "generic") -> List[ValidationResult]:
        """Validate service configuration."""
        # Define required fields by service type
        service_requirements = {
            'api': ['host', 'port'],
            'database': ['host', 'port', 'database'],
            'redis': ['host', 'port'],
            'mongodb': ['host', 'port', 'database'],
            'generic': []
        }
        
        required_fields = service_requirements.get(service_type, [])
        return self.service_validator.validate_service_config(config, required_fields)
    
    def validate_database_config(self, config: Dict[str, Any], db_type: str = "mongodb") -> List[ValidationResult]:
        """Validate database configuration."""
        results = []
        
        if 'url' in config:
            results.append(self.db_validator.validate_database_url(config['url']))
        
        if db_type == 'mongodb':
            results.extend(self.db_validator.validate_mongodb_config(config))
        
        return results
    
    def validate_security_config(self, config: Dict[str, Any]) -> List[ValidationResult]:
        """Validate security configuration."""
        results = []
        
        if 'ssl' in config:
            results.extend(self.security_validator.validate_ssl_config(config['ssl']))
        
        if 'cors' in config:
            results.extend(self.security_validator.validate_cors_config(config['cors']))
        
        return results
    
    def validate_against_schema(self, config: Dict[str, Any], schema: Union[Dict[str, Any], Union[str, Path]]) -> List[ValidationResult]:
        """Validate configuration against schema."""
        if isinstance(schema, (str, Path)):
            schema = self.schema_validator.load_schema_from_file(schema)
        
        return self.schema_validator.validate_json_schema(config, schema)
    
    def validate_complete_config(self, config: Dict[str, Any], 
                                schema: Optional[Union[Dict[str, Any], Union[str, Path]]] = None) -> List[ValidationResult]:
        """Perform complete configuration validation."""
        results = []
        
        # Schema validation if provided
        if schema:
            results.extend(self.validate_against_schema(config, schema))
        
        # Network configuration validation
        if 'network' in config:
            results.extend(self.validate_network_config(config['network']))
        
        # Service configuration validation
        if 'services' in config:
            for service_name, service_config in config['services'].items():
                service_results = self.validate_service_config(service_config, service_name)
                for result in service_results:
                    result.field = f"services.{service_name}.{result.field}"
                results.extend(service_results)
        
        # Database configuration validation
        if 'database' in config:
            db_results = self.validate_database_config(config['database'])
            for result in db_results:
                result.field = f"database.{result.field}"
            results.extend(db_results)
        
        # Security configuration validation
        if 'security' in config:
            security_results = self.validate_security_config(config['security'])
            for result in security_results:
                result.field = f"security.{result.field}"
            results.extend(security_results)
        
        return results


# Global configuration validator instance
_config_validator: Optional[ConfigurationValidator] = None


def get_config_validator() -> ConfigurationValidator:
    """Get global configuration validator instance."""
    global _config_validator
    if _config_validator is None:
        _config_validator = ConfigurationValidator()
    return _config_validator


def validate_config_file(config_path: Union[str, Path]) -> List[ValidationResult]:
    """Validate configuration file."""
    return get_config_validator().validate_config_file(config_path)


def validate_environment_config(required_vars: List[str]) -> List[ValidationResult]:
    """Validate environment configuration."""
    return get_config_validator().validate_environment_config(required_vars)


def validate_network_config(config: Dict[str, Any]) -> List[ValidationResult]:
    """Validate network configuration."""
    return get_config_validator().validate_network_config(config)


def validate_service_config(config: Dict[str, Any], service_type: str = "generic") -> List[ValidationResult]:
    """Validate service configuration."""
    return get_config_validator().validate_service_config(config, service_type)


def validate_database_config(config: Dict[str, Any], db_type: str = "mongodb") -> List[ValidationResult]:
    """Validate database configuration."""
    return get_config_validator().validate_database_config(config, db_type)


def validate_security_config(config: Dict[str, Any]) -> List[ValidationResult]:
    """Validate security configuration."""
    return get_config_validator().validate_security_config(config)


def validate_against_schema(config: Dict[str, Any], schema: Union[Dict[str, Any], Union[str, Path]]) -> List[ValidationResult]:
    """Validate configuration against schema."""
    return get_config_validator().validate_against_schema(config, schema)


def validate_complete_config(config: Dict[str, Any], 
                            schema: Optional[Union[Dict[str, Any], Union[str, Path]]] = None) -> List[ValidationResult]:
    """Perform complete configuration validation."""
    return get_config_validator().validate_complete_config(config, schema)
