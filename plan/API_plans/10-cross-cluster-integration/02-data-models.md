# Cross-Cluster Integration Data Models

## Overview

This document defines the complete data models, schemas, and validation rules for the Cross-Cluster Integration cluster, including service discovery, Beta sidecar management, service mesh control, and inter-service communication.

## Core Data Models

### 1. Service Identity Model

#### ServiceIdentifier
```yaml
ServiceIdentifier:
  type: object
  required:
    - serviceId
    - serviceName
    - cluster
    - plane
  properties:
    serviceId:
      type: string
      format: uuid
      description: Unique service instance identifier
      example: "550e8400-e29b-41d4-a716-446655440000"
    serviceName:
      type: string
      pattern: '^[a-z0-9-]+$'
      minLength: 3
      maxLength: 50
      description: Service name following naming convention
      examples:
        - "api-gateway"
        - "blockchain-core"
        - "session-recorder"
        - "tron-payment-service"
    cluster:
      type: string
      enum:
        - "api-gateway"
        - "blockchain-core"
        - "session-management"
        - "rdp-services"
        - "node-management"
        - "admin-interface"
        - "tron-payment"
        - "storage-database"
        - "authentication"
      description: Service cluster identifier
    plane:
      type: string
      enum: ["ops", "chain", "wallet"]
      description: Service plane for isolation
    version:
      type: string
      pattern: '^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9-]+)?$'
      description: Semantic version
      example: "1.0.0"
    instanceId:
      type: string
      pattern: '^[a-z0-9-]+$'
      description: Instance identifier within service
      example: "api-gateway-01"
```

#### ServiceEndpoint
```yaml
ServiceEndpoint:
  type: object
  required:
    - host
    - port
    - protocol
  properties:
    host:
      type: string
      format: hostname
      description: Service hostname or IP address
      examples:
        - "api-gateway.lucid.onion"
        - "blockchain-core.lucid.onion"
        - "10.0.1.100"
    port:
      type: integer
      minimum: 1
      maximum: 65535
      description: Service port number
      examples:
        - 8080
        - 8084
        - 8085
    protocol:
      type: string
      enum: ["http", "https", "grpc", "grpcs"]
      description: Communication protocol
    path:
      type: string
      pattern: '^/[a-zA-Z0-9/_-]*$'
      description: Base path for API endpoints
      example: "/api/v1"
    tls:
      type: object
      properties:
        enabled:
          type: boolean
        certAuthority:
          type: string
        clientCert:
          type: string
        clientKey:
          type: string
```

### 2. Service Registration Models

#### ServiceRegistration
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
    - healthCheck
  properties:
    serviceId:
      $ref: '#/ServiceIdentifier/properties/serviceId'
    serviceName:
      $ref: '#/ServiceIdentifier/properties/serviceName'
    cluster:
      $ref: '#/ServiceIdentifier/properties/cluster'
    plane:
      $ref: '#/ServiceIdentifier/properties/plane'
    endpoint:
      $ref: '#/ServiceEndpoint'
    version:
      $ref: '#/ServiceIdentifier/properties/version'
    instanceId:
      $ref: '#/ServiceIdentifier/properties/instanceId'
    healthCheck:
      $ref: '#/HealthCheckConfig'
    metadata:
      type: object
      additionalProperties: true
      description: Additional service metadata
      properties:
        description:
          type: string
          maxLength: 500
        tags:
          type: array
          items:
            type: string
        capabilities:
          type: array
          items:
            type: string
        dependencies:
          type: array
          items:
            type: string
    registrationTime:
      type: string
      format: date-time
      description: Service registration timestamp
    ttl:
      type: integer
      minimum: 30
      maximum: 3600
      description: Time to live in seconds
      default: 300
```

#### HealthCheckConfig
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
      pattern: '^/[a-zA-Z0-9/_-]*$'
      description: Health check endpoint path
      example: "/health"
    interval:
      type: integer
      minimum: 5
      maximum: 300
      description: Health check interval in seconds
      default: 30
    timeout:
      type: integer
      minimum: 1
      maximum: 60
      description: Health check timeout in seconds
      default: 10
    retries:
      type: integer
      minimum: 1
      maximum: 10
      description: Number of retries before marking unhealthy
      default: 3
    successThreshold:
      type: integer
      minimum: 1
      maximum: 10
      description: Successes needed to mark healthy
      default: 1
    failureThreshold:
      type: integer
      minimum: 1
      maximum: 10
      description: Failures needed to mark unhealthy
      default: 3
    httpCheck:
      type: object
      properties:
        method:
          type: string
          enum: ["GET", "POST", "HEAD"]
          default: "GET"
        headers:
          type: object
          additionalProperties: string
        body:
          type: string
        expectedStatus:
          type: array
          items:
            type: integer
          default: [200]
    grpcCheck:
      type: object
      properties:
        service:
          type: string
        method:
          type: string
        timeout:
          type: integer
          default: 5
```

#### HealthStatus
```yaml
HealthStatus:
  type: object
  required:
    - status
    - timestamp
  properties:
    status:
      type: string
      enum: ["healthy", "unhealthy", "unknown", "degraded"]
      description: Current health status
    timestamp:
      type: string
      format: date-time
      description: Health check timestamp
    lastCheck:
      type: string
      format: date-time
      description: Last health check time
    consecutiveFailures:
      type: integer
      minimum: 0
      description: Number of consecutive failures
    consecutiveSuccesses:
      type: integer
      minimum: 0
      description: Number of consecutive successes
    responseTime:
      type: number
      minimum: 0
      description: Last health check response time in milliseconds
    error:
      type: string
      description: Last error message if unhealthy
    details:
      type: object
      additionalProperties: true
      description: Additional health check details
```

### 3. Beta Sidecar Models

#### SidecarConfiguration
```yaml
SidecarConfiguration:
  type: object
  required:
    - serviceId
    - policies
    - routing
  properties:
    serviceId:
      $ref: '#/ServiceIdentifier/properties/serviceId'
    policies:
      type: array
      items:
        $ref: '#/SidecarPolicy'
      description: List of sidecar policies
    routing:
      $ref: '#/RoutingConfig'
    security:
      $ref: '#/SecurityConfig'
    monitoring:
      $ref: '#/MonitoringConfig'
    resources:
      $ref: '#/ResourceConfig'
    version:
      type: string
      description: Configuration version
    lastUpdated:
      type: string
      format: date-time
      description: Last configuration update time
```

#### SidecarPolicy
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
      pattern: '^[a-z0-9-]+$'
      description: Unique policy identifier
      example: "rate-limit-api-calls"
    type:
      type: string
      enum: ["rate-limit", "circuit-breaker", "retry", "timeout", "auth", "logging"]
      description: Policy type
    rules:
      type: array
      items:
        $ref: '#/PolicyRule'
      description: Policy rules
    priority:
      type: integer
      minimum: 1
      maximum: 1000
      description: Policy priority (higher number = higher priority)
      default: 100
    enabled:
      type: boolean
      description: Whether policy is enabled
      default: true
    conditions:
      type: object
      properties:
        source:
          type: string
          description: Source service selector
        destination:
          type: string
          description: Destination service selector
        path:
          type: string
          description: Path pattern to match
        method:
          type: string
          description: HTTP method to match
        headers:
          type: object
          additionalProperties: string
          description: Header conditions
```

#### PolicyRule
```yaml
PolicyRule:
  type: object
  required:
    - action
  properties:
    action:
      type: string
      enum: ["allow", "deny", "redirect", "mirror", "rate-limit", "circuit-break", "retry", "timeout"]
      description: Action to take when rule matches
    parameters:
      type: object
      additionalProperties: true
      description: Action-specific parameters
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
        query:
          type: object
          additionalProperties: string
        body:
          type: object
          additionalProperties: true
    weight:
      type: integer
      minimum: 0
      maximum: 100
      description: Rule weight for load balancing
```

#### RoutingConfig
```yaml
RoutingConfig:
  type: object
  required:
    - defaultRoute
  properties:
    defaultRoute:
      type: string
      description: Default routing destination
    routes:
      type: array
      items:
        $ref: '#/Route'
      description: Custom routing rules
    loadBalancing:
      $ref: '#/LoadBalancingConfig'
    retry:
      $ref: '#/RetryConfig'
    timeout:
      $ref: '#/TimeoutConfig'
```

#### Route
```yaml
Route:
  type: object
  required:
    - match
    - destination
  properties:
    match:
      type: object
      properties:
        path:
          type: string
          description: Path pattern to match
        method:
          type: string
          description: HTTP method to match
        headers:
          type: object
          additionalProperties: string
        query:
          type: object
          additionalProperties: string
    destination:
      type: string
      description: Destination service or endpoint
    weight:
      type: integer
      minimum: 0
      maximum: 100
      description: Route weight for load balancing
    timeout:
      type: integer
      description: Route-specific timeout in milliseconds
    retry:
      $ref: '#/RetryConfig'
```

#### LoadBalancingConfig
```yaml
LoadBalancingConfig:
  type: object
  required:
    - algorithm
  properties:
    algorithm:
      type: string
      enum: ["round-robin", "least-connections", "random", "weighted", "consistent-hash"]
      description: Load balancing algorithm
      default: "round-robin"
    healthCheck:
      type: object
      properties:
        enabled:
          type: boolean
          default: true
        interval:
          type: integer
          default: 30
        timeout:
          type: integer
          default: 5
        unhealthyThreshold:
          type: integer
          default: 3
        healthyThreshold:
          type: integer
          default: 2
    stickySession:
      type: object
      properties:
        enabled:
          type: boolean
          default: false
        cookie:
          type: string
          description: Cookie name for sticky sessions
        ttl:
          type: integer
          description: Cookie TTL in seconds
```

### 4. Service Mesh Models

#### TrafficPolicy
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
      pattern: '^[a-z0-9-]+$'
      description: Policy name
      example: "api-gateway-to-blockchain"
    source:
      type: string
      description: Source service selector
      example: "api-gateway"
    destination:
      type: string
      description: Destination service selector
      example: "blockchain-core"
    rules:
      type: array
      items:
        $ref: '#/TrafficRule'
      description: Traffic rules
    priority:
      type: integer
      minimum: 1
      maximum: 1000
      description: Policy priority
      default: 100
    enabled:
      type: boolean
      description: Whether policy is enabled
      default: true
    namespace:
      type: string
      description: Policy namespace
      default: "default"
    labels:
      type: object
      additionalProperties: string
      description: Policy labels
```

#### TrafficRule
```yaml
TrafficRule:
  type: object
  required:
    - action
  properties:
    action:
      type: string
      enum: ["allow", "deny", "redirect", "mirror", "weighted-split"]
      description: Traffic action
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
        query:
          type: object
          additionalProperties: string
        sourceLabels:
          type: object
          additionalProperties: string
        destinationLabels:
          type: object
          additionalProperties: string
    parameters:
      type: object
      additionalProperties: true
      description: Action-specific parameters
    weight:
      type: integer
      minimum: 0
      maximum: 100
      description: Rule weight for load balancing
```

#### CircuitBreakerConfig
```yaml
CircuitBreakerConfig:
  type: object
  required:
    - failureThreshold
    - recoveryTimeout
  properties:
    failureThreshold:
      type: integer
      minimum: 1
      maximum: 100
      description: Number of failures before opening circuit
      default: 5
    recoveryTimeout:
      type: integer
      minimum: 1
      maximum: 3600
      description: Time to wait before attempting recovery in seconds
      default: 30
    halfOpenMaxCalls:
      type: integer
      minimum: 1
      maximum: 100
      description: Maximum calls in half-open state
      default: 3
    successThreshold:
      type: integer
      minimum: 1
      maximum: 100
      description: Successes needed to close circuit
      default: 3
    timeout:
      type: integer
      minimum: 100
      maximum: 30000
      description: Request timeout in milliseconds
      default: 5000
    errorTypes:
      type: array
      items:
        type: string
      description: Error types that trigger circuit breaker
      default: ["5xx", "timeout", "connection-error"]
```

#### SecurityPolicy
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
      pattern: '^[a-z0-9-]+$'
      description: Security policy name
    source:
      type: string
      description: Source service selector
    destination:
      type: string
      description: Destination service selector
    rules:
      type: array
      items:
        $ref: '#/SecurityRule'
      description: Security rules
    priority:
      type: integer
      minimum: 1
      maximum: 1000
      description: Policy priority
      default: 100
    enabled:
      type: boolean
      description: Whether policy is enabled
      default: true
    namespace:
      type: string
      description: Policy namespace
      default: "default"
```

#### SecurityRule
```yaml
SecurityRule:
  type: object
  required:
    - action
  properties:
    action:
      type: string
      enum: ["allow", "deny", "require-auth", "require-mtls", "require-role"]
      description: Security action
    authentication:
      type: object
      properties:
        required:
          type: boolean
          default: true
        methods:
          type: array
          items:
            type: string
            enum: ["jwt", "mtls", "api-key", "oauth2"]
        jwt:
          type: object
          properties:
            issuer:
              type: string
            audience:
              type: string
            requiredClaims:
              type: object
              additionalProperties: true
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
        resourceAccess:
          type: object
          additionalProperties: true
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
        sourceLabels:
          type: object
          additionalProperties: string
```

### 5. Inter-Service Communication Models

#### InterServiceMessage
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
      description: Unique message identifier
    source:
      type: string
      description: Source service identifier
    destination:
      type: string
      description: Destination service identifier
    payload:
      type: object
      additionalProperties: true
      description: Message payload
    headers:
      type: object
      additionalProperties: string
      description: Message headers
    priority:
      type: string
      enum: ["low", "normal", "high", "critical"]
      description: Message priority
      default: "normal"
    ttl:
      type: integer
      minimum: 1
      maximum: 86400
      description: Time to live in seconds
      default: 3600
    retryPolicy:
      $ref: '#/RetryPolicy'
    correlationId:
      type: string
      format: uuid
      description: Correlation ID for request tracking
    timestamp:
      type: string
      format: date-time
      description: Message creation timestamp
```

#### MessageStatus
```yaml
MessageStatus:
  type: object
  required:
    - messageId
    - status
    - timestamp
  properties:
    messageId:
      type: string
      format: uuid
      description: Message identifier
    status:
      type: string
      enum: ["queued", "processing", "delivered", "failed", "expired"]
      description: Message delivery status
    timestamp:
      type: string
      format: date-time
      description: Status update timestamp
    attempts:
      type: integer
      minimum: 0
      description: Number of delivery attempts
    lastAttempt:
      type: string
      format: date-time
      description: Last delivery attempt timestamp
    error:
      type: string
      description: Error message if failed
    deliveredTo:
      type: string
      description: Service that received the message
    processingTime:
      type: number
      description: Message processing time in milliseconds
```

#### ServiceEvent
```yaml
ServiceEvent:
  type: object
  required:
    - eventId
    - eventType
    - source
    - timestamp
    - data
  properties:
    eventId:
      type: string
      format: uuid
      description: Unique event identifier
    eventType:
      type: string
      pattern: '^[a-z0-9.-]+$'
      description: Event type identifier
      examples:
        - "session.created"
        - "block.anchored"
        - "payment.completed"
        - "service.registered"
    source:
      type: string
      description: Source service identifier
    timestamp:
      type: string
      format: date-time
      description: Event timestamp
    data:
      type: object
      additionalProperties: true
      description: Event data payload
    version:
      type: string
      description: Event schema version
      default: "1.0"
    correlationId:
      type: string
      format: uuid
      description: Correlation ID for event tracking
    tags:
      type: object
      additionalProperties: string
      description: Event tags for filtering
```

#### EventSubscription
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
      examples:
        - ["session.*", "block.*"]
        - ["payment.completed", "user.registered"]
    filters:
      type: object
      additionalProperties: true
      description: Event filtering criteria
      properties:
        source:
          type: array
          items:
            type: string
        tags:
          type: object
          additionalProperties: string
        data:
          type: object
          additionalProperties: true
    deliveryMode:
      type: string
      enum: ["push", "pull"]
      description: Event delivery mode
      default: "push"
    batchSize:
      type: integer
      minimum: 1
      maximum: 1000
      description: Number of events to batch together
      default: 1
    maxRetries:
      type: integer
      minimum: 0
      maximum: 10
      description: Maximum delivery retries
      default: 3
    retryDelay:
      type: integer
      minimum: 1000
      maximum: 300000
      description: Retry delay in milliseconds
      default: 5000
```

### 6. Configuration Models

#### RetryConfig
```yaml
RetryConfig:
  type: object
  required:
    - maxAttempts
  properties:
    maxAttempts:
      type: integer
      minimum: 1
      maximum: 10
      description: Maximum retry attempts
      default: 3
    initialDelay:
      type: integer
      minimum: 100
      maximum: 10000
      description: Initial retry delay in milliseconds
      default: 1000
    maxDelay:
      type: integer
      minimum: 1000
      maximum: 60000
      description: Maximum retry delay in milliseconds
      default: 10000
    backoffMultiplier:
      type: number
      minimum: 1.0
      maximum: 5.0
      description: Backoff multiplier for exponential backoff
      default: 2.0
    retryableErrors:
      type: array
      items:
        type: string
      description: Error types that should trigger retry
      default: ["5xx", "timeout", "connection-error"]
```

#### TimeoutConfig
```yaml
TimeoutConfig:
  type: object
  properties:
    connect:
      type: integer
      minimum: 100
      maximum: 30000
      description: Connection timeout in milliseconds
      default: 5000
    request:
      type: integer
      minimum: 1000
      maximum: 300000
      description: Request timeout in milliseconds
      default: 30000
    response:
      type: integer
      minimum: 1000
      maximum: 300000
      description: Response timeout in milliseconds
      default: 30000
    idle:
      type: integer
      minimum: 1000
      maximum: 300000
      description: Idle connection timeout in milliseconds
      default: 60000
```

#### SecurityConfig
```yaml
SecurityConfig:
  type: object
  properties:
    mTLS:
      type: object
      properties:
        enabled:
          type: boolean
          default: true
        certAuthority:
          type: string
          description: Certificate authority
        clientCert:
          type: string
          description: Client certificate
        clientKey:
          type: string
          description: Client private key
    authentication:
      type: object
      properties:
        required:
          type: boolean
          default: true
        methods:
          type: array
          items:
            type: string
            enum: ["jwt", "mtls", "api-key"]
    authorization:
      type: object
      properties:
        enabled:
          type: boolean
          default: true
        policy:
          type: string
          enum: ["allow-all", "deny-all", "rbac"]
          default: "rbac"
```

#### MonitoringConfig
```yaml
MonitoringConfig:
  type: object
  properties:
    metrics:
      type: object
      properties:
        enabled:
          type: boolean
          default: true
        endpoint:
          type: string
          description: Metrics endpoint
        interval:
          type: integer
          description: Metrics collection interval in seconds
          default: 30
    tracing:
      type: object
      properties:
        enabled:
          type: boolean
          default: true
        samplingRate:
          type: number
          minimum: 0.0
          maximum: 1.0
          description: Trace sampling rate
          default: 0.1
        endpoint:
          type: string
          description: Tracing endpoint
    logging:
      type: object
      properties:
        enabled:
          type: boolean
          default: true
        level:
          type: string
          enum: ["debug", "info", "warn", "error"]
          default: "info"
        format:
          type: string
          enum: ["json", "text"]
          default: "json"
```

#### ResourceConfig
```yaml
ResourceConfig:
  type: object
  properties:
    limits:
      type: object
      properties:
        cpu:
          type: string
          description: CPU limit
          example: "500m"
        memory:
          type: string
          description: Memory limit
          example: "512Mi"
        connections:
          type: integer
          description: Maximum connections
          default: 1000
    requests:
      type: object
      properties:
        cpu:
          type: string
          description: CPU request
          example: "100m"
        memory:
          type: string
          description: Memory request
          example: "128Mi"
        connections:
          type: integer
          description: Minimum connections
          default: 10
```

## Validation Rules

### 1. Service Naming Validation
```yaml
ServiceNamingRules:
  serviceName:
    pattern: '^[a-z0-9-]+$'
    minLength: 3
    maxLength: 50
    description: Service names must be lowercase, alphanumeric with hyphens
  cluster:
    enum: ["api-gateway", "blockchain-core", "session-management", "rdp-services", "node-management", "admin-interface", "tron-payment", "storage-database", "authentication"]
    description: Must be one of the defined clusters
  plane:
    enum: ["ops", "chain", "wallet"]
    description: Must be one of the defined planes
```

### 2. Endpoint Validation
```yaml
EndpointValidationRules:
  host:
    format: hostname
    description: Must be a valid hostname or IP address
  port:
    minimum: 1
    maximum: 65535
    description: Must be a valid port number
  protocol:
    enum: ["http", "https", "grpc", "grpcs"]
    description: Must be a supported protocol
```

### 3. Policy Validation
```yaml
PolicyValidationRules:
  policyId:
    pattern: '^[a-z0-9-]+$'
    minLength: 3
    maxLength: 50
    description: Policy IDs must be lowercase, alphanumeric with hyphens
  priority:
    minimum: 1
    maximum: 1000
    description: Priority must be between 1 and 1000
  weight:
    minimum: 0
    maximum: 100
    description: Weight must be between 0 and 100
```

### 4. Message Validation
```yaml
MessageValidationRules:
  messageId:
    format: uuid
    description: Must be a valid UUID
  priority:
    enum: ["low", "normal", "high", "critical"]
    description: Must be a valid priority level
  ttl:
    minimum: 1
    maximum: 86400
    description: TTL must be between 1 and 86400 seconds
```

## Database Collections

### 1. Service Registry Collection
```yaml
ServiceRegistryCollection:
  name: "service_registry"
  indexes:
    - serviceId: 1
      unique: true
    - serviceName: 1
    - cluster: 1
    - plane: 1
    - status: 1
    - lastHealthCheck: 1
  schema:
    serviceId: "string (uuid)"
    serviceName: "string"
    cluster: "string"
    plane: "string"
    endpoint: "object"
    version: "string"
    status: "string"
    healthCheck: "object"
    metadata: "object"
    registeredAt: "datetime"
    lastHealthCheck: "datetime"
    ttl: "integer"
```

### 2. Service Mesh Policies Collection
```yaml
ServiceMeshPoliciesCollection:
  name: "service_mesh_policies"
  indexes:
    - name: 1
      unique: true
    - type: 1
    - source: 1
    - destination: 1
    - priority: 1
    - enabled: 1
  schema:
    name: "string"
    type: "string"
    source: "string"
    destination: "string"
    rules: "array"
    priority: "integer"
    enabled: "boolean"
    namespace: "string"
    labels: "object"
    createdAt: "datetime"
    updatedAt: "datetime"
```

### 3. Message Queue Collection
```yaml
MessageQueueCollection:
  name: "message_queue"
  indexes:
    - messageId: 1
      unique: true
    - destination: 1
    - status: 1
    - priority: 1
    - createdAt: 1
    - ttl: 1
  schema:
    messageId: "string (uuid)"
    source: "string"
    destination: "string"
    payload: "object"
    headers: "object"
    priority: "string"
    status: "string"
    ttl: "integer"
    attempts: "integer"
    createdAt: "datetime"
    updatedAt: "datetime"
    deliveredAt: "datetime"
```

### 4. Event Stream Collection
```yaml
EventStreamCollection:
  name: "event_stream"
  indexes:
    - eventId: 1
      unique: true
    - eventType: 1
    - source: 1
    - timestamp: 1
    - tags: 1
  schema:
    eventId: "string (uuid)"
    eventType: "string"
    source: "string"
    timestamp: "datetime"
    data: "object"
    version: "string"
    correlationId: "string (uuid)"
    tags: "object"
```

## Error Codes

### Service Discovery Errors
- `LUCID_ERR_1001`: Service registration failed
- `LUCID_ERR_1002`: Service not found
- `LUCID_ERR_1003`: Service already registered
- `LUCID_ERR_1004`: Invalid service configuration
- `LUCID_ERR_1005`: Service discovery timeout

### Beta Sidecar Errors
- `LUCID_ERR_1101`: Sidecar configuration failed
- `LUCID_ERR_1102`: Policy validation failed
- `LUCID_ERR_1103`: Routing configuration invalid
- `LUCID_ERR_1104`: Sidecar proxy unavailable
- `LUCID_ERR_1105`: Policy enforcement failed

### Service Mesh Errors
- `LUCID_ERR_1201`: Traffic policy creation failed
- `LUCID_ERR_1202`: Circuit breaker configuration invalid
- `LUCID_ERR_1203`: Security policy violation
- `LUCID_ERR_1204`: mTLS configuration failed
- `LUCID_ERR_1205`: Service mesh controller unavailable

### Inter-Service Communication Errors
- `LUCID_ERR_1301`: Message delivery failed
- `LUCID_ERR_1302`: Event subscription failed
- `LUCID_ERR_1303`: Message queue unavailable
- `LUCID_ERR_1304`: Event stream unavailable
- `LUCID_ERR_1305`: Message timeout

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-01-10  
**Next Review**: 2025-02-10
