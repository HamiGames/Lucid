# Service Mesh Configuration Directory

This directory contains configuration files for the Lucid Service Mesh Controller.

## File Structure

```
config/
├── service-mesh.yaml          # Main service mesh configuration (REQUIRED - mounted at runtime)
├── services/                  # Service-specific configurations (OPTIONAL)
│   └── *.yaml                # Individual service config files
└── policies/                  # Policy configurations (OPTIONAL)
    └── *.yaml                # Individual policy config files
```

## Configuration Files

### Main Configuration

**File:** `service-mesh.yaml`
- **Status:** ✅ Created
- **Location:** `infrastructure/service-mesh/config/service-mesh.yaml`
- **Mount Path:** `/config/service-mesh.yaml` (via docker-compose volume)
- **Purpose:** Main service mesh configuration including:
  - Service mesh settings (controller, discovery, sidecar, security, networking)
  - Services registry (all foundation and core services)
  - Policies configuration
  - Network topology
  - Service planes
  - Integration settings

### Optional Service Configurations

**Directory:** `services/`
- **Status:** Optional (directory created, no files required)
- **Mount Path:** `/config/services/` (via docker-compose volume)
- **Purpose:** Service-specific configurations that override or extend the main config
- **Format:** One YAML file per service (e.g., `lucid-auth-service.yaml`)

**Example Service Config:**
```yaml
# services/lucid-auth-service.yaml
name: "lucid-auth-service"
port: 8089
health_check: "/health"
health_check_interval: 30
tags: ["auth", "foundation"]
sidecar_enabled: true
circuit_breaker:
  failure_threshold: 5
  recovery_timeout: 30
```

### Optional Policy Configurations

**Directory:** `policies/`
- **Status:** Optional (directory created, no files required)
- **Mount Path:** `/config/policies/` (via docker-compose volume)
- **Purpose:** Policy configurations for traffic management, security, and governance
- **Format:** One YAML file per policy (e.g., `rate-limiting-policy.yaml`)

**Example Policy Config:**
```yaml
# policies/custom-rate-limiting.yaml
name: "custom-rate-limiting-policy"
description: "Custom rate limiting for specific services"
enabled: true
rules:
  - type: "rate_limiting"
    config:
      requests_per_second: 50
      burst_size: 100
      apply_to: ["lucid-api-gateway"]
```

## Docker Compose Mount

The configuration directory is mounted into the container at runtime via docker-compose:

```yaml
volumes:
  - /mnt/myssd/Lucid/Lucid/infrastructure/service-mesh/config:/config:ro
```

**Note:** The config files are **NOT** copied into the Docker image. They are mounted at runtime, allowing for:
- Dynamic configuration updates without rebuilding the image
- Environment-specific configurations
- Easy configuration management

## Configuration Loading

The `config_manager.py` loads configurations in this order:

1. **Main Config:** `/config/service-mesh.yaml` (if exists, else uses defaults)
2. **Service Configs:** `/config/services/*.yaml` (if directory exists)
3. **Policy Configs:** `/config/policies/*.yaml` (if directory exists)

If `service-mesh.yaml` is not found, the controller uses built-in default configuration.

## Envoy Configuration Files

**Note:** Envoy configuration files (`bootstrap.yaml`, `cluster.yaml`, `listener.yaml`) are:
- Located in source code: `infrastructure/service-mesh/sidecar/envoy/config/`
- Copied into the Docker image at: `/app/sidecar/envoy/config/`
- Used as templates/references by the proxy manager
- The proxy manager creates runtime configs at `/etc/envoy/` when needed

These files are **NOT** in this config directory - they're part of the application source code.

