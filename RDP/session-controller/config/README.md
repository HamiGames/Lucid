# RDP Controller Configuration

This directory contains configuration templates and documentation for the RDP Controller service.

## Files

### `env.rdp-controller.template`

Environment variable template file. Copy this to `.env.rdp-controller` and fill in actual values:

```bash
cp env.rdp-controller.template /mnt/myssd/Lucid/Lucid/configs/environment/.env.rdp-controller
```

**Important:** Do NOT commit `.env.rdp-controller` to version control.

## Configuration Priority

Configuration is loaded in the following priority order (highest to lowest):

1. **Environment Variables** (from `.env.*` files in docker-compose)
2. **YAML Configuration File** (`config.yaml` - optional)
3. **Pydantic Field Defaults** (lowest priority)

## Required Environment Variables

The following environment variables MUST be set:

- `MONGODB_URL` - MongoDB connection string (from `.env.secrets`)
- `REDIS_URL` - Redis connection string (from `.env.core` or `.env.secrets`)

## Optional Environment Variables

- `RDP_CONTROLLER_PORT` - Service port (default: 8092)
- `RDP_CONTROLLER_URL` - Service URL for service discovery
- `LOG_LEVEL` - Logging level (default: INFO)
- `RDP_XRDP_URL` - RDP XRDP service URL
- `RDP_SERVER_MANAGER_URL` - RDP Server Manager service URL
- `RDP_MONITOR_URL` - RDP Monitor service URL
- `SESSION_RECORDER_URL` - Session Recorder service URL
- `SESSION_PROCESSOR_URL` - Session Processor service URL
- `SESSION_API_URL` - Session API service URL
- `SESSION_STORAGE_URL` - Session Storage service URL
- `SESSION_PIPELINE_URL` - Session Pipeline service URL
- `SERVICE_TIMEOUT_SECONDS` - Service request timeout (default: 30.0)
- `SERVICE_RETRY_COUNT` - Number of retry attempts (default: 3)
- `SERVICE_RETRY_DELAY_SECONDS` - Delay between retries (default: 1.0)

## Configuration File Location

The configuration file (`config.yaml`) is located at:
- Container path: `/app/session-controller/config.yaml`
- Build path: `RDP/session-controller/config.yaml`

## Usage

Configuration is automatically loaded on service startup via `config.py`. The `RDPControllerConfig` class handles loading and validation.

Example:

```python
from config import load_config

config = load_config()
mongodb_url = config.settings.MONGODB_URL
controller_port = config.settings.RDP_CONTROLLER_PORT
```

