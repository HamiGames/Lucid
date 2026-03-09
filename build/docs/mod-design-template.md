# Lucid Module Design Template

**Version:** 1.0.0  
**Last Updated:** 2025-01-21  
**Purpose:** Template pattern for creating new Lucid service modules and their Docker Compose configurations

This document provides a standardized template pattern derived from analysis of:
- Foundation services (docker-compose.foundation.yml)
- Core services (docker-compose.core.yml)
- Application services (docker-compose.application.yml)
- Session services (session-pipeline, session-recorder, session-processor, session-storage)
- RDP services (rdp-monitor)

---

## 1. Docker Compose Service Template

### Standard Service Structure

```yaml
<service-name>:
  image: pickme/lucid-<service-name>:latest-arm64
  container_name: <service-name>
  restart: unless-stopped
  env_file:
    - /mnt/myssd/Lucid/Lucid/configs/environment/.env.foundation
    - /mnt/myssd/Lucid/Lucid/configs/environment/.env.core
    - /mnt/myssd/Lucid/Lucid/configs/environment/.env.<cluster>
    - /mnt/myssd/Lucid/Lucid/configs/environment/.env.secrets
    - /mnt/myssd/Lucid/Lucid/configs/environment/.env.<service-name>  # Optional service-specific
  networks:
    - lucid-pi-network
    # Optional: Additional network (e.g., lucid-gui-network)
    # - lucid-gui-network
  ports:
    - "${<SERVICE>_PORT:-<default-port>}:${<SERVICE>_PORT:-<default-port>}"
  volumes:
    - /mnt/myssd/Lucid/Lucid/data/<service-name>:/app/data:rw
    - /mnt/myssd/Lucid/Lucid/logs/<service-name>:/app/logs:rw
    - <service-name>-cache:/tmp/<service>
    # Optional: External config file mount
    # - /mnt/myssd/Lucid/Lucid/configs/<service-name>/config.yaml:/app/<service>/config.yaml:ro
  environment:
    - LUCID_ENV=production
    - LUCID_PLATFORM=arm64
    - PROJECT_ROOT=/mnt/myssd/Lucid/Lucid
    - <SERVICE>_HOST=<service-name>
    - <SERVICE>_PORT=${<SERVICE>_PORT:-<default-port>}
    - <SERVICE>_URL=http://<service-name>:<default-port>
    - MONGODB_URL=${MONGODB_URL:?MONGODB_URL not set}
    - REDIS_URL=${REDIS_URL}
    # Optional: Service-specific environment variables
    # - ELASTICSEARCH_URL=${ELASTICSEARCH_URL}
    # - API_GATEWAY_URL=${API_GATEWAY_URL}
    # - BLOCKCHAIN_ENGINE_URL=${BLOCKCHAIN_ENGINE_URL}
  user: "65532:65532"
  security_opt:
    - no-new-privileges:true
    - seccomp:unconfined
  cap_drop:
    - ALL
  cap_add:
    - NET_BIND_SERVICE  # Only if service needs to bind to ports < 1024
  read_only: true
  tmpfs:
    - /tmp:noexec,nosuid,size=100m  # Adjust size as needed (100m, 200m)
  healthcheck:
    test:
      [
        "CMD",
        "/usr/bin/python3.11",
        "-c",
        "import os, urllib.request, sys; port = os.getenv('<SERVICE>_PORT', '<default-port>'); url = 'http://127.0.0.1:' + str(port) + '/health'; urllib.request.urlopen(url, timeout=10).read(); sys.exit(0)",
      ]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 40s
  labels:
    - "lucid.service=<service-name>"
    - "lucid.type=distroless"
    - "lucid.platform=arm64"
    - "lucid.security=hardened"
    - "lucid.cluster=<cluster>"  # foundation, core, application, support
  depends_on:
    tor-proxy:
      condition: service_started
    lucid-mongodb:
      condition: service_healthy
    lucid-redis:
      condition: service_healthy
    # Optional: Additional dependencies
    # lucid-elasticsearch:
    #   condition: service_healthy
    # <other-service>:
    #   condition: service_healthy
```

### Cluster-Specific env_file Patterns

**Foundation Cluster:**
```yaml
env_file:
  - /mnt/myssd/Lucid/Lucid/configs/environment/.env.foundation
  - /mnt/myssd/Lucid/Lucid/configs/environment/.env.distroless
  - /mnt/myssd/Lucid/Lucid/configs/environment/.env.core
  - /mnt/myssd/Lucid/Lucid/configs/environment/.env.secrets
```

**Core Cluster:**
```yaml
env_file:
  - /mnt/myssd/Lucid/Lucid/configs/environment/.env.foundation
  - /mnt/myssd/Lucid/Lucid/configs/environment/.env.core
  - /mnt/myssd/Lucid/Lucid/configs/environment/.env.secrets
```

**Application Cluster:**
```yaml
env_file:
  - /mnt/myssd/Lucid/Lucid/configs/environment/.env.secrets
  - /mnt/myssd/Lucid/Lucid/configs/environment/.env.core
  - /mnt/myssd/Lucid/Lucid/configs/environment/.env.application
  - /mnt/myssd/Lucid/Lucid/configs/environment/.env.foundation
  - /mnt/myssd/Lucid/Lucid/configs/environment/.env.<service-name>  # Optional
```

**Support Cluster:**
```yaml
env_file:
  - /mnt/myssd/Lucid/Lucid/configs/environment/.env.foundation
  - /mnt/myssd/Lucid/Lucid/configs/environment/.env.core
  - /mnt/myssd/Lucid/Lucid/configs/environment/.env.support
  - /mnt/myssd/Lucid/Lucid/configs/environment/.env.secrets
```

### Alternative Healthcheck Patterns

**Simple Python Healthcheck (for services without HTTP health endpoint):**
```yaml
healthcheck:
  test: ["CMD", "python3", "-c", "import sys; sys.exit(0)"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

**Socket-based Healthcheck:**
```yaml
healthcheck:
  test:
    [
      "CMD",
      "/usr/bin/python3.11",
      "-c",
      "import socket; s = socket.socket(); s.settimeout(2); result = s.connect_ex(('127.0.0.1', <port>)); s.close(); exit(0 if result == 0 else 1)",
    ]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

**Custom Healthcheck Script:**
```yaml
healthcheck:
  test:
    [
      "CMD",
      "/usr/bin/python3.11",
      "-c",
      "import sys; sys.argv = ['health-check.py', '<service-name>']; exec(open('/tmp/health-check.py').read())",
    ]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 60s
```

### Volume Template

```yaml
volumes:
  <service-name>-cache:
    driver: local
    name: lucid-<service-name>-cache
    external: false
```

---

## 2. Python Module Structure Template

### Directory Structure

```
<service-name>/
├── __init__.py
├── entrypoint.py          # Container entrypoint
├── main.py                # FastAPI application
├── config.py              # Configuration management (Pydantic Settings)
├── <service-name>_service.py  # Main service logic
├── config/                # Optional: Configuration files
│   ├── config.yaml
│   ├── config.json.example
│   ├── env.<service-name>.template
│   └── README.md
└── [additional modules as needed]
```

### entrypoint.py Template

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
<Service Name> Service Entrypoint
UTF-8 encoded entrypoint script for distroless container

This script serves as the entrypoint for the <service-name> container,
providing clean startup with environment variable configuration.
No hardcoded values - all configuration from environment variables.
"""

import os
import sys

# Ensure site-packages is in Python path (per master-docker-design.md)
site_packages = '/usr/local/lib/python3.11/site-packages'
if site_packages not in sys.path:
    sys.path.insert(0, site_packages)

if __name__ == "__main__":
    # Get configuration from environment variables (from docker-compose)
    port_str = os.getenv('<SERVICE>_PORT', '<default-port>')
    host = '0.0.0.0'  # Always bind to all interfaces in container
    
    try:
        port = int(port_str)
    except ValueError:
        print(f"ERROR: Invalid <SERVICE>_PORT value: {port_str}", file=sys.stderr)
        sys.exit(1)
    
    # Import uvicorn and start the application
    try:
        import uvicorn
    except ImportError as e:
        print(f"ERROR: Failed to import uvicorn: {e}", file=sys.stderr)
        sys.exit(1)
    
    uvicorn.run('<module.path>.main:app', host=host, port=port)
```

### main.py Template Structure

```python
#!/usr/bin/env python3
"""
LUCID <Service Name> Service - Main Entry Point
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .<service>_service import <Service>Service, <Service>Config
from .config import <Service>ConfigManager

# Configure logging (structured logging per master design)
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global service instances
<service>_service: Optional[<Service>Service] = None
config_manager: Optional[<Service>ConfigManager] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global <service>_service, config_manager
    
    # Startup
    logger.info("Starting <Service Name> Service...")
    
    try:
        # Initialize configuration using Pydantic Settings (per master design)
        config_manager = <Service>ConfigManager()
        
        # Get configuration dictionary
        config_dict = config_manager.get_<service>_config_dict()
        
        # Get database URLs from settings (already validated)
        mongo_url = config_manager.settings.MONGODB_URL
        redis_url = config_manager.settings.REDIS_URL
        
        # Initialize service
        <service>_service = <Service>Service(config_dict, mongo_url, redis_url)
        
        logger.info("<Service Name> Service started successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start <Service Name> Service: {e}", exc_info=True)
        raise
    
    finally:
        # Shutdown (graceful shutdown per master design)
        logger.info("Shutting down <Service Name> Service...")
        
        try:
            if <service>_service:
                await <service>_service.close()
        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)

# Create FastAPI application
app = FastAPI(
    title="<Service Name> Service",
    description="<Service description>",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware if needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "<service-name>",
        "timestamp": datetime.utcnow().isoformat()
    }

# Add your routes here
@app.get("/")
async def root():
    """Root endpoint"""
    return {"service": "<service-name>", "status": "running"}

# Additional routes...
```

### config.py Template (Pydantic Settings)

```python
"""
<Service Name> Configuration Management
Uses Pydantic Settings for environment variable validation
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class <Service>Settings(BaseSettings):
    """Base settings for <Service Name> service"""
    
    # Service configuration
    <SERVICE>_HOST: str = Field(default="0.0.0.0", description="Service host")
    <SERVICE>_PORT: int = Field(default=<default-port>, description="Service port")
    <SERVICE>_URL: str = Field(description="Service URL")
    
    # Database configuration
    MONGODB_URL: str = Field(description="MongoDB connection URL")
    REDIS_URL: str = Field(description="Redis connection URL")
    
    # Optional: Additional service dependencies
    # ELASTICSEARCH_URL: Optional[str] = Field(default=None)
    # API_GATEWAY_URL: Optional[str] = Field(default=None)
    
    # Environment
    LUCID_ENV: str = Field(default="production")
    LUCID_PLATFORM: str = Field(default="arm64")
    PROJECT_ROOT: str = Field(default="/mnt/myssd/Lucid/Lucid")
    
    model_config = SettingsConfigDict(
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )

class <Service>ConfigManager:
    """Configuration manager for <Service Name>"""
    
    def __init__(self):
        self.settings = <Service>Settings()
        self._validate_config()
    
    def _validate_config(self):
        """Validate configuration"""
        if not self.settings.MONGODB_URL:
            raise ValueError("MONGODB_URL is required")
        if not self.settings.REDIS_URL:
            raise ValueError("REDIS_URL is required")
    
    def get_<service>_config_dict(self) -> dict:
        """Get service configuration as dictionary"""
        return {
            "host": self.settings.<SERVICE>_HOST,
            "port": self.settings.<SERVICE>_PORT,
            "url": self.settings.<SERVICE>_URL,
            # Add service-specific configuration fields
        }
```

---

## 3. Standard Environment Variables

### Required Environment Variables

```bash
# Service Identity
LUCID_ENV=production
LUCID_PLATFORM=arm64
PROJECT_ROOT=/mnt/myssd/Lucid/Lucid

# Service Configuration
<SERVICE>_HOST=<service-name>
<SERVICE>_PORT=<default-port>
<SERVICE>_URL=http://<service-name>:<default-port>

# Database Connections
MONGODB_URL=mongodb://lucid:${MONGODB_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin
REDIS_URL=redis://:${REDIS_PASSWORD}@lucid-redis:6379/0
```

### Optional Environment Variables

```bash
# Additional Services
ELASTICSEARCH_URL=http://lucid-elasticsearch:9200
API_GATEWAY_URL=http://api-gateway:8080
BLOCKCHAIN_ENGINE_URL=http://blockchain-engine:8084
AUTH_SERVICE_URL=http://lucid-auth-service:8089

# Service-Specific Configuration
# Add as needed for your service
```

---

## 4. Network Configuration Patterns

### Standard Network (Most Services)

```yaml
networks:
  - lucid-pi-network
```

**Note:** Static IP addresses (`ipv4_address`) are being phased out. Use service names for discovery.

### Multi-Network Configuration (GUI Services)

```yaml
networks:
  - lucid-pi-network
  - lucid-gui-network
```

### Network Definition (External)

```yaml
networks:
  lucid-pi-network:
    external: true
    name: lucid-pi-network
```

---

## 5. Security Configuration Standard

All services must include:

```yaml
user: "65532:65532"
security_opt:
  - no-new-privileges:true
  - seccomp:unconfined
cap_drop:
  - ALL
cap_add:
  - NET_BIND_SERVICE  # Only if needed for ports < 1024
read_only: true
tmpfs:
  - /tmp:noexec,nosuid,size=100m  # Adjust size: 100m, 200m
```

---

## 6. Volume Mount Patterns

### Standard Volume Mounts

```yaml
volumes:
  - /mnt/myssd/Lucid/Lucid/data/<service-name>:/app/data:rw
  - /mnt/myssd/Lucid/Lucid/logs/<service-name>:/app/logs:rw
  - <service-name>-cache:/tmp/<service>
```

### Optional: External Configuration Mount

```yaml
volumes:
  # Optional: Mount external config file
  - /mnt/myssd/Lucid/Lucid/configs/<service-name>/config.yaml:/app/<service>/config.yaml:ro
```

And corresponding environment variable:
```yaml
environment:
  - <SERVICE>_CONFIG_FILE=/app/<service>/config.yaml
```

### Read-Only Data Mount

```yaml
volumes:
  - <readonly-data-volume>:/data/<service>:ro
```

---

## 7. Dependency Patterns

### Foundation Dependencies (Most Services)

```yaml
depends_on:
  tor-proxy:
    condition: service_started
  lucid-mongodb:
    condition: service_healthy
  lucid-redis:
    condition: service_healthy
```

### Additional Dependencies

```yaml
depends_on:
  # ... foundation dependencies ...
  lucid-elasticsearch:
    condition: service_healthy
  <other-service>:
    condition: service_healthy
```

---

## 8. Label Standards

All services must include these labels:

```yaml
labels:
  - "lucid.service=<service-name>"
  - "lucid.type=distroless"
  - "lucid.platform=arm64"
  - "lucid.security=hardened"
  - "lucid.cluster=<cluster>"  # foundation, core, application, support
```

---

## 9. Common Service URL Patterns

### Internal Service URLs (Container-to-Container)

```yaml
<SERVICE>_URL=http://<service-name>:<port>
API_GATEWAY_URL=http://api-gateway:8080
AUTH_SERVICE_URL=http://lucid-auth-service:8089
BLOCKCHAIN_ENGINE_URL=http://blockchain-engine:8084
MONGODB_URL=mongodb://lucid:${MONGODB_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin
REDIS_URL=redis://:${REDIS_PASSWORD}@lucid-redis:6379/0
ELASTICSEARCH_URL=http://lucid-elasticsearch:9200
```

**Important:** Always use container names, not IP addresses, for service discovery.

---

## 10. Implementation Checklist

When creating a new service module:

- [ ] Docker Compose service definition following template
- [ ] Service directory structure created
- [ ] `entrypoint.py` implemented
- [ ] `main.py` with FastAPI app and lifespan manager
- [ ] `config.py` with Pydantic Settings
- [ ] Service-specific logic module(s)
- [ ] Environment variable template file (`.env.<service-name>.template`)
- [ ] Health check endpoint (`/health`)
- [ ] Proper logging configuration
- [ ] Error handling and graceful shutdown
- [ ] Volume mounts configured correctly
- [ ] Network configuration (no static IPs)
- [ ] Security configuration (user, caps, read-only, tmpfs)
- [ ] Dependencies correctly specified
- [ ] Labels properly set
- [ ] Documentation/README for the service

---

## 11. Quick Reference: Service Examples

### Foundation Service Example (mongodb, redis, elasticsearch)

**Characteristics:**
- Uses `.env.foundation`, `.env.distroless`, `.env.core`, `.env.secrets`
- Cluster: `foundation`
- May have static IP (legacy) or service name only
- Often requires `cap_add: ["NET_BIND_SERVICE"]`

### Core Service Example (blockchain-engine, api-gateway)

**Characteristics:**
- Uses `.env.foundation`, `.env.core`, `.env.secrets`
- Cluster: `core`
- No static IPs (use service names)
- Standard healthcheck patterns

### Application Service Example (session-*, rdp-*)

**Characteristics:**
- Uses `.env.secrets`, `.env.core`, `.env.application`, `.env.foundation`, `.env.<service-name>`
- Cluster: `application` or `support`
- No static IPs
- May have service-specific environment files
- Standard volume patterns

---

## 12. Anti-Patterns to Avoid

**❌ DON'T:**
- Use static IP addresses (`ipv4_address`) - use service names instead
- Hardcode values in code - use environment variables
- Use shell scripts in distroless containers
- Skip health checks
- Use `privileged: true`
- Omit security configurations (user, caps, read_only, tmpfs)
- Create empty marker files - use contentful files per Dockerfile-copy-pattern.md
- Use different logging formats across services
- Mix cluster-specific env_file patterns incorrectly

**✅ DO:**
- Use service names for service discovery
- Read all configuration from environment variables
- Use Python-based entrypoints for distroless containers
- Implement proper health checks
- Follow security best practices
- Use consistent volume mount patterns
- Use standardized logging
- Follow cluster-specific env_file patterns

---

## 13. Related Documentation

- `build/docs/dockerfile-design.md` - Dockerfile patterns
- `plan/constants/Dockerfile-copy-pattern.md` - COPY command patterns
- `docs/architecture/DISTROLESS-CONTAINER-SPEC.md` - Distroless container requirements
- `build/docs/master-docker-design.md` - Master design principles

---

## Document History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0.0 | 2025-01-21 | Initial template creation based on existing services | System |

---

**Last Updated:** 2025-01-21  
**Status:** ACTIVE  
**Maintained By:** Lucid Development Team

