# Session Recorder Container Design Template

## Overview

This document provides a comprehensive design template for creating new Lucid service containers based on the session-recorder container architecture. It covers module structure, configuration management, Dockerfile patterns, integration patterns, and deployment best practices.

**Reference Implementation:** `sessions/recorder/`  
**Dockerfile:** `sessions/Dockerfile.recorder`  
**Service Port:** 8090  
**Image:** `pickme/lucid-session-recorder:latest-arm64`

---

## Table of Contents

1. [Container Architecture](#container-architecture)
2. [Module Structure](#module-structure)
3. [Configuration Management](#configuration-management)
4. [Dockerfile Pattern](#dockerfile-pattern)
5. [Entrypoint Pattern](#entrypoint-pattern)
6. [Integration Pattern](#integration-pattern)
7. [Requirements Management](#requirements-management)
8. [Build and Deployment](#build-and-deployment)
9. [Best Practices](#best-practices)

---

## Container Architecture

### Multi-Stage Build Pattern

The container uses a **two-stage build** pattern:

1. **Builder Stage** (`python:3.11-slim-bookworm`)
   - Installs build dependencies
   - Compiles Python packages
   - Validates package installation

2. **Runtime Stage** (`gcr.io/distroless/python3-debian12:latest`)
   - Minimal distroless base
   - Only runtime dependencies
   - Non-root user (65532:65532)

### Container Layout

```
/app/
├── core/                          # Shared core modules
│   ├── __init__.py
│   ├── logging.py
│   ├── chunker.py
│   └── merkle_builder.py
├── sessions/
│   ├── __init__.py
│   ├── recorder/                  # Service-specific modules
│   │   ├── __init__.py
│   │   ├── main.py                # FastAPI application
│   │   ├── entrypoint.py          # Container entrypoint
│   │   ├── config.py              # Configuration management
│   │   ├── session_recorder.py    # Core service logic
│   │   ├── chunk_generator.py
│   │   ├── compression.py
│   │   ├── video_capture.py
│   │   ├── resource_monitor.py
│   │   ├── integration/           # Service integration clients
│   │   │   ├── __init__.py
│   │   │   ├── integration_manager.py
│   │   │   ├── service_base.py
│   │   │   ├── session_pipeline_client.py
│   │   │   └── session_storage_client.py
│   │   └── config/                # Configuration templates
│   │       ├── env.session-recorder.template
│   │       └── README.md
│   ├── pipeline/
│   │   ├── __init__.py
│   │   └── integration/           # Shared integration clients
│   └── config/
│       └── recorder-config.yaml   # YAML configuration file
└── /usr/local/lib/python3.11/site-packages/  # Python packages
```

---

## Module Structure

### Core Module Organization

#### 1. Main Application Module (`main.py`)

**Purpose:** FastAPI application entry point with lifespan management

**Key Components:**
- FastAPI app initialization
- Lifespan context manager (startup/shutdown)
- Global service instances
- Signal handlers
- Health check endpoints
- API route definitions

**Template Structure:**
```python
#!/usr/bin/env python3
"""
[Service Name] Service
Main entry point for the [service description]
"""

import asyncio
import os
import signal
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, Any, Dict

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .[service_module] import [ServiceClass]
from .config import [ConfigClass], load_config
from core.logging import setup_logging, get_logger

# Initialize logging
setup_logging()
logger = get_logger(__name__)

# Global instances
service_instance: Optional[ServiceClass] = None
config: Optional[ConfigClass] = None
integrations: Optional[Any] = None

def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown"""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global service_instance, config, integrations
    
    logger.info("Starting [Service Name] Service")
    
    try:
        # Load configuration
        config = load_config()
        
        # Setup signal handlers
        setup_signal_handlers()
        
        # Initialize integration manager
        try:
            from .integration.integration_manager import IntegrationManager
            integrations = IntegrationManager(...)
            logger.info("Integration manager initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize integration manager: {str(e)}")
            integrations = None
        
        # Initialize service
        service_instance = ServiceClass(config=config)
        
        logger.info("[Service Name] Service started successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start [Service Name] Service: {str(e)}")
        raise
    finally:
        # Shutdown
        logger.info("Shutting down [Service Name] Service...")
        if integrations:
            await integrations.close_all()
        logger.info("[Service Name] Service shutdown complete")

# Create FastAPI application
app = FastAPI(
    title="[Service Name]",
    description="[Service description]",
    version="1.0.0",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "[service-name]",
        "timestamp": datetime.utcnow().isoformat()
    }

# Additional endpoints...
```

#### 2. Entrypoint Module (`entrypoint.py`)

**Purpose:** Container entrypoint script for distroless containers

**Key Features:**
- Environment variable configuration
- Python path setup
- Error handling
- Uvicorn server startup

**Template Structure:**
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[Service Name] Service Entrypoint
UTF-8 encoded entrypoint script for distroless container

This script serves as the entrypoint for the [service-name] container,
providing clean startup with environment variable configuration.
No hardcoded values - all configuration from environment variables.
"""

import os
import sys

# Ensure site-packages is in Python path
site_packages = '/usr/local/lib/python3.11/site-packages'
if site_packages not in sys.path:
    sys.path.insert(0, site_packages)

if __name__ == "__main__":
    # Get configuration from environment variables
    port_str = os.getenv('[SERVICE]_PORT', '[default_port]')
    host = '0.0.0.0'  # Always bind to all interfaces in container
    
    try:
        port = int(port_str)
    except ValueError:
        print(f"ERROR: Invalid [SERVICE]_PORT value: {port_str}", file=sys.stderr)
        sys.exit(1)
    
    # Import uvicorn and start the application
    try:
        import uvicorn
    except ImportError as e:
        print(f"ERROR: Failed to import uvicorn: {e}", file=sys.stderr)
        print(f"ERROR: Python path: {sys.path}", file=sys.stderr)
        print(f"ERROR: Site packages exists: {os.path.exists(site_packages)}", file=sys.stderr)
        if os.path.exists(site_packages):
            try:
                contents = os.listdir(site_packages)
                print(f"ERROR: Site packages contents (first 20): {contents[:20]}", file=sys.stderr)
            except Exception as list_err:
                print(f"ERROR: Could not list site packages: {list_err}", file=sys.stderr)
        sys.exit(1)
    
    uvicorn.run('[module.path].main:app', host=host, port=port)
```

#### 3. Configuration Module (`config.py`)

**Purpose:** Configuration management with YAML and environment variable support

**Key Features:**
- Pydantic settings models
- YAML file loading
- Environment variable overrides
- Validation and defaults

**Template Structure:**
```python
"""
Configuration Module for [Service Name]
Manages configuration settings for the [service description].

Configuration is loaded from YAML file with environment variable overrides.
"""

import os
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

logger = logging.getLogger(__name__)

class ServiceSettings(BaseSettings):
    """Global service settings"""
    service_name: str = "[service-name]"
    service_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"
    # Add service-specific settings

class [Service]Config(BaseSettings):
    """Main configuration class"""
    settings: ServiceSettings = ServiceSettings()
    # Add configuration sections
    
    @classmethod
    def from_yaml(cls, yaml_path: Optional[str] = None) -> '[Service]Config':
        """Load configuration from YAML file"""
        if yaml_path is None:
            yaml_path = os.getenv('[SERVICE]_CONFIG_PATH', '/app/[service]/config/[service]-config.yaml')
        
        config_dict = {}
        if YAML_AVAILABLE and os.path.exists(yaml_path):
            try:
                with open(yaml_path, 'r') as f:
                    config_dict = yaml.safe_load(f) or {}
                logger.info(f"Loaded configuration from {yaml_path}")
            except Exception as e:
                logger.warning(f"Failed to load YAML config: {e}")
        
        # Override with environment variables
        # Example: config_dict['database']['mongodb_url'] = os.getenv('MONGODB_URL', '')
        
        return cls(**config_dict)
    
    def validate_config(self) -> bool:
        """Validate configuration"""
        # Add validation logic
        return True

def load_config() -> '[Service]Config':
    """Load configuration with fallback to defaults"""
    try:
        config = [Service]Config.from_yaml()
        if config.validate_config():
            return config
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
    
    # Fallback to defaults
    return [Service]Config()
```

#### 4. Integration Module (`integration/`)

**Purpose:** Service-to-service communication clients

**Structure:**
```
integration/
├── __init__.py
├── integration_manager.py    # Centralized integration management
├── service_base.py           # Base client class
└── [service]_client.py       # Specific service clients
```

**Integration Manager Template:**
```python
"""
Integration Manager for [Service Name]
Manages initialization and lifecycle of integration clients
"""

import logging
import os
from typing import Optional, Dict, Any

# Import clients from pipeline integration (shared across services)
try:
    from sessions.pipeline.integration.blockchain_engine_client import BlockchainEngineClient
    from sessions.pipeline.integration.node_manager_client import NodeManagerClient
    from sessions.pipeline.integration.api_gateway_client import APIGatewayClient
    from sessions.pipeline.integration.auth_service_client import AuthServiceClient
except ImportError:
    BlockchainEngineClient = None
    NodeManagerClient = None
    APIGatewayClient = None
    AuthServiceClient = None

# Import local service clients
try:
    from .[service]_client import [Service]Client
except ImportError:
    [Service]Client = None

logger = logging.getLogger(__name__)

class IntegrationManager:
    """Manages integration service clients"""
    
    def __init__(self, service_timeout: float = 30.0, service_retry_count: int = 3, service_retry_delay: float = 1.0):
        self.service_timeout = float(os.getenv('SERVICE_TIMEOUT_SECONDS', service_timeout))
        self.service_retry_count = int(os.getenv('SERVICE_RETRY_COUNT', service_retry_count))
        self.service_retry_delay = float(os.getenv('SERVICE_RETRY_DELAY_SECONDS', service_retry_delay))
        
        # Initialize client references (lazy loading)
        self._blockchain_client: Optional[BlockchainEngineClient] = None
        self._node_manager_client: Optional[NodeManagerClient] = None
        # ... other clients
    
    @property
    def blockchain(self) -> Optional[BlockchainEngineClient]:
        """Get blockchain engine client (lazy initialization)"""
        if self._blockchain_client is None and BlockchainEngineClient:
            url = os.getenv('BLOCKCHAIN_ENGINE_URL', '')
            if url:
                try:
                    self._blockchain_client = BlockchainEngineClient(
                        base_url=url,
                        timeout=self.service_timeout,
                        retry_count=self.service_retry_count,
                        retry_delay=self.service_retry_delay
                    )
                    logger.info("Initialized BlockchainEngineClient")
                except Exception as e:
                    logger.warning(f"Failed to initialize BlockchainEngineClient: {str(e)}")
        return self._blockchain_client
    
    # ... other client properties
    
    async def close_all(self):
        """Close all client connections"""
        # Close all clients
        logger.info("Closed all integration clients")
```

**Service Base Client Template:**
```python
"""
Base Service Client for Integration Modules
Provides common functionality for service communication
"""

import asyncio
import logging
import os
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
import httpx
from datetime import datetime

try:
    from core.logging import get_logger
except ImportError:
    logger = logging.getLogger(__name__)
    def get_logger(name):
        return logging.getLogger(name)

logger = get_logger(__name__)

class ServiceError(Exception):
    """Base exception for service communication errors"""
    pass

class ServiceTimeoutError(ServiceError):
    """Exception raised when service call times out"""
    pass

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
            raise ValueError(f"Service base_url is required but not provided")
        
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout or float(os.getenv('SERVICE_TIMEOUT_SECONDS', '30'))
        self.retry_count = retry_count or int(os.getenv('SERVICE_RETRY_COUNT', '3'))
        self.retry_delay = retry_delay or float(os.getenv('SERVICE_RETRY_DELAY_SECONDS', '1.0'))
        self.api_key = api_key or os.getenv('JWT_SECRET_KEY', '')
        
        # Create HTTP client
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout, connect=5.0),
            follow_redirects=True
        )
        
        logger.info(f"Initialized {self.__class__.__name__} with base_url={self.base_url}")
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Make HTTP request with retry logic"""
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

---

## Configuration Management

### YAML Configuration File

**Location:** `sessions/config/[service]-config.yaml`

**Structure:**
```yaml
# [Service Name] - Configuration
# Optional YAML configuration for [service description]
# File: sessions/config/[service]-config.yaml
# Purpose: Define [service] parameters and settings
# NOTE: All service URLs, ports, and database connections must be provided via
# environment variables from docker-compose.application.yml

# Global Service Configuration
global:
  service_name: "[service-name]"
  service_version: "1.0.0"
  debug: false
  log_level: "INFO"  # Override with LOG_LEVEL env var
  # Storage paths come from volumes mounted in docker-compose.application.yml
  data_path: "/app/data"
  output_path: "/app/output"

# Service-Specific Configuration
[service_section]:
  # Configuration options
  enabled: true
  # ... other settings

# Database Configuration
# NOTE: Database URLs MUST come from environment variables:
# - MONGODB_URL (required, from .env.secrets)
# - REDIS_URL (from .env.core or .env.secrets)
database:
  mongodb_url: ""  # Set via MONGODB_URL env var (required)
  redis_url: ""    # Set via REDIS_URL env var

# Network Configuration
# NOTE: Host and port MUST come from environment variables:
# - [SERVICE]_HOST (default: [service-name])
# - [SERVICE]_PORT (default: [port])
network:
  host: "0.0.0.0"  # Bind address (always 0.0.0.0 in container)
  port: [port]  # Override with [SERVICE]_PORT env var

# Monitoring and Metrics
monitoring:
  enabled: true
  metrics:
    - "metric1"
    - "metric2"
  
  health_check:
    enabled: true
    interval_seconds: 30
    timeout_seconds: 10

# Error Handling
error_handling:
  retry:
    enabled: true
    max_retries: 3
    retry_delay_seconds: 5
    exponential_backoff: true
  
  recovery:
    enabled: true
    auto_recovery: true
    recovery_timeout_seconds: 60

# Security Configuration
security:
  access_control:
    require_authentication: true
    require_authorization: true
    allowed_roles: ["USER", "NODE_OPERATOR", "ADMIN", "SUPER_ADMIN"]
  
  data_privacy:
    encrypt_data: false
    mask_sensitive_data: false
    audit_log_enabled: true
    audit_log_retention_days: 90
```

### Environment Variable Template

**Location:** `sessions/[service]/config/env.[service].template`

**Structure:**
```bash
# [Service Name] Environment Variables Template
# Copy this file to .env.[service] and fill in actual values
# DO NOT commit .env.[service] to version control

# Service Configuration
[SERVICE]_HOST=[service-name]
[SERVICE]_PORT=[port]
[SERVICE]_URL=http://[service-name]:[port]

# Logging
LOG_LEVEL=INFO

# Database URLs (from .env.secrets)
MONGODB_URL=
REDIS_URL=

# Service Integration URLs
BLOCKCHAIN_ENGINE_URL=
NODE_MANAGEMENT_URL=
API_GATEWAY_URL=
AUTH_SERVICE_URL=
SESSION_PIPELINE_URL=
SESSION_STORAGE_URL=

# Service Timeout Configuration
SERVICE_TIMEOUT_SECONDS=30
SERVICE_RETRY_COUNT=3
SERVICE_RETRY_DELAY_SECONDS=1.0

# Authentication
JWT_SECRET_KEY=

# Service-Specific Variables
# Add service-specific environment variables here
```

---

## Dockerfile Pattern

### Complete Dockerfile Template

```dockerfile
# syntax=docker/dockerfile:1.5

# [SERVICE NAME] - Distroless Container
# Aligned with dockerfile-design.md, Dockerfile-copy-pattern.md
# [Service description] ([service-name]) - Port [port]
# Image: pickme/lucid-[service-name]:latest-arm64
# Build Context: . (project root)
# Deployment: Pi console at /mnt/myssd/Lucid/Lucid/

# =============================================================================
# BUILD ARGUMENTS
# =============================================================================
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0
ARG TARGETPLATFORM=linux/arm64
ARG BUILDPLATFORM=linux/amd64
ARG PYTHON_VERSION=3.11

############################
# Stage 1 – Builder
############################
FROM --platform=$TARGETPLATFORM python:3.11-slim-bookworm AS builder

ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG PYTHON_VERSION

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_PREFER_BINARY=1 \
    DEBIAN_FRONTEND=noninteractive

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    rm -rf /var/lib/apt/lists/* && \
    apt-get update --allow-releaseinfo-change && \
    apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        g++ \
        libffi-dev \
        libssl-dev \
        pkg-config \
        curl \
        ca-certificates \
        # Add service-specific build dependencies
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /build

# Ensures /var/run and /var/lib exist with real content
RUN echo "LUCID_[SERVICE]_RUNTIME_DIRECTORY" > /var/run/.keep && \
    echo "LUCID_[SERVICE]_LIB_DIRECTORY" > /var/lib/.keep && \
    chown -R 65532:65532 /var/run /var/lib

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel

COPY sessions/requirements.[service].txt ./requirements.txt

RUN mkdir -p /root/.local/lib/python3.11/site-packages && \
    mkdir -p /root/.local/bin

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --user --no-cache-dir --prefer-binary -r requirements.txt

# Marker files (per Dockerfile-copy-pattern.md)
RUN echo "LUCID_[SERVICE]_PACKAGES_INSTALLED_$(date +%s)" > /root/.local/lib/python3.11/site-packages/.lucid-marker && \
    echo "LUCID_[SERVICE]_BINARIES_INSTALLED_$(date +%s)" > /root/.local/bin/.lucid-marker && \
    chown -R 65532:65532 /root/.local

# Builder-stage verification
RUN python3 -c "import [critical_packages]; print('✅ critical packages installed')" && \
    test -d /root/.local/lib/python3.11/site-packages && \
    test -f /root/.local/lib/python3.11/site-packages/.lucid-marker && \
    test -s /root/.local/lib/python3.11/site-packages/.lucid-marker && \
    echo "✅ Marker file verified in builder (non-empty)"

# Application source COPY
COPY sessions/[service]/ ./[service]/
COPY sessions/core/ ./core/
COPY sessions/pipeline/__init__.py ./pipeline/__init__.py
COPY sessions/pipeline/integration/ ./pipeline/integration/
COPY sessions/__init__.py ./__init__.py
COPY sessions/config/[service]-config.yaml ./config/[service]-config.yaml

############################
# Stage 2 – Runtime
############################
FROM --platform=$TARGETPLATFORM gcr.io/distroless/python3-debian12:latest

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0

LABEL maintainer="Lucid Development Team" \
      org.opencontainers.image.title="Lucid [Service Name]" \
      org.opencontainers.image.description="Distroless [service description] for Lucid project" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      com.lucid.service="[service-name]" \
      com.lucid.platform="arm64" \
      com.lucid.cluster="[cluster]" \
      com.lucid.security="distroless"

ENV PATH=/usr/local/bin:/usr/bin:/bin \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app:/usr/local/lib/python3.11/site-packages \
    PYTHONIOENCODING=utf-8 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    [SERVICE]_PORT=[port] \
    [SERVICE]_HOST=0.0.0.0

WORKDIR /app

# System directories & certificates
COPY --from=builder --chown=65532:65532 /var/run /var/run
COPY --from=builder --chown=65532:65532 /var/lib /var/lib
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt

# Python packages
COPY --from=builder --chown=65532:65532 /root/.local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder --chown=65532:65532 /root/.local/bin /usr/local/bin

# Runtime verification of packages
RUN ["/usr/bin/python3.11", "-c", "import sys; import os; \
site_packages = '/usr/local/lib/python3.11/site-packages'; \
sys.path.insert(0, site_packages); \
assert os.path.exists(site_packages), site_packages + ' does not exist'; \
# Verify critical packages exist \
assert os.path.exists(os.path.join(site_packages, 'uvicorn')), 'uvicorn not found'; \
assert os.path.exists(os.path.join(site_packages, 'fastapi')), 'fastapi not found'; \
# Verify marker file \
marker_path = os.path.join(site_packages, '.lucid-marker'); \
assert os.path.exists(marker_path), 'marker file not found'; \
assert os.path.getsize(marker_path) > 0, 'marker file is empty'; \
# Actually import packages \
import uvicorn; assert uvicorn, 'uvicorn import failed'; \
import fastapi; assert fastapi, 'fastapi import failed'; \
print('✅ All packages verified in runtime stage')"]

# Application layout COPY
COPY --chown=65532:65532 --from=builder /build/core /app/core
COPY --chown=65532:65532 --from=builder /build/[service] /app/sessions/[service]
COPY --chown=65532:65532 --from=builder /build/pipeline/__init__.py /app/sessions/pipeline/__init__.py
COPY --chown=65532:65532 --from=builder /build/pipeline/integration /app/sessions/pipeline/integration
COPY --chown=65532:65532 --from=builder /build/__init__.py /app/sessions/__init__.py
COPY --chown=65532:65532 --from=builder /build/config/[service]-config.yaml /app/sessions/config/[service]-config.yaml

# Verify application source files were copied
RUN ["/usr/bin/python3.11", "-c", "import os; \
assert os.path.exists('/app/sessions/[service]'), '[service] directory not found'; \
assert os.path.exists('/app/sessions/[service]/entrypoint.py'), 'entrypoint.py not found'; \
assert os.path.exists('/app/sessions/[service]/main.py'), 'main.py not found'; \
assert os.path.exists('/app/core'), 'core directory not found'; \
print('✅ All application source files verified')"]

EXPOSE [port]

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD ["/usr/bin/python3.11", "-c", "import socket; s = socket.socket(); s.settimeout(2); result = s.connect_ex(('127.0.0.1', [port])); s.close(); exit(0 if result == 0 else 1)"]

USER 65532:65532

# Clear base ENTRYPOINT so CMD works as expected
ENTRYPOINT []

CMD ["/usr/bin/python3.11", "/app/sessions/[service]/entrypoint.py"]
```

---

## Requirements Management

### Requirements File Structure

**Location:** `sessions/requirements.[service].txt`

**Template:**
```txt
# [Service Name] Dependencies
# Production requirements for [service-name] container

# =============================================================================
# Core FastAPI and async dependencies
# =============================================================================
fastapi>=0.111,<1.0
uvicorn[standard]>=0.30
pydantic>=2.5.0
pydantic-settings>=2.1.0

# =============================================================================
# Async support
# =============================================================================
aiofiles>=23.2.1
httpx>=0.25.2

# =============================================================================
# Database and caching
# =============================================================================
motor>=3.3.2
pymongo>=4.6.0
redis>=5.0.1
async-timeout>=4.0.2

# =============================================================================
# Cryptography and hashing
# =============================================================================
cryptography>=41.0.7
blake3>=0.3.3

# =============================================================================
# Compression libraries (if needed)
# =============================================================================
# zstandard>=0.21.0
# lz4>=4.3.2

# =============================================================================
# Data processing and validation
# =============================================================================
PyYAML>=6.0.1

# =============================================================================
# Monitoring and observability
# =============================================================================
structlog>=23.2.0

# =============================================================================
# Service-specific dependencies
# =============================================================================
# Add service-specific packages here
```

---

## Build and Deployment

### Build Commands

**Build without cache:**
```bash
docker build --no-cache -f sessions/Dockerfile.[service] -t pickme/lucid-[service-name]:latest-arm64 .
```

**Build with docker-compose:**
```bash
docker-compose build --no-cache [service-name]
```

### Verification Commands

**Verify package installation:**
```bash
docker run --rm pickme/lucid-[service-name]:latest-arm64 python3.11 -c "import [critical_package]; print('[critical_package] version:', [critical_package].__version__)"
```

**Verify container health:**
```bash
docker run --rm -p [port]:[port] pickme/lucid-[service-name]:latest-arm64
# In another terminal:
curl http://localhost:[port]/health
```

---

## Best Practices

### 1. Import Management

- **Always use try/except for optional imports:**
```python
try:
    from core.logging import get_logger
except ImportError:
    logger = logging.getLogger(__name__)
    def get_logger(name):
        return logging.getLogger(name)
```

- **Use absolute imports for cross-package imports:**
```python
# Good
from sessions.encryption.encryptor import SessionEncryptor

# Bad (can fail in containers)
from ..encryption.encryptor import SessionEncryptor
```

### 2. Configuration Management

- **Never hardcode values** - use environment variables
- **YAML files are optional** - always have environment variable fallbacks
- **Validate configuration** on startup
- **Log configuration loading** for debugging

### 3. Error Handling

- **Graceful degradation** - services should start even if optional integrations fail
- **Clear error messages** - include actionable information
- **Proper logging** - use structured logging with appropriate levels

### 4. Security

- **Non-root user** - always use USER 65532:65532
- **Distroless base** - minimal attack surface
- **No secrets in code** - use environment variables
- **Input validation** - validate all inputs

### 5. Performance

- **Lazy initialization** - initialize clients only when needed
- **Connection pooling** - reuse HTTP clients
- **Async operations** - use async/await for I/O operations
- **Resource cleanup** - properly close connections on shutdown

### 6. Testing

- **Health check endpoint** - always implement `/health`
- **Integration tests** - test service interactions
- **Error scenarios** - test failure cases
- **Container verification** - verify packages and files in Dockerfile

---

## Checklist for New Container

- [ ] Create service directory structure
- [ ] Create `main.py` with FastAPI app
- [ ] Create `entrypoint.py` for container startup
- [ ] Create `config.py` with Pydantic models
- [ ] Create YAML configuration file
- [ ] Create environment variable template
- [ ] Create `requirements.[service].txt`
- [ ] Create `Dockerfile.[service]`
- [ ] Create integration clients (if needed)
- [ ] Add health check endpoint
- [ ] Add signal handlers for graceful shutdown
- [ ] Add proper error handling
- [ ] Add logging configuration
- [ ] Test container build
- [ ] Test container startup
- [ ] Test health check
- [ ] Test service endpoints
- [ ] Update docker-compose configuration
- [ ] Document service in project docs

---

## Reference Files

- **Session Recorder Implementation:** `sessions/recorder/`
- **Dockerfile:** `sessions/Dockerfile.recorder`
- **Requirements:** `sessions/requirements.recorder.txt`
- **Configuration:** `sessions/config/recorder-config.yaml`
- **Environment Template:** `sessions/recorder/config/env.session-recorder.template`

---

## Version History

- **v1.0.0** (2024-12-23): Initial design template based on session-recorder container

---

## Notes

- This template is based on the session-recorder container implementation
- Adapt sections as needed for specific service requirements
- Follow Lucid project conventions and patterns
- Consult `dockerfile-design.md` and `Dockerfile-copy-pattern.md` for Docker-specific guidance

