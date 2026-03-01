# Cross-Cluster Integration Deployment & Operations

## Overview

This document provides comprehensive deployment and operational guidance for the Cross-Cluster Integration cluster, including Docker configurations, Kubernetes deployments, health monitoring, troubleshooting, and disaster recovery procedures.

## Distroless Docker Configurations

### 1. Service Mesh Controller

```dockerfile
# deployments/docker/Dockerfile.service-mesh-controller
# Path: lucid/deployments/docker/Dockerfile.service-mesh-controller

# ============================================================================
# Stage 1: Build Stage
# ============================================================================
FROM python:3.11-slim AS builder

LABEL maintainer="Lucid Development Team <dev@lucid.onion>"
LABEL description="Service Mesh Controller - Build Stage"

WORKDIR /build

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        make \
        libffi-dev \
        libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements/service-mesh-controller.txt requirements.txt

# Install Python dependencies to user site-packages
RUN pip install --no-cache-dir --user -r requirements.txt

# ============================================================================
# Stage 2: Runtime Stage - Distroless
# ============================================================================
FROM gcr.io/distroless/python3-debian12:nonroot

LABEL maintainer="Lucid Development Team <dev@lucid.onion>"
LABEL description="Service Mesh Controller - Distroless Runtime"
LABEL version="1.0.0"

# Copy Python dependencies from builder
COPY --from=builder --chown=nonroot:nonroot /root/.local /home/nonroot/.local

# Copy application code
COPY --chown=nonroot:nonroot service-mesh/controller /app/controller
COPY --chown=nonroot:nonroot service-mesh/discovery /app/discovery
COPY --chown=nonroot:nonroot service-mesh/security /app/security
COPY --chown=nonroot:nonroot service-mesh/monitoring /app/monitoring
COPY --chown=nonroot:nonroot service-mesh/communication /app/communication
COPY --chown=nonroot:nonroot config/service-mesh-config.yaml /app/config/service-mesh-config.yaml

# Set environment variables
ENV PYTHONPATH=/app \
    PATH=/home/nonroot/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    SERVICE_MESH_CONFIG=/app/config/service-mesh-config.yaml

# Set working directory
WORKDIR /app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["/usr/bin/python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/health').read()"]

# Expose ports
EXPOSE 8080 8081

# Run as non-root user (distroless default: nonroot)
USER nonroot:nonroot

# Run the controller
ENTRYPOINT ["/usr/bin/python3", "-m", "controller.main"]
CMD ["--config", "/app/config/service-mesh-config.yaml"]
```

**Requirements File:**
```txt
# requirements/service-mesh-controller.txt
# Path: lucid/requirements/service-mesh-controller.txt

# Core dependencies
python-consul==1.1.0
grpcio==1.60.0
grpcio-tools==1.60.0
protobuf==4.25.1

# Monitoring
prometheus-client==0.19.0
opentelemetry-api==1.22.0
opentelemetry-sdk==1.22.0
opentelemetry-exporter-jaeger==1.22.0

# Security
cryptography==41.0.7
pyjwt==2.8.0

# Utilities
pyyaml==6.0.1
requests==2.31.0
```

### 2. Envoy Sidecar Proxy

```dockerfile
# deployments/docker/Dockerfile.envoy-sidecar
# Path: lucid/deployments/docker/Dockerfile.envoy-sidecar

# ============================================================================
# Use official Envoy distroless image
# ============================================================================
FROM envoyproxy/envoy:distroless-v1.28-latest

LABEL maintainer="Lucid Development Team <dev@lucid.onion>"
LABEL description="Envoy Beta Sidecar Proxy - Distroless"
LABEL version="1.28.0"

# Copy Envoy configuration files
COPY --chown=nonroot:nonroot service-mesh/sidecar/envoy/config/bootstrap.yaml /etc/envoy/envoy.yaml
COPY --chown=nonroot:nonroot service-mesh/sidecar/envoy/config/listener.yaml /etc/envoy/listener.yaml
COPY --chown=nonroot:nonroot service-mesh/sidecar/envoy/config/cluster.yaml /etc/envoy/cluster.yaml

# Note: Certificates will be mounted as volumes at runtime
# Expected mount path: /etc/certs/

# Health check
HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=3 \
    CMD ["/usr/local/bin/envoy", "--config-path", "/etc/envoy/envoy.yaml", "--mode", "validate"]

# Expose ports
EXPOSE 15001 9901

# Run as non-root user
USER nonroot:nonroot

# Run Envoy
ENTRYPOINT ["/usr/local/bin/envoy"]
CMD ["-c", "/etc/envoy/envoy.yaml", \
     "--service-cluster", "lucid-sidecar", \
     "--service-node", "lucid-sidecar-node", \
     "--log-level", "info"]
```

### 3. Consul Service Discovery

```dockerfile
# deployments/docker/Dockerfile.consul
# Path: lucid/deployments/docker/Dockerfile.consul

# ============================================================================
# Stage 1: Get Consul Binary
# ============================================================================
FROM consul:1.17 AS consul-binary

# ============================================================================
# Stage 2: Runtime Stage - Distroless
# ============================================================================
FROM gcr.io/distroless/static-debian12:nonroot

LABEL maintainer="Lucid Development Team <dev@lucid.onion>"
LABEL description="Consul Service Discovery - Distroless"
LABEL version="1.17.0"

# Copy Consul binary from official image
COPY --from=consul-binary --chown=nonroot:nonroot /bin/consul /bin/consul

# Copy configuration
COPY --chown=nonroot:nonroot config/consul/consul.json /consul/config/consul.json
COPY --chown=nonroot:nonroot config/consul/acl.json /consul/config/acl.json

# Note: Data directory will be mounted as volume
# Expected mount path: /consul/data

# Expose ports
# 8300: Server RPC
# 8301: Serf LAN
# 8302: Serf WAN
# 8500: HTTP API
# 8600: DNS
EXPOSE 8300 8301 8302 8500 8600

# Run as non-root user
USER nonroot:nonroot

# Run Consul
ENTRYPOINT ["/bin/consul"]
CMD ["agent", "-config-dir=/consul/config"]
```

**Consul Configuration:**
```json
{
  "datacenter": "dc1",
  "data_dir": "/consul/data",
  "log_level": "INFO",
  "node_name": "consul-server-01",
  "server": true,
  "bootstrap_expect": 1,
  "ui": true,
  "client_addr": "0.0.0.0",
  "bind_addr": "0.0.0.0",
  "advertise_addr": "{{ GetInterfaceIP \"eth0\" }}",
  "enable_script_checks": false,
  "enable_local_script_checks": false,
  "encrypt": "CONSUL_GOSSIP_ENCRYPTION_KEY_HERE",
  "verify_incoming": true,
  "verify_outgoing": true,
  "verify_server_hostname": true,
  "ca_file": "/consul/config/certs/ca.crt",
  "cert_file": "/consul/config/certs/consul.crt",
  "key_file": "/consul/config/certs/consul.key",
  "ports": {
    "http": 8500,
    "https": 8501,
    "grpc": 8502,
    "dns": 8600
  },
  "connect": {
    "enabled": true
  },
  "telemetry": {
    "prometheus_retention_time": "60s",
    "disable_hostname": false
  }
}
```

### 4. etcd (Alternative Service Discovery)

```dockerfile
# deployments/docker/Dockerfile.etcd
# Path: lucid/deployments/docker/Dockerfile.etcd

# ============================================================================
# Stage 1: Get etcd Binary
# ============================================================================
FROM gcr.io/etcd-development/etcd:v3.5.11 AS etcd-binary

# ============================================================================
# Stage 2: Runtime Stage - Distroless
# ============================================================================
FROM gcr.io/distroless/static-debian12:nonroot

LABEL maintainer="Lucid Development Team <dev@lucid.onion>"
LABEL description="etcd Service Discovery - Distroless"
LABEL version="3.5.11"

# Copy etcd binaries
COPY --from=etcd-binary --chown=nonroot:nonroot /usr/local/bin/etcd /usr/local/bin/etcd
COPY --from=etcd-binary --chown=nonroot:nonroot /usr/local/bin/etcdctl /usr/local/bin/etcdctl
COPY --from=etcd-binary --chown=nonroot:nonroot /usr/local/bin/etcdutl /usr/local/bin/etcdutl

# Expose ports
# 2379: Client requests
# 2380: Peer communication
EXPOSE 2379 2380

# Run as non-root user
USER nonroot:nonroot

# Run etcd
ENTRYPOINT ["/usr/local/bin/etcd"]
CMD ["--name", "etcd-01", \
     "--data-dir", "/etcd-data", \
     "--listen-client-urls", "http://0.0.0.0:2379", \
     "--advertise-client-urls", "http://0.0.0.0:2379", \
     "--listen-peer-urls", "http://0.0.0.0:2380", \
     "--initial-advertise-peer-urls", "http://0.0.0.0:2380"]
```

## Docker Compose Configuration

### Complete Service Mesh Stack

```yaml
# docker-compose.yml
# Path: lucid/docker-compose.service-mesh.yml

version: '3.8'

networks:
  lucid-mesh:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
  
  lucid-ops:
    driver: bridge
    internal: false
  
  lucid-chain:
    driver: bridge
    internal: true
  
  lucid-wallet:
    driver: bridge
    internal: true

volumes:
  consul-data:
    driver: local
  etcd-data:
    driver: local
  rabbitmq-data:
    driver: local
  prometheus-data:
    driver: local
  jaeger-data:
    driver: local

services:
  # ============================================================================
  # Service Discovery - Consul
  # ============================================================================
  consul:
    build:
      context: .
      dockerfile: deployments/docker/Dockerfile.consul
    image: lucid/consul:1.17-distroless
    container_name: lucid-consul
    hostname: consul
    networks:
      - lucid-mesh
    ports:
      - "8500:8500"  # HTTP API
      - "8600:8600"  # DNS
    volumes:
      - consul-data:/consul/data
      - ./config/consul:/consul/config:ro
      - ./certs/consul:/consul/config/certs:ro
    environment:
      - CONSUL_BIND_INTERFACE=eth0
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "/bin/consul", "members"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 20s

  # ============================================================================
  # Service Discovery - etcd (Alternative)
  # ============================================================================
  etcd:
    build:
      context: .
      dockerfile: deployments/docker/Dockerfile.etcd
    image: lucid/etcd:3.5-distroless
    container_name: lucid-etcd
    hostname: etcd
    networks:
      - lucid-mesh
    ports:
      - "2379:2379"  # Client
      - "2380:2380"  # Peer
    volumes:
      - etcd-data:/etcd-data
    environment:
      - ETCD_NAME=etcd-01
      - ETCD_DATA_DIR=/etcd-data
      - ETCD_LISTEN_CLIENT_URLS=http://0.0.0.0:2379
      - ETCD_ADVERTISE_CLIENT_URLS=http://etcd:2379
      - ETCD_LISTEN_PEER_URLS=http://0.0.0.0:2380
      - ETCD_INITIAL_ADVERTISE_PEER_URLS=http://etcd:2380
      - ETCD_INITIAL_CLUSTER=etcd-01=http://etcd:2380
      - ETCD_INITIAL_CLUSTER_STATE=new
      - ETCD_INITIAL_CLUSTER_TOKEN=lucid-etcd-cluster
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "/usr/local/bin/etcdctl", "endpoint", "health"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ============================================================================
  # Service Mesh Controller
  # ============================================================================
  service-mesh-controller:
    build:
      context: .
      dockerfile: deployments/docker/Dockerfile.service-mesh-controller
    image: lucid/service-mesh-controller:1.0-distroless
    container_name: lucid-service-mesh-controller
    hostname: service-mesh-controller
    networks:
      - lucid-mesh
    ports:
      - "8080:8080"  # HTTP API
      - "8081:8081"  # gRPC
    volumes:
      - ./config/service-mesh-config.yaml:/app/config/service-mesh-config.yaml:ro
      - ./certs/service-mesh:/etc/certs:ro
    environment:
      - SERVICE_MESH_CONFIG=/app/config/service-mesh-config.yaml
      - CONSUL_HOST=consul
      - CONSUL_PORT=8500
      - LOG_LEVEL=info
    depends_on:
      consul:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # ============================================================================
  # Message Queue - RabbitMQ
  # ============================================================================
  rabbitmq:
    image: rabbitmq:3.12-management-alpine
    container_name: lucid-rabbitmq
    hostname: rabbitmq
    networks:
      - lucid-mesh
    ports:
      - "5672:5672"   # AMQP
      - "15672:15672" # Management UI
    volumes:
      - rabbitmq-data:/var/lib/rabbitmq
      - ./config/rabbitmq:/etc/rabbitmq:ro
    environment:
      - RABBITMQ_DEFAULT_USER=lucid
      - RABBITMQ_DEFAULT_PASS=${RABBITMQ_PASSWORD}
      - RABBITMQ_DEFAULT_VHOST=lucid
      - RABBITMQ_ERLANG_COOKIE=${RABBITMQ_ERLANG_COOKIE}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "check_running"]
      interval: 30s
      timeout: 10s
      retries: 5

  # ============================================================================
  # Monitoring - Prometheus
  # ============================================================================
  prometheus:
    image: prom/prometheus:v2.48.0
    container_name: lucid-prometheus
    hostname: prometheus
    networks:
      - lucid-mesh
    ports:
      - "9090:9090"
    volumes:
      - prometheus-data:/prometheus
      - ./config/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./config/prometheus/alerts.yml:/etc/prometheus/alerts.yml:ro
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'
      - '--storage.tsdb.retention.time=30d'
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:9090/-/healthy"]
      interval: 30s
      timeout: 10s
      retries: 3

  # ============================================================================
  # Monitoring - Grafana
  # ============================================================================
  grafana:
    image: grafana/grafana:10.2.2
    container_name: lucid-grafana
    hostname: grafana
    networks:
      - lucid-mesh
    ports:
      - "3000:3000"
    volumes:
      - ./config/grafana/dashboards:/etc/grafana/provisioning/dashboards:ro
      - ./config/grafana/datasources:/etc/grafana/provisioning/datasources:ro
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}
      - GF_USERS_ALLOW_SIGN_UP=false
    depends_on:
      - prometheus
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:3000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # ============================================================================
  # Tracing - Jaeger
  # ============================================================================
  jaeger:
    image: jaegertracing/all-in-one:1.52
    container_name: lucid-jaeger
    hostname: jaeger
    networks:
      - lucid-mesh
    ports:
      - "5775:5775/udp"   # Zipkin compact
      - "6831:6831/udp"   # Jaeger compact
      - "6832:6832/udp"   # Jaeger binary
      - "5778:5778"       # Serve configs
      - "16686:16686"     # Web UI
      - "14268:14268"     # Jaeger collector
      - "14250:14250"     # gRPC
      - "9411:9411"       # Zipkin
    environment:
      - COLLECTOR_ZIPKIN_HOST_PORT=:9411
      - SPAN_STORAGE_TYPE=badger
      - BADGER_EPHEMERAL=false
      - BADGER_DIRECTORY_VALUE=/badger/data
      - BADGER_DIRECTORY_KEY=/badger/key
    volumes:
      - jaeger-data:/badger
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:16686"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Environment Variables

```bash
# .env
# Path: lucid/.env.service-mesh

# RabbitMQ
RABBITMQ_PASSWORD=secure_password_here
RABBITMQ_ERLANG_COOKIE=secure_erlang_cookie_here

# Grafana
GRAFANA_ADMIN_PASSWORD=secure_grafana_password_here

# Consul
CONSUL_GOSSIP_KEY=secure_gossip_key_here

# Service Mesh
SERVICE_MESH_JWT_SECRET=secure_jwt_secret_here
```

## Kubernetes Deployments

### 1. Service Mesh Controller Deployment

```yaml
# deployments/kubernetes/service-mesh-controller.yaml
# Path: lucid/deployments/kubernetes/service-mesh-controller.yaml

apiVersion: v1
kind: Namespace
metadata:
  name: lucid-service-mesh
  labels:
    name: lucid-service-mesh

---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: service-mesh-controller
  namespace: lucid-service-mesh

---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: service-mesh-controller
rules:
- apiGroups: [""]
  resources: ["services", "endpoints", "pods"]
  verbs: ["get", "list", "watch"]
- apiGroups: [""]
  resources: ["configmaps"]
  verbs: ["get", "list", "watch", "create", "update"]
- apiGroups: ["networking.k8s.io"]
  resources: ["networkpolicies"]
  verbs: ["get", "list", "watch", "create", "update"]

---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: service-mesh-controller
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: service-mesh-controller
subjects:
- kind: ServiceAccount
  name: service-mesh-controller
  namespace: lucid-service-mesh

---
apiVersion: v1
kind: ConfigMap
metadata:
  name: service-mesh-config
  namespace: lucid-service-mesh
data:
  service-mesh-config.yaml: |
    serviceMesh:
      version: "1.0.0"
      controller:
        host: "0.0.0.0"
        port: 8080
        logLevel: "info"
      discovery:
        provider: "consul"
        consul:
          host: "consul.lucid-service-mesh.svc.cluster.local"
          port: 8500
      security:
        mtls:
          enabled: true
          certPath: "/etc/certs/tls.crt"
          keyPath: "/etc/certs/tls.key"
          caPath: "/etc/certs/ca.crt"

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: service-mesh-controller
  namespace: lucid-service-mesh
  labels:
    app: service-mesh-controller
    component: controller
spec:
  replicas: 3
  selector:
    matchLabels:
      app: service-mesh-controller
  template:
    metadata:
      labels:
        app: service-mesh-controller
        component: controller
    spec:
      serviceAccountName: service-mesh-controller
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        fsGroup: 65532
      containers:
      - name: controller
        image: lucid/service-mesh-controller:1.0-distroless
        imagePullPolicy: IfNotPresent
        ports:
        - name: http
          containerPort: 8080
          protocol: TCP
        - name: grpc
          containerPort: 8081
          protocol: TCP
        env:
        - name: SERVICE_MESH_CONFIG
          value: "/app/config/service-mesh-config.yaml"
        - name: CONSUL_HOST
          value: "consul.lucid-service-mesh.svc.cluster.local"
        - name: CONSUL_PORT
          value: "8500"
        - name: LOG_LEVEL
          value: "info"
        volumeMounts:
        - name: config
          mountPath: /app/config
          readOnly: true
        - name: certs
          mountPath: /etc/certs
          readOnly: true
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
      volumes:
      - name: config
        configMap:
          name: service-mesh-config
      - name: certs
        secret:
          secretName: service-mesh-certs

---
apiVersion: v1
kind: Service
metadata:
  name: service-mesh-controller
  namespace: lucid-service-mesh
  labels:
    app: service-mesh-controller
spec:
  type: ClusterIP
  selector:
    app: service-mesh-controller
  ports:
  - name: http
    port: 8080
    targetPort: 8080
    protocol: TCP
  - name: grpc
    port: 8081
    targetPort: 8081
    protocol: TCP

---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: service-mesh-controller
  namespace: lucid-service-mesh
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: service-mesh-controller
```

### 2. Consul Deployment

```yaml
# deployments/kubernetes/consul.yaml
# Path: lucid/deployments/kubernetes/consul.yaml

apiVersion: v1
kind: Service
metadata:
  name: consul
  namespace: lucid-service-mesh
  labels:
    app: consul
spec:
  type: ClusterIP
  clusterIP: None
  selector:
    app: consul
  ports:
  - name: http
    port: 8500
    targetPort: 8500
  - name: dns
    port: 8600
    targetPort: 8600
  - name: rpc
    port: 8300
    targetPort: 8300
  - name: serf-lan
    port: 8301
    targetPort: 8301
  - name: serf-wan
    port: 8302
    targetPort: 8302

---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: consul
  namespace: lucid-service-mesh
  labels:
    app: consul
spec:
  serviceName: consul
  replicas: 3
  selector:
    matchLabels:
      app: consul
  template:
    metadata:
      labels:
        app: consul
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        fsGroup: 65532
      containers:
      - name: consul
        image: lucid/consul:1.17-distroless
        imagePullPolicy: IfNotPresent
        ports:
        - name: http
          containerPort: 8500
        - name: dns
          containerPort: 8600
        - name: rpc
          containerPort: 8300
        - name: serf-lan
          containerPort: 8301
        - name: serf-wan
          containerPort: 8302
        volumeMounts:
        - name: data
          mountPath: /consul/data
        - name: config
          mountPath: /consul/config
          readOnly: true
        - name: certs
          mountPath: /consul/config/certs
          readOnly: true
        resources:
          requests:
            cpu: 200m
            memory: 256Mi
          limits:
            cpu: 1000m
            memory: 1Gi
        livenessProbe:
          exec:
            command:
            - /bin/consul
            - members
          initialDelaySeconds: 30
          periodSeconds: 10
      volumes:
      - name: config
        configMap:
          name: consul-config
      - name: certs
        secret:
          secretName: consul-certs
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 10Gi
```

## Health Monitoring

### Prometheus Configuration

```yaml
# config/prometheus/prometheus.yml
# Path: lucid/config/prometheus/prometheus.yml

global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'lucid'
    environment: 'production'

alerting:
  alertmanagers:
  - static_configs:
    - targets:
      - 'alertmanager:9093'

rule_files:
  - '/etc/prometheus/alerts.yml'

scrape_configs:
  # Service Mesh Controller
  - job_name: 'service-mesh-controller'
    static_configs:
    - targets: ['service-mesh-controller:8080']
    metrics_path: '/metrics'
  
  # Consul
  - job_name: 'consul'
    static_configs:
    - targets: ['consul:8500']
    metrics_path: '/v1/agent/metrics'
    params:
      format: ['prometheus']
  
  # Envoy Sidecars
  - job_name: 'envoy-sidecars'
    kubernetes_sd_configs:
    - role: pod
    relabel_configs:
    - source_labels: [__meta_kubernetes_pod_container_name]
      action: keep
      regex: envoy-sidecar
    - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
      action: keep
      regex: true
    - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_port]
      action: replace
      target_label: __address__
      regex: ([^:]+)(?::\d+)?;(\d+)
      replacement: $1:$2
  
  # RabbitMQ
  - job_name: 'rabbitmq'
    static_configs:
    - targets: ['rabbitmq:15692']
    metrics_path: '/metrics'
```

### Alert Rules

```yaml
# config/prometheus/alerts.yml
# Path: lucid/config/prometheus/alerts.yml

groups:
- name: service_mesh_alerts
  interval: 30s
  rules:
  # Service Discovery
  - alert: ServiceDiscoveryDown
    expr: up{job="consul"} == 0
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "Service discovery is down"
      description: "Consul service discovery has been down for more than 2 minutes"
  
  # Service Mesh Controller
  - alert: ServiceMeshControllerDown
    expr: up{job="service-mesh-controller"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Service mesh controller is down"
      description: "Service mesh controller has been down for more than 1 minute"
  
  # High Latency
  - alert: HighServiceDiscoveryLatency
    expr: histogram_quantile(0.95, rate(service_discovery_latency_seconds_bucket[5m])) > 0.1
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High service discovery latency"
      description: "Service discovery P95 latency is above 100ms for more than 5 minutes"
  
  # Circuit Breaker
  - alert: CircuitBreakerOpen
    expr: circuit_breaker_state{state="open"} > 0
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "Circuit breaker is open"
      description: "Circuit breaker for {{ $labels.service }} has been open for more than 2 minutes"
  
  # mTLS Failures
  - alert: MTLSAuthenticationFailures
    expr: rate(mtls_authentication_failures_total[5m]) > 10
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "High mTLS authentication failure rate"
      description: "mTLS authentication failures are above 10/minute"
```

## Troubleshooting Guide

### Common Issues

#### 1. Service Registration Failures

**Symptom:** Services fail to register with Consul

**Diagnosis:**
```bash
# Check Consul health
docker exec lucid-consul consul members

# Check Consul logs
docker logs lucid-consul

# Verify connectivity
curl http://localhost:8500/v1/status/leader
```

**Resolution:**
- Verify Consul is running and healthy
- Check network connectivity between service and Consul
- Verify service registration payload is valid
- Check Consul ACL policies if enabled

#### 2. Service Discovery Timeouts

**Symptom:** Service resolution takes >100ms or times out

**Diagnosis:**
```bash
# Check Consul query performance
consul catalog services -detailed

# Monitor query latency
curl http://localhost:8500/v1/health/service/api-gateway?passing
```

**Resolution:**
- Enable Consul query caching
- Optimize Consul indexes
- Scale Consul cluster horizontally
- Implement client-side caching

#### 3. Sidecar Proxy Errors

**Symptom:** Envoy sidecar fails to start or proxy requests

**Diagnosis:**
```bash
# Check Envoy logs
docker logs envoy-sidecar

# Verify Envoy configuration
docker exec envoy-sidecar envoy --config-path /etc/envoy/envoy.yaml --mode validate

# Check Envoy admin interface
curl http://localhost:9901/stats
curl http://localhost:9901/config_dump
```

**Resolution:**
- Validate Envoy configuration syntax
- Verify certificates are properly mounted
- Check upstream cluster connectivity
- Review Envoy error logs for specific issues

#### 4. mTLS Certificate Issues

**Symptom:** Services fail mTLS authentication

**Diagnosis:**
```bash
# Verify certificate validity
openssl x509 -in /etc/certs/tls.crt -text -noout

# Check certificate chain
openssl verify -CAfile /etc/certs/ca.crt /etc/certs/tls.crt

# Test TLS connection
openssl s_client -connect service:8080 -CAfile /etc/certs/ca.crt -cert /etc/certs/client.crt -key /etc/certs/client.key
```

**Resolution:**
- Regenerate expired certificates
- Verify certificate Subject Alternative Names (SANs)
- Check certificate trust chain
- Ensure clocks are synchronized (NTP)

#### 5. Message Queue Delivery Failures

**Symptom:** Messages not delivered between services

**Diagnosis:**
```bash
# Check RabbitMQ status
docker exec lucid-rabbitmq rabbitmqctl status

# List queues
docker exec lucid-rabbitmq rabbitmqctl list_queues

# Check queue bindings
docker exec lucid-rabbitmq rabbitmqctl list_bindings
```

**Resolution:**
- Verify RabbitMQ is running
- Check queue and exchange configuration
- Verify routing keys are correct
- Check message TTL settings

### Diagnostic Commands

```bash
# Check all service mesh components
docker ps --filter "name=lucid-*"

# View service mesh controller logs
docker logs -f lucid-service-mesh-controller

# Check Consul services
curl http://localhost:8500/v1/catalog/services | jq

# Check Prometheus targets
curl http://localhost:9090/api/v1/targets | jq

# View Jaeger traces
open http://localhost:16686

# Check RabbitMQ queues
curl -u lucid:password http://localhost:15672/api/queues | jq
```

## Operational Runbooks

### Certificate Rotation

```bash
#!/bin/bash
# scripts/rotate-certificates.sh
# Path: lucid/scripts/rotate-certificates.sh

set -e

echo "Starting certificate rotation..."

# 1. Generate new certificates
python3 -m lucid.service_mesh.security.cert_manager \
    --action rotate \
    --services-file /etc/service-list.txt

# 2. Update Kubernetes secrets
kubectl create secret generic service-mesh-certs \
    --from-file=certs/ \
    --namespace lucid-service-mesh \
    --dry-run=client -o yaml | kubectl apply -f -

# 3. Rolling restart of services
kubectl rollout restart deployment/service-mesh-controller -n lucid-service-mesh

# 4. Verify rotation
echo "Waiting for rollout to complete..."
kubectl rollout status deployment/service-mesh-controller -n lucid-service-mesh

echo "Certificate rotation complete!"
```

### Scaling Services

```bash
#!/bin/bash
# scripts/scale-service-mesh.sh
# Path: lucid/scripts/scale-service-mesh.sh

set -e

COMPONENT=$1
REPLICAS=$2

if [ -z "$COMPONENT" ] || [ -z "$REPLICAS" ]; then
    echo "Usage: $0 <component> <replicas>"
    exit 1
fi

echo "Scaling $COMPONENT to $REPLICAS replicas..."

kubectl scale deployment/$COMPONENT \
    --replicas=$REPLICAS \
    -n lucid-service-mesh

kubectl rollout status deployment/$COMPONENT -n lucid-service-mesh

echo "Scaling complete!"
```

## Disaster Recovery

### Backup Procedures

```bash
#!/bin/bash
# scripts/backup-service-mesh.sh
# Path: lucid/scripts/backup-service-mesh.sh

set -e

BACKUP_DIR="/backups/service-mesh/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "Starting service mesh backup..."

# 1. Backup Consul data
docker exec lucid-consul consul snapshot save /tmp/consul-backup.snap
docker cp lucid-consul:/tmp/consul-backup.snap "$BACKUP_DIR/consul-snapshot.snap"

# 2. Backup etcd data
docker exec lucid-etcd etcdctl snapshot save /tmp/etcd-backup.db
docker cp lucid-etcd:/tmp/etcd-backup.db "$BACKUP_DIR/etcd-snapshot.db"

# 3. Backup configurations
kubectl get configmap -n lucid-service-mesh -o yaml > "$BACKUP_DIR/configmaps.yaml"
kubectl get secret -n lucid-service-mesh -o yaml > "$BACKUP_DIR/secrets.yaml"

# 4. Backup policies
kubectl get networkpolicy -n lucid-service-mesh -o yaml > "$BACKUP_DIR/network-policies.yaml"

echo "Backup complete: $BACKUP_DIR"
```

### Restore Procedures

```bash
#!/bin/bash
# scripts/restore-service-mesh.sh
# Path: lucid/scripts/restore-service-mesh.sh

set -e

BACKUP_DIR=$1

if [ -z "$BACKUP_DIR" ]; then
    echo "Usage: $0 <backup-directory>"
    exit 1
fi

echo "Starting service mesh restore from: $BACKUP_DIR"

# 1. Restore Consul
docker cp "$BACKUP_DIR/consul-snapshot.snap" lucid-consul:/tmp/consul-restore.snap
docker exec lucid-consul consul snapshot restore /tmp/consul-restore.snap

# 2. Restore etcd
docker cp "$BACKUP_DIR/etcd-snapshot.db" lucid-etcd:/tmp/etcd-restore.db
docker exec lucid-etcd etcdctl snapshot restore /tmp/etcd-restore.db

# 3. Restore configurations
kubectl apply -f "$BACKUP_DIR/configmaps.yaml"
kubectl apply -f "$BACKUP_DIR/secrets.yaml"
kubectl apply -f "$BACKUP_DIR/network-policies.yaml"

# 4. Restart services
kubectl rollout restart deployment -n lucid-service-mesh

echo "Restore complete!"
```

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-01-10  
**Next Review**: 2025-02-10

