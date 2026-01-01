"""
RDP Controller Schema Validation Module
Uses JSON schema files for request/response validation

This module provides schema validation utilities for the rdp-controller service,
following the patterns established in session-api-design.md and master-docker-design.md.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, Union

try:
    import jsonschema
    from jsonschema import validate, ValidationError, Draft7Validator
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False
    jsonschema = None
    validate = None
    ValidationError = None
    Draft7Validator = None

logger = logging.getLogger(__name__)


class SchemaValidationError(Exception):
    """Exception raised when schema validation fails"""
    def __init__(self, message: str, errors: Optional[list] = None):
        super().__init__(message)
        self.errors = errors or []


class SchemaValidator:
    """
    Schema validator for RDP Controller service
    
    Loads and validates data against JSON schemas defined in:
    - health-schema.json: Health check response validation
    - session-schema.json: Session data structure validation
    - metrics-schema.json: Metrics data structure validation
    """
    
    def __init__(self, schema_dir: Optional[str] = None):
        """
        Initialize schema validator
        
        Args:
            schema_dir: Directory containing schema files (default: /app/session_controller)
        """
        if not JSONSCHEMA_AVAILABLE:
            logger.warning("jsonschema not available, schema validation disabled")
            self.enabled = False
            return
        
        self.enabled = True
        self.schema_dir = Path(schema_dir or '/app/session_controller')
        self._schemas: Dict[str, Dict[str, Any]] = {}
        self._validators: Dict[str, Draft7Validator] = {}
        
        # Load schemas on initialization
        self._load_schemas()
    
    def _load_schemas(self):
        """Load all JSON schema files"""
        if not self.enabled:
            return
        
        schema_files = {
            'health': 'health-schema.json',
            'session': 'session-schema.json',
            'metrics': 'metrics-schema.json'
        }
        
        for schema_name, schema_file in schema_files.items():
            schema_path = self.schema_dir / schema_file
            try:
                if schema_path.exists():
                    with open(schema_path, 'r', encoding='utf-8') as f:
                        schema = json.load(f)
                        self._schemas[schema_name] = schema
                        self._validators[schema_name] = Draft7Validator(schema)
                        logger.info(f"Loaded schema: {schema_name} from {schema_path}")
                else:
                    logger.warning(f"Schema file not found: {schema_path}")
            except Exception as e:
                logger.error(f"Failed to load schema {schema_name}: {e}", exc_info=True)
    
    def validate_health_response(self, data: Dict[str, Any]) -> bool:
        """
        Validate health check response against health-schema.json
        
        Args:
            data: Health check response data
            
        Returns:
            True if valid
            
        Raises:
            SchemaValidationError: If validation fails
        """
        if not self.enabled:
            return True
        
        if 'health' not in self._validators:
            logger.warning("Health schema not loaded, skipping validation")
            return True
        
        try:
            self._validators['health'].validate(data)
            return True
        except ValidationError as e:
            errors = [str(error) for error in self._validators['health'].iter_errors(data)]
            raise SchemaValidationError(
                f"Health response validation failed: {e.message}",
                errors=errors
            )
    
    def validate_session_data(self, data: Dict[str, Any]) -> bool:
        """
        Validate session data against session-schema.json
        
        Args:
            data: Session data dictionary
            
        Returns:
            True if valid
            
        Raises:
            SchemaValidationError: If validation fails
        """
        if not self.enabled:
            return True
        
        if 'session' not in self._validators:
            logger.warning("Session schema not loaded, skipping validation")
            return True
        
        try:
            # Extract RdpSession definition from schema if it exists
            schema = self._schemas.get('session', {})
            if 'definitions' in schema and 'RdpSession' in schema['definitions']:
                session_schema = {
                    "$schema": schema.get("$schema", "http://json-schema.org/draft-07/schema#"),
                    **schema['definitions']['RdpSession']
                }
                validate(instance=data, schema=session_schema)
            else:
                # Fallback to full schema if no definitions
                self._validators['session'].validate(data)
            return True
        except ValidationError as e:
            errors = []
            if 'definitions' in schema and 'RdpSession' in schema['definitions']:
                session_schema = {
                    "$schema": schema.get("$schema", "http://json-schema.org/draft-07/schema#"),
                    **schema['definitions']['RdpSession']
                }
                validator = Draft7Validator(session_schema)
                errors = [str(error) for error in validator.iter_errors(data)]
            else:
                errors = [str(error) for error in self._validators['session'].iter_errors(data)]
            raise SchemaValidationError(
                f"Session data validation failed: {e.message}",
                errors=errors
            )
    
    def validate_metrics_data(self, data: Dict[str, Any]) -> bool:
        """
        Validate metrics data against metrics-schema.json
        
        Args:
            data: Metrics data dictionary
            
        Returns:
            True if valid
            
        Raises:
            SchemaValidationError: If validation fails
        """
        if not self.enabled:
            return True
        
        if 'metrics' not in self._validators:
            logger.warning("Metrics schema not loaded, skipping validation")
            return True
        
        try:
            self._validators['metrics'].validate(data)
            return True
        except ValidationError as e:
            errors = [str(error) for error in self._validators['metrics'].iter_errors(data)]
            raise SchemaValidationError(
                f"Metrics data validation failed: {e.message}",
                errors=errors
            )
    
    def validate_against_schema(self, data: Dict[str, Any], schema_name: str) -> bool:
        """
        Generic validation against a named schema
        
        Args:
            data: Data to validate
            schema_name: Name of schema ('health', 'session', 'metrics')
            
        Returns:
            True if valid
            
        Raises:
            SchemaValidationError: If validation fails
        """
        if not self.enabled:
            return True
        
        if schema_name not in self._validators:
            logger.warning(f"Schema '{schema_name}' not loaded, skipping validation")
            return True
        
        try:
            self._validators[schema_name].validate(data)
            return True
        except ValidationError as e:
            errors = [str(error) for error in self._validators[schema_name].iter_errors(data)]
            raise SchemaValidationError(
                f"Schema validation failed for '{schema_name}': {e.message}",
                errors=errors
            )
    
    def get_schema(self, schema_name: str) -> Optional[Dict[str, Any]]:
        """
        Get loaded schema by name
        
        Args:
            schema_name: Name of schema ('health', 'session', 'metrics')
            
        Returns:
            Schema dictionary or None if not found
        """
        return self._schemas.get(schema_name)


# Global schema validator instance (initialized on module import)
_schema_validator: Optional[SchemaValidator] = None


def get_schema_validator() -> SchemaValidator:
    """
    Get global schema validator instance (singleton pattern)
    
    Returns:
        SchemaValidator instance
    """
    global _schema_validator
    if _schema_validator is None:
        schema_dir = os.getenv('RDP_CONTROLLER_SCHEMA_DIR', '/app/session_controller')
        _schema_validator = SchemaValidator(schema_dir=schema_dir)
    return _schema_validator


def validate_health_response(data: Dict[str, Any]) -> bool:
    """
    Convenience function to validate health response
    
    Args:
        data: Health check response data
        
    Returns:
        True if valid
        
    Raises:
        SchemaValidationError: If validation fails
    """
    return get_schema_validator().validate_health_response(data)


def validate_session_data(data: Dict[str, Any]) -> bool:
    """
    Convenience function to validate session data
    
    Args:
        data: Session data dictionary
        
    Returns:
        True if valid
        
    Raises:
        SchemaValidationError: If validation fails
    """
    return get_schema_validator().validate_session_data(data)


def validate_metrics_data(data: Dict[str, Any]) -> bool:
    """
    Convenience function to validate metrics data
    
    Args:
        data: Metrics data dictionary
        
    Returns:
        True if valid
        
    Raises:
        SchemaValidationError: If validation fails
    """
    return get_schema_validator().validate_metrics_data(data)

