# XRDP API Configuration

This directory contains configuration templates and documentation for the `rdp-xrdp` service.

## Files

- `env.rdp-xrdp.template` - Environment variable template file

## Configuration Philosophy

The XRDP API service follows the master design pattern for configuration management:

1. **Environment Variables** (highest priority) - Override all other sources
2. **YAML Configuration File** (`config.yaml`) - Default values baked into the image
3. **Pydantic Field Defaults** (lowest priority) - Fallback defaults

## Environment Variables

### Required Variables

These must be set via docker-compose environment files:

- `MONGODB_URL` - MongoDB connection string (from `.env.secrets`)
- `REDIS_URL` - Redis connection string (from `.env.core` or `.env.secrets`)
- `RDP_XRDP_HOST` - Service name for service discovery (from docker-compose)
- `RDP_XRDP_URL` - Service URL (from docker-compose)

### Optional Variables

- `XRDP_PORT` - Service port (default: 3389)
- `MAX_XRDP_PROCESSES` - Maximum concurrent XRDP processes (default: 10)
- `PROCESS_TIMEOUT` - Process timeout in seconds (default: 30)
- `LOG_LEVEL` - Logging level (default: INFO)
- `CORS_ORIGINS` - CORS allowed origins (default: "*")

## Configuration File

The service supports an optional `config.yaml` file that can be mounted into the container. This file provides default values that can be overridden by environment variables.

### Location

- **Baked-in:** `/app/xrdp/config.yaml` (included in Docker image)
- **External mount:** Can be mounted via volume in docker-compose

### Environment Variable Override

The `XRDP_CONFIG_FILE` environment variable can be used to specify a custom configuration file path:

```yaml
environment:
  - XRDP_CONFIG_FILE=/app/config/xrdp-config.yaml
```

## Usage

1. Copy the template file:
   ```bash
   cp RDP/xrdp/config/env.rdp-xrdp.template configs/environment/.env.rdp-xrdp
   ```

2. Customize values in `.env.rdp-xrdp` as needed

3. Ensure docker-compose references the file:
   ```yaml
   env_file:
     - /mnt/myssd/Lucid/Lucid/configs/environment/.env.rdp-xrdp
   ```

## Notes

- All database URLs must use service names (not `localhost` or `127.0.0.1`)
- Storage paths should match volume mount paths in docker-compose
- CORS origins can be a comma-separated list or "*" for all origins
- Port validation ensures ports are in the valid range (1-65535)

