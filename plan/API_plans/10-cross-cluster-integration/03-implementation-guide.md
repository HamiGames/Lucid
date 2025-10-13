# Cross-Cluster Integration Implementation Guide

## Overview

This document provides comprehensive implementation guidance for the Cross-Cluster Integration cluster, including service mesh architecture, Beta sidecar proxy implementation, service discovery patterns, and inter-service communication protocols.

## Directory Structure

```
lucid/
├── service-mesh/
│   ├── controller/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config_manager.py
│   │   ├── policy_engine.py
│   │   └── health_checker.py
│   ├── sidecar/
│   │   ├── envoy/
│   │   │   ├── config/
│   │   │   │   ├── bootstrap.yaml
│   │   │   │   ├── listener.yaml
│   │   │   │   └── cluster.yaml
│   │   │   └── filters/
│   │   │       ├── auth_filter.py
│   │   │       ├── rate_limit_filter.py
│   │   │       └── metrics_filter.py
│   │   └── proxy/
│   │       ├── __init__.py
│   │       ├── proxy_manager.py
│   │       └── policy_enforcer.py
│   ├── discovery/
│   │   ├── __init__.py
│   │   ├── consul_client.py
│   │   ├── etcd_client.py
│   │   ├── service_registry.py
│   │   └── dns_resolver.py
│   ├── communication/
│   │   ├── __init__.py
│   │   ├── grpc_client.py
│   │   ├── grpc_server.py
│   │   ├── message_queue.py
│   │   └── event_stream.py
│   ├── security/
│   │   ├── __init__.py
│   │   ├── mtls_manager.py
│   │   ├── cert_manager.py
│   │   └── auth_provider.py
│   └── monitoring/
│       ├── __init__.py
│       ├── metrics_collector.py
│       ├── tracer.py
│       └── health_monitor.py
├── config/
│   ├── service-mesh-config.yaml
│   ├── sidecar-policies.yaml
│   └── discovery-config.yaml
└── deployments/
    ├── docker/
    │   ├── Dockerfile.consul
    │   ├── Dockerfile.envoy
    │   └── Dockerfile.controller
    └── kubernetes/
        ├── service-mesh-controller.yaml
        ├── consul-deployment.yaml
        └── network-policies.yaml
```

## Naming Conventions

### Service Identifiers

```yaml
ServiceNaming:
  serviceId:
    format: "UUID v4"
    example: "550e8400-e29b-41d4-a716-446655440000"
    
  serviceName:
    pattern: "^[a-z0-9-]+$"
    examples:
      - "api-gateway"
      - "blockchain-core"
      - "session-recorder"
      - "tron-payment-service"
      - "lucid-blocks"
    
  instanceId:
    pattern: "^[serviceName]-[instance-number]$"
    examples:
      - "api-gateway-01"
      - "blockchain-core-02"
      - "session-recorder-03"
```

### Policy Identifiers

```yaml
PolicyNaming:
  policyId:
    pattern: "^[a-z0-9-]+$"
    examples:
      - "rate-limit-api-calls"
      - "circuit-breaker-blockchain"
      - "retry-tron-payment"
      - "timeout-session-recorder"
      
  policyName:
    pattern: "^[source]-to-[destination]-[type]$"
    examples:
      - "api-gateway-to-blockchain-traffic"
      - "wallet-plane-isolation-security"
      - "chain-plane-rate-limit"
```

### Endpoint Patterns

```yaml
EndpointNaming:
  internalServices:
    pattern: "[service-name].lucid.internal:[port]"
    examples:
      - "api-gateway.lucid.internal:8080"
      - "blockchain-core.lucid.internal:8084"
      
  onionServices:
    pattern: "[service-name].lucid.onion:[port]"
    examples:
      - "api-gateway.lucid.onion:8080"
      - "admin-interface.lucid.onion:8083"
      
  healthEndpoints:
    pattern: "/health"
    example: "http://api-gateway.lucid.internal:8080/health"
    
  metricsEndpoints:
    pattern: "/metrics"
    example: "http://api-gateway.lucid.internal:8080/metrics"
```

## Service Discovery Implementation

### 1. Service Registration Client

```python
# lucid/service-mesh/discovery/service_registry.py

import uuid
import consul
import logging
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class ServiceRegistry:
    """Client for registering and managing services in Consul."""
    
    def __init__(self, consul_host: str = "consul.lucid.internal", 
                 consul_port: int = 8500):
        self.consul = consul.Consul(host=consul_host, port=consul_port)
        
    def register_service(
        self,
        service_name: str,
        cluster: str,
        plane: str,
        host: str,
        port: int,
        version: str,
        health_check_path: str = "/health",
        health_check_interval: str = "30s",
        health_check_timeout: str = "10s",
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Register a service with the service discovery system.
        
        Args:
            service_name: Name of the service (e.g., "api-gateway")
            cluster: Cluster identifier
            plane: Service plane (ops, chain, wallet)
            host: Service host address
            port: Service port number
            version: Service version
            health_check_path: Health check endpoint path
            health_check_interval: Health check interval
            health_check_timeout: Health check timeout
            metadata: Additional service metadata
            
        Returns:
            service_id: Unique service instance identifier
            
        Raises:
            ServiceRegistrationError: If registration fails (LUCID_ERR_1001)
        """
        service_id = str(uuid.uuid4())
        instance_id = f"{service_name}-{service_id[:8]}"
        
        # Build service registration payload
        service_config = {
            "ID": service_id,
            "Name": service_name,
            "Tags": [
                f"cluster:{cluster}",
                f"plane:{plane}",
                f"version:{version}"
            ],
            "Address": host,
            "Port": port,
            "Meta": {
                "service_id": service_id,
                "cluster": cluster,
                "plane": plane,
                "version": version,
                "registered_at": datetime.utcnow().isoformat(),
                **(metadata or {})
            },
            "Check": {
                "HTTP": f"http://{host}:{port}{health_check_path}",
                "Interval": health_check_interval,
                "Timeout": health_check_timeout,
                "DeregisterCriticalServiceAfter": "90s"
            }
        }
        
        try:
            # Register service with Consul
            success = self.consul.agent.service.register(
                name=service_name,
                service_id=service_id,
                address=host,
                port=port,
                tags=service_config["Tags"],
                meta=service_config["Meta"],
                check=service_config["Check"]
            )
            
            if success:
                logger.info(
                    f"Service registered: {service_name} "
                    f"(ID: {service_id}, Cluster: {cluster}, Plane: {plane})"
                )
                return service_id
            else:
                raise ServiceRegistrationError(
                    "LUCID_ERR_1001",
                    f"Failed to register service: {service_name}"
                )
                
        except Exception as e:
            logger.error(f"Service registration failed: {str(e)}")
            raise ServiceRegistrationError("LUCID_ERR_1001", str(e))
    
    def deregister_service(self, service_id: str) -> bool:
        """
        Deregister a service from the service discovery system.
        
        Args:
            service_id: Service instance identifier
            
        Returns:
            success: True if deregistration was successful
        """
        try:
            success = self.consul.agent.service.deregister(service_id)
            if success:
                logger.info(f"Service deregistered: {service_id}")
            return success
        except Exception as e:
            logger.error(f"Service deregistration failed: {str(e)}")
            return False
    
    def update_health_status(
        self,
        service_id: str,
        status: str,
        output: str = ""
    ) -> bool:
        """
        Update the health status of a registered service.
        
        Args:
            service_id: Service instance identifier
            status: Health status (passing, warning, critical)
            output: Status message
            
        Returns:
            success: True if update was successful
        """
        try:
            check_id = f"service:{service_id}"
            
            if status == "passing":
                success = self.consul.agent.check.ttl_pass(check_id, output)
            elif status == "warning":
                success = self.consul.agent.check.ttl_warn(check_id, output)
            else:  # critical
                success = self.consul.agent.check.ttl_fail(check_id, output)
            
            return success
            
        except Exception as e:
            logger.error(f"Health status update failed: {str(e)}")
            return False


class ServiceRegistrationError(Exception):
    """Exception raised when service registration fails."""
    
    def __init__(self, error_code: str, message: str):
        self.error_code = error_code
        self.message = message
        super().__init__(f"[{error_code}] {message}")
```

### 2. Service Discovery Client

```python
# lucid/service-mesh/discovery/dns_resolver.py

import consul
import logging
from typing import List, Optional, Dict
import random

logger = logging.getLogger(__name__)

class ServiceDiscoveryClient:
    """Client for discovering and resolving services."""
    
    def __init__(self, consul_host: str = "consul.lucid.internal",
                 consul_port: int = 8500):
        self.consul = consul.Consul(host=consul_host, port=consul_port)
    
    def discover_services(
        self,
        cluster: Optional[str] = None,
        plane: Optional[str] = None,
        status: str = "passing"
    ) -> List[Dict]:
        """
        Discover available services with optional filtering.
        
        Args:
            cluster: Filter by cluster (optional)
            plane: Filter by plane (optional)
            status: Filter by health status
            
        Returns:
            services: List of service information
            
        Raises:
            ServiceDiscoveryError: If discovery fails (LUCID_ERR_1002)
        """
        try:
            # Get all services
            index, services = self.consul.catalog.services()
            
            discovered_services = []
            
            for service_name in services:
                # Get service instances
                index, instances = self.consul.health.service(
                    service_name,
                    passing=(status == "passing")
                )
                
                for instance in instances:
                    service_meta = instance['Service'].get('Meta', {})
                    
                    # Apply filters
                    if cluster and service_meta.get('cluster') != cluster:
                        continue
                    if plane and service_meta.get('plane') != plane:
                        continue
                    
                    discovered_services.append({
                        'serviceId': instance['Service']['ID'],
                        'serviceName': service_name,
                        'cluster': service_meta.get('cluster'),
                        'plane': service_meta.get('plane'),
                        'endpoint': {
                            'host': instance['Service']['Address'],
                            'port': instance['Service']['Port']
                        },
                        'version': service_meta.get('version'),
                        'status': self._get_health_status(instance),
                        'lastHealthCheck': instance['Checks'][0]['ModifyIndex']
                            if instance['Checks'] else None
                    })
            
            return discovered_services
            
        except Exception as e:
            logger.error(f"Service discovery failed: {str(e)}")
            raise ServiceDiscoveryError("LUCID_ERR_1002", str(e))
    
    def resolve_service(
        self,
        service_name: str,
        version: Optional[str] = None,
        load_balance: str = "round-robin"
    ) -> Optional[Dict]:
        """
        Resolve a service endpoint using load balancing.
        
        Args:
            service_name: Name of the service to resolve
            version: Service version (optional)
            load_balance: Load balancing algorithm
            
        Returns:
            endpoint: Service endpoint information
            
        Raises:
            ServiceNotFoundError: If service not found (LUCID_ERR_1002)
        """
        try:
            # Get healthy service instances
            index, instances = self.consul.health.service(
                service_name,
                passing=True
            )
            
            if not instances:
                raise ServiceNotFoundError(
                    "LUCID_ERR_1002",
                    f"Service not found: {service_name}"
                )
            
            # Filter by version if specified
            if version:
                instances = [
                    i for i in instances
                    if i['Service'].get('Meta', {}).get('version') == version
                ]
            
            if not instances:
                raise ServiceNotFoundError(
                    "LUCID_ERR_1002",
                    f"Service not found with version {version}: {service_name}"
                )
            
            # Apply load balancing
            instance = self._apply_load_balancing(instances, load_balance)
            
            return {
                'serviceId': instance['Service']['ID'],
                'serviceName': service_name,
                'endpoint': {
                    'host': instance['Service']['Address'],
                    'port': instance['Service']['Port'],
                    'protocol': 'https'
                },
                'version': instance['Service'].get('Meta', {}).get('version'),
                'status': 'healthy'
            }
            
        except ServiceNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Service resolution failed: {str(e)}")
            raise ServiceDiscoveryError("LUCID_ERR_1005", str(e))
    
    def _apply_load_balancing(
        self,
        instances: List[Dict],
        algorithm: str
    ) -> Dict:
        """Apply load balancing algorithm to select instance."""
        if algorithm == "random":
            return random.choice(instances)
        elif algorithm == "round-robin":
            # Simple round-robin (stateless)
            return instances[0]
        elif algorithm == "least-connections":
            # TODO: Implement connection tracking
            return instances[0]
        else:
            return instances[0]
    
    def _get_health_status(self, instance: Dict) -> str:
        """Determine health status from instance checks."""
        if not instance.get('Checks'):
            return "unknown"
        
        statuses = [check['Status'] for check in instance['Checks']]
        
        if 'critical' in statuses:
            return "unhealthy"
        elif 'warning' in statuses:
            return "degraded"
        else:
            return "healthy"


class ServiceDiscoveryError(Exception):
    """Exception raised when service discovery fails."""
    
    def __init__(self, error_code: str, message: str):
        self.error_code = error_code
        self.message = message
        super().__init__(f"[{error_code}] {message}")


class ServiceNotFoundError(ServiceDiscoveryError):
    """Exception raised when service is not found."""
    pass
```

## Beta Sidecar Proxy Implementation

### 1. Envoy Bootstrap Configuration

```yaml
# lucid/service-mesh/sidecar/envoy/config/bootstrap.yaml

admin:
  access_log_path: /tmp/admin_access.log
  address:
    socket_address:
      protocol: TCP
      address: 127.0.0.1
      port_value: 9901

static_resources:
  listeners:
  - name: listener_0
    address:
      socket_address:
        protocol: TCP
        address: 0.0.0.0
        port_value: 15001
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
                  cluster: local_service
          http_filters:
          - name: envoy.filters.http.jwt_authn
            typed_config:
              "@type": type.googleapis.com/envoy.extensions.filters.http.jwt_authn.v3.JwtAuthentication
              providers:
                lucid_jwt:
                  issuer: "lucid.onion"
                  audiences:
                  - "lucid-services"
                  remote_jwks:
                    http_uri:
                      uri: "https://auth.lucid.onion/.well-known/jwks.json"
                      cluster: auth_service
                      timeout: 5s
                    cache_duration:
                      seconds: 300
              rules:
              - match:
                  prefix: "/api/"
                requires:
                  provider_name: "lucid_jwt"
          - name: envoy.filters.http.ratelimit
            typed_config:
              "@type": type.googleapis.com/envoy.extensions.filters.http.ratelimit.v3.RateLimit
              domain: lucid_services
              rate_limit_service:
                grpc_service:
                  envoy_grpc:
                    cluster_name: rate_limit_service
          - name: envoy.filters.http.router
            typed_config:
              "@type": type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
      transport_socket:
        name: envoy.transport_sockets.tls
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.transport_sockets.tls.v3.DownstreamTlsContext
          common_tls_context:
            tls_certificates:
            - certificate_chain:
                filename: "/etc/certs/tls.crt"
              private_key:
                filename: "/etc/certs/tls.key"
            validation_context:
              trusted_ca:
                filename: "/etc/certs/ca.crt"
          require_client_certificate: true

  clusters:
  - name: local_service
    connect_timeout: 5s
    type: LOGICAL_DNS
    dns_lookup_family: V4_ONLY
    lb_policy: ROUND_ROBIN
    load_assignment:
      cluster_name: local_service
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: 127.0.0.1
                port_value: 8080
    health_checks:
    - timeout: 5s
      interval: 30s
      unhealthy_threshold: 3
      healthy_threshold: 2
      http_health_check:
        path: "/health"
    
  - name: auth_service
    connect_timeout: 5s
    type: LOGICAL_DNS
    dns_lookup_family: V4_ONLY
    lb_policy: ROUND_ROBIN
    load_assignment:
      cluster_name: auth_service
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: auth.lucid.onion
                port_value: 8089
    transport_socket:
      name: envoy.transport_sockets.tls
      typed_config:
        "@type": type.googleapis.com/envoy.extensions.transport_sockets.tls.v3.UpstreamTlsContext
        common_tls_context:
          tls_certificates:
          - certificate_chain:
              filename: "/etc/certs/client.crt"
            private_key:
              filename: "/etc/certs/client.key"
          validation_context:
            trusted_ca:
              filename: "/etc/certs/ca.crt"

dynamic_resources:
  lds_config:
    resource_api_version: V3
    api_config_source:
      api_type: GRPC
      transport_api_version: V3
      grpc_services:
      - envoy_grpc:
          cluster_name: xds_cluster
  cds_config:
    resource_api_version: V3
    api_config_source:
      api_type: GRPC
      transport_api_version: V3
      grpc_services:
      - envoy_grpc:
          cluster_name: xds_cluster
```

### 2. Circuit Breaker Configuration

```yaml
# lucid/service-mesh/sidecar/envoy/config/circuit_breaker.yaml

CircuitBreakerConfiguration:
  defaultConfig:
    failureThreshold: 5
    recoveryTimeout: 30
    halfOpenMaxCalls: 3
    successThreshold: 3
    timeout: 5000
    errorTypes:
      - "5xx"
      - "timeout"
      - "connection-error"
  
  serviceSpecific:
    blockchain-core:
      failureThreshold: 3
      recoveryTimeout: 60
      timeout: 10000
      errorTypes:
        - "5xx"
        - "timeout"
    
    tron-payment-service:
      failureThreshold: 10
      recoveryTimeout: 30
      timeout: 15000
      errorTypes:
        - "5xx"
        - "timeout"
        - "payment-error"
    
    session-recorder:
      failureThreshold: 5
      recoveryTimeout: 45
      timeout: 8000
```

## Inter-Service Communication Patterns

### 1. gRPC Service Implementation

```python
# lucid/service-mesh/communication/grpc_server.py

import grpc
from concurrent import futures
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)

class LucidGRPCServer:
    """Base gRPC server for inter-service communication."""
    
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8080,
        max_workers: int = 10,
        enable_mtls: bool = True,
        cert_path: Optional[str] = "/etc/certs/tls.crt",
        key_path: Optional[str] = "/etc/certs/tls.key",
        ca_path: Optional[str] = "/etc/certs/ca.crt"
    ):
        self.host = host
        self.port = port
        self.max_workers = max_workers
        self.enable_mtls = enable_mtls
        self.cert_path = cert_path
        self.key_path = key_path
        self.ca_path = ca_path
        self.server = None
    
    def start(self, servicer_factory: Callable):
        """
        Start the gRPC server with the provided servicer.
        
        Args:
            servicer_factory: Function that returns a servicer instance
        """
        # Create server
        self.server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=self.max_workers),
            options=[
                ('grpc.max_send_message_length', 100 * 1024 * 1024),
                ('grpc.max_receive_message_length', 100 * 1024 * 1024),
                ('grpc.keepalive_time_ms', 30000),
                ('grpc.keepalive_timeout_ms', 5000),
            ]
        )
        
        # Add servicer to server
        servicer = servicer_factory()
        servicer.add_to_server(self.server)
        
        # Configure mTLS if enabled
        if self.enable_mtls:
            with open(self.cert_path, 'rb') as f:
                cert_chain = f.read()
            with open(self.key_path, 'rb') as f:
                private_key = f.read()
            with open(self.ca_path, 'rb') as f:
                root_cert = f.read()
            
            server_credentials = grpc.ssl_server_credentials(
                [(private_key, cert_chain)],
                root_certificates=root_cert,
                require_client_auth=True
            )
            
            self.server.add_secure_port(
                f'{self.host}:{self.port}',
                server_credentials
            )
            logger.info(
                f"gRPC server starting with mTLS on {self.host}:{self.port}"
            )
        else:
            self.server.add_insecure_port(f'{self.host}:{self.port}')
            logger.info(
                f"gRPC server starting (insecure) on {self.host}:{self.port}"
            )
        
        # Start server
        self.server.start()
        logger.info("gRPC server started successfully")
    
    def stop(self, grace_period: int = 30):
        """Stop the gRPC server gracefully."""
        if self.server:
            logger.info(f"Stopping gRPC server (grace: {grace_period}s)")
            self.server.stop(grace_period)
            logger.info("gRPC server stopped")
    
    def wait_for_termination(self):
        """Block until server terminates."""
        if self.server:
            self.server.wait_for_termination()
```

### 2. Message Queue Client

```python
# lucid/service-mesh/communication/message_queue.py

import uuid
import json
import logging
from typing import Dict, Optional, Callable
from datetime import datetime, timedelta
import pika

logger = logging.getLogger(__name__)

class MessageQueueClient:
    """Client for inter-service message queue communication."""
    
    def __init__(
        self,
        rabbitmq_host: str = "rabbitmq.lucid.internal",
        rabbitmq_port: int = 5672,
        rabbitmq_user: str = "lucid",
        rabbitmq_password: str = "",
        enable_ssl: bool = True
    ):
        self.host = rabbitmq_host
        self.port = rabbitmq_port
        self.credentials = pika.PlainCredentials(
            rabbitmq_user,
            rabbitmq_password
        )
        self.connection = None
        self.channel = None
        self.enable_ssl = enable_ssl
    
    def connect(self):
        """Establish connection to RabbitMQ."""
        try:
            if self.enable_ssl:
                ssl_options = pika.SSLOptions(
                    context=self._create_ssl_context()
                )
                parameters = pika.ConnectionParameters(
                    host=self.host,
                    port=self.port,
                    credentials=self.credentials,
                    ssl_options=ssl_options,
                    heartbeat=60
                )
            else:
                parameters = pika.ConnectionParameters(
                    host=self.host,
                    port=self.port,
                    credentials=self.credentials,
                    heartbeat=60
                )
            
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            logger.info(f"Connected to RabbitMQ at {self.host}:{self.port}")
            
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {str(e)}")
            raise MessageQueueError("LUCID_ERR_1303", str(e))
    
    def send_message(
        self,
        source: str,
        destination: str,
        payload: Dict,
        priority: str = "normal",
        ttl: int = 3600,
        headers: Optional[Dict] = None
    ) -> str:
        """
        Send a message to another service.
        
        Args:
            source: Source service identifier
            destination: Destination service identifier
            payload: Message payload
            priority: Message priority (low, normal, high, critical)
            ttl: Time to live in seconds
            headers: Additional message headers
            
        Returns:
            message_id: Unique message identifier
            
        Raises:
            MessageQueueError: If message sending fails (LUCID_ERR_1301)
        """
        message_id = str(uuid.uuid4())
        
        message = {
            "messageId": message_id,
            "source": source,
            "destination": destination,
            "payload": payload,
            "headers": headers or {},
            "priority": priority,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            # Declare exchange and queue
            exchange_name = "lucid.inter-service"
            queue_name = f"lucid.{destination}"
            
            self.channel.exchange_declare(
                exchange=exchange_name,
                exchange_type='topic',
                durable=True
            )
            
            self.channel.queue_declare(
                queue=queue_name,
                durable=True,
                arguments={
                    'x-message-ttl': ttl * 1000
                }
            )
            
            self.channel.queue_bind(
                exchange=exchange_name,
                queue=queue_name,
                routing_key=destination
            )
            
            # Publish message
            self.channel.basic_publish(
                exchange=exchange_name,
                routing_key=destination,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Persistent
                    priority=self._get_priority_value(priority),
                    message_id=message_id,
                    timestamp=int(datetime.utcnow().timestamp()),
                    expiration=str(ttl * 1000)
                )
            )
            
            logger.info(
                f"Message sent: {message_id} "
                f"(from: {source}, to: {destination})"
            )
            
            return message_id
            
        except Exception as e:
            logger.error(f"Failed to send message: {str(e)}")
            raise MessageQueueError("LUCID_ERR_1301", str(e))
    
    def _get_priority_value(self, priority: str) -> int:
        """Convert priority string to integer value."""
        priority_map = {
            "low": 1,
            "normal": 5,
            "high": 8,
            "critical": 10
        }
        return priority_map.get(priority, 5)
    
    def _create_ssl_context(self):
        """Create SSL context for secure connection."""
        import ssl
        context = ssl.create_default_context()
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        return context
    
    def close(self):
        """Close connection to RabbitMQ."""
        if self.connection:
            self.connection.close()
            logger.info("Disconnected from RabbitMQ")


class MessageQueueError(Exception):
    """Exception raised when message queue operation fails."""
    
    def __init__(self, error_code: str, message: str):
        self.error_code = error_code
        self.message = message
        super().__init__(f"[{error_code}] {message}")
```

## Distroless Container Configurations

### 1. Service Mesh Controller Dockerfile

```dockerfile
# deployments/docker/Dockerfile.controller

# Build stage
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Runtime stage - Distroless
FROM gcr.io/distroless/python3-debian12

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY service-mesh/controller /app/controller
COPY service-mesh/security /app/security
COPY service-mesh/monitoring /app/monitoring
COPY config /app/config

# Set environment variables
ENV PYTHONPATH=/app
ENV PATH=/root/.local/bin:$PATH

# Set working directory
WORKDIR /app

# Run as non-root user
USER nonroot:nonroot

# Run the controller
ENTRYPOINT ["python3", "-m", "controller.main"]
```

### 2. Envoy Proxy Dockerfile

```dockerfile
# deployments/docker/Dockerfile.envoy

# Use official Envoy distroless image
FROM envoyproxy/envoy:distroless-v1.28-latest

# Copy Envoy configuration
COPY service-mesh/sidecar/envoy/config/bootstrap.yaml /etc/envoy/envoy.yaml
COPY service-mesh/sidecar/envoy/config/listener.yaml /etc/envoy/listener.yaml
COPY service-mesh/sidecar/envoy/config/cluster.yaml /etc/envoy/cluster.yaml

# Copy certificates (will be mounted at runtime)
# COPY certs /etc/certs

# Expose ports
EXPOSE 15001 9901

# Run Envoy
ENTRYPOINT ["/usr/local/bin/envoy"]
CMD ["-c", "/etc/envoy/envoy.yaml", "--service-cluster", "lucid-sidecar"]
```

### 3. Consul Dockerfile

```dockerfile
# deployments/docker/Dockerfile.consul

# Build stage
FROM consul:1.17 AS consul-binary

# Runtime stage - Distroless
FROM gcr.io/distroless/static-debian12

# Copy Consul binary from official image
COPY --from=consul-binary /bin/consul /bin/consul

# Copy configuration
COPY config/consul-config.json /consul/config/config.json

# Create data directory
# Note: This will need to be a volume mount in production

# Expose ports
EXPOSE 8300 8301 8302 8500 8600

# Set user
USER nonroot:nonroot

# Run Consul
ENTRYPOINT ["/bin/consul"]
CMD ["agent", "-config-dir=/consul/config"]
```

## Configuration Management

### Service Mesh Configuration

```yaml
# config/service-mesh-config.yaml

serviceMesh:
  version: "1.0.0"
  
  controller:
    host: "0.0.0.0"
    port: 8080
    logLevel: "info"
    
  discovery:
    provider: "consul"
    consul:
      host: "consul.lucid.internal"
      port: 8500
      datacenter: "dc1"
      
  sidecar:
    envoy:
      adminPort: 9901
      listenerPort: 15001
      clusterDiscoveryService:
        host: "service-mesh-controller.lucid.internal"
        port: 18000
      listenerDiscoveryService:
        host: "service-mesh-controller.lucid.internal"
        port: 18000
    
  security:
    mtls:
      enabled: true
      certPath: "/etc/certs/tls.crt"
      keyPath: "/etc/certs/tls.key"
      caPath: "/etc/certs/ca.crt"
      certRotationInterval: "24h"
    
    authentication:
      required: true
      methods:
        - jwt
        - mtls
      jwt:
        issuer: "lucid.onion"
        audience: "lucid-services"
        jwksUrl: "https://auth.lucid.onion/.well-known/jwks.json"
    
  monitoring:
    metrics:
      enabled: true
      port: 9090
      path: "/metrics"
    
    tracing:
      enabled: true
      samplingRate: 0.1
      jaeger:
        host: "jaeger.lucid.internal"
        port: 6831
    
    logging:
      level: "info"
      format: "json"
      
  planeIsolation:
    enabled: true
    planes:
      ops:
        allowedClusters:
          - "api-gateway"
          - "admin-interface"
          - "session-management"
          - "rdp-services"
          - "node-management"
      chain:
        allowedClusters:
          - "blockchain-core"
          - "storage-database"
      wallet:
        allowedClusters:
          - "tron-payment"
    
    policies:
      - name: "ops-to-chain-readonly"
        source: "ops"
        destination: "chain"
        rules:
          - action: "allow"
            methods: ["GET"]
      
      - name: "wallet-isolation"
        source: "*"
        destination: "wallet"
        rules:
          - action: "deny"
            except:
              - source: "api-gateway"
                methods: ["POST"]
                paths: ["/api/v1/payments/*"]
```

## Best Practices

### 1. Service Registration Best Practices

- Register services on startup with proper health check configuration
- Use meaningful service names following naming conventions
- Include comprehensive metadata (version, cluster, plane)
- Implement graceful deregistration on shutdown
- Set appropriate TTL values (recommended: 300 seconds)

### 2. Service Discovery Best Practices

- Cache service discovery results with appropriate TTL
- Implement circuit breakers for service resolution failures
- Use health-based filtering to avoid unhealthy instances
- Apply appropriate load balancing algorithms
- Handle service not found errors gracefully

### 3. Inter-Service Communication Best Practices

- Always use mTLS for inter-service communication
- Include correlation IDs for request tracing
- Set appropriate timeouts and retry policies
- Use message queues for asynchronous communication
- Implement idempotent message handlers

### 4. Beta Sidecar Best Practices

- Deploy sidecar proxy alongside every service
- Configure circuit breakers for external dependencies
- Implement rate limiting to prevent abuse
- Enable distributed tracing for observability
- Use policy-based routing for traffic management

## Error Handling

All service mesh components should handle errors using the standard error codes defined in `02-data-models.md`:

- **LUCID_ERR_1001**: Service registration failed
- **LUCID_ERR_1002**: Service not found
- **LUCID_ERR_1003**: Service already registered
- **LUCID_ERR_1004**: Invalid service configuration
- **LUCID_ERR_1005**: Service discovery timeout
- **LUCID_ERR_1101**: Sidecar configuration failed
- **LUCID_ERR_1102**: Policy validation failed
- **LUCID_ERR_1103**: Routing configuration invalid
- **LUCID_ERR_1104**: Sidecar proxy unavailable
- **LUCID_ERR_1105**: Policy enforcement failed
- **LUCID_ERR_1201**: Traffic policy creation failed
- **LUCID_ERR_1202**: Circuit breaker configuration invalid
- **LUCID_ERR_1203**: Security policy violation
- **LUCID_ERR_1204**: mTLS configuration failed
- **LUCID_ERR_1205**: Service mesh controller unavailable
- **LUCID_ERR_1301**: Message delivery failed
- **LUCID_ERR_1302**: Event subscription failed
- **LUCID_ERR_1303**: Message queue unavailable
- **LUCID_ERR_1304**: Event stream unavailable
- **LUCID_ERR_1305**: Message timeout

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-01-10  
**Next Review**: 2025-02-10

