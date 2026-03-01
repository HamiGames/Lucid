# Cluster 10: Cross-Cluster Integration - Detailed Build Guide

## Document Control

| Attribute | Value |
|-----------|-------|
| Cluster ID | 10-CROSS-CLUSTER-INTEGRATION |
| Build Phase | Phase 2 (Weeks 3-4) |
| Parallel Track | Track B |
| Version | 1.0.0 |

---

## Cluster Overview

### Service Type
Service mesh and inter-cluster communication infrastructure

### Key Components
- Service mesh controller
- Beta sidecar proxy (Envoy)
- Service discovery (Consul/etcd)
- gRPC communication
- mTLS certificate management
- Metrics and tracing

### Dependencies
- Cluster 09 (Authentication): mTLS cert validation

---

## MVP Files (35 files, ~4,500 lines)

### Service Mesh Controller (8 files, ~1,200 lines)
1. `service-mesh/controller/main.py` (200) - Controller entry
2. `service-mesh/controller/config_manager.py` (300) - Config management
3. `service-mesh/controller/policy_engine.py` (280) - Policy enforcement
4. `service-mesh/controller/health_checker.py` (220) - Health monitoring

### Beta Sidecar Proxy (8 files, ~1,500 lines)
5. `service-mesh/sidecar/envoy/config/bootstrap.yaml` (300) - Envoy bootstrap
6. `service-mesh/sidecar/envoy/config/listener.yaml` (250) - Listeners
7. `service-mesh/sidecar/envoy/config/cluster.yaml` (250) - Clusters
8. `service-mesh/sidecar/proxy/proxy_manager.py` (350) - Proxy management
9. `service-mesh/sidecar/proxy/policy_enforcer.py` (300) - Policy enforcement

### Service Discovery (6 files, ~900 lines)
10. `service-mesh/discovery/consul_client.py` (300) - Consul integration
11. `service-mesh/discovery/service_registry.py` (280) - Service registration
12. `service-mesh/discovery/dns_resolver.py` (200) - DNS resolution

### Communication Layer (6 files, ~900 lines)
13. `service-mesh/communication/grpc_client.py` (250) - gRPC client
14. `service-mesh/communication/grpc_server.py` (280) - gRPC server
15. `service-mesh/communication/message_queue.py` (220) - Message queue
16. `service-mesh/communication/event_stream.py` (150) - Event streaming

### Security (5 files, ~700 lines)
17. `service-mesh/security/mtls_manager.py` (280) - mTLS management
18. `service-mesh/security/cert_manager.py` (250) - Certificate management
19. `service-mesh/security/auth_provider.py` (170) - Auth provider

### Configuration (7 files, ~300 lines)
20-26. Docker configs, K8s manifests, network policies

---

## Build Sequence (10 days)

### Days 1-3: Service Discovery
- Setup Consul cluster
- Implement service registration
- Build DNS resolver
- Test service discovery

### Days 4-5: Beta Sidecar Proxy
- Configure Envoy proxy
- Setup listeners and clusters
- Implement policy enforcement

### Days 6-7: gRPC Communication
- Build gRPC client/server
- Implement message queue
- Add event streaming

### Days 8-9: Security & mTLS
- Implement mTLS manager
- Setup certificate rotation
- Test secure communication

### Day 10: Integration & Testing
- Full service mesh testing
- Performance testing
- Documentation

---

## Key Implementations

### Service Registry
```python
# service-mesh/discovery/service_registry.py (280 lines)
import consul.aio

class ServiceRegistry:
    def __init__(self, consul_host: str):
        self.consul = consul.aio.Consul(host=consul_host)
        
    async def register_service(
        self,
        service_id: str,
        service_name: str,
        address: str,
        port: int,
        tags: list = None
    ):
        await self.consul.agent.service.register(
            name=service_name,
            service_id=service_id,
            address=address,
            port=port,
            tags=tags or [],
            check=consul.Check.http(
                url=f"http://{address}:{port}/health",
                interval="30s",
                timeout="10s"
            )
        )
        
    async def discover_service(self, service_name: str):
        _, services = await self.consul.health.service(
            service_name,
            passing=True  # Only healthy services
        )
        return services
```

### gRPC Server
```python
# service-mesh/communication/grpc_server.py (280 lines)
import grpc
from concurrent import futures

class GRPCServer:
    def __init__(self, port: int):
        self.server = grpc.aio.server(
            futures.ThreadPoolExecutor(max_workers=10)
        )
        self.port = port
        
    async def start(self):
        self.server.add_insecure_port(f'[::]:{self.port}')
        await self.server.start()
        
    async def add_service(self, servicer, add_servicer_func):
        add_servicer_func(servicer, self.server)
```

### mTLS Manager
```python
# service-mesh/security/mtls_manager.py (280 lines)
import ssl
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa

class mTLSManager:
    async def generate_certificate(
        self,
        service_name: str,
        validity_days: int = 90
    ):
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        
        # Generate certificate
        subject = x509.Name([
            x509.NameAttribute(
                NameOID.COMMON_NAME, 
                f"{service_name}.lucid.internal"
            )
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            subject
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=validity_days)
        ).sign(private_key, hashes.SHA256())
        
        return cert, private_key
```

---

## Envoy Configuration

### Bootstrap Config
```yaml
# service-mesh/sidecar/envoy/config/bootstrap.yaml (300 lines)
static_resources:
  listeners:
  - name: listener_0
    address:
      socket_address:
        address: 0.0.0.0
        port_value: 15001  # Sidecar proxy port
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: ingress_http
          route_config:
            name: local_route
            virtual_hosts:
            - name: backend
              domains: ["*"]
              routes:
              - match:
                  prefix: "/"
                route:
                  cluster: local_service
          http_filters:
          - name: envoy.filters.http.router

  clusters:
  - name: local_service
    connect_timeout: 0.25s
    type: STATIC
    lb_policy: ROUND_ROBIN
    load_assignment:
      cluster_name: local_service
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: 127.0.0.1
                port_value: 8080  # Local service port
```

---

## Service Mesh Architecture

### Beta Sidecar Pattern
```
┌─────────────────────────────────────┐
│         Service Container           │
│  ┌─────────────┐  ┌──────────────┐  │
│  │   App       │  │ Beta Sidecar │  │
│  │  (e.g. API  │←→│   (Envoy)    │  │
│  │  Gateway)   │  │              │  │
│  └─────────────┘  └──────┬───────┘  │
└────────────────────────│─────────────┘
                         │
                         ↓
            ┌────────────────────────┐
            │   Service Mesh         │
            │   Controller           │
            │   (Policy Enforcement) │
            └────────────────────────┘
```

### Service Plane Isolation
```
┌─────────────────────────────────────┐
│          Ops Plane                  │
│  (Management & Monitoring)          │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│         Chain Plane                 │
│  (Blockchain Operations)            │
│  - lucid_blocks ONLY                │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│        Wallet Plane                 │
│  (TRON Payment ONLY)                │
│  - Isolated Network                 │
└─────────────────────────────────────┘
```

---

## Environment Variables
```bash
# Service Mesh Controller
SERVICE_MESH_CONTROLLER_PORT=8500
CONSUL_HOST=consul:8500
ENVOY_ADMIN_PORT=15000

# Service Discovery
ENABLE_SERVICE_DISCOVERY=true
DISCOVERY_BACKEND=consul  # or etcd
SERVICE_REGISTRY_TTL=60

# mTLS Configuration
ENABLE_MTLS=true
CERT_VALIDITY_DAYS=90
AUTO_ROTATE_CERTS=true

# Metrics
ENABLE_METRICS=true
METRICS_PORT=9090
TRACING_ENABLED=true
```

---

## Docker Compose
```yaml
version: '3.8'
services:
  consul:
    image: consul:1.16
    container_name: lucid-consul
    ports:
      - "8500:8500"
    command: agent -server -bootstrap -ui -client=0.0.0.0
    networks:
      - lucid-network

  service-mesh-controller:
    build:
      context: .
      dockerfile: Dockerfile.controller
    ports:
      - "8600:8600"
    environment:
      - CONSUL_HOST=consul:8500
    depends_on:
      - consul
    networks:
      - lucid-network
```

---

## Testing Strategy

### Service Discovery Tests
- Service registration
- Service deregistration
- Health check monitoring
- DNS resolution

### Communication Tests
- gRPC client/server
- Message queue
- Event streaming
- Circuit breaker

### Security Tests
- mTLS handshake
- Certificate validation
- Certificate rotation
- Authorization

---

## Success Criteria

- [ ] Consul cluster operational
- [ ] Service registration working
- [ ] Beta sidecar proxies deployed
- [ ] gRPC communication functional
- [ ] mTLS enabled and tested
- [ ] Service discovery resolving services
- [ ] Metrics collection working
- [ ] All services in mesh

---

**Build Time**: 10 days (2 developers)  
**Dependencies**: Auth service for mTLS validation

