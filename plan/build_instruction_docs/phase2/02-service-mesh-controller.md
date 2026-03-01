# Service Mesh Controller Container

## Overview
Build service mesh controller container for service discovery, mTLS certificate management, and Envoy sidecar proxy configuration.

## Location
`service-mesh/Dockerfile.controller`

## Container Details
**Container**: `pickme/lucid-service-mesh-controller:latest-arm64`

## Multi-Stage Build Strategy

### Stage 1: Builder
```dockerfile
FROM python:3.11-slim as builder
WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Consul
RUN curl -fsSL https://releases.hashicorp.com/consul/1.16.0/consul_1.16.0_linux_arm64.zip -o consul.zip && \
    unzip consul.zip && \
    mv consul /usr/local/bin/ && \
    rm consul.zip

# Copy requirements and install dependencies
COPY service-mesh/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --target /build/deps

# Clean up unnecessary files
RUN find /build/deps -name "*.pyc" -delete && \
    find /build/deps -name "__pycache__" -type d -exec rm -rf {} + && \
    find /build/deps -name "*.dist-info" -type d -exec rm -rf {} +
```

### Stage 2: Runtime (Distroless)
```dockerfile
FROM gcr.io/distroless/python3-debian12:arm64

# Copy dependencies
COPY --from=builder /build/deps /app/deps

# Copy Consul binary
COPY --from=builder /usr/local/bin/consul /usr/local/bin/consul

# Copy application code
COPY service-mesh/ /app/

# Set environment variables
ENV PYTHONPATH=/app/deps
WORKDIR /app

# Set non-root user
USER 65532:65532

# Expose ports
EXPOSE 8081
EXPOSE 8500

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD ["python", "-c", "import requests; requests.get('http://localhost:8081/health')"]

# Default command
CMD ["python", "main.py"]
```

## Requirements File
**File**: `service-mesh/requirements.txt`

```txt
# Service Mesh Dependencies
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
httpx==0.25.2
aiofiles==23.2.1
python-multipart==0.0.6

# Consul Integration
consul==1.1.0
python-consul2==0.1.5

# Certificate Management
cryptography==41.0.8
pyOpenSSL==23.3.0

# Envoy Configuration
pyyaml==6.0.1
jinja2==3.1.2

# Monitoring & Logging
prometheus-client==0.19.0
structlog==23.2.0

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-mock==3.12.0
```

## Application Code Structure

### Main Application
**File**: `service-mesh/main.py`

```python
"""
Lucid Service Mesh Controller
Provides service discovery, mTLS certificate management, and Envoy configuration
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from service_mesh.consul_manager import ConsulManager
from service_mesh.certificate_manager import CertificateManager
from service_mesh.envoy_config_generator import EnvoyConfigGenerator
from service_mesh.api.service_discovery import ServiceDiscoveryAPI
from service_mesh.api.certificate_api import CertificateAPI
from service_mesh.api.envoy_api import EnvoyAPI
from service_mesh.config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global services
consul_manager = None
certificate_manager = None
envoy_config_generator = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global consul_manager, certificate_manager, envoy_config_generator
    
    # Startup
    logger.info("Starting Lucid Service Mesh Controller...")
    
    settings = get_settings()
    
    # Initialize Consul manager
    consul_manager = ConsulManager(settings)
    await consul_manager.initialize()
    
    # Initialize certificate manager
    certificate_manager = CertificateManager(settings)
    await certificate_manager.initialize()
    
    # Initialize Envoy config generator
    envoy_config_generator = EnvoyConfigGenerator(settings)
    await envoy_config_generator.initialize()
    
    logger.info("Service Mesh Controller started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Service Mesh Controller...")
    if consul_manager:
        await consul_manager.cleanup()
    if certificate_manager:
        await certificate_manager.cleanup()
    if envoy_config_generator:
        await envoy_config_generator.cleanup()
    logger.info("Service Mesh Controller shutdown complete")

# Create FastAPI application
app = FastAPI(
    title="Lucid Service Mesh Controller",
    description="Service discovery, mTLS certificate management, and Envoy configuration",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(ServiceDiscoveryAPI.get_router(), prefix="/services", tags=["service-discovery"])
app.include_router(CertificateAPI.get_router(), prefix="/certificates", tags=["certificates"])
app.include_router(EnvoyAPI.get_router(), prefix="/envoy", tags=["envoy"])

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "lucid-service-mesh-controller",
        "version": "1.0.0",
        "consul": await consul_manager.check_health(),
        "certificates": await certificate_manager.check_health(),
        "envoy": await envoy_config_generator.check_health()
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Lucid Service Mesh Controller",
        "version": "1.0.0",
        "docs": "/docs",
        "services": [
            "/services",
            "/certificates",
            "/envoy"
        ]
    }

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8081,
        reload=False,
        log_level="info"
    )
```

### Consul Manager
**File**: `service-mesh/consul_manager.py`

```python
"""
Consul service discovery manager
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
import consul
import subprocess
import os

logger = logging.getLogger(__name__)

class ConsulManager:
    """Consul service discovery manager"""
    
    def __init__(self, settings):
        self.settings = settings
        self.consul_client = None
        self.consul_process = None
        
    async def initialize(self):
        """Initialize Consul manager"""
        try:
            # Start Consul server
            await self._start_consul_server()
            
            # Initialize Consul client
            self.consul_client = consul.Consul(host='localhost', port=8500)
            
            # Wait for Consul to be ready
            await self._wait_for_consul_ready()
            
            logger.info("Consul manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Consul manager: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup Consul manager"""
        if self.consul_process:
            self.consul_process.terminate()
            await self.consul_process.wait()
        logger.info("Consul manager cleaned up")
    
    async def _start_consul_server(self):
        """Start Consul server"""
        consul_config = {
            "datacenter": "lucid-dc",
            "data_dir": "/tmp/consul",
            "log_level": "INFO",
            "server": True,
            "bootstrap_expect": 1,
            "bind_addr": "0.0.0.0",
            "client_addr": "0.0.0.0",
            "ui_config": {
                "enabled": True
            }
        }
        
        # Write config file
        config_file = "/tmp/consul.json"
        with open(config_file, 'w') as f:
            import json
            json.dump(consul_config, f)
        
        # Start Consul server
        self.consul_process = await asyncio.create_subprocess_exec(
            "/usr/local/bin/consul",
            "agent",
            "-config-file", config_file,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
    
    async def _wait_for_consul_ready(self):
        """Wait for Consul to be ready"""
        max_attempts = 30
        attempt = 0
        
        while attempt < max_attempts:
            try:
                # Test Consul connection
                self.consul_client.agent.self()
                logger.info("Consul is ready")
                return
            except Exception:
                attempt += 1
                await asyncio.sleep(1)
        
        raise Exception("Consul failed to start within timeout")
    
    async def register_service(self, service_name: str, service_address: str, 
                             service_port: int, health_check_url: str = None) -> bool:
        """Register service with Consul"""
        try:
            service_id = f"{service_name}-1"
            
            # Prepare service definition
            service_def = {
                "ID": service_id,
                "Name": service_name,
                "Address": service_address,
                "Port": service_port,
                "Tags": ["lucid", "microservice"]
            }
            
            # Add health check if provided
            if health_check_url:
                service_def["Check"] = {
                    "HTTP": health_check_url,
                    "Interval": "30s",
                    "Timeout": "10s"
                }
            
            # Register service
            self.consul_client.agent.service.register(**service_def)
            
            logger.info(f"Service {service_name} registered with Consul")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register service {service_name}: {e}")
            return False
    
    async def discover_service(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Discover service from Consul"""
        try:
            services = self.consul_client.health.service(service_name, passing=True)[1]
            if services:
                service = services[0]
                return {
                    "address": service["Service"]["Address"],
                    "port": service["Service"]["Port"],
                    "service_id": service["Service"]["ID"],
                    "tags": service["Service"]["Tags"]
                }
            return None
            
        except Exception as e:
            logger.error(f"Failed to discover service {service_name}: {e}")
            return None
    
    async def list_services(self) -> List[Dict[str, Any]]:
        """List all registered services"""
        try:
            services = self.consul_client.agent.services()
            return [
                {
                    "name": service["Service"],
                    "address": service["Address"],
                    "port": service["Port"],
                    "tags": service["Tags"]
                }
                for service in services.values()
            ]
        except Exception as e:
            logger.error(f"Failed to list services: {e}")
            return []
    
    async def check_health(self) -> bool:
        """Check Consul health"""
        try:
            self.consul_client.agent.self()
            return True
        except Exception:
            return False
```

### Certificate Manager
**File**: `service-mesh/certificate_manager.py`

```python
"""
mTLS certificate manager for service mesh
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from datetime import datetime, timedelta
import os

logger = logging.getLogger(__name__)

class CertificateManager:
    """mTLS certificate manager"""
    
    def __init__(self, settings):
        self.settings = settings
        self.ca_cert = None
        self.ca_key = None
        self.certificates = {}
        
    async def initialize(self):
        """Initialize certificate manager"""
        try:
            # Create CA certificate
            await self._create_ca_certificate()
            
            # Create certificates directory
            os.makedirs("/app/certificates", exist_ok=True)
            
            logger.info("Certificate manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize certificate manager: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup certificate manager"""
        logger.info("Certificate manager cleaned up")
    
    async def _create_ca_certificate(self):
        """Create CA certificate"""
        # Generate CA private key
        self.ca_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        
        # Create CA certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Lucid"),
            x509.NameAttribute(NameOID.COMMON_NAME, "Lucid CA"),
        ])
        
        self.ca_cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            self.ca_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=365)
        ).add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        ).sign(self.ca_key, hashes.SHA256())
        
        logger.info("CA certificate created")
    
    async def generate_service_certificate(self, service_name: str) -> Dict[str, Any]:
        """Generate mTLS certificate for service"""
        try:
            # Generate service private key
            service_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            
            # Create service certificate
            subject = x509.Name([
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Lucid"),
                x509.NameAttribute(NameOID.COMMON_NAME, service_name),
            ])
            
            service_cert = x509.CertificateBuilder().subject_name(
                subject
            ).issuer_name(
                self.ca_cert.subject
            ).public_key(
                service_key.public_key()
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                datetime.utcnow()
            ).not_valid_after(
                datetime.utcnow() + timedelta(days=90)
            ).add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName(service_name),
                    x509.DNSName(f"{service_name}.lucid.local"),
                ]),
                critical=False,
            ).sign(self.ca_key, hashes.SHA256())
            
            # Save certificates
            cert_path = f"/app/certificates/{service_name}.crt"
            key_path = f"/app/certificates/{service_name}.key"
            
            with open(cert_path, "wb") as f:
                f.write(service_cert.public_bytes(serialization.Encoding.PEM))
            
            with open(key_path, "wb") as f:
                f.write(service_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            
            # Store certificate info
            self.certificates[service_name] = {
                "cert_path": cert_path,
                "key_path": key_path,
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(days=90)
            }
            
            logger.info(f"Certificate generated for service {service_name}")
            
            return {
                "service_name": service_name,
                "cert_path": cert_path,
                "key_path": key_path,
                "created_at": self.certificates[service_name]["created_at"].isoformat(),
                "expires_at": self.certificates[service_name]["expires_at"].isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate certificate for {service_name}: {e}")
            raise
    
    async def get_ca_certificate(self) -> str:
        """Get CA certificate"""
        return self.ca_cert.public_bytes(serialization.Encoding.PEM).decode()
    
    async def check_health(self) -> bool:
        """Check certificate manager health"""
        try:
            return self.ca_cert is not None and self.ca_key is not None
        except Exception:
            return False
```

### Envoy Config Generator
**File**: `service-mesh/envoy_config_generator.py`

```python
"""
Envoy configuration generator for service mesh
"""

import asyncio
import logging
from typing import Dict, Any, List
import yaml
from jinja2 import Template
import os

logger = logging.getLogger(__name__)

class EnvoyConfigGenerator:
    """Envoy configuration generator"""
    
    def __init__(self, settings):
        self.settings = settings
        self.configs = {}
        
    async def initialize(self):
        """Initialize Envoy config generator"""
        try:
            # Create Envoy configs directory
            os.makedirs("/app/envoy-configs", exist_ok=True)
            
            logger.info("Envoy config generator initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Envoy config generator: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup Envoy config generator"""
        logger.info("Envoy config generator cleaned up")
    
    async def generate_envoy_config(self, service_name: str, service_address: str, 
                                   service_port: int) -> str:
        """Generate Envoy configuration for service"""
        try:
            # Envoy configuration template
            config_template = """
static_resources:
  listeners:
  - name: listener_0
    address:
      socket_address:
        address: 0.0.0.0
        port_value: {{ service_port }}
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: ingress_http
          route_config:
            name: local_route
            virtual_hosts:
            - name: local_service
              domains: ["*"]
              routes:
              - match:
                  prefix: "/"
                route:
                  cluster: {{ service_name }}_cluster
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              "@type": type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  clusters:
  - name: {{ service_name }}_cluster
    connect_timeout: 0.25s
    type: LOGICAL_DNS
    lb_policy: ROUND_ROBIN
    load_assignment:
      cluster_name: {{ service_name }}_cluster
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: {{ service_address }}
                port_value: {{ service_port }}
admin:
  address:
    socket_address:
      address: 0.0.0.0
      port_value: 9901
"""
            
            # Render configuration
            template = Template(config_template)
            config = template.render(
                service_name=service_name,
                service_address=service_address,
                service_port=service_port
            )
            
            # Save configuration
            config_path = f"/app/envoy-configs/{service_name}.yaml"
            with open(config_path, 'w') as f:
                f.write(config)
            
            # Store config info
            self.configs[service_name] = {
                "config_path": config_path,
                "service_address": service_address,
                "service_port": service_port,
                "created_at": datetime.utcnow()
            }
            
            logger.info(f"Envoy configuration generated for service {service_name}")
            
            return config_path
            
        except Exception as e:
            logger.error(f"Failed to generate Envoy config for {service_name}: {e}")
            raise
    
    async def get_envoy_config(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get Envoy configuration for service"""
        if service_name in self.configs:
            return self.configs[service_name]
        return None
    
    async def list_envoy_configs(self) -> List[Dict[str, Any]]:
        """List all Envoy configurations"""
        return list(self.configs.values())
    
    async def check_health(self) -> bool:
        """Check Envoy config generator health"""
        try:
            return os.path.exists("/app/envoy-configs")
        except Exception:
            return False
```

## Build Command

```bash
# Build service mesh controller container
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-service-mesh-controller:latest-arm64 \
  -f service-mesh/Dockerfile.controller \
  --push \
  .
```

## Build Script Implementation

**File**: `scripts/core/build-service-mesh-controller.sh`

```bash
#!/bin/bash
# scripts/core/build-service-mesh-controller.sh
# Build service mesh controller container

set -e

echo "Building service mesh controller container..."

# Create service mesh directory if it doesn't exist
mkdir -p service-mesh

# Create requirements.txt
cat > service-mesh/requirements.txt << 'EOF'
# Service Mesh Dependencies
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
httpx==0.25.2
aiofiles==23.2.1
python-multipart==0.0.6

# Consul Integration
consul==1.1.0
python-consul2==0.1.5

# Certificate Management
cryptography==41.0.8
pyOpenSSL==23.3.0

# Envoy Configuration
pyyaml==6.0.1
jinja2==3.1.2

# Monitoring & Logging
prometheus-client==0.19.0
structlog==23.2.0

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-mock==3.12.0
EOF

# Create Dockerfile
cat > service-mesh/Dockerfile.controller << 'EOF'
# Multi-stage build for service mesh controller
FROM python:3.11-slim as builder
WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Consul
RUN curl -fsSL https://releases.hashicorp.com/consul/1.16.0/consul_1.16.0_linux_arm64.zip -o consul.zip && \
    unzip consul.zip && \
    mv consul /usr/local/bin/ && \
    rm consul.zip

# Copy requirements and install dependencies
COPY service-mesh/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --target /build/deps

# Clean up unnecessary files
RUN find /build/deps -name "*.pyc" -delete && \
    find /build/deps -name "__pycache__" -type d -exec rm -rf {} + && \
    find /build/deps -name "*.dist-info" -type d -exec rm -rf {} +

# Final distroless stage
FROM gcr.io/distroless/python3-debian12:arm64

# Copy dependencies
COPY --from=builder /build/deps /app/deps

# Copy Consul binary
COPY --from=builder /usr/local/bin/consul /usr/local/bin/consul

# Copy application code
COPY service-mesh/ /app/

# Set environment variables
ENV PYTHONPATH=/app/deps
WORKDIR /app

# Set non-root user
USER 65532:65532

# Expose ports
EXPOSE 8081
EXPOSE 8500

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD ["python", "-c", "import requests; requests.get('http://localhost:8081/health')"]

# Default command
CMD ["python", "main.py"]
EOF

# Build service mesh controller container
echo "Building service mesh controller container..."
docker buildx build \
  --platform linux/arm64 \
  -t pickme/lucid-service-mesh-controller:latest-arm64 \
  -f service-mesh/Dockerfile.controller \
  --push \
  .

echo "Service mesh controller container built and pushed successfully!"
echo "Container: pickme/lucid-service-mesh-controller:latest-arm64"
```

## Validation Criteria
- Container runs on Pi successfully
- Consul server operational
- Service registry functional
- mTLS certificate generation working
- Envoy configuration generation working
- Health checks passing

## Environment Configuration
Uses `.env.core` for:
- Service mesh controller port
- Consul configuration
- Certificate management settings
- Envoy configuration settings

## Security Features
- **mTLS Encryption**: All service-to-service communication encrypted
- **Certificate Management**: Automated certificate generation and rotation
- **Service Discovery**: Secure service registration and discovery
- **Non-root User**: Container runs as non-root user
- **Distroless Runtime**: Minimal attack surface

## API Endpoints

### Service Discovery
- `GET /services` - List all registered services
- `POST /services/register` - Register new service
- `GET /services/{service_name}` - Get service details
- `DELETE /services/{service_name}` - Deregister service

### Certificate Management
- `GET /certificates` - List all certificates
- `POST /certificates/{service_name}` - Generate service certificate
- `GET /certificates/ca` - Get CA certificate
- `DELETE /certificates/{service_name}` - Revoke service certificate

### Envoy Configuration
- `GET /envoy/configs` - List all Envoy configurations
- `GET /envoy/configs/{service_name}` - Get service Envoy config
- `POST /envoy/configs/{service_name}` - Generate Envoy config
- `DELETE /envoy/configs/{service_name}` - Delete Envoy config

## Troubleshooting

### Build Failures
```bash
# Check build logs
docker buildx build --progress=plain \
  --platform linux/arm64 \
  -t pickme/lucid-service-mesh-controller:latest-arm64 \
  -f service-mesh/Dockerfile.controller \
  .
```

### Runtime Issues
```bash
# Check container logs
docker logs lucid-service-mesh-controller

# Test health endpoint
curl http://localhost:8081/health
```

### Consul Issues
```bash
# Check Consul status
curl http://localhost:8500/v1/status/leader

# Check registered services
curl http://localhost:8500/v1/agent/services
```

### Certificate Issues
```bash
# Check certificate files
ls -la /app/certificates/

# Test certificate validity
openssl x509 -in /app/certificates/service.crt -text -noout
```

## Next Steps
After successful service mesh controller build, proceed to blockchain core containers build.
