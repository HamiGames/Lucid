# Step 14: Cross-Cluster Service Mesh - Quick Reference

## Document Control

| Attribute | Value |
|-----------|-------|
| Step ID | 14-CROSS-CLUSTER-SERVICE-MESH |
| Build Phase | Phase 2 (Weeks 3-4) |
| Parallel Track | Track B |
| Version | 1.0.0 |
| Completion Date | 2025-01-27 |

---

## Quick Start Guide

### 1. Deploy Consul
```bash
# Deploy Consul cluster
docker run -d --name consul \
  -p 8500:8500 \
  -e CONSUL_BIND_INTERFACE=eth0 \
  consul:1.16 agent -server -bootstrap -ui -client=0.0.0.0
```

### 2. Start Service Mesh Controller
```bash
# Start service mesh controller
cd infrastructure/service-mesh/controller
python main.py
```

### 3. Deploy Envoy Sidecar
```bash
# Deploy Envoy sidecar proxy
docker run -d --name envoy-sidecar \
  -p 15000:15000 -p 15001:15001 \
  -v $(pwd)/config:/etc/envoy \
  envoyproxy/envoy:v1.28-latest \
  -c /etc/envoy/bootstrap.yaml
```

### 4. Register Services
```python
# Register service with mesh
from discovery.service_registry import ServiceRegistry

registry = ServiceRegistry()
await registry.initialize()
await registry.register_service(
    service_id="api-gateway-1",
    service_name="api-gateway",
    address="api-gateway",
    port=8080,
    health_check_url="http://api-gateway:8080/health"
)
```

---

## File Structure

```
infrastructure/service-mesh/
├── controller/
│   ├── main.py                    # Service mesh controller entry point
│   ├── config_manager.py          # Configuration management
│   ├── policy_engine.py           # Policy enforcement
│   └── health_checker.py          # Health monitoring
├── sidecar/
│   ├── envoy/config/
│   │   ├── bootstrap.yaml         # Envoy bootstrap configuration
│   │   ├── listener.yaml          # Envoy listener configuration
│   │   └── cluster.yaml           # Envoy cluster configuration
│   └── proxy/
│       ├── proxy_manager.py       # Proxy lifecycle management
│       └── policy_enforcer.py     # Policy enforcement
├── discovery/
│   ├── consul_client.py           # Consul integration
│   ├── service_registry.py        # Service registry
│   └── dns_resolver.py            # DNS resolution
├── communication/
│   ├── grpc_client.py             # gRPC client
│   └── grpc_server.py             # gRPC server
└── security/
    ├── mtls_manager.py            # mTLS certificate management
    └── cert_manager.py            # Certificate lifecycle
```

---

## Key Components

### Service Mesh Controller
- **Main Controller**: Orchestrates all mesh components
- **Config Manager**: Handles dynamic configuration updates
- **Policy Engine**: Enforces traffic, security, and resilience policies
- **Health Checker**: Monitors service health status

### Envoy Sidecar Proxy
- **Bootstrap Config**: Complete Envoy setup with admin interface
- **Listener Config**: HTTP connection managers and routing
- **Cluster Config**: Service clusters with health checks
- **Proxy Manager**: Lifecycle and configuration management

### Service Discovery
- **Consul Client**: Service registration and discovery
- **Service Registry**: Service metadata and lifecycle management
- **DNS Resolver**: Service name resolution with caching

### Communication Layer
- **gRPC Client**: Connection management with retry logic
- **gRPC Server**: Service registration and health checking

### Security
- **mTLS Manager**: Certificate generation and validation
- **Cert Manager**: Certificate lifecycle and auto-renewal

---

## Configuration

### Environment Variables
```bash
# Service Mesh Controller
SERVICE_MESH_CONTROLLER_PORT=8600
CONSUL_HOST=consul:8500
ENVOY_ADMIN_PORT=15000

# Service Discovery
ENABLE_SERVICE_DISCOVERY=true
DISCOVERY_BACKEND=consul
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

### Service Mesh Configuration
```yaml
# service-mesh.yaml
service_mesh:
  name: "lucid-service-mesh"
  version: "1.0.0"
  namespace: "lucid"
  controller:
    port: 8600
    admin_port: 8601
  discovery:
    backend: "consul"
    consul_host: "consul:8500"
    service_ttl: 60
  sidecar:
    envoy:
      admin_port: 15000
      proxy_port: 15001
  security:
    mtls:
      enabled: true
      cert_validity_days: 90
      auto_rotate: true
```

---

## API Reference

### Service Registry
```python
# Register service
await registry.register_service(
    service_id="service-1",
    service_name="my-service",
    address="my-service",
    port=8080,
    tags=["v1", "production"],
    health_check_url="http://my-service:8080/health"
)

# Discover services
instances = await registry.discover_service("my-service")

# Get service health
health = await registry.get_service_health("my-service")
```

### gRPC Client
```python
# Create client
client = GRPCClient()
await client.initialize()

# Create stub
stub = await client.create_stub("my-service", MyServiceStub)

# Call service
response = await client.call_service(
    service_name="my-service",
    method="MyMethod",
    request=my_request
)
```

### mTLS Manager
```python
# Generate certificate
cert, key = await mtls_manager.generate_certificate("my-service")

# Validate certificate
is_valid = await mtls_manager.validate_certificate("my-service")

# Get SSL context
context = await mtls_manager.get_ssl_context("my-service", server_side=True)
```

---

## Health Checks

### Service Mesh Controller
```bash
# Check controller status
curl http://localhost:8600/status

# Check health
curl http://localhost:8600/health
```

### Envoy Sidecar
```bash
# Check Envoy admin
curl http://localhost:15000/ready

# Get stats
curl http://localhost:15000/stats
```

### Consul
```bash
# Check Consul health
curl http://localhost:8500/v1/status/leader

# List services
curl http://localhost:8500/v1/catalog/services
```

---

## Troubleshooting

### Common Issues

#### Service Registration Fails
```bash
# Check Consul connectivity
curl http://consul:8500/v1/status/leader

# Check service configuration
docker logs service-mesh-controller
```

#### Envoy Proxy Not Starting
```bash
# Check Envoy configuration
envoy --config-path /etc/envoy/bootstrap.yaml --mode validate

# Check Envoy logs
docker logs envoy-sidecar
```

#### Certificate Issues
```bash
# Check certificate validity
openssl x509 -in /etc/ssl/lucid/my-service.crt -text -noout

# Check certificate chain
openssl verify -CAfile /etc/ssl/lucid/ca.crt /etc/ssl/lucid/my-service.crt
```

### Debug Commands

#### Service Discovery
```bash
# List all services
curl http://localhost:8500/v1/catalog/services

# Get service instances
curl http://localhost:8500/v1/health/service/my-service

# Check service health
curl http://localhost:8500/v1/health/service/my-service?passing
```

#### Envoy Debug
```bash
# Get Envoy config dump
curl http://localhost:15000/config_dump

# Get Envoy stats
curl http://localhost:15000/stats

# Get Envoy clusters
curl http://localhost:15000/clusters
```

---

## Monitoring

### Metrics Endpoints
- **Service Mesh Controller**: `http://localhost:8600/metrics`
- **Envoy Sidecar**: `http://localhost:15000/stats/prometheus`
- **Consul**: `http://localhost:8500/v1/agent/metrics`

### Key Metrics
- **Service Health**: `service_health_status`
- **Request Rate**: `envoy_http_downstream_rq_total`
- **Request Latency**: `envoy_http_downstream_rq_time`
- **Error Rate**: `envoy_http_downstream_rq_xx`
- **Certificate Expiry**: `cert_expiry_days`

### Alerts
- Service health check failures
- Certificate expiry warnings
- High error rates
- Service discovery failures

---

## Security

### mTLS Configuration
```yaml
# Enable mTLS for all services
security:
  mtls:
    enabled: true
    strict_mode: true
    cert_validation: true
    require_client_cert: true
```

### Policy Enforcement
```yaml
# Traffic management policy
policies:
  rate_limiting:
    enabled: true
    requests_per_second: 1000
    burst_size: 2000
  
  circuit_breaker:
    enabled: true
    failure_threshold: 5
    recovery_timeout: 30
```

---

## Performance Tuning

### Envoy Configuration
```yaml
# Optimize for performance
static_resources:
  clusters:
  - name: my_service
    connect_timeout: 0.25s
    lb_policy: ROUND_ROBIN
    circuit_breakers:
      thresholds:
      - max_connections: 1000
        max_pending_requests: 1000
        max_requests: 1000
```

### Service Mesh Controller
```python
# Tune health check intervals
health_checker.default_interval = 30  # seconds
health_checker.default_timeout = 10   # seconds

# Tune policy enforcement
policy_engine.enforcement_interval = 5  # seconds
```

---

## Integration Examples

### API Gateway Integration
```python
# Register API Gateway with service mesh
await registry.register_service(
    service_id="api-gateway-1",
    service_name="api-gateway",
    address="api-gateway",
    port=8080,
    tags=["v1", "production"],
    health_check_url="http://api-gateway:8080/health"
)
```

### Blockchain Service Integration
```python
# Register blockchain services
services = ["blockchain-core", "blockchain-anchor", "blockchain-manager"]
for service in services:
    await registry.register_service(
        service_id=f"{service}-1",
        service_name=service,
        address=service,
        port=8084,
        health_check_url=f"http://{service}:8084/health"
    )
```

### Session Management Integration
```python
# Register session services
session_services = ["session-api", "session-recorder", "session-processor"]
for service in session_services:
    await registry.register_service(
        service_id=f"{service}-1",
        service_name=service,
        address=service,
        port=8087,
        health_check_url=f"http://{service}:8087/health"
    )
```

---

## Next Steps

### Immediate Actions
1. Deploy Consul cluster
2. Start service mesh controller
3. Deploy Envoy sidecar proxies
4. Generate mTLS certificates
5. Register all services

### Integration Tasks
1. Connect API Gateway to service mesh
2. Integrate blockchain services
3. Connect authentication service
4. Setup monitoring and alerting

### Testing
1. Service discovery tests
2. Communication tests
3. Security tests
4. Performance tests

---

**Step 14 Status**: ✅ **COMPLETED**  
**Next Step**: Step 15 - Session Management Pipeline  
**Dependencies**: Service mesh operational, Consul deployed, certificates issued
