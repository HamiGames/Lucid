# RDP Controller Container Design Template

**Version:** 1.0.0  
**Last Updated:** 2025-01-27  
**Service:** `lucid-rdp-controller`  
**Container Name:** `rdp-controller`  
**Purpose:** Architectural design template for building future containers based on rdp-controller patterns

This document provides a comprehensive architectural template derived from the `rdp-controller` container, serving as a reference for building new containers with consistent patterns, structure, and best practices.

---

## Table of Contents

1. [Container Overview](#1-container-overview)
2. [Architecture Patterns](#2-architecture-patterns)
3. [Directory Structure](#3-directory-structure)
4. [Module Organization](#4-module-organization)
5. [Configuration Management](#5-configuration-management)
6. [Docker Compose Template](#6-docker-compose-template)
7. [Dockerfile Template](#7-dockerfile-template)
8. [Integration Patterns](#8-integration-patterns)
9. [Schema and Validation](#9-schema-and-validation)
10. [Error Handling](#10-error-handling)
11. [Security Patterns](#11-security-patterns)
12. [Build and Deployment](#12-build-and-deployment)

---

## 1. Container Overview

### 1.1 Service Identity

```yaml
Service Name: lucid-<service-name>
Container Name: <service-name>
Image: pickme/lucid-<service-name>:latest-arm64
Port: <port-number>
Protocol: REST API (FastAPI)
Version: 1.0.0
```

### 1.2 Key Characteristics

- **Distroless Base**: `gcr.io/distroless/python3-debian12:latest`
- **Python Version**: 3.11
- **Framework**: FastAPI + Uvicorn
- **Configuration**: Pydantic Settings with YAML/JSON support
- **Security**: Non-root user (65532:65532), read-only filesystem
- **Architecture**: Multi-stage build (builder + runtime)

### 1.3 Core Responsibilities

The rdp-controller container demonstrates these patterns:

1. **Session Management**: Lifecycle management, state tracking
2. **Connection Management**: Connection pooling, health monitoring
3. **Integration Management**: Centralized service client management
4. **Schema Validation**: JSON schema validation for API responses
5. **OpenAPI Integration**: OpenAPI spec loading for documentation
6. **Graceful Degradation**: Service continues even if optional components fail

---

## 2. Architecture Patterns

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    <service-name> Container                  │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   main.py    │  │ <service>_   │  │  connection_ │      │
│  │  (FastAPI)   │──│  controller  │──│   manager    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   config.py  │  │ entrypoint.py│  │ integration/ │      │
│  │  (Settings)  │  │  (Startup)   │  │   manager    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │schema_validator│ │  openapi.yaml│  │  *.schema.json│     │
│  │  (Validation) │ │  (API Docs)  │  │  (Schemas)    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────────┐
        │  External Services                  │
        │  • MongoDB (lucid-mongodb)           │
        │  • Redis (lucid-redis)               │
        │  • Integration Services              │
        └─────────────────────────────────────┘
```

### 2.2 Request Flow

1. **Request Reception**: FastAPI receives HTTP request
2. **Routing**: Route handler processes request
3. **Validation**: Schema validation (optional, graceful degradation)
4. **Business Logic**: Service controller processes request
5. **Integration**: Integration manager coordinates with external services
6. **Response**: FastAPI returns validated JSON response

### 2.3 Component Responsibilities

- **`main.py`**: FastAPI app, lifespan management, route definitions
- **`<service>_controller.py`**: Core business logic
- **`connection_manager.py`**: Connection pooling and lifecycle
- **`config.py`**: Configuration loading and validation
- **`entrypoint.py`**: Container entrypoint script
- **`integration/`**: Service-to-service communication clients
- **`schema_validator.py`**: JSON schema validation utilities

---

## 3. Directory Structure

### 3.1 Standard Container Structure

```
<service-name>/
├── __init__.py                 # Package initialization
├── main.py                     # FastAPI application
├── entrypoint.py               # Container entrypoint
├── config.py                   # Configuration management
├── <service>_controller.py     # Main service logic
├── connection_manager.py       # Connection management (if needed)
├── schema_validator.py         # Schema validation (if using schemas)
├── config.yaml                 # Optional YAML configuration
├── openapi.yaml                # OpenAPI 3.0 specification
├── health-schema.json          # Health check response schema
├── <service>-schema.json       # Service data schema
├── metrics-schema.json          # Metrics data schema
├── requirements.txt            # Python dependencies
├── config/                     # Configuration directory
│   ├── env.<service-name>.template
│   └── README.md
└── integration/                # Integration clients
    ├── __init__.py
    ├── integration_manager.py
    ├── service_base.py
    └── <service>_client.py
```

### 3.2 Container Internal Structure

```
/app/
├── <service_name>/              # Service-specific modules
│   ├── __init__.py
│   ├── main.py
│   ├── entrypoint.py
│   ├── config.py
│   ├── <service>_controller.py
│   ├── config.yaml
│   ├── openapi.yaml
│   ├── *.schema.json
│   ├── config/
│   └── integration/
├── common/                      # Shared common modules
├── security/                    # Shared security modules
├── protocol/                    # Shared protocol modules
└── /usr/local/lib/python3.11/site-packages/  # Python packages
```

---

## 4. Module Organization

### 4.1 main.py Pattern

**Purpose**: FastAPI application setup and lifespan management

**Key Components**:
```python
from fastapi import FastAPI
from contextlib import asynccontextmanager
from .config import load_config
from .<service>_controller import <Service>Controller
from .integration.integration_manager import IntegrationManager

# Global instances
<service>_controller = None
integration_manager = None
controller_config = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global <service>_controller, integration_manager, controller_config
    
    # Startup
    controller_config = load_config()
    integration_manager = IntegrationManager(...)
    <service>_controller = <Service>Controller(...)
    
    yield
    
    # Shutdown
    if integration_manager:
        await integration_manager.close_all()

def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    app = FastAPI(
        title="Lucid <Service Name>",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # Load OpenAPI schema if available
    openapi_schema = load_openapi_schema()
    if openapi_schema:
        app.openapi = lambda: openapi_schema
    
    # Add routes
    @app.get("/health")
    async def health_check():
        # Validate response against schema
        response_data = {...}
        validate_health_response(response_data)  # Optional
        return response_data
    
    return app

app = create_app()
```

**Key Patterns**:
- Lifespan context manager for startup/shutdown
- Global instances for service components
- OpenAPI schema loading (optional)
- Schema validation in endpoints (graceful degradation)

### 4.2 entrypoint.py Pattern

**Purpose**: Container entrypoint script (Python-based for distroless)

**Pattern**:
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
<Service Name> Service Entrypoint
UTF-8 encoded entrypoint script for distroless container
"""

import os
import sys

# Ensure site-packages and app directory are in Python path
site_packages = '/usr/local/lib/python3.11/site-packages'
app_path = '/app'

if site_packages not in sys.path:
    sys.path.insert(0, site_packages)
if app_path not in sys.path:
    sys.path.insert(0, app_path)

if __name__ == "__main__":
    # Get configuration from environment variables
    port_str = os.getenv('<SERVICE>_PORT', '<default-port>')
    host = '0.0.0.0'  # Always bind to all interfaces
    
    try:
        port = int(port_str)
    except ValueError:
        print(f"ERROR: Invalid <SERVICE>_PORT value: {port_str}", file=sys.stderr)
        sys.exit(1)
    
    # Import uvicorn and start the application
    try:
        import uvicorn
        from <service_name>.main import app
    except ImportError as e:
        print(f"ERROR: Failed to import: {e}", file=sys.stderr)
        sys.exit(1)
    
    uvicorn.run(app, host=host, port=port)
```

**Key Points**:
- Sets up Python path correctly
- Reads port from environment variable
- Always binds to `0.0.0.0`
- Handles errors gracefully with clear messages

### 4.3 config.py Pattern

**Purpose**: Configuration management using Pydantic Settings

**Pattern**:
```python
"""
<Service Name> Configuration Management
Uses Pydantic Settings for environment variable validation
"""

import os
import re
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    yaml = None

logger = logging.getLogger(__name__)

# Regex patterns for URL validation (compiled at module level)
LOCALHOST_PATTERN = re.compile(r'\blocalhost\b', re.IGNORECASE)
IP_127_PATTERN = re.compile(r'\b127\.0\.0\.1\b')


class <Service>Settings(BaseSettings):
    """Base settings for <Service Name> service"""
    
    # Service Configuration
    <SERVICE>_HOST: str = Field(default="0.0.0.0", description="Service bind address")
    <SERVICE>_PORT: int = Field(default=<port>, description="Service port")
    <SERVICE>_URL: str = Field(default="", description="Service URL")
    
    # Database Configuration (Required)
    MONGODB_URL: str = Field(default="", description="MongoDB connection URL")
    REDIS_URL: str = Field(default="", description="Redis connection URL")
    
    # Integration Service URLs
    <SERVICE>_INTEGRATION_URL: str = Field(default="", description="Integration service URL")
    
    # Environment
    LUCID_ENV: str = Field(default="production")
    LUCID_PLATFORM: str = Field(default="arm64")
    PROJECT_ROOT: str = Field(default="/mnt/myssd/Lucid/Lucid")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO")
    
    # Storage Paths
    LUCID_STORAGE_PATH: str = Field(default="/app/data")
    LUCID_LOGS_PATH: str = Field(default="/app/logs")
    
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


class <Service>Config:
    """Configuration manager for <Service Name>"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or os.getenv(
            '<SERVICE>_CONFIG_FILE',
            f'/app/<service_name>/config.yaml'
        )
        self.settings = self._load_config()
        self._validate_config()
    
    def _load_config(self) -> <Service>Settings:
        """Load configuration from YAML/JSON file and environment variables"""
        config_dict = {}
        
        # Load from YAML/JSON file if available
        if os.path.exists(self.config_file):
            try:
                config_dict = self._load_config_file(self.config_file)
                logger.info(f"Loaded configuration from {self.config_file}")
            except Exception as e:
                logger.warning(f"Failed to load config file {self.config_file}: {e}")
        
        # Environment variables override file values
        try:
            settings = <Service>Settings(**config_dict)
            return settings
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise ValueError(f"Configuration loading failed: {str(e)}") from e
    
    def _load_config_file(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML or JSON file"""
        path = Path(config_path)
        if path.suffix.lower() in ['.yaml', '.yml']:
            if YAML_AVAILABLE:
                with open(path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
        elif path.suffix.lower() == '.json':
            import json
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f) or {}
        return {}
    
    def _validate_config(self):
        """Validate configuration"""
        if not self.settings.MONGODB_URL:
            raise ValueError("MONGODB_URL is required")
        if not self.settings.REDIS_URL:
            raise ValueError("REDIS_URL is required")


def load_config(config_file: Optional[str] = None) -> <Service>Config:
    """Load configuration with fallback to defaults"""
    try:
        return <Service>Config(config_file=config_file)
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        raise
```

**Key Patterns**:
- Pydantic Settings for validation
- Module-level regex patterns for URL validation
- YAML/JSON file support (optional)
- Environment variable priority
- Clear validation error messages

### 4.4 Integration Manager Pattern

**Purpose**: Centralized management of service integration clients

**Pattern**:
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

**Key Patterns**:
- Lazy initialization (clients created on first use)
- Graceful degradation (missing URLs don't break service)
- Centralized configuration
- Health check aggregation

### 4.5 Service Base Client Pattern

**Purpose**: Base class for all service integration clients

**Pattern**:
```python
"""
Base Service Client for <Service Name> Integration Modules
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


class ServiceTimeoutError(ServiceError):
    """Exception raised when service call times out"""
    pass


class ServiceNotFoundError(ServiceError):
    """Exception raised when a resource is not found (HTTP 404)"""
    def __init__(self, message: str = "Resource not found", status_code: int = 404):
        super().__init__(message, status_code)


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
        url = f"{self.base_url}{endpoint}"
        request_headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        if self.api_key:
            request_headers['Authorization'] = f'Bearer {self.api_key}'
        if headers:
            request_headers.update(headers)
        
        last_error = None
        for attempt in range(self.retry_count):
            try:
                response = await self.client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    headers=request_headers
                )
                response.raise_for_status()
                return response.json()
            except httpx.TimeoutException as e:
                last_error = ServiceTimeoutError(f"Request to {url} timed out")
                logger.warning(f"Request timeout (attempt {attempt + 1}/{self.retry_count})")
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise ServiceNotFoundError(f"Resource not found at {url}", status_code=404)
                last_error = ServiceError(f"HTTP error {e.response.status_code}", status_code=e.response.status_code)
                if 400 <= e.response.status_code < 500:
                    raise last_error
            except Exception as e:
                last_error = ServiceError(f"Request failed: {str(e)}")
                logger.warning(f"Request error (attempt {attempt + 1}/{self.retry_count}): {str(e)}")
            
            if attempt < self.retry_count - 1:
                await asyncio.sleep(self.retry_delay * (attempt + 1))
        
        raise last_error or ServiceError(f"Request to {url} failed after {self.retry_count} attempts")
    
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

**Key Patterns**:
- Module-level regex patterns for URL validation
- Retry logic with exponential backoff
- Custom exception classes (ServiceError, ServiceTimeoutError, ServiceNotFoundError)
- No retry on 4xx errors (except 404 handled specially)
- Health check method

---

## 5. Configuration Management

### 5.1 Configuration Priority

**Order (highest to lowest)**:
1. Environment variables (from `.env.*` files)
2. YAML/JSON configuration file (`config.yaml`)
3. Pydantic field defaults

### 5.2 Environment Variables Template

**File**: `<service-name>/config/env.<service-name>.template`

**Pattern**:
```bash
# <Service Name> Environment Variables Template
# Copy this file to .env.<service-name> and fill in actual values

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

### 5.3 Configuration File (config.yaml)

**File**: `<service-name>/config.yaml`

**Pattern**:
```yaml
# <Service Name> - Configuration File
# Optional YAML configuration
# Environment variables override these values

# Service Configuration
<SERVICE>_HOST: "0.0.0.0"
<SERVICE>_PORT: <port>
<SERVICE>_URL: ""  # Must be set via environment variable
LOG_LEVEL: "INFO"

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

---

## 6. Docker Compose Template

### 6.1 Standard Service Definition

```yaml
<service-name>:
  image: pickme/lucid-<service-name>:latest-arm64
  container_name: <service-name>
  restart: unless-stopped
  env_file:
    - /mnt/myssd/Lucid/Lucid/configs/environment/.env.secrets
    - /mnt/myssd/Lucid/Lucid/configs/environment/.env.core
    - /mnt/myssd/Lucid/Lucid/configs/environment/.env.application
    - /mnt/myssd/Lucid/Lucid/configs/environment/.env.foundation
    - /mnt/myssd/Lucid/Lucid/configs/environment/.env.<service-name>  # Optional
  networks:
    lucid-pi-network: {}
  ports:
    - "<port>:<port>"
  volumes:
    - /mnt/myssd/Lucid/Lucid/data/<service-name>:/app/data:rw
    - /mnt/myssd/Lucid/Lucid/logs/<service-name>:/app/logs:rw
    - <service-name>-cache:/tmp/<service>
  environment:
    - LUCID_ENV=production
    - LUCID_PLATFORM=arm64
    - PROJECT_ROOT=/mnt/myssd/Lucid/Lucid
    - <SERVICE>_HOST=<service-name>
    - <SERVICE>_PORT=<port>
    - <SERVICE>_URL=http://<service-name>:<port>
    - MONGODB_URL=${MONGODB_URL:?MONGODB_URL not set}
    - REDIS_URL=${REDIS_URL:?REDIS_URL not set}
    # Service-specific storage paths
    - LUCID_STORAGE_PATH=/app/data
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
    - /tmp:noexec,nosuid,size=100m
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
  labels:
    - "lucid.service=<service-name>"
    - "lucid.type=distroless"
    - "lucid.platform=arm64"
    - "lucid.security=hardened"
    - "lucid.cluster=application"
  depends_on:
    tor-proxy:
      condition: service_started
    lucid-mongodb:
      condition: service_healthy
    lucid-redis:
      condition: service_healthy
    # Service-specific dependencies
    # <other-service>:
    #   condition: service_healthy
```

### 6.2 Volume Definition

```yaml
volumes:
  <service-name>-cache:
    driver: local
    name: lucid-<service-name>-cache
    external: false
```

---

## 7. Dockerfile Template

### 7.1 Complete Dockerfile Structure

```dockerfile
# syntax=docker/dockerfile:1.5

# LUCID <SERVICE NAME> - Distroless Container
# Aligned with dockerfile-design.md, master-docker-design.md
# Image: pickme/lucid-<service-name>:latest-arm64

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

WORKDIR /build

# System directory markers (per Dockerfile-copy-pattern.md)
RUN echo "LUCID_<SERVICE>_RUNTIME_DIRECTORY" > /var/run/.keep && \
    echo "LUCID_<SERVICE>_LIB_DIRECTORY" > /var/lib/.keep && \
    chown -R 65532:65532 /var/run /var/lib

# Install build dependencies
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
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Upgrade pip, setuptools, wheel
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel

# Create site-packages directory
RUN mkdir -p /root/.local/lib/python3.11/site-packages && \
    mkdir -p /root/.local/bin

# Copy and install Python dependencies
COPY <service-name>/requirements.txt ./requirements.txt

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --user --no-cache-dir --prefer-binary -r requirements.txt

# Create marker files with content (per Dockerfile-copy-pattern.md)
RUN echo "LUCID_<SERVICE>_PACKAGES_INSTALLED_$(date +%s)" > /root/.local/lib/python3.11/site-packages/.lucid-marker && \
    echo "LUCID_<SERVICE>_BINARIES_INSTALLED_$(date +%s)" > /root/.local/bin/.lucid-marker && \
    chown -R 65532:65532 /root/.local

# Verify packages in builder stage
RUN python3 -c "import fastapi, uvicorn, pydantic, pydantic_settings, motor, pymongo, redis, httpx; print('✅ critical packages installed')" && \
    test -f /root/.local/lib/python3.11/site-packages/.lucid-marker && \
    test -s /root/.local/lib/python3.11/site-packages/.lucid-marker && \
    echo "✅ Marker file verified in builder (non-empty)"

# Copy application source
COPY <service-name>/ ./<service_name>/
COPY common/ ./common/
COPY security/ ./security/
COPY protocol/ ./protocol/
COPY __init__.py ./__init__.py

# Verify source files
RUN test -d ./<service_name>/integration || (echo "ERROR: integration directory not found" && exit 1) && \
    test -f ./<service_name>/config.py || (echo "ERROR: config.py not found" && exit 1) && \
    echo "✅ Source files verified"

############################
# Stage 2 – Runtime
############################
FROM --platform=$TARGETPLATFORM gcr.io/distroless/python3-debian12:latest

ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0

LABEL maintainer="Lucid Development Team" \
      org.opencontainers.image.title="Lucid <Service Name>" \
      org.opencontainers.image.description="Distroless <service-name> for Lucid project" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      com.lucid.service="<service-id>" \
      com.lucid.platform="arm64" \
      com.lucid.cluster="application" \
      com.lucid.security="distroless"

ENV PATH=/usr/local/bin:/usr/bin:/bin \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app:/usr/local/lib/python3.11/site-packages \
    PYTHONIOENCODING=utf-8 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    <SERVICE>_HOST=0.0.0.0 \
    <SERVICE>_PORT=<port>

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
assert os.path.exists(os.path.join(site_packages, 'uvicorn')), 'uvicorn not found'; \
assert os.path.exists(os.path.join(site_packages, 'fastapi')), 'fastapi not found'; \
marker_path = os.path.join(site_packages, '.lucid-marker'); \
assert os.path.exists(marker_path), 'marker file not found'; \
assert os.path.getsize(marker_path) > 0, 'marker file is empty'; \
import uvicorn; assert uvicorn, 'uvicorn import failed'; \
import fastapi; assert fastapi, 'fastapi import failed'; \
print('✅ All packages verified in runtime stage')"]

# Copy application source
COPY --from=builder --chown=65532:65532 /build/<service_name> /app/<service_name>
COPY --from=builder --chown=65532:65532 /build/common /app/common
COPY --from=builder --chown=65532:65532 /build/security /app/security
COPY --from=builder --chown=65532:65532 /build/protocol /app/protocol
COPY --from=builder --chown=65532:65532 /build/__init__.py /app/__init__.py

# Verify application source files
RUN ["/usr/bin/python3.11", "-c", "import os; \
assert os.path.exists('/app/<service_name>'), '<service_name> directory not found'; \
assert os.path.exists('/app/<service_name>/main.py'), 'main.py not found'; \
assert os.path.exists('/app/<service_name>/entrypoint.py'), 'entrypoint.py not found'; \
assert os.path.exists('/app/<service_name>/config.py'), 'config.py not found'; \
assert os.path.exists('/app/<service_name>/integration'), 'integration directory not found'; \
print('✅ All application source files verified')"]

EXPOSE <port>

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD ["/usr/bin/python3.11", "-c", "import socket; s = socket.socket(); s.settimeout(2); result = s.connect_ex(('127.0.0.1', <port>)); s.close(); exit(0 if result == 0 else 1)"]

USER 65532:65532

# Clear base ENTRYPOINT so CMD works as expected
ENTRYPOINT []

# Use entrypoint.py script
CMD ["/usr/bin/python3.11", "/app/<service_name>/entrypoint.py"]
```

---

## 8. Integration Patterns

### 8.1 Integration Client Pattern

**File**: `<service-name>/integration/<service>_client.py`

**Pattern**:
```python
"""
<Service> Client for <Service Name> Integration
Client for interacting with <service> service
"""

import logging
from typing import Dict, Any, Optional
from .service_base import ServiceClientBase, ServiceError, ServiceNotFoundError

logger = logging.getLogger(__name__)


class <Service>Client(ServiceClientBase):
    """Client for interacting with <service> service"""
    
    async def get_resource(self, resource_id: str) -> Dict[str, Any]:
        """Get resource by ID"""
        try:
            return await self._make_request('GET', f'/resources/{resource_id}')
        except ServiceNotFoundError:
            return {"status": "not_found"}
        except ServiceError as e:
            logger.error(f"Failed to get resource {resource_id}: {str(e)}")
            raise
    
    async def list_resources(self) -> Dict[str, Any]:
        """List all resources"""
        return await self._make_request('GET', '/resources')
    
    async def create_resource(self, resource_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new resource"""
        return await self._make_request('POST', '/resources', json_data=resource_data)
```

**Key Patterns**:
- Inherits from `ServiceClientBase`
- Handles `ServiceNotFoundError` for 404 responses
- Uses `_make_request()` for all HTTP calls
- Clear error logging

### 8.2 Integration Manager Pattern

**File**: `<service-name>/integration/integration_manager.py`

**Pattern**:
```python
"""
Integration Manager for <Service Name>
Centralized management of service integration clients
"""

import os
import logging
from typing import Optional, Dict, Any
from .service_base import ServiceClientBase
from .<service1>_client import <Service1>Client
from .<service2>_client import <Service2>Client

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
    def client1(self) -> Optional[<Service1>Client]:
        """Get client1 (lazy initialization)"""
        if self._client1 is None:
            url = os.getenv('<SERVICE1>_URL', '')
            if url:
                try:
                    self._client1 = <Service1>Client(
                        base_url=url,
                        timeout=self.service_timeout,
                        retry_count=self.service_retry_count,
                        retry_delay=self.service_retry_delay
                    )
                    logger.info("Initialized <Service1>Client")
                except Exception as e:
                    logger.warning(f"Failed to initialize <Service1>Client: {str(e)}")
            else:
                logger.warning("<SERVICE1>_URL not set, client1 unavailable")
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

---

## 9. Schema and Validation

### 9.1 Schema Validator Pattern

**File**: `<service-name>/schema_validator.py`

**Purpose**: JSON schema validation for API responses

**Pattern**:
```python
"""
<Service Name> Schema Validation Module
Uses JSON schema files for request/response validation
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import jsonschema
    from jsonschema import validate, ValidationError, Draft7Validator
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False
    jsonschema = None

logger = logging.getLogger(__name__)


class SchemaValidationError(Exception):
    """Exception raised when schema validation fails"""
    def __init__(self, message: str, errors: Optional[list] = None):
        super().__init__(message)
        self.errors = errors or []


class SchemaValidator:
    """Schema validator for <Service Name> service"""
    
    def __init__(self, schema_dir: Optional[str] = None):
        if not JSONSCHEMA_AVAILABLE:
            logger.warning("jsonschema not available, schema validation disabled")
            self.enabled = False
            return
        
        self.enabled = True
        self.schema_dir = Path(schema_dir or f'/app/<service_name>')
        self._schemas: Dict[str, Dict[str, Any]] = {}
        self._validators: Dict[str, Draft7Validator] = {}
        self._load_schemas()
    
    def _load_schemas(self):
        """Load all JSON schema files"""
        schema_files = {
            'health': 'health-schema.json',
            '<service>': '<service>-schema.json',
            'metrics': 'metrics-schema.json'
        }
        
        for schema_name, schema_file in schema_files.items():
            schema_path = self.schema_dir / schema_file
            if schema_path.exists():
                with open(schema_path, 'r', encoding='utf-8') as f:
                    schema = json.load(f)
                    self._schemas[schema_name] = schema
                    self._validators[schema_name] = Draft7Validator(schema)
                    logger.info(f"Loaded schema: {schema_name}")
    
    def validate_health_response(self, data: Dict[str, Any]) -> bool:
        """Validate health check response"""
        if not self.enabled or 'health' not in self._validators:
            return True
        try:
            self._validators['health'].validate(data)
            return True
        except ValidationError as e:
            errors = [str(error) for error in self._validators['health'].iter_errors(data)]
            raise SchemaValidationError(f"Health response validation failed: {e.message}", errors=errors)


# Global schema validator instance (singleton)
_schema_validator: Optional[SchemaValidator] = None

def get_schema_validator() -> SchemaValidator:
    """Get global schema validator instance"""
    global _schema_validator
    if _schema_validator is None:
        schema_dir = os.getenv('<SERVICE>_SCHEMA_DIR', f'/app/<service_name>')
        _schema_validator = SchemaValidator(schema_dir=schema_dir)
    return _schema_validator
```

### 9.2 OpenAPI Integration Pattern

**File**: `<service-name>/main.py`

**Pattern**:
```python
def load_openapi_schema() -> Optional[Dict[str, Any]]:
    """Load OpenAPI schema from openapi.yaml file"""
    schema_path = Path(f'/app/<service_name>/openapi.yaml')
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


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    
    # Load OpenAPI schema if available
    openapi_schema = load_openapi_schema()
    
    app = FastAPI(
        title="Lucid <Service Name>",
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
    
    # Add routes with schema validation
    @app.get("/health")
    async def health_check():
        response_data = {...}
        
        # Validate response against schema (graceful degradation)
        try:
            schema_validator = get_schema_validator()
            if schema_validator.enabled:
                schema_validator.validate_health_response(response_data)
        except SchemaValidationError as e:
            logger.warning(f"Health response schema validation failed: {e}")
        
        return response_data
    
    return app
```

### 9.3 Schema Files

**Required Schema Files**:
- `health-schema.json`: Health check response schema
- `<service>-schema.json`: Service data structure schema
- `metrics-schema.json`: Metrics data structure schema
- `openapi.yaml`: OpenAPI 3.0 specification

**Location**: `/app/<service_name>/` (container path)

---

## 10. Error Handling

### 10.1 Graceful Degradation Pattern

**Key Principle**: Service continues operation even if optional components fail

**Pattern**:
```python
# Storage initialization
try:
    self.storage_path.mkdir(parents=True, exist_ok=True)
    logger.info("Storage initialized")
except Exception as e:
    logger.warning(f"Storage unavailable (continuing in degraded mode): {e}")
    self.storage_path = None  # Indicate storage unavailable

# Schema validation
try:
    schema_validator.validate_response(data)
except SchemaValidationError as e:
    logger.warning(f"Schema validation failed: {e}")
    # Continue with response anyway

# Integration client initialization
try:
    self.client = ServiceClient(base_url=url)
except Exception as e:
    logger.warning(f"Failed to initialize client: {e}")
    self.client = None  # Indicate client unavailable
```

### 10.2 Error Message Patterns

**Storage Errors**:
```python
error_msg = (
    f"Parent directory does not exist: {parent_path}. "
    f"Ensure volume mount provides /app/data directory. "
    f"Expected volume mount: /mnt/myssd/Lucid/Lucid/data/<service-name>:/app/data:rw"
)
```

**Permission Errors**:
```python
error_msg = (
    f"Parent directory is not writable: {parent_path}. "
    f"Container runs as user 65532:65532 and needs write access. "
    f"On the host, run: sudo chown -R 65532:65532 /mnt/myssd/Lucid/Lucid/data/<service-name>"
)
```

### 10.3 Exception Classes

**Custom Exceptions**:
```python
class ServiceError(Exception):
    """Base exception for service communication errors"""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code

class ServiceTimeoutError(ServiceError):
    """Exception raised when service call times out"""
    pass

class ServiceNotFoundError(ServiceError):
    """Exception raised when a resource is not found (HTTP 404)"""
    def __init__(self, message: str = "Resource not found", status_code: int = 404):
        super().__init__(message, status_code)

class SchemaValidationError(Exception):
    """Exception raised when schema validation fails"""
    def __init__(self, message: str, errors: Optional[list] = None):
        super().__init__(message)
        self.errors = errors or []
```

---

## 11. Security Patterns

### 11.1 URL Validation Pattern

**Module-Level Regex Patterns**:
```python
import re

# Regex patterns for URL validation (compiled at module level)
LOCALHOST_PATTERN = re.compile(r'\blocalhost\b', re.IGNORECASE)
IP_127_PATTERN = re.compile(r'\b127\.0\.0\.1\b')

# Usage in validators
@field_validator('MONGODB_URL')
@classmethod
def validate_mongodb_url(cls, v: str) -> str:
    """Validate MongoDB URL doesn't use localhost"""
    if v and (LOCALHOST_PATTERN.search(v) or IP_127_PATTERN.search(v)):
        raise ValueError("MONGODB_URL must not use localhost. Use service name (e.g., lucid-mongodb)")
    return v
```

**Key Points**:
- Patterns compiled at module level (performance)
- Word boundaries (`\b`) prevent false positives
- Case-insensitive matching for `localhost`

### 11.2 Storage Path Validation

**Pattern**:
```python
def _initialize_storage(self):
    """Initialize storage directories with validation"""
    try:
        # Verify parent directory exists (from volume mount)
        parent_path = self.storage_path.parent
        if not parent_path.exists():
            error_msg = (
                f"Parent directory does not exist: {parent_path}. "
                f"Ensure volume mount provides /app/data directory."
            )
            logger.warning(error_msg)
            self.storage_path = None  # Graceful degradation
            return
        
        # Check if parent is writable
        if not os.access(parent_path, os.W_OK):
            error_msg = (
                f"Parent directory is not writable: {parent_path}. "
                f"Container runs as user 65532:65532 and needs write access."
            )
            logger.warning(error_msg)
            self.storage_path = None  # Graceful degradation
            return
        
        # Create directories
        self.storage_path.mkdir(parents=True, exist_ok=True, mode=0o700)
        logger.info(f"Storage initialized: {self.storage_path}")
    except Exception as e:
        logger.warning(f"Failed to initialize storage (continuing in degraded mode): {e}")
        self.storage_path = None
```

### 11.3 Lazy Initialization for Security Modules

**Pattern**:
```python
# Global instance (lazy initialization)
_security_module: Optional[SecurityModule] = None

def get_security_module() -> SecurityModule:
    """Get global security module instance (singleton with lazy initialization)"""
    global _security_module
    if _security_module is None:
        try:
            _security_module = SecurityModule()
            logger.info("Security module initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize security module: {e}", exc_info=True)
            # Create degraded instance
            _security_module = SecurityModule.__new__(SecurityModule)
            _security_module.storage_path = None
            # ... initialize with None paths ...
            logger.warning("Security module initialized in degraded mode")
    return _security_module

# Backward compatibility proxy
class _SecurityModuleProxy:
    def __getattr__(self, name):
        return getattr(get_security_module(), name)

security_module = _SecurityModuleProxy()
```

---

## 12. Build and Deployment

### 12.1 Build Command

```bash
docker build \
  --platform linux/arm64 \
  -t pickme/lucid-<service-name>:latest-arm64 \
  -f <service-name>/Dockerfile.<service-name> \
  --build-arg BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ") \
  --build-arg VCS_REF=$(git rev-parse --short HEAD) \
  --build-arg VERSION=1.0.0 \
  .
```

### 12.2 Deployment Command

```bash
docker compose \
  -p lucid-foundation \
  -f configs/docker/docker-compose.foundation.yml \
  -f configs/docker/docker-compose.core.yml \
  -f configs/docker/docker-compose.application.yml \
  --env-file /mnt/myssd/Lucid/Lucid/configs/environment/.env.secrets \
  --env-file /mnt/myssd/Lucid/Lucid/configs/environment/.env.foundation \
  --env-file /mnt/myssd/Lucid/Lucid/configs/environment/.env.core \
  --env-file /mnt/myssd/Lucid/Lucid/configs/environment/.env.application \
  --env-file /mnt/myssd/Lucid/Lucid/configs/environment/.env.<service-name> \
  up -d <service-name>
```

### 12.3 Host Directory Setup

```bash
# Create directories
sudo mkdir -p /mnt/myssd/Lucid/Lucid/data/<service-name>
sudo mkdir -p /mnt/myssd/Lucid/Lucid/logs/<service-name>

# Set ownership (container user: 65532:65532)
sudo chown -R 65532:65532 /mnt/myssd/Lucid/Lucid/data/<service-name>
sudo chown -R 65532:65532 /mnt/myssd/Lucid/Lucid/logs/<service-name>

# Set permissions
sudo chmod -R 755 /mnt/myssd/Lucid/Lucid/data/<service-name>
sudo chmod -R 755 /mnt/myssd/Lucid/Lucid/logs/<service-name>
```

### 12.4 Environment File Creation

```bash
# Copy template to environment file
cp <service-name>/config/env.<service-name>.template \
   /mnt/myssd/Lucid/Lucid/configs/environment/.env.<service-name>

# Edit and fill in values
nano /mnt/myssd/Lucid/Lucid/configs/environment/.env.<service-name>
```

---

## 13. Naming Conventions

### 13.1 Container Naming

- **Container Name**: `<service-name>` (lowercase, hyphen-separated)
- **Service Name**: `<service-name>` (for API responses)
- **Image Name**: `pickme/lucid-<service-name>:latest-arm64`

### 13.2 Module Naming

- **Main Module**: `<service_name>/` (snake_case directory)
- **Controller**: `<service>_controller.py` (snake_case file)
- **Config**: `config.py`
- **Entrypoint**: `entrypoint.py`
- **Integration**: `integration/` directory

### 13.3 Environment Variable Naming

- **Service Prefix**: `<SERVICE>_*` (uppercase, underscore-separated)
- **Examples**: `<SERVICE>_HOST`, `<SERVICE>_PORT`, `<SERVICE>_URL`
- **Storage Paths**: `LUCID_STORAGE_PATH`, `LUCID_LOGS_PATH`
- **Integration URLs**: `<INTEGRATION>_URL`

### 13.4 Schema File Naming

- **Health Schema**: `health-schema.json`
- **Service Schema**: `<service>-schema.json`
- **Metrics Schema**: `metrics-schema.json`
- **OpenAPI Spec**: `openapi.yaml`

---

## 14. Key Design Principles

### 14.1 Always Follow

✅ **Distroless Base**: Use `gcr.io/distroless/python3-debian12:latest`  
✅ **Multi-Stage Build**: Builder + Runtime stages  
✅ **Non-Root User**: `65532:65532`  
✅ **Read-Only Filesystem**: `read_only: true`  
✅ **Environment-Driven Config**: No hardcoded values  
✅ **Graceful Degradation**: Service continues even if optional components fail  
✅ **Module-Level Patterns**: Regex patterns compiled at module level  
✅ **Lazy Initialization**: Optional components initialized on first use  
✅ **Schema Validation**: Optional validation with graceful degradation  
✅ **OpenAPI Integration**: Load OpenAPI spec for documentation  

### 14.2 Never Do

❌ **Hardcode Values**: All configuration from environment variables  
❌ **Import-Time Failures**: Use lazy initialization for optional components  
❌ **Break on Validation**: Schema validation errors don't break service  
❌ **Use localhost**: Always use service names for inter-service communication  
❌ **Inline Regex**: Always use module-level compiled patterns  
❌ **Empty Marker Files**: Marker files must have content  
❌ **Shell Scripts**: Use Python for all runtime operations  

---

## 15. Quick Reference Checklist

### When Creating a New Container:

- [ ] Create directory structure following template
- [ ] Implement `main.py` with lifespan manager
- [ ] Implement `entrypoint.py` with Python path setup
- [ ] Implement `config.py` with Pydantic Settings
- [ ] Create `config.yaml` (optional)
- [ ] Create `openapi.yaml` (optional)
- [ ] Create schema JSON files (optional)
- [ ] Implement `schema_validator.py` (if using schemas)
- [ ] Create `integration/` directory with clients
- [ ] Implement `integration_manager.py`
- [ ] Implement `service_base.py` for integration clients
- [ ] Create `env.<service-name>.template` file
- [ ] Create Dockerfile following template
- [ ] Add service to docker-compose file
- [ ] Create volume definition
- [ ] Add environment variables
- [ ] Set up host directories with correct ownership
- [ ] Test container startup
- [ ] Verify health check works
- [ ] Test graceful degradation scenarios

---

## 16. Example: Complete Service Structure

### 16.1 File Organization

```
<service-name>/
├── Dockerfile.<service-name>
├── requirements.txt
├── <service_name>/
│   ├── __init__.py
│   ├── main.py
│   ├── entrypoint.py
│   ├── config.py
│   ├── <service>_controller.py
│   ├── connection_manager.py (if needed)
│   ├── schema_validator.py (if using schemas)
│   ├── config.yaml
│   ├── openapi.yaml
│   ├── health-schema.json
│   ├── <service>-schema.json
│   ├── metrics-schema.json
│   ├── config/
│   │   ├── env.<service-name>.template
│   │   └── README.md
│   └── integration/
│       ├── __init__.py
│       ├── integration_manager.py
│       ├── service_base.py
│       └── <service>_client.py
```

### 16.2 Docker Compose Entry

```yaml
<service-name>:
  image: pickme/lucid-<service-name>:latest-arm64
  container_name: <service-name>
  restart: unless-stopped
  env_file:
    - /mnt/myssd/Lucid/Lucid/configs/environment/.env.secrets
    - /mnt/myssd/Lucid/Lucid/configs/environment/.env.core
    - /mnt/myssd/Lucid/Lucid/configs/environment/.env.application
    - /mnt/myssd/Lucid/Lucid/configs/environment/.env.foundation
    - /mnt/myssd/Lucid/Lucid/configs/environment/.env.<service-name>
  networks:
    lucid-pi-network: {}
  ports:
    - "<port>:<port>"
  volumes:
    - /mnt/myssd/Lucid/Lucid/data/<service-name>:/app/data:rw
    - /mnt/myssd/Lucid/Lucid/logs/<service-name>:/app/logs:rw
    - <service-name>-cache:/tmp/<service>
  environment:
    - LUCID_ENV=production
    - LUCID_PLATFORM=arm64
    - PROJECT_ROOT=/mnt/myssd/Lucid/Lucid
    - <SERVICE>_HOST=<service-name>
    - <SERVICE>_PORT=<port>
    - <SERVICE>_URL=http://<service-name>:<port>
    - MONGODB_URL=${MONGODB_URL:?MONGODB_URL not set}
    - REDIS_URL=${REDIS_URL:?REDIS_URL not set}
    - LUCID_STORAGE_PATH=/app/data
  user: "65532:65532"
  security_opt:
    - no-new-privileges:true
    - seccomp:unconfined
  cap_drop:
    - ALL
  cap_add:
    - NET_BIND_SERVICE
  read_only: true
  tmpfs:
    - /tmp:noexec,nosuid,size=100m
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
  labels:
    - "lucid.service=<service-name>"
    - "lucid.type=distroless"
    - "lucid.platform=arm64"
    - "lucid.security=hardened"
    - "lucid.cluster=application"
  depends_on:
    tor-proxy:
      condition: service_started
    lucid-mongodb:
      condition: service_healthy
    lucid-redis:
      condition: service_healthy
```

---

## 17. Common Patterns Summary

### 17.1 Configuration Loading

```python
# Priority: Environment Variables > YAML File > Defaults
config_dict = load_yaml_config() if yaml_exists else {}
settings = Settings(**config_dict)  # Environment vars override YAML
```

### 17.2 Integration Client Usage

```python
# Lazy initialization
integration_manager = IntegrationManager(...)
client = integration_manager.client1  # Created on first access

# Health check aggregation
health_status = await integration_manager.health_check_all()

# Graceful shutdown
await integration_manager.close_all()
```

### 17.3 Schema Validation

```python
# Optional validation with graceful degradation
try:
    schema_validator = get_schema_validator()
    if schema_validator.enabled:
        schema_validator.validate_response(response_data)
except SchemaValidationError as e:
    logger.warning(f"Schema validation failed: {e}")
    # Continue anyway
```

### 17.4 Error Handling

```python
# Storage initialization
try:
    initialize_storage()
except Exception as e:
    logger.warning(f"Storage unavailable (degraded mode): {e}")
    storage_path = None  # Indicate unavailable

# Save operations
if storage_path is None:
    logger.debug("Skipping save (storage unavailable)")
    return
# ... save logic ...
```

---

## 18. Related Documentation

- `build/docs/master-docker-design.md` - Master Docker design principles
- `build/docs/mod-design-template.md` - Module design template
- `build/docs/session-api-design.md` - Session API design patterns
- `build/docs/session-pipeline-design.md` - Pipeline design patterns
- `build/docs/dockerfile-design.md` - Dockerfile patterns
- `plan/constants/Dockerfile-copy-pattern.md` - COPY command patterns

---

## 19. Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0.0 | 2025-01-27 | Initial design template creation based on rdp-controller | System |

---

**Last Updated:** 2025-01-27  
**Status:** ACTIVE  
**Maintained By:** Lucid Development Team

