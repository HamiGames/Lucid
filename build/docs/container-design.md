# Container Design Reference - Universal Standards and Validation Template

**Version:** 1.0.0  
**Last Updated:** 2025-01-27  
**Purpose:** Comprehensive reference template for all Lucid container configurations, validation rules, and error detection patterns

This document consolidates **all common design factors** from existing container design documents and provides a validation template for checking container configurations against Lucid standards.

---

## Table of Contents

1. [Edit Rules and Constraints](#1-edit-rules-and-constraints)
2. [Architectural Requirements](#2-architectural-requirements)
3. [Dockerfile Structure Requirements](#3-dockerfile-structure-requirements)
4. [Support Files Structure](#4-support-files-structure)
5. [Cross-Container Linking Modules](#5-cross-container-linking-modules)
6. [Configuration File Standards](#6-configuration-file-standards)
7. [Container Name Registry](#7-container-name-registry)
8. [Sensitive Data Detection Patterns](#8-sensitive-data-detection-patterns)
9. [Validation Checklist](#9-validation-checklist)
10. [Error Detection and Fix Template](#10-error-detection-and-fix-template)

---

## 1. Edit Rules and Constraints

### 1.1 Immutable Rules

**CRITICAL: These rules MUST NEVER be violated:**

1. **Container Name Immutability**
   - ❌ **NEVER** change `container_name` values in docker-compose files
   - ❌ **NEVER** rename containers without updating all references
   - ✅ Container names are service identifiers and must remain consistent
   - ✅ Use `container_name` field to explicitly set names

2. **No Placeholders**
   - ❌ **NEVER** leave placeholder values like `<service-name>`, `<port>`, `<SERVICE>_PORT`
   - ❌ **NEVER** use `TODO`, `FIXME`, `XXX` in production configurations
   - ✅ All values must be concrete and valid
   - ✅ Use environment variables with defaults instead of placeholders

3. **No Sensitive Data Exposure**
   - ❌ **NEVER** hardcode passwords, API keys, or secrets
   - ❌ **NEVER** commit `.env.secrets` files to version control
   - ❌ **NEVER** expose credentials in docker-compose files
   - ❌ **NEVER** log sensitive data (passwords, tokens, keys)
   - ✅ All secrets must come from environment variables
   - ✅ Use `${VARIABLE:?error message}` syntax for required secrets
   - ✅ Secrets must be in `.env.secrets` file only

### 1.2 Configuration Validation Rules

**All configurations must:**
- Use environment variables for all dynamic values
- Validate required environment variables on startup
- Fail fast with clear error messages for missing required config
- Never expose sensitive data in error messages
- Use Pydantic Settings for validation

---

## 2. Architectural Requirements

### 2.1 Universal Architecture Pattern

**All containers MUST follow:**

```
┌─────────────────────────────────────────────────────────────┐
│                    Multi-Stage Build Pattern                │
│                                                             │
│  Stage 1: Builder (python:3.11-slim-bookworm)              │
│  ├── Install build dependencies                            │
│  ├── Install Python packages                              │
│  ├── Create marker files                                  │
│  └── Copy application source                              │
│                                                             │
│  Stage 2: Runtime (gcr.io/distroless/python3-debian12)   │
│  ├── Copy packages from builder                           │
│  ├── Copy application code                                │
│  ├── Set non-root user (65532:65532)                     │
│  └── Configure entrypoint                                 │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Base Image Requirements

**Builder Stage:**
- Base: `python:3.11-slim-bookworm`
- Platform: `linux/arm64` (Raspberry Pi compatible)
- Build tools: `build-essential`, `gcc`, `g++`, `libffi-dev`, `libssl-dev`

**Runtime Stage:**
- Base: `gcr.io/distroless/python3-debian12:latest`
- No shell, package manager, or unnecessary binaries
- Minimal attack surface

### 2.3 User and Security Requirements

**All containers MUST:**
- Run as non-root user: `USER 65532:65532`
- Use `read_only: true` filesystem
- Drop all capabilities: `cap_drop: ALL`
- Add only necessary capabilities: `cap_add: [NET_BIND_SERVICE]` (if needed)
- Use `security_opt: [no-new-privileges:true]`
- Mount writable tmpfs: `/tmp:noexec,nosuid,size=100m`

---

## 3. Dockerfile Structure Requirements

### 3.1 Required Build Arguments

```dockerfile
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0
ARG TARGETPLATFORM=linux/arm64
ARG BUILDPLATFORM=linux/amd64
ARG PYTHON_VERSION=3.11
```

### 3.2 Builder Stage Requirements

**Required Steps:**

1. **System Dependencies Installation**
   ```dockerfile
   RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
       --mount=type=cache,target=/var/lib/apt,sharing=locked \
       rm -rf /var/lib/apt/lists/* && \
       apt-get update --allow-releaseinfo-change && \
       apt-get install -y --no-install-recommends \
           build-essential gcc g++ libffi-dev libssl-dev \
           pkg-config curl ca-certificates \
       && apt-get clean \
       && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
   ```

2. **System Directory Markers**
   ```dockerfile
   RUN echo "LUCID_<SERVICE>_RUNTIME_DIRECTORY" > /var/run/.keep && \
       echo "LUCID_<SERVICE>_LIB_DIRECTORY" > /var/lib/.keep && \
       chown -R 65532:65532 /var/run /var/lib
   ```

3. **Python Package Installation**
   ```dockerfile
   RUN --mount=type=cache,target=/root/.cache/pip \
       pip install --upgrade pip setuptools wheel
   
   COPY <service>/requirements.txt ./requirements.txt
   
   RUN mkdir -p /root/.local/lib/python3.11/site-packages && \
       mkdir -p /root/.local/bin
   
   RUN --mount=type=cache,target=/root/.cache/pip \
       pip install --user --no-cache-dir --prefer-binary -r requirements.txt
   ```

4. **Marker Files Creation**
   ```dockerfile
   RUN echo "LUCID_<SERVICE>_PACKAGES_INSTALLED_$(date +%s)" > \
       /root/.local/lib/python3.11/site-packages/.lucid-marker && \
       echo "LUCID_<SERVICE>_BINARIES_INSTALLED_$(date +%s)" > \
       /root/.local/bin/.lucid-marker && \
       chown -R 65532:65532 /root/.local
   ```

5. **Builder Verification**
   ```dockerfile
   RUN python3 -c "import fastapi, uvicorn, pydantic; \
       print('✅ critical packages installed')" && \
       test -f /root/.local/lib/python3.11/site-packages/.lucid-marker && \
       test -s /root/.local/lib/python3.11/site-packages/.lucid-marker && \
       echo "✅ Marker file verified in builder (non-empty)"
   ```

### 3.3 Runtime Stage Requirements

**Required Steps:**

1. **Base Image and Labels**
   ```dockerfile
   FROM --platform=$TARGETPLATFORM gcr.io/distroless/python3-debian12:latest
   
   LABEL maintainer="Lucid Development Team" \
         org.opencontainers.image.title="Lucid <Service>" \
         org.opencontainers.image.version="${VERSION}" \
         com.lucid.service="<service-id>" \
         com.lucid.platform="arm64" \
         com.lucid.security="distroless"
   ```

2. **Environment Variables**
   ```dockerfile
   ENV PATH=/usr/local/bin:/usr/bin:/bin \
       PYTHONUNBUFFERED=1 \
       PYTHONDONTWRITEBYTECODE=1 \
       PYTHONPATH=/app:/usr/local/lib/python3.11/site-packages \
       PYTHONIOENCODING=utf-8 \
       LANG=C.UTF-8 \
       LC_ALL=C.UTF-8 \
       <SERVICE>_PORT=<port> \
       <SERVICE>_HOST=0.0.0.0
   ```

3. **System Directories and Certificates**
   ```dockerfile
   COPY --from=builder --chown=65532:65532 /var/run /var/run
   COPY --from=builder --chown=65532:65532 /var/lib /var/lib
   COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
   ```

4. **Python Packages Copy**
   ```dockerfile
   COPY --from=builder --chown=65532:65532 \
       /root/.local/lib/python3.11/site-packages \
       /usr/local/lib/python3.11/site-packages
   COPY --from=builder --chown=65532:65532 \
       /root/.local/bin /usr/local/bin
   ```

5. **Runtime Verification**
   ```dockerfile
   RUN ["/usr/bin/python3.11", "-c", "import sys; import os; \
       site_packages = '/usr/local/lib/python3.11/site-packages'; \
       sys.path.insert(0, site_packages); \
       assert os.path.exists(site_packages), site_packages + ' does not exist'; \
       assert os.path.exists(os.path.join(site_packages, 'uvicorn')), 'uvicorn not found'; \
       assert os.path.exists(os.path.join(site_packages, 'fastapi')), 'fastapi not found'; \
       marker_path = os.path.join(site_packages, '.lucid-marker'); \
       assert os.path.exists(marker_path), 'marker file not found'; \
       assert os.path.getsize(marker_path) > 0, 'marker file is empty'; \
       import uvicorn; import fastapi; \
       print('✅ All packages verified in runtime stage')"]
   ```

6. **Application Code Copy**
   ```dockerfile
   COPY --chown=65532:65532 --from=builder /build/<service> /app/<service>
   ```

7. **Health Check**
   ```dockerfile
   HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
       CMD ["/usr/bin/python3.11", "-c", \
       "import socket; s = socket.socket(); s.settimeout(2); \
       result = s.connect_ex(('127.0.0.1', <port>)); \
       s.close(); exit(0 if result == 0 else 1)"]
   ```

8. **User and Entrypoint**
   ```dockerfile
   USER 65532:65532
   ENTRYPOINT []
   CMD ["/usr/bin/python3.11", "/app/<service>/entrypoint.py"]
   ```

---

## 4. Support Files Structure

### 4.1 Required Support Files

**Every container MUST have:**

```
<service-name>/
├── Dockerfile.<service-name>          # Multi-stage Dockerfile
├── requirements.txt                   # Python dependencies
├── <service-name>/
│   ├── __init__.py                   # Package initialization
│   ├── main.py                       # FastAPI application
│   ├── entrypoint.py                 # Container entrypoint
│   ├── config.py                     # Configuration management
│   └── config/
│       └── env.<service-name>.template  # Environment template
└── [service-specific modules]
```

### 4.2 Entrypoint Pattern

**Required entrypoint.py structure:**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
<Service Name> Service Entrypoint
UTF-8 encoded entrypoint script for distroless container
"""

import os
import sys

# Ensure site-packages is in Python path
site_packages = '/usr/local/lib/python3.11/site-packages'
if site_packages not in sys.path:
    sys.path.insert(0, site_packages)

if __name__ == "__main__":
    port_str = os.getenv('<SERVICE>_PORT', '<default-port>')
    host = '0.0.0.0'  # Always bind to all interfaces
    
    try:
        port = int(port_str)
    except ValueError:
        print(f"ERROR: Invalid <SERVICE>_PORT value: {port_str}", file=sys.stderr)
        sys.exit(1)
    
    try:
        import uvicorn
        from <service>.main import app
    except ImportError as e:
        print(f"ERROR: Failed to import: {e}", file=sys.stderr)
        sys.exit(1)
    
    uvicorn.run(app, host=host, port=port)
```

### 4.3 Configuration Management Pattern

**Required config.py structure:**

```python
"""
<Service Name> Configuration Management
Uses Pydantic Settings for environment variable validation
"""

import os
import re
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Regex patterns for URL validation (compiled at module level)
LOCALHOST_PATTERN = re.compile(r'\blocalhost\b', re.IGNORECASE)
IP_127_PATTERN = re.compile(r'\b127\.0\.0\.1\b')

class <Service>Settings(BaseSettings):
    """Base settings for <Service Name> service"""
    
    # Service Configuration
    <SERVICE>_HOST: str = Field(default="0.0.0.0")
    <SERVICE>_PORT: int = Field(default=<port>)
    <SERVICE>_URL: str = Field(default="")
    
    # Database Configuration (Required)
    MONGODB_URL: str = Field(default="")
    REDIS_URL: str = Field(default="")
    
    model_config = SettingsConfigDict(
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )
    
    @field_validator('MONGODB_URL')
    @classmethod
    def validate_mongodb_url(cls, v: str) -> str:
        """Validate MongoDB URL doesn't use localhost"""
        if v and (LOCALHOST_PATTERN.search(v) or IP_127_PATTERN.search(v)):
            raise ValueError("MONGODB_URL must not use localhost. Use service name (e.g., lucid-mongodb)")
        return v
    
    @field_validator('REDIS_URL')
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        """Validate Redis URL doesn't use localhost"""
        if v and (LOCALHOST_PATTERN.search(v) or IP_127_PATTERN.search(v)):
            raise ValueError("REDIS_URL must not use localhost. Use service name (e.g., lucid-redis)")
        return v
```

---

## 5. Cross-Container Linking Modules

### 5.1 Integration Module Structure

**Standard integration module pattern:**

```
<service-name>/
└── integration/
    ├── __init__.py
    ├── integration_manager.py      # Centralized integration management
    ├── service_base.py              # Base client class
    └── <service>_client.py         # Specific service clients
```

### 5.2 Service Base Client Pattern

**Required service_base.py structure:**

```python
"""
Base Service Client for Integration Modules
Provides common functionality for service communication
"""

import asyncio
import re
import logging
import os
from typing import Dict, Any, Optional
from abc import ABC
import httpx

logger = logging.getLogger(__name__)

# Regex patterns for URL validation (compiled at module level)
LOCALHOST_PATTERN = re.compile(r'\blocalhost\b', re.IGNORECASE)
IP_127_PATTERN = re.compile(r'\b127\.0\.0\.1\b')

class ServiceError(Exception):
    """Base exception for service communication errors"""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code

class ServiceClientBase(ABC):
    """Base class for service integration clients"""
    
    def __init__(
        self,
        base_url: str,
        timeout: Optional[float] = None,
        retry_count: Optional[int] = None,
        retry_delay: Optional[float] = None,
        api_key: Optional[str] = None
    ):
        if not base_url:
            raise ValueError("Service base_url is required")
        
        # Validate URL doesn't use localhost
        if LOCALHOST_PATTERN.search(base_url) or IP_127_PATTERN.search(base_url):
            raise ValueError(f"Service URL must not use localhost: {base_url}. Use service name instead.")
        
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout or float(os.getenv('SERVICE_TIMEOUT_SECONDS', '30'))
        self.retry_count = retry_count or int(os.getenv('SERVICE_RETRY_COUNT', '3'))
        self.retry_delay = retry_delay or float(os.getenv('SERVICE_RETRY_DELAY_SECONDS', '1.0'))
        self.api_key = api_key or os.getenv('JWT_SECRET_KEY', '')
        
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout, connect=5.0),
            follow_redirects=True
        )
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Make HTTP request with retry logic and exponential backoff"""
        # Implementation with retry logic
        pass
    
    async def health_check(self) -> Dict[str, Any]:
        """Check service health"""
        try:
            return await self._make_request('GET', '/health')
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {"status": "unhealthy", "error": str(e)}
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
```

### 5.3 Integration Manager Pattern

**Required integration_manager.py structure:**

```python
"""
Integration Manager for <Service Name>
Centralized management of service integration clients
"""

import os
import logging
from typing import Optional, Dict, Any
from .service_base import ServiceClientBase

logger = logging.getLogger(__name__)

class IntegrationManager:
    """Centralized manager for all integration clients"""
    
    def __init__(
        self,
        service_timeout: float = 30.0,
        service_retry_count: int = 3,
        service_retry_delay: float = 1.0
    ):
        self.service_timeout = service_timeout
        self.service_retry_count = service_retry_count
        self.service_retry_delay = service_retry_delay
        
        # Lazy-initialized clients
        self._client1 = None
        self._client2 = None
    
    @property
    def client1(self) -> Optional[ServiceClientBase]:
        """Get client1 (lazy initialization)"""
        if self._client1 is None:
            url = os.getenv('CLIENT1_URL', '')
            if url:
                try:
                    self._client1 = Client1Client(
                        base_url=url,
                        timeout=self.service_timeout,
                        retry_count=self.service_retry_count,
                        retry_delay=self.service_retry_delay
                    )
                    logger.info("Initialized Client1Client")
                except Exception as e:
                    logger.warning(f"Failed to initialize Client1Client: {str(e)}")
            else:
                logger.warning("CLIENT1_URL not set, client1 unavailable")
        return self._client1
    
    async def health_check_all(self) -> Dict[str, Any]:
        """Check health of all integration clients"""
        results = {}
        if self.client1:
            try:
                results['client1'] = await self.client1.health_check()
            except Exception as e:
                results['client1'] = {"status": "error", "error": str(e)}
        return results
    
    async def close_all(self):
        """Close all integration clients"""
        if self._client1:
            try:
                await self._client1.close()
            except Exception as e:
                logger.warning(f"Error closing client1: {e}")
```

### 5.4 Cross-Container Communication Rules

**Service Discovery:**
- ✅ Use container names (e.g., `lucid-mongodb`, `lucid-redis`)
- ✅ Use service URLs: `http://<service-name>:<port>`
- ❌ Never use `localhost` or `127.0.0.1`
- ❌ Never use IP addresses

**URL Validation:**
- All service URLs must be validated against localhost patterns
- Validation must happen at module level (compiled regex)
- Validation must happen in both config.py and service_base.py

---

## 6. Configuration File Standards

### 6.1 YAML Configuration Files

**Supported YAML Structure:**

```yaml
# <Service Name> - Configuration File
# Optional YAML configuration
# Environment variables override these values

# Service Configuration
<SERVICE>_HOST: "0.0.0.0"
<SERVICE>_PORT: <port>
<SERVICE>_URL: ""  # Must be set via environment variable

# Database URLs (MUST come from .env.secrets)
MONGODB_URL: ""
REDIS_URL: ""

# Integration Service URLs
<INTEGRATION>_URL: "http://<integration-service>:<port>"

# Service Timeout Configuration
SERVICE_TIMEOUT_SECONDS: 30.0
SERVICE_RETRY_COUNT: 3
SERVICE_RETRY_DELAY_SECONDS: 1.0

# Storage Paths
LUCID_STORAGE_PATH: "/app/data"
LUCID_LOGS_PATH: "/app/logs"

# Environment
LUCID_ENV: "production"
LUCID_PLATFORM: "arm64"
PROJECT_ROOT: "/mnt/myssd/Lucid/Lucid"
```

**YAML File Rules:**
- ✅ Empty strings for secrets (must come from environment)
- ✅ Sensible defaults for optional values
- ✅ Comments explaining requirements
- ❌ No hardcoded passwords or secrets
- ❌ No placeholder values

### 6.2 JSON Configuration Files

**Supported JSON Structure:**

```json
{
  "service": {
    "name": "<service-name>",
    "version": "1.0.0",
    "host": "0.0.0.0",
    "port": <port>
  },
  "database": {
    "mongodb_url": "",
    "redis_url": ""
  },
  "integration": {
    "<service>_url": "http://<service-name>:<port>"
  },
  "storage": {
    "data_path": "/app/data",
    "logs_path": "/app/logs"
  }
}
```

**JSON File Rules:**
- ✅ Empty strings for secrets
- ✅ Use environment variable names as keys
- ❌ No hardcoded credentials
- ❌ No placeholder values

### 6.3 Environment Variable Templates

**Required template structure:**

```bash
# <Service Name> Environment Variables Template
# Copy this file to .env.<service-name> and fill in actual values
# DO NOT commit .env.<service-name> to version control

# Service Configuration
<SERVICE>_HOST=<service-name>
<SERVICE>_PORT=<port>
<SERVICE>_URL=http://<service-name>:<port>
LOG_LEVEL=INFO

# Database URLs (from .env.secrets)
MONGODB_URL=mongodb://lucid:${MONGODB_PASSWORD}@lucid-mongodb:27017/lucid?authSource=admin
REDIS_URL=redis://:${REDIS_PASSWORD}@lucid-redis:6379/0

# Integration Service URLs
<INTEGRATION>_URL=http://<integration-service>:<port>

# Service Timeout Configuration
SERVICE_TIMEOUT_SECONDS=30.0
SERVICE_RETRY_COUNT=3
SERVICE_RETRY_DELAY_SECONDS=1.0

# Storage Paths (from volume mounts)
LUCID_STORAGE_PATH=/app/data
LUCID_LOGS_PATH=/app/logs

# Environment
LUCID_ENV=production
LUCID_PLATFORM=arm64
PROJECT_ROOT=/mnt/myssd/Lucid/Lucid
```

**Template Rules:**
- ✅ Use `${VARIABLE}` syntax for secrets
- ✅ Include all required variables
- ✅ Document variable purpose
- ❌ No actual secret values
- ❌ No placeholder text

---

## 7. Container Name Registry

### 7.1 Standard Container Names

**Foundation Cluster:**
- `tor-proxy`
- `lucid-mongodb`
- `lucid-redis`
- `lucid-elasticsearch`

**Core Cluster:**
- `api-gateway`
- `blockchain-engine`
- `lucid-auth-service`
- `service-mesh`

**Application Cluster:**
- `session-api`
- `session-processor`
- `session-recorder`
- `session-pipeline`
- `session-storage`
- `rdp-controller`
- `rdp-server-manager`
- `node-management`

**Support Cluster:**
- `rdp-monitor`
- `[additional support services]`

### 7.2 Container Name Rules

**Naming Convention:**
- Use lowercase with hyphens: `service-name`
- Use descriptive names: `session-api`, not `sa`
- Prefix Lucid services: `lucid-<service>`
- Be consistent across all files

**Immutable Rules:**
- ❌ **NEVER** change container names without updating all references
- ❌ **NEVER** use different names in docker-compose vs code
- ✅ Container names must match service names in code
- ✅ Use `container_name` field explicitly

---

## 8. Sensitive Data Detection Patterns

### 8.1 Password Detection Patterns

**Patterns to detect:**

```regex
# Common password patterns
password\s*=\s*['"][^'"]+['"]
password\s*:\s*['"][^'"]+['"]
PASSWORD\s*=\s*['"][^'"]+['"]
PASSWORD\s*:\s*['"][^'"]+['"]

# MongoDB connection strings with passwords
mongodb://[^:]+:[^@]+@
mongodb\+srv://[^:]+:[^@]+@

# Redis connection strings with passwords
redis://:[^@]+@
rediss://:[^@]+@

# API keys
api[_-]?key\s*=\s*['"][^'"]+['"]
API[_-]?KEY\s*=\s*['"][^'"]+['"]
secret[_-]?key\s*=\s*['"][^'"]+['"]
SECRET[_-]?KEY\s*=\s*['"][^'"]+['"]
```

### 8.2 Hardcoded Credentials Detection

**Patterns to detect:**

```regex
# Hardcoded passwords in code
password\s*=\s*['"](?!\$\{)[^'"]+['"]
PASSWORD\s*=\s*['"](?!\$\{)[^'"]+['"]

# Hardcoded tokens
token\s*=\s*['"][^'"]+['"]
TOKEN\s*=\s*['"][^'"]+['"]
bearer\s+[a-zA-Z0-9_-]{20,}

# Hardcoded API keys
api[_-]?key\s*=\s*['"][a-zA-Z0-9_-]{20,}['"]
```

### 8.3 Environment Variable Exposure Detection

**Patterns to detect:**

```regex
# Exposed in docker-compose
MONGODB_PASSWORD\s*=\s*[^$]
REDIS_PASSWORD\s*=\s*[^$]
.*PASSWORD\s*=\s*[^$]

# Exposed in code
os\.getenv\(['"]PASSWORD['"]\s*,\s*['"][^'"]+['"]
os\.environ\[['"]PASSWORD['"]\s*\]\s*=\s*['"][^'"]+['"]
```

### 8.4 Validation Checklist for Sensitive Data

**Check all files for:**
- [ ] Hardcoded passwords
- [ ] Hardcoded API keys
- [ ] Hardcoded tokens
- [ ] Exposed credentials in docker-compose
- [ ] Secrets in YAML/JSON config files
- [ ] Secrets in code comments
- [ ] Secrets in log messages
- [ ] Secrets in error messages

---

## 9. Validation Checklist

### 9.1 Dockerfile Validation

**Builder Stage:**
- [ ] Uses `python:3.11-slim-bookworm` base
- [ ] Installs build dependencies correctly
- [ ] Creates system directory markers with content
- [ ] Installs Python packages to `/root/.local`
- [ ] Creates marker files with content (not empty)
- [ ] Verifies packages in builder stage
- [ ] Sets ownership to `65532:65532`

**Runtime Stage:**
- [ ] Uses `gcr.io/distroless/python3-debian12:latest` base
- [ ] Copies system directories with correct ownership
- [ ] Copies CA certificates
- [ ] Copies Python packages to `/usr/local/lib/python3.11/site-packages`
- [ ] Verifies packages in runtime stage
- [ ] Verifies marker files exist and are non-empty
- [ ] Copies application code with correct ownership
- [ ] Sets `USER 65532:65532`
- [ ] Clears `ENTRYPOINT []`
- [ ] Uses explicit Python path in CMD
- [ ] Uses socket-based health check

### 9.2 Docker Compose Validation

**Service Definition:**
- [ ] Uses correct image name pattern: `pickme/lucid-<service>:latest-arm64`
- [ ] Sets `container_name` explicitly
- [ ] Uses correct `restart` policy: `unless-stopped`
- [ ] Includes all required `env_file` entries
- [ ] Uses correct network: `lucid-pi-network`
- [ ] Exposes correct ports
- [ ] Mounts required volumes
- [ ] Sets `user: "65532:65532"`
- [ ] Configures security options correctly
- [ ] Sets `read_only: true`
- [ ] Configures tmpfs correctly
- [ ] Includes health check
- [ ] Sets correct labels
- [ ] Defines dependencies correctly

**Environment Variables:**
- [ ] No hardcoded secrets
- [ ] Uses `${VARIABLE:?error}` for required secrets
- [ ] All service URLs use container names (not localhost)
- [ ] All ports use environment variables
- [ ] No placeholder values

### 9.3 Code Validation

**Entrypoint:**
- [ ] Sets up Python path correctly
- [ ] Reads port from environment variable
- [ ] Binds to `0.0.0.0` (not hostname)
- [ ] Handles errors gracefully
- [ ] Uses UTF-8 encoding

**Configuration:**
- [ ] Uses Pydantic Settings
- [ ] Validates required environment variables
- [ ] Validates URLs don't use localhost
- [ ] Provides clear error messages
- [ ] No hardcoded values

**Integration:**
- [ ] Uses service names (not localhost/IP)
- [ ] Validates URLs at module level
- [ ] Implements retry logic
- [ ] Handles errors gracefully
- [ ] Uses lazy initialization

---

## 10. Error Detection and Fix Template

### 10.1 Container Name Errors

**Error Pattern:**
```yaml
# Wrong: container_name changed or missing
service-name:
  image: pickme/lucid-service-name:latest-arm64
  # Missing container_name

# Wrong: container_name doesn't match service name
service-name:
  container_name: different-name
```

**Fix:**
```yaml
# Correct: explicit container_name matching service
service-name:
  image: pickme/lucid-service-name:latest-arm64
  container_name: service-name
```

### 10.2 Placeholder Errors

**Error Pattern:**
```yaml
# Wrong: placeholder values
environment:
  - SERVICE_PORT=<port>
  - SERVICE_URL=http://<service-name>:<port>

# Wrong: TODO comments
environment:
  - SERVICE_PORT=8080  # TODO: change port
```

**Fix:**
```yaml
# Correct: concrete values or environment variables
environment:
  - SERVICE_PORT=${SERVICE_PORT:-8080}
  - SERVICE_URL=http://service-name:${SERVICE_PORT:-8080}
```

### 10.3 Sensitive Data Exposure Errors

**Error Pattern:**
```yaml
# Wrong: hardcoded password
environment:
  - MONGODB_PASSWORD=secret123

# Wrong: password in docker-compose
environment:
  - MONGODB_URL=mongodb://user:password@host:27017/db
```

**Fix:**
```yaml
# Correct: use environment variable reference
environment:
  - MONGODB_URL=mongodb://lucid:${MONGODB_PASSWORD:?MONGODB_PASSWORD not set}@lucid-mongodb:27017/lucid?authSource=admin

# And ensure MONGODB_PASSWORD is in .env.secrets only
```

### 10.4 Localhost URL Errors

**Error Pattern:**
```python
# Wrong: localhost in URLs
MONGODB_URL = "mongodb://localhost:27017/db"
REDIS_URL = "redis://localhost:6379/0"
base_url = "http://localhost:8080"
```

**Fix:**
```python
# Correct: use service names
MONGODB_URL = "mongodb://lucid-mongodb:27017/lucid"
REDIS_URL = "redis://lucid-redis:6379/0"
base_url = "http://service-name:8080"
```

### 10.5 Missing Validation Errors

**Error Pattern:**
```python
# Wrong: no URL validation
class Settings(BaseSettings):
    MONGODB_URL: str = ""
```

**Fix:**
```python
# Correct: validate URLs
LOCALHOST_PATTERN = re.compile(r'\blocalhost\b', re.IGNORECASE)
IP_127_PATTERN = re.compile(r'\b127\.0\.0\.1\b')

class Settings(BaseSettings):
    MONGODB_URL: str = ""
    
    @field_validator('MONGODB_URL')
    @classmethod
    def validate_mongodb_url(cls, v: str) -> str:
        if v and (LOCALHOST_PATTERN.search(v) or IP_127_PATTERN.search(v)):
            raise ValueError("MONGODB_URL must not use localhost. Use service name (e.g., lucid-mongodb)")
        return v
```

### 10.6 Quick Fix Reference

**When checking a container configuration, verify:**

1. **Container Name:**
   ```bash
   grep -r "container_name" docker-compose.*.yml | grep -v "^#"
   # Should show: container_name: <service-name>
   ```

2. **Placeholders:**
   ```bash
   grep -r "<.*>" docker-compose.*.yml Dockerfile.* | grep -v "^#"
   # Should return nothing
   ```

3. **Sensitive Data:**
   ```bash
   grep -ri "password\|secret\|key\|token" docker-compose.*.yml | grep -v "PASSWORD\|SECRET\|KEY\|TOKEN" | grep -v "^#"
   # Should return nothing (except variable names)
   ```

4. **Localhost URLs:**
   ```bash
   grep -ri "localhost\|127\.0\.0\.1" docker-compose.*.yml *.py | grep -v "^#"
   # Should return nothing (except comments or validation code)
   ```

---

## 11. Container-Specific Configuration Standards

### 11.1 JSON Configuration Per Container

**session-api:**
```json
{
  "service": {
    "name": "session-api",
    "port": 8113
  },
  "database": {
    "mongodb_url": "",
    "redis_url": ""
  },
  "integration": {
    "session_storage_url": "http://session-storage:8092",
    "session_processor_url": "http://session-processor:8091",
    "session_pipeline_url": "http://session-pipeline:8083"
  }
}
```

**session-processor:**
```json
{
  "service": {
    "name": "session-processor",
    "port": 8091
  },
  "database": {
    "mongodb_url": "",
    "redis_url": ""
  },
  "integration": {
    "session_storage_url": "http://session-storage:8092",
    "session_pipeline_url": "http://session-pipeline:8083"
  },
  "compression": {
    "algorithm": "zstd",
    "level": 6
  }
}
```

**rdp-controller:**
```json
{
  "service": {
    "name": "rdp-controller",
    "port": 8082
  },
  "database": {
    "mongodb_url": "",
    "redis_url": ""
  },
  "integration": {
    "rdp_server_manager_url": "http://rdp-server-manager:8081",
    "session_api_url": "http://session-api:8113"
  }
}
```

### 11.2 YAML Configuration Per Container

**Standard YAML structure (all containers):**
```yaml
# Service Configuration
service_name: "<service-name>"
service_version: "1.0.0"
host: "0.0.0.0"
port: <port>
url: ""  # Set via environment variable

# Database Configuration
database:
  mongodb_url: ""  # From .env.secrets
  redis_url: ""    # From .env.secrets

# Integration Configuration
integration:
  <service>_url: "http://<service-name>:<port>"

# Storage Configuration
storage:
  data_path: "/app/data"
  logs_path: "/app/logs"
```

---

## 12. Related Documentation

- `build/docs/master-docker-design.md` - Universal design patterns
- `build/docs/dockerfile-design.md` - Dockerfile-specific patterns
- `build/docs/mod-design-template.md` - Module design template
- `plan/constants/Dockerfile-copy-pattern.md` - COPY command patterns
- `docs/architecture/DISTROLESS-CONTAINER-SPEC.md` - Distroless requirements

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0.0 | 2025-01-27 | Initial container design reference document | System |

---

**Last Updated:** 2025-01-27  
**Status:** ACTIVE  
**Maintained By:** Lucid Development Team

