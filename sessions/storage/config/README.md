# Session Storage Configuration Guide

## Overview

The session-storage container follows the **master-docker-design.md** configuration philosophy:

1. **Environment Variables** (PRIMARY source - highest priority, override everything)
2. **YAML/JSON Configuration Files** (OPTIONAL - defaults only, with env var fallbacks)
3. **Pydantic Field Defaults** (fallback - lowest priority)

**Key Principles:**
- Environment variables are the **primary** configuration source
- Configuration files (YAML/JSON) are **optional** and provide defaults only
- Environment variables **always override** file-based configuration
- **No secrets in code** - all secrets must come from environment variables
- Configuration is validated on startup with clear error messages

## Configuration Files (Optional)

**Note:** Configuration files are **optional**. Environment variables are the primary configuration source and always override file values.

### Supported Formats

- **YAML** (`.yaml`, `.yml`) - Requires PyYAML (included in requirements)
- **JSON** (`.json`) - Built-in Python support (always available)

### Configuration File Locations

The container looks for configuration files in this order:

1. Path specified by `SESSION_STORAGE_CONFIG_FILE` environment variable (if set)
2. `/app/sessions/storage/config.yaml` (baked into image - optional)
3. `/app/sessions/storage/config.json` (baked into image - optional)

If no configuration file is found, the service uses environment variables and Pydantic defaults only.

### Using External Configuration Files

#### Option 1: Environment Variable

Set `SESSION_STORAGE_CONFIG_FILE` environment variable in docker-compose:

```yaml
environment:
  - SESSION_STORAGE_CONFIG_FILE=/app/config/session-storage.yaml
```

#### Option 2: Volume Mount

Mount an external config file in docker-compose:

```yaml
volumes:
  - /mnt/myssd/Lucid/Lucid/configs/session-storage/config.yaml:/app/sessions/storage/config.yaml:ro
```

Or for JSON:

```yaml
volumes:
  - /mnt/myssd/Lucid/Lucid/configs/session-storage/config.json:/app/sessions/storage/config.json:ro
```

## Configuration Priority (Master Design Standard)

**Priority Order** (highest to lowest):

1. **Environment Variables** - Always override file values
2. **YAML/JSON Configuration Files** - Provide defaults (optional)
3. **Pydantic Field Defaults** - Fallback values

**Example:**
- Config file sets: `LUCID_CHUNK_SIZE_MB: 10`
- Environment variable: `LUCID_CHUNK_SIZE_MB=20`
- **Result**: `LUCID_CHUNK_SIZE_MB = 20` (environment variable wins)

This follows the master-docker-design.md configuration philosophy.

## Configuration File Format

### YAML Example

```yaml
SERVICE_NAME: "lucid-session-storage"
LOG_LEVEL: "INFO"
LUCID_CHUNK_SIZE_MB: 10
LUCID_COMPRESSION_LEVEL: 6
LUCID_COMPRESSION_ALGORITHM: "zstd"
LUCID_RETENTION_DAYS: 30
```

### JSON Example

**Note:** JSON does not support comments. For detailed field descriptions, see `config.yaml` or `env.session-storage.template`.

```json
{
  "SERVICE_NAME": "lucid-session-storage",
  "LOG_LEVEL": "INFO",
  "LUCID_CHUNK_SIZE_MB": 10,
  "LUCID_COMPRESSION_LEVEL": 6,
  "LUCID_COMPRESSION_ALGORITHM": "zstd",
  "LUCID_RETENTION_DAYS": 30,
  "MONGODB_URL": "",
  "REDIS_URL": ""
}
```

**Important:** Empty strings (`""`) for `MONGODB_URL` and `REDIS_URL` indicate these values must be provided via environment variables (required, no secrets in config files).

## Empty Values in Config Files

Empty strings (`""`) in configuration files indicate "use environment variable". These are automatically filtered out, allowing environment variables to provide the values.

Example:
```yaml
MONGODB_URL: ""  # Will use MONGODB_URL from environment
REDIS_URL: ""    # Will use REDIS_URL from environment
```

## Best Practices (Master Design Compliance)

1. **Environment Variables for Secrets**: Never put passwords, URLs, or secrets in config files - use environment variables only
2. **Config Files for Defaults Only**: Use YAML/JSON files for non-sensitive defaults, override with env vars per environment
3. **No Hardcoded Values**: All configuration from environment variables (primary) or files (optional defaults)
4. **Validation on Startup**: Configuration is validated on startup with clear error messages
5. **Read-Only Mounts**: Mount config files as read-only (`:ro`) for security
6. **Version Control**: Keep config file templates in version control, but not production values or secrets

## Example: Production Setup

```yaml
# docker-compose.application.yml
session-storage:
  volumes:
    # Mount external config for easy updates without rebuild
    - /mnt/myssd/Lucid/Lucid/configs/session-storage/production.yaml:/app/sessions/storage/config.yaml:ro
  environment:
    # Override specific values per environment
    - LUCID_RETENTION_DAYS=90
    - LUCID_MAX_SESSIONS=5000
```

## Troubleshooting

### Config file not loading

1. Check file path is correct
2. Verify file permissions (readable by user 65532:65532)
3. Check container logs for configuration loading messages
4. Verify file format (YAML or JSON syntax)

### Environment variables not overriding

1. Ensure environment variable name matches exactly (case-sensitive)
2. Check docker-compose environment section
3. Verify env_file entries are loaded in correct order

### Validation errors

1. Check configuration file syntax
2. Verify value types match expected types (int, str, bool)
3. Check value ranges (e.g., LUCID_CHUNK_SIZE_MB must be 1-100)

## Reference Files

- `config.yaml` - Default YAML configuration template (baked into image, optional)
- `config.json.example` - Example JSON configuration template (baked into image, optional)
- `env.session-storage.template` - Environment variable template (required - use for secrets and URLs)

## Environment Variables

See `env.session-storage.template` for the complete list of supported environment variables.

**Required Environment Variables:**
- `MONGODB_URL` or `MONGO_URL` - MongoDB connection string (required)
- `REDIS_URL` - Redis connection string (required)

**Optional Environment Variables:**
- `SESSION_STORAGE_HOST` - Host bind address (default: `0.0.0.0`)
- `SESSION_STORAGE_PORT` - Service port (default: `8082`)
- `SESSION_STORAGE_CONFIG_FILE` - Path to external config file (optional)
- `LOG_LEVEL` - Logging level (default: `INFO`)
- See `env.session-storage.template` for complete list

## API Endpoints

- `GET /health` - Health check endpoint
- `GET /docs` - OpenAPI documentation
- `GET /redoc` - ReDoc documentation

## Error Handling

The configuration system follows master-docker-design.md error handling patterns:

- **Invalid JSON/YAML**: Logs error with context, falls back to environment variables and defaults (graceful degradation)
- **Missing file**: If explicitly specified via `SESSION_STORAGE_CONFIG_FILE`, raises clear error. Otherwise, uses environment variables and defaults
- **Validation errors**: Logs detailed error with actionable information, specifies what failed and why
- **Missing required values**: Pydantic validators ensure required values are present, fail fast with clear messages
- **Clear error messages**: All errors include actionable information and resolution suggestions

## Related Documentation

- `build/docs/master-docker-design.md` - Universal Docker design patterns
- `sessions/storage/config.py` - Configuration module implementation

