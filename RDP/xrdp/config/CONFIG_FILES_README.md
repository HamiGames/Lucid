# XRDP Service Configuration Files

This directory contains support configuration files for the `rdp-xrdp` container to make it more operational and robust.

## File Overview

### 1. `docker-compose.application.yml`
**Purpose:** Docker Compose service definition snippet for the rdp-xrdp container.

**Usage:**
- Include this snippet in `configs/docker/docker-compose.application.yml`
- Provides complete service definition with volumes, networks, environment variables, health checks, and security settings
- Follows the master-docker-design.md patterns

**Key Features:**
- Distroless container configuration
- Proper volume mounts for config, data, and logs
- Health check using socket-based Python command
- Security hardening (read-only filesystem, dropped capabilities)
- Proper user permissions (65532:65532)

### 2. `operational-config.json`
**Purpose:** Runtime operational settings in JSON format with schema validation.

**Usage:**
- Can be loaded by the application at startup
- Provides structured configuration for process management, resource limits, network, security, monitoring, storage, and integration
- Includes JSON schema for validation

**Key Sections:**
- `service`: Service identification and metadata
- `process_management`: XRDP process lifecycle settings
- `resource_limits`: Memory, CPU, and disk limits
- `network`: Network configuration
- `security`: Security and CORS settings
- `monitoring`: Metrics and logging configuration
- `storage`: Storage paths and retention policies
- `integration`: Service integration URLs and timeouts

### 3. `monitoring-config.yaml`
**Purpose:** Prometheus metrics, alerting rules, and monitoring setup.

**Usage:**
- Configure Prometheus scraping
- Define metrics to collect
- Set up alerting rules for critical conditions
- Service discovery configuration

**Key Features:**
- Process metrics (counters, gauges)
- Configuration metrics
- API metrics (request counts, durations, errors)
- Health metrics
- Alert rules for:
  - High process failure rate
  - Maximum processes reached
  - High memory/CPU usage
  - API errors and slow responses
  - Service health issues

### 4. `logging-config.yaml`
**Purpose:** Structured logging configuration following Python logging standards.

**Usage:**
- Python logging configuration in YAML format
- Can be loaded using `logging.config.dictConfig()`
- Supports multiple handlers (console, file, JSON)

**Key Features:**
- Multiple loggers (application, FastAPI, access, error)
- Rotating file handlers with size limits
- JSON logging for machine parsing
- Structured logging fields
- Log rotation and retention policies
- Sensitive data filtering

**Log Files:**
- `/app/logs/xrdp-service.log` - Human-readable application logs
- `/app/logs/xrdp-service.json.log` - Machine-readable JSON logs
- `/app/logs/xrdp-access.log` - HTTP access logs
- `/app/logs/xrdp-error.log` - Error logs only

### 5. `service-config.yaml`
**Purpose:** Enhanced service configuration with detailed operational settings.

**Usage:**
- Extends the base `config.yaml` with additional operational settings
- Provides comprehensive configuration for all service aspects
- Can be merged with environment variables (env vars take precedence)

**Key Sections:**
- Service metadata
- Network configuration with CORS
- Database configuration (MongoDB, Redis)
- Process management settings
- Resource limits
- Storage configuration
- Security settings
- Integration service URLs
- Health check configuration
- Monitoring settings
- XRDP configuration generation
- Error handling
- Performance tuning
- Feature flags

### 6. `health-check-config.json`
**Purpose:** Detailed health check configuration with component-level checks.

**Usage:**
- Define health check behavior and thresholds
- Configure individual component checks
- Set up dependency health checks
- Customize response format

**Key Features:**
- Main health check settings (interval, timeout, retries)
- Component checks:
  - Service initialization
  - MongoDB connection
  - Redis connection
  - Process manager
  - Config manager
  - Storage paths
  - Active processes
- Response format customization
- HTTP status code mapping
- External dependency checks

## Configuration Priority

Configuration loading priority (highest to lowest):

1. **Environment Variables** (highest priority - always override)
2. **YAML Configuration Files** (`config.yaml`, `service-config.yaml`)
3. **JSON Configuration Files** (`operational-config.json`, `health-check-config.json`)
4. **Default Values** (lowest priority)

## Usage Examples

### Loading YAML Configuration

```python
import yaml
from pathlib import Path

config_path = Path("/app/config/service-config.yaml")
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)
```

### Loading JSON Configuration

```python
import json
from pathlib import Path

config_path = Path("/app/config/operational-config.json")
with open(config_path, 'r') as f:
    config = json.load(f)
```

### Loading Logging Configuration

```python
import yaml
import logging.config
from pathlib import Path

logging_config_path = Path("/app/config/logging-config.yaml")
with open(logging_config_path, 'r') as f:
    logging_config = yaml.safe_load(f)
    logging.config.dictConfig(logging_config)
```

## Environment Variables

All configuration files support environment variable overrides. Key environment variables:

- `MONGODB_URL` - MongoDB connection URL (required)
- `REDIS_URL` - Redis connection URL (required)
- `XRDP_PORT` - Service port (default: 3389)
- `RDP_XRDP_URL` - Service URL for internal communication
- `MAX_XRDP_PROCESSES` - Maximum concurrent processes (default: 10)
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `CORS_ORIGINS` - CORS allowed origins (comma-separated)
- `SERVICE_TIMEOUT_SECONDS` - Service call timeout (default: 30)
- `SERVICE_RETRY_COUNT` - Service retry count (default: 3)

## Integration with Docker Compose

To use the docker-compose snippet:

1. Copy the contents of `docker-compose.application.yml` into `configs/docker/docker-compose.application.yml`
2. Ensure all required environment files exist:
   - `.env.foundation`
   - `.env.core`
   - `.env.application`
   - `.env.secrets`
   - `.env.rdp-xrdp`
3. Create required directories on the host:
   ```bash
   mkdir -p /mnt/myssd/Lucid/Lucid/data/rdp-xrdp/{config,sessions}
   mkdir -p /mnt/myssd/Lucid/Lucid/logs/rdp-xrdp
   chown -R 65532:65532 /mnt/myssd/Lucid/Lucid/data/rdp-xrdp
   chown -R 65532:65532 /mnt/myssd/Lucid/Lucid/logs/rdp-xrdp
   ```

## Monitoring Integration

To integrate with Prometheus:

1. Add the service discovery configuration from `monitoring-config.yaml` to your Prometheus configuration
2. Ensure the metrics endpoint is accessible at `http://rdp-xrdp:9090/metrics`
3. Import the alerting rules from `monitoring-config.yaml` into your Alertmanager configuration

## Logging Integration

To use structured logging:

1. Load `logging-config.yaml` at application startup
2. Ensure log directories exist and have proper permissions
3. Configure log rotation and retention as needed
4. For production, use JSON logging for better integration with log aggregation systems

## Health Check Integration

The health check configuration can be used to:

1. Customize health check behavior
2. Add component-level health checks
3. Configure dependency health checks
4. Customize response format for monitoring systems

## Notes

- All paths in configuration files use container paths (e.g., `/app/config`, `/app/logs`)
- Host paths are mapped via Docker volume mounts
- Environment variables always override file-based configuration
- JSON schema validation is available for `operational-config.json` and `health-check-config.json`
- YAML files follow standard YAML 1.2 specification
- All configuration files are optional - the service can run with environment variables only

## Related Files

- `config.yaml` - Base configuration file (already exists)
- `config.py` - Configuration loading module
- `env.rdp-xrdp.template` - Environment variable template
- `README.md` - General configuration documentation

