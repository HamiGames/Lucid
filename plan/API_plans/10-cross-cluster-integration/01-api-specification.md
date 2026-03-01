# Cross-Cluster Integration API Specification

## Overview

This document defines the complete OpenAPI 3.0 specification for the Cross-Cluster Integration cluster, including service discovery, Beta sidecar management, inter-service communication, and service mesh control APIs.

## Base Configuration

```yaml
openapi: 3.0.3
info:
  title: Lucid Cross-Cluster Integration API
  description: Inter-service communication and service mesh management APIs
  version: 1.0.0
  contact:
    name: Lucid Development Team
    email: dev@lucid.onion
servers:
  - url: https://service-mesh.lucid.onion/api/v1
    description: Production service mesh API
  - url: https://service-discovery.lucid.onion/api/v1
    description: Service discovery API
  - url: https://sidecar-proxy.lucid.onion/api/v1
    description: Beta sidecar proxy API
```

## Service Discovery APIs

### 1. Service Registration

#### Register Service
```yaml
/service-discovery/services:
  post:
    summary: Register a new service
    description: Register a service instance with the service discovery system
    tags: [Service Discovery]
    security:
      - ServiceAuth: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/ServiceRegistration'
    responses:
      '201':
        description: Service registered successfully
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ServiceRegistrationResponse'
      '400':
        $ref: '#/components/responses/BadRequest'
      '401':
        $ref: '#/components/responses/Unauthorized'
      '409':
        description: Service already registered
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ErrorResponse'
```

#### Deregister Service
```yaml
/service-discovery/services/{serviceId}:
  delete:
    summary: Deregister a service
    description: Remove a service instance from the service discovery system
    tags: [Service Discovery]
    security:
      - ServiceAuth: []
    parameters:
      - name: serviceId
        in: path
        required: true
        schema:
          type: string
          format: uuid
    responses:
      '204':
        description: Service deregistered successfully
      '404':
        $ref: '#/components/responses/NotFound'
      '401':
        $ref: '#/components/responses/Unauthorized'
```

#### Update Service Health
```yaml
/service-discovery/services/{serviceId}/health:
  put:
    summary: Update service health status
    description: Update the health status of a registered service
    tags: [Service Discovery]
    security:
      - ServiceAuth: []
    parameters:
      - name: serviceId
        in: path
        required: true
        schema:
          type: string
          format: uuid
    requestBody:
      required: true
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/HealthUpdate'
    responses:
      '200':
        description: Health status updated
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/HealthStatus'
      '404':
        $ref: '#/components/responses/NotFound'
      '401':
        $ref: '#/components/responses/Unauthorized'
```

### 2. Service Discovery

#### Discover Services
```yaml
/service-discovery/services:
  get:
    summary: Discover available services
    description: Get list of available services with optional filtering
    tags: [Service Discovery]
    security:
      - ServiceAuth: []
    parameters:
      - name: cluster
        in: query
        schema:
          type: string
          enum: [api-gateway, blockchain-core, session-management, rdp-services, node-management, admin-interface, tron-payment, storage-database, authentication]
      - name: plane
        in: query
        schema:
          type: string
          enum: [ops, chain, wallet]
      - name: status
        in: query
        schema:
          type: string
          enum: [healthy, unhealthy, unknown]
      - name: limit
        in: query
        schema:
          type: integer
          minimum: 1
          maximum: 1000
          default: 100
      - name: offset
        in: query
        schema:
          type: integer
          minimum: 0
          default: 0
    responses:
      '200':
        description: List of services
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ServiceDiscoveryResponse'
      '401':
        $ref: '#/components/responses/Unauthorized'
```

#### Resolve Service
```yaml
/service-discovery/services/{serviceName}/resolve:
  get:
    summary: Resolve service endpoint
    description: Get the endpoint information for a specific service
    tags: [Service Discovery]
    security:
      - ServiceAuth: []
    parameters:
      - name: serviceName
        in: path
        required: true
        schema:
          type: string
      - name: version
        in: query
        schema:
          type: string
      - name: loadBalance
        in: query
        schema:
          type: string
          enum: [round-robin, least-connections, random]
          default: round-robin
    responses:
      '200':
        description: Service endpoint resolved
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ServiceEndpoint'
      '404':
        $ref: '#/components/responses/NotFound'
      '401':
        $ref: '#/components/responses/Unauthorized'
```

## Beta Sidecar Management APIs

### 1. Sidecar Configuration

#### Configure Sidecar
```yaml
/sidecar-proxy/config:
  post:
    summary: Configure Beta sidecar proxy
    description: Configure routing, security, and monitoring policies for a sidecar proxy
    tags: [Beta Sidecar]
    security:
      - ServiceAuth: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/SidecarConfiguration'
    responses:
      '200':
        description: Sidecar configured successfully
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/SidecarConfigurationResponse'
      '400':
        $ref: '#/components/responses/BadRequest'
      '401':
        $ref: '#/components/responses/Unauthorized'
```

#### Update Sidecar Policy
```yaml
/sidecar-proxy/policies/{policyId}:
  put:
    summary: Update sidecar policy
    description: Update a specific policy for the sidecar proxy
    tags: [Beta Sidecar]
    security:
      - ServiceAuth: []
    parameters:
      - name: policyId
        in: path
        required: true
        schema:
          type: string
    requestBody:
      required: true
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/SidecarPolicy'
    responses:
      '200':
        description: Policy updated successfully
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/SidecarPolicyResponse'
      '404':
        $ref: '#/components/responses/NotFound'
      '401':
        $ref: '#/components/responses/Unauthorized'
```

### 2. Sidecar Monitoring

#### Get Sidecar Metrics
```yaml
/sidecar-proxy/metrics:
  get:
    summary: Get sidecar proxy metrics
    description: Retrieve performance and operational metrics for the sidecar proxy
    tags: [Beta Sidecar]
    security:
      - ServiceAuth: []
    parameters:
      - name: timeRange
        in: query
        schema:
          type: string
          enum: [1m, 5m, 15m, 1h, 6h, 24h]
          default: 15m
      - name: metrics
        in: query
        schema:
          type: array
          items:
            type: string
            enum: [requests, latency, errors, connections, bandwidth]
    responses:
      '200':
        description: Sidecar metrics
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/SidecarMetrics'
      '401':
        $ref: '#/components/responses/Unauthorized'
```

#### Get Sidecar Health
```yaml
/sidecar-proxy/health:
  get:
    summary: Get sidecar proxy health
    description: Get the health status of the sidecar proxy
    tags: [Beta Sidecar]
    security:
      - ServiceAuth: []
    responses:
      '200':
        description: Sidecar health status
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/SidecarHealth'
      '503':
        description: Sidecar unhealthy
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/SidecarHealth'
```

## Service Mesh Control APIs

### 1. Traffic Management

#### Create Traffic Policy
```yaml
/service-mesh/traffic-policies:
  post:
    summary: Create traffic management policy
    description: Create a new traffic management policy for service mesh
    tags: [Service Mesh]
    security:
      - AdminAuth: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/TrafficPolicy'
    responses:
      '201':
        description: Traffic policy created
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/TrafficPolicyResponse'
      '400':
        $ref: '#/components/responses/BadRequest'
      '401':
        $ref: '#/components/responses/Unauthorized'
      '403':
        $ref: '#/components/responses/Forbidden'
```

#### Update Circuit Breaker
```yaml
/service-mesh/circuit-breakers/{serviceName}:
  put:
    summary: Update circuit breaker configuration
    description: Update circuit breaker settings for a specific service
    tags: [Service Mesh]
    security:
      - AdminAuth: []
    parameters:
      - name: serviceName
        in: path
        required: true
        schema:
          type: string
    requestBody:
      required: true
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/CircuitBreakerConfig'
    responses:
      '200':
        description: Circuit breaker updated
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CircuitBreakerResponse'
      '404':
        $ref: '#/components/responses/NotFound'
      '401':
        $ref: '#/components/responses/Unauthorized'
      '403':
        $ref: '#/components/responses/Forbidden'
```

### 2. Security Management

#### Create Security Policy
```yaml
/service-mesh/security-policies:
  post:
    summary: Create security policy
    description: Create a new security policy for service mesh
    tags: [Service Mesh]
    security:
      - AdminAuth: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/SecurityPolicy'
    responses:
      '201':
        description: Security policy created
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/SecurityPolicyResponse'
      '400':
        $ref: '#/components/responses/BadRequest'
      '401':
        $ref: '#/components/responses/Unauthorized'
      '403':
        $ref: '#/components/responses/Forbidden'
```

#### Update mTLS Configuration
```yaml
/service-mesh/mtls:
  put:
    summary: Update mTLS configuration
    description: Update mutual TLS configuration for service mesh
    tags: [Service Mesh]
    security:
      - AdminAuth: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/MTLSConfig'
    responses:
      '200':
        description: mTLS configuration updated
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/MTLSConfigResponse'
      '400':
        $ref: '#/components/responses/BadRequest'
      '401':
        $ref: '#/components/responses/Unauthorized'
      '403':
        $ref: '#/components/responses/Forbidden'
```

## Inter-Service Communication APIs

### 1. Message Queue Management

#### Send Message
```yaml
/inter-service/messages:
  post:
    summary: Send inter-service message
    description: Send a message to another service via the message queue
    tags: [Inter-Service Communication]
    security:
      - ServiceAuth: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/InterServiceMessage'
    responses:
      '202':
        description: Message queued for delivery
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/MessageResponse'
      '400':
        $ref: '#/components/responses/BadRequest'
      '401':
        $ref: '#/components/responses/Unauthorized'
```

#### Get Message Status
```yaml
/inter-service/messages/{messageId}/status:
  get:
    summary: Get message delivery status
    description: Get the delivery status of a sent message
    tags: [Inter-Service Communication]
    security:
      - ServiceAuth: []
    parameters:
      - name: messageId
        in: path
        required: true
        schema:
          type: string
          format: uuid
    responses:
      '200':
        description: Message status
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/MessageStatus'
      '404':
        $ref: '#/components/responses/NotFound'
      '401':
        $ref: '#/components/responses/Unauthorized'
```

### 2. Event Streaming

#### Subscribe to Events
```yaml
/inter-service/events/subscribe:
  post:
    summary: Subscribe to service events
    description: Subscribe to events from specific services
    tags: [Inter-Service Communication]
    security:
      - ServiceAuth: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/EventSubscription'
    responses:
      '200':
        description: Event subscription created
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/EventSubscriptionResponse'
      '400':
        $ref: '#/components/responses/BadRequest'
      '401':
        $ref: '#/components/responses/Unauthorized'
```

#### Publish Event
```yaml
/inter-service/events:
  post:
    summary: Publish service event
    description: Publish an event to the event stream
    tags: [Inter-Service Communication]
    security:
      - ServiceAuth: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/ServiceEvent'
    responses:
      '202':
        description: Event published
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/EventResponse'
      '400':
        $ref: '#/components/responses/BadRequest'
      '401':
        $ref: '#/components/responses/Unauthorized'
```

## Data Models

### Service Registration
```yaml
ServiceRegistration:
  type: object
  required:
    - serviceId
    - serviceName
    - cluster
    - plane
    - endpoint
    - version
  properties:
    serviceId:
      type: string
      format: uuid
      description: Unique service instance identifier
    serviceName:
      type: string
      description: Service name (e.g., api-gateway, blockchain-core)
    cluster:
      type: string
      enum: [api-gateway, blockchain-core, session-management, rdp-services, node-management, admin-interface, tron-payment, storage-database, authentication]
      description: Service cluster identifier
    plane:
      type: string
      enum: [ops, chain, wallet]
      description: Service plane (ops, chain, or wallet)
    endpoint:
      type: object
      properties:
        host:
          type: string
        port:
          type: integer
        protocol:
          type: string
          enum: [http, https, grpc]
        path:
          type: string
    version:
      type: string
      description: Service version
    metadata:
      type: object
      additionalProperties: true
      description: Additional service metadata
    healthCheck:
      $ref: '#/components/schemas/HealthCheckConfig'
```

### Health Check Configuration
```yaml
HealthCheckConfig:
  type: object
  required:
    - endpoint
    - interval
    - timeout
  properties:
    endpoint:
      type: string
      description: Health check endpoint path
    interval:
      type: integer
      description: Health check interval in seconds
    timeout:
      type: integer
      description: Health check timeout in seconds
    retries:
      type: integer
      description: Number of retries before marking unhealthy
```

### Sidecar Configuration
```yaml
SidecarConfiguration:
  type: object
  required:
    - serviceId
    - policies
  properties:
    serviceId:
      type: string
      format: uuid
    policies:
      type: array
      items:
        $ref: '#/components/schemas/SidecarPolicy'
    routing:
      $ref: '#/components/schemas/RoutingConfig'
    security:
      $ref: '#/components/schemas/SecurityConfig'
    monitoring:
      $ref: '#/components/schemas/MonitoringConfig'
```

### Sidecar Policy
```yaml
SidecarPolicy:
  type: object
  required:
    - policyId
    - type
    - rules
  properties:
    policyId:
      type: string
    type:
      type: string
      enum: [rate-limit, circuit-breaker, retry, timeout, auth]
    rules:
      type: array
      items:
        type: object
    priority:
      type: integer
      description: Policy priority (higher number = higher priority)
    enabled:
      type: boolean
      default: true
```

### Traffic Policy
```yaml
TrafficPolicy:
  type: object
  required:
    - name
    - source
    - destination
    - rules
  properties:
    name:
      type: string
    source:
      type: string
      description: Source service or service selector
    destination:
      type: string
      description: Destination service or service selector
    rules:
      type: array
      items:
        $ref: '#/components/schemas/TrafficRule'
    priority:
      type: integer
    enabled:
      type: boolean
      default: true
```

### Traffic Rule
```yaml
TrafficRule:
  type: object
  required:
    - action
  properties:
    action:
      type: string
      enum: [allow, deny, redirect, mirror]
    match:
      type: object
      properties:
        headers:
          type: object
          additionalProperties: string
        path:
          type: string
        method:
          type: string
    weight:
      type: integer
      description: Traffic weight for load balancing
    timeout:
      type: integer
      description: Request timeout in milliseconds
```

### Circuit Breaker Configuration
```yaml
CircuitBreakerConfig:
  type: object
  required:
    - failureThreshold
    - recoveryTimeout
  properties:
    failureThreshold:
      type: integer
      description: Number of failures before opening circuit
    recoveryTimeout:
      type: integer
      description: Time to wait before attempting recovery
    halfOpenMaxCalls:
      type: integer
      description: Maximum calls in half-open state
    successThreshold:
      type: integer
      description: Successes needed to close circuit
```

### Security Policy
```yaml
SecurityPolicy:
  type: object
  required:
    - name
    - source
    - destination
    - rules
  properties:
    name:
      type: string
    source:
      type: string
    destination:
      type: string
    rules:
      type: array
      items:
        $ref: '#/components/schemas/SecurityRule'
    priority:
      type: integer
    enabled:
      type: boolean
      default: true
```

### Security Rule
```yaml
SecurityRule:
  type: object
  required:
    - action
  properties:
    action:
      type: string
      enum: [allow, deny, require-auth, require-mtls]
    authentication:
      type: object
      properties:
        required:
          type: boolean
        methods:
          type: array
          items:
            type: string
            enum: [jwt, mtls, api-key]
    authorization:
      type: object
      properties:
        roles:
          type: array
          items:
            type: string
        permissions:
          type: array
          items:
            type: string
```

### Inter-Service Message
```yaml
InterServiceMessage:
  type: object
  required:
    - messageId
    - source
    - destination
    - payload
  properties:
    messageId:
      type: string
      format: uuid
    source:
      type: string
      description: Source service identifier
    destination:
      type: string
      description: Destination service identifier
    payload:
      type: object
      description: Message payload
    headers:
      type: object
      additionalProperties: string
    priority:
      type: string
      enum: [low, normal, high, critical]
      default: normal
    ttl:
      type: integer
      description: Time to live in seconds
    retryPolicy:
      $ref: '#/components/schemas/RetryPolicy'
```

### Event Subscription
```yaml
EventSubscription:
  type: object
  required:
    - subscriberId
    - eventTypes
  properties:
    subscriberId:
      type: string
      description: Subscriber service identifier
    eventTypes:
      type: array
      items:
        type: string
      description: Types of events to subscribe to
    filters:
      type: object
      additionalProperties: true
      description: Event filtering criteria
    deliveryMode:
      type: string
      enum: [push, pull]
      default: push
    batchSize:
      type: integer
      description: Number of events to batch together
```

## Error Responses

### Standard Error Response
```yaml
ErrorResponse:
  type: object
  required:
    - error
  properties:
    error:
      type: object
      required:
        - code
        - message
        - request_id
        - timestamp
      properties:
        code:
          type: string
          pattern: '^LUCID_ERR_[0-9]{4}$'
        message:
          type: string
        details:
          type: object
          additionalProperties: true
        request_id:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time
        service:
          type: string
        version:
          type: string
```

## Security Schemes

### Service Authentication
```yaml
ServiceAuth:
  type: http
  scheme: bearer
  bearerFormat: JWT
  description: JWT token for service-to-service authentication
```

### Admin Authentication
```yaml
AdminAuth:
  type: http
  scheme: bearer
  bearerFormat: JWT
  description: JWT token for admin operations
```

## Rate Limiting

### Service Discovery APIs
- **Registration/Deregistration**: 100 requests/minute per service
- **Health Updates**: 1000 requests/minute per service
- **Service Discovery**: 1000 requests/minute per service

### Beta Sidecar APIs
- **Configuration Updates**: 10 requests/minute per sidecar
- **Metrics Retrieval**: 100 requests/minute per sidecar
- **Health Checks**: 1000 requests/minute per sidecar

### Service Mesh APIs
- **Policy Management**: 50 requests/minute per admin
- **Traffic Management**: 100 requests/minute per admin
- **Security Management**: 50 requests/minute per admin

### Inter-Service Communication APIs
- **Message Sending**: 1000 messages/minute per service
- **Event Publishing**: 500 events/minute per service
- **Event Subscription**: 100 subscriptions/minute per service

## Response Examples

### Service Registration Success
```json
{
  "serviceId": "550e8400-e29b-41d4-a716-446655440000",
  "serviceName": "api-gateway",
  "cluster": "api-gateway",
  "plane": "ops",
  "endpoint": {
    "host": "api-gateway.lucid.onion",
    "port": 8080,
    "protocol": "https",
    "path": "/api/v1"
  },
  "version": "1.0.0",
  "status": "registered",
  "registeredAt": "2025-01-10T19:08:00Z"
}
```

### Service Discovery Response
```json
{
  "services": [
    {
      "serviceId": "550e8400-e29b-41d4-a716-446655440000",
      "serviceName": "api-gateway",
      "cluster": "api-gateway",
      "plane": "ops",
      "endpoint": {
        "host": "api-gateway.lucid.onion",
        "port": 8080,
        "protocol": "https"
      },
      "version": "1.0.0",
      "status": "healthy",
      "lastHealthCheck": "2025-01-10T19:08:00Z"
    }
  ],
  "total": 1,
  "limit": 100,
  "offset": 0
}
```

### Sidecar Metrics
```json
{
  "serviceId": "550e8400-e29b-41d4-a716-446655440000",
  "timeRange": "15m",
  "metrics": {
    "requests": {
      "total": 15000,
      "rate": 16.67,
      "byStatus": {
        "2xx": 14250,
        "4xx": 600,
        "5xx": 150
      }
    },
    "latency": {
      "p50": 25,
      "p95": 150,
      "p99": 500
    },
    "errors": {
      "total": 750,
      "rate": 0.83
    },
    "connections": {
      "active": 45,
      "total": 15000
    }
  },
  "timestamp": "2025-01-10T19:08:00Z"
}
```

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-01-10  
**Next Review**: 2025-02-10
