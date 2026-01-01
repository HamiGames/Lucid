# RDP Controller Schema Usage Documentation

**Version:** 1.0.0  
**Last Updated:** 2025-01-27  
**Service:** `lucid-rdp-controller`  
**Container Name:** `rdp-controller`  
**Purpose:** Documentation for JSON schema and OpenAPI YAML file usage in the RDP Controller service

This document explains how the `rdp-controller` container uses its support JSON and YAML files for operations and functions, following the patterns established in `session-api-design.md`, `master-docker-design.md`, and other Lucid design documents.

---

## Table of Contents

1. [Overview](#overview)
2. [Schema Files](#schema-files)
3. [OpenAPI Integration](#openapi-integration)
4. [Schema Validation](#schema-validation)
5. [Usage Patterns](#usage-patterns)
6. [Configuration](#configuration)
7. [Error Handling](#error-handling)
8. [Best Practices](#best-practices)

---

## Overview

The `rdp-controller` container uses JSON schema files and an OpenAPI YAML specification file to:

- **Validate API responses** against defined schemas
- **Document API structure** via OpenAPI specification
- **Ensure data consistency** across service boundaries
- **Provide type safety** for API responses
- **Enable API documentation** generation (Swagger/ReDoc)

### Design Principles

Following `master-docker-design.md` and `session-api-design.md`:

1. **Graceful Degradation**: Schema validation is optional - service continues operation if validation fails
2. **No Hardcoded Values**: All schema paths configurable via environment variables
3. **Error Handling**: Validation errors are logged but don't break service operation
4. **Performance**: Schema loading happens once at startup, validation is fast
5. **Consistency**: Uses same patterns as other Lucid services (session-api, session-pipeline)

---

## Schema Files

### File Locations

All schema files are located in `/app/session_controller/` (container path):

```
/app/session_controller/
├── health-schema.json      # Health check response schema
├── session-schema.json     # Session data structure schema
├── metrics-schema.json     # Metrics data structure schema
└── openapi.yaml            # OpenAPI 3.0 specification
```

### Schema File Descriptions

#### 1. `health-schema.json`

**Purpose**: Validates health check endpoint responses

**Schema Structure**:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "RDP Controller Health Check Response Schema",
  "type": "object",
  "required": ["status", "service", "version", "timestamp"],
  "properties": {
    "status": {"type": "string", "enum": ["healthy"]},
    "service": {"type": "string"},
    "version": {"type": "string"},
    "timestamp": {"type": "string", "format": "date-time"}
  }
}
```

**Used By**: `/health` endpoint response validation

**Validation**: Automatic on health check responses

#### 2. `session-schema.json`

**Purpose**: Validates RDP session data structures

**Schema Structure**:
- Defines `RdpSession` object structure
- Defines `SessionStatus` enumeration
- Defines `SessionMetrics` object structure
- Defines `RdpConnection` object structure

**Used By**: 
- `/api/v1/sessions` endpoints
- Session creation and retrieval
- Session status updates

**Validation**: Automatic on session data responses

#### 3. `metrics-schema.json`

**Purpose**: Validates metrics data structures

**Schema Structure**:
- Defines service metrics structure
- Defines session metrics structure
- Defines connection metrics structure
- Defines integration health status structure

**Used By**:
- `/api/v1/sessions/{session_id}/metrics` endpoint
- `/api/v1/connections/{connection_id}/metrics` endpoint
- Metrics collection and reporting

**Validation**: Automatic on metrics responses

#### 4. `openapi.yaml`

**Purpose**: OpenAPI 3.0 specification for API documentation

**Contents**:
- Complete API endpoint definitions
- Request/response schemas
- Error response definitions
- Authentication requirements
- Example requests/responses

**Used By**:
- FastAPI automatic documentation generation (`/docs`, `/redoc`)
- API client generation
- API testing tools

**Integration**: Loaded at application startup and used to override FastAPI's auto-generated OpenAPI schema

---

## OpenAPI Integration

### Loading OpenAPI Schema

The OpenAPI schema is loaded at application startup in `main.py`:

```python
def load_openapi_schema() -> Optional[Dict[str, Any]]:
    """Load OpenAPI schema from openapi.yaml file"""
    schema_path = Path('/app/session_controller/openapi.yaml')
    if not schema_path.exists():
        logger.warning(f"OpenAPI schema file not found: {schema_path}")
        return None
    
    try:
        if YAML_AVAILABLE:
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema = yaml.safe_load(f)
                logger.info(f"Loaded OpenAPI schema from {schema_path}")
                return schema
        else:
            logger.warning("PyYAML not available, cannot load OpenAPI schema")
            return None
    except Exception as e:
        logger.error(f"Failed to load OpenAPI schema: {e}", exc_info=True)
        return None
```

### FastAPI Integration

The loaded schema overrides FastAPI's auto-generated OpenAPI schema:

```python
app = FastAPI(
    title="Lucid RDP Session Controller",
    description="RDP session management and monitoring service",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Override OpenAPI schema if loaded from file
if openapi_schema:
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    
    app.openapi = custom_openapi
    logger.info("OpenAPI schema loaded from openapi.yaml")
```

### Benefits

1. **Consistent Documentation**: API docs match the actual API structure
2. **Client Generation**: Can generate API clients from OpenAPI spec
3. **Testing**: Can use OpenAPI spec for API testing
4. **Versioning**: OpenAPI spec documents API version and changes

---

## Schema Validation

### Schema Validator Module

The `schema_validator.py` module provides schema validation functionality:

**Location**: `/app/session_controller/schema_validator.py`

**Key Classes**:
- `SchemaValidator`: Main validation class
- `SchemaValidationError`: Exception for validation failures

**Key Functions**:
- `validate_health_response(data)`: Validate health check responses
- `validate_session_data(data)`: Validate session data
- `validate_metrics_data(data)`: Validate metrics data
- `get_schema_validator()`: Get singleton validator instance

### Validation Pattern

Validation follows a graceful degradation pattern:

```python
# Validate response against schema (graceful degradation if validation fails)
try:
    schema_validator = get_schema_validator()
    if schema_validator.enabled:
        schema_validator.validate_health_response(response_data)
except SchemaValidationError as e:
    logger.warning(f"Health response schema validation failed: {e}")
    # Continue anyway - validation is optional
```

**Key Points**:
- Validation errors are logged but don't break service operation
- Service continues even if schema files are missing
- Validation is disabled if `jsonschema` package is not available

### Validation Usage Examples

#### Health Check Validation

```python
@app.get("/health")
async def health_check():
    response_data = {
        "status": "healthy",
        "service": "rdp-session-controller",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "integrations": integration_status
    }
    
    # Validate against health-schema.json
    try:
        schema_validator = get_schema_validator()
        if schema_validator.enabled:
            schema_validator.validate_health_response(response_data)
    except SchemaValidationError as e:
        logger.warning(f"Health response schema validation failed: {e}")
    
    return response_data
```

#### Session Data Validation

```python
@app.get("/api/v1/sessions/{session_id}")
async def get_session(session_id: UUID):
    session = await session_controller.get_session(session_id)
    session_dict = session.to_dict()
    
    # Validate against session-schema.json
    try:
        schema_validator = get_schema_validator()
        if schema_validator.enabled:
            schema_validator.validate_session_data(session_dict)
    except SchemaValidationError as e:
        logger.warning(f"Session data schema validation failed: {e}")
    
    return session_dict
```

#### Metrics Data Validation

```python
@app.get("/api/v1/sessions/{session_id}/metrics")
async def get_session_metrics(session_id: UUID):
    metrics = await session_controller.get_session_metrics(session_id)
    metrics_dict = metrics.to_dict()
    
    # Validate against metrics-schema.json
    try:
        schema_validator = get_schema_validator()
        if schema_validator.enabled:
            schema_validator.validate_metrics_data(metrics_dict)
    except SchemaValidationError as e:
        logger.warning(f"Metrics data schema validation failed: {e}")
    
    return metrics_dict
```

---

## Usage Patterns

### Pattern 1: Automatic Response Validation

**Use Case**: Validate all API responses against schemas

**Implementation**: Add validation to each endpoint handler

**Benefits**:
- Catches data structure errors early
- Ensures API consistency
- Helps with debugging

**Example**:
```python
@app.get("/api/v1/sessions/{session_id}")
async def get_session(session_id: UUID):
    session = await session_controller.get_session(session_id)
    session_dict = session.to_dict()
    
    # Automatic validation
    validate_session_data(session_dict)  # Raises SchemaValidationError if invalid
    
    return session_dict
```

### Pattern 2: Optional Validation

**Use Case**: Validate responses but don't break service if validation fails

**Implementation**: Wrap validation in try/except

**Benefits**:
- Service continues even if schemas are outdated
- Validation errors are logged for debugging
- Production stability

**Example**:
```python
try:
    schema_validator.validate_session_data(session_dict)
except SchemaValidationError as e:
    logger.warning(f"Schema validation failed: {e}")
    # Continue with response anyway
```

### Pattern 3: Schema Loading at Startup

**Use Case**: Load all schemas once at application startup

**Implementation**: Initialize `SchemaValidator` in `lifespan()` startup

**Benefits**:
- Fast validation (schemas pre-loaded)
- Early error detection (fail fast if schemas invalid)
- Single point of configuration

**Example**:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    schema_validator = get_schema_validator()  # Loads all schemas
    logger.info("Schema validator initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down")
```

---

## Configuration

### Environment Variables

**Schema Directory**:
- `RDP_CONTROLLER_SCHEMA_DIR`: Directory containing schema files (default: `/app/session_controller`)

**Example**:
```bash
RDP_CONTROLLER_SCHEMA_DIR=/app/session_controller
```

### Schema File Paths

All schema files are expected in the schema directory:

```
${RDP_CONTROLLER_SCHEMA_DIR}/
├── health-schema.json
├── session-schema.json
├── metrics-schema.json
└── openapi.yaml
```

### Dockerfile Integration

Schema files are copied into the container during build:

```dockerfile
# Copy schema files
COPY --chown=65532:65532 RDP/session-controller/health-schema.json /app/session_controller/health-schema.json
COPY --chown=65532:65532 RDP/session-controller/session-schema.json /app/session_controller/session-schema.json
COPY --chown=65532:65532 RDP/session-controller/metrics-schema.json /app/session_controller/metrics-schema.json
COPY --chown=65532:65532 RDP/session-controller/openapi.yaml /app/session_controller/openapi.yaml
```

---

## Error Handling

### Schema Loading Errors

**Scenario**: Schema file missing or invalid

**Handling**:
- Log warning
- Continue without validation
- Service operates normally

**Example**:
```python
if schema_path.exists():
    schema = load_schema(schema_path)
else:
    logger.warning(f"Schema file not found: {schema_path}")
    # Continue without validation
```

### Validation Errors

**Scenario**: Response data doesn't match schema

**Handling**:
- Log warning with error details
- Return response anyway (graceful degradation)
- Don't break service operation

**Example**:
```python
try:
    schema_validator.validate_session_data(session_dict)
except SchemaValidationError as e:
    logger.warning(f"Schema validation failed: {e}")
    logger.debug(f"Validation errors: {e.errors}")
    # Continue with response
```

### Missing Dependencies

**Scenario**: `jsonschema` package not installed

**Handling**:
- Disable validation
- Log warning
- Service operates normally

**Example**:
```python
try:
    import jsonschema
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False
    logger.warning("jsonschema not available, schema validation disabled")
```

---

## Best Practices

### 1. Keep Schemas Updated

**Practice**: Update schemas when API changes

**Rationale**: Outdated schemas cause false validation failures

**Example**:
- When adding new fields to session data, update `session-schema.json`
- When changing health response format, update `health-schema.json`

### 2. Use Graceful Degradation

**Practice**: Never break service operation due to validation failures

**Rationale**: Production stability is more important than perfect validation

**Example**:
```python
try:
    validate_response(data)
except SchemaValidationError:
    logger.warning("Validation failed, but continuing")
    # Don't raise exception
```

### 3. Log Validation Errors

**Practice**: Log all validation errors with context

**Rationale**: Helps with debugging and monitoring

**Example**:
```python
except SchemaValidationError as e:
    logger.warning(f"Schema validation failed: {e}")
    logger.debug(f"Validation errors: {e.errors}")
    logger.debug(f"Data: {data}")
```

### 4. Validate at Response Time

**Practice**: Validate responses before returning to client

**Rationale**: Catches errors early, ensures API consistency

**Example**:
```python
response_data = build_response()
validate_response(response_data)  # Validate before return
return response_data
```

### 5. Use OpenAPI for Documentation

**Practice**: Keep `openapi.yaml` synchronized with actual API

**Rationale**: Accurate API documentation helps developers

**Example**:
- Update `openapi.yaml` when adding new endpoints
- Update request/response schemas in OpenAPI spec
- Use OpenAPI spec for client generation

---

## Naming Consistency

### Container Naming

Following `mod-design-template.md` and `master-docker-design.md`:

- **Container Name**: `rdp-controller` (lowercase, hyphen-separated)
- **Service Name**: `rdp-session-controller` (for API responses)
- **Image Name**: `pickme/lucid-rdp-controller:latest-arm64`

### Schema File Naming

Following `session-api-design.md` patterns:

- **Health Schema**: `health-schema.json`
- **Session Schema**: `session-schema.json`
- **Metrics Schema**: `metrics-schema.json`
- **OpenAPI Spec**: `openapi.yaml`

### Module Naming

Following Python naming conventions:

- **Validator Module**: `schema_validator.py`
- **Validator Class**: `SchemaValidator`
- **Exception Class**: `SchemaValidationError`
- **Function Names**: `validate_health_response()`, `validate_session_data()`, etc.

### Environment Variable Naming

Following `master-docker-design.md`:

- **Schema Directory**: `RDP_CONTROLLER_SCHEMA_DIR`
- **Service Prefix**: `RDP_CONTROLLER_*` (consistent with other env vars)

---

## Cross-Container Consistency

### Alignment with Other Services

The `rdp-controller` schema usage follows the same patterns as:

1. **session-api**: Uses similar schema validation patterns
2. **session-pipeline**: Uses similar error handling patterns
3. **data-chain**: Uses similar graceful degradation patterns

### Shared Patterns

All Lucid services follow these patterns:

1. **Schema Loading**: Load at startup, cache for performance
2. **Validation**: Optional, graceful degradation on failure
3. **Error Handling**: Log warnings, don't break service
4. **Configuration**: Environment variable driven
5. **Documentation**: OpenAPI spec for API documentation

---

## Related Documentation

- `build/docs/master-docker-design.md` - Master Docker design principles
- `build/docs/session-api-design.md` - Session API design patterns
- `build/docs/mod-design-template.md` - Module design template
- `RDP/session-controller/config.py` - Configuration management
- `RDP/session-controller/main.py` - FastAPI application

---

## Summary

The `rdp-controller` container uses JSON schema files and OpenAPI YAML for:

1. **Response Validation**: Validates API responses against schemas
2. **API Documentation**: Uses OpenAPI spec for Swagger/ReDoc docs
3. **Data Consistency**: Ensures consistent data structures
4. **Error Detection**: Catches data structure errors early
5. **Developer Experience**: Provides accurate API documentation

All schema usage follows Lucid design principles:
- Graceful degradation
- Environment-driven configuration
- Consistent naming conventions
- Cross-container alignment
- Production stability

---

**Last Updated:** 2025-01-27  
**Status:** ACTIVE  
**Maintained By:** Lucid Development Team

