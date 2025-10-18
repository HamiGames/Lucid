# Node Management Cluster API Specification

## OpenAPI 3.0 Specification

### Service Information
- **Title**: Lucid Node Management API
- **Version**: 1.0.0
- **Description**: API for managing worker nodes, pools, and PoOT operations
- **Base URL**: `https://node-management.lucid.onion/api/v1`
- **Contact**: Lucid Development Team

### Authentication
- **Type**: Bearer Token (JWT)
- **Header**: `Authorization: Bearer <token>`
- **Scopes**: `node:read`, `node:write`, `poot:read`, `poot:write`, `payout:read`, `payout:write`

### Rate Limiting
- **Authenticated Nodes**: 1000 requests/minute
- **Admin Operations**: 10000 requests/minute
- **PoOT Operations**: 100 requests/minute
- **Payout Operations**: 50 requests/minute

## API Endpoints

### Node Lifecycle Management

#### List All Nodes
```yaml
GET /nodes:
  summary: List all nodes
  description: Retrieve a paginated list of all registered nodes
  tags: [Nodes]
  parameters:
    - name: page
      in: query
      schema:
        type: integer
        minimum: 1
        default: 1
    - name: limit
      in: query
      schema:
        type: integer
        minimum: 1
        maximum: 100
        default: 20
    - name: status
      in: query
      schema:
        type: string
        enum: [active, inactive, maintenance, error]
    - name: pool_id
      in: query
      schema:
        type: string
  responses:
    '200':
      description: List of nodes retrieved successfully
      content:
        application/json:
          schema:
            type: object
            properties:
              nodes:
                type: array
                items:
                  $ref: '#/components/schemas/Node'
              pagination:
                $ref: '#/components/schemas/Pagination'
    '401':
      $ref: '#/components/responses/Unauthorized'
    '429':
      $ref: '#/components/responses/RateLimited'
```

#### Create New Node
```yaml
POST /nodes:
  summary: Create new node
  description: Register a new worker node
  tags: [Nodes]
  requestBody:
    required: true
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/NodeCreateRequest'
  responses:
    '201':
      description: Node created successfully
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Node'
    '400':
      $ref: '#/components/responses/BadRequest'
    '401':
      $ref: '#/components/responses/Unauthorized'
    '409':
      description: Node already exists
```

#### Get Node Details
```yaml
GET /nodes/{node_id}:
  summary: Get node details
  description: Retrieve detailed information about a specific node
  tags: [Nodes]
  parameters:
    - name: node_id
      in: path
      required: true
      schema:
        type: string
        pattern: '^node_[a-zA-Z0-9_-]+$'
  responses:
    '200':
      description: Node details retrieved successfully
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Node'
    '404':
      $ref: '#/components/responses/NotFound'
```

#### Update Node Configuration
```yaml
PUT /nodes/{node_id}:
  summary: Update node configuration
  description: Update node configuration and settings
  tags: [Nodes]
  parameters:
    - name: node_id
      in: path
      required: true
      schema:
        type: string
        pattern: '^node_[a-zA-Z0-9_-]+$'
  requestBody:
    required: true
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/NodeUpdateRequest'
  responses:
    '200':
      description: Node updated successfully
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Node'
    '400':
      $ref: '#/components/responses/BadRequest'
    '404':
      $ref: '#/components/responses/NotFound'
```

#### Start Node
```yaml
POST /nodes/{node_id}/start:
  summary: Start node
  description: Start a stopped or inactive node
  tags: [Nodes]
  parameters:
    - name: node_id
      in: path
      required: true
      schema:
        type: string
        pattern: '^node_[a-zA-Z0-9_-]+$'
  responses:
    '200':
      description: Node started successfully
      content:
        application/json:
          schema:
            type: object
            properties:
              node_id:
                type: string
              status:
                type: string
                enum: [starting, active]
              started_at:
                type: string
                format: date-time
    '400':
      description: Node cannot be started
    '404':
      $ref: '#/components/responses/NotFound'
```

#### Stop Node
```yaml
POST /nodes/{node_id}/stop:
  summary: Stop node
  description: Stop an active node
  tags: [Nodes]
  parameters:
    - name: node_id
      in: path
      required: true
      schema:
        type: string
        pattern: '^node_[a-zA-Z0-9_-]+$'
  responses:
    '200':
      description: Node stopped successfully
      content:
        application/json:
          schema:
            type: object
            properties:
              node_id:
                type: string
              status:
                type: string
                enum: [stopping, inactive]
              stopped_at:
                type: string
                format: date-time
    '400':
      description: Node cannot be stopped
    '404':
      $ref: '#/components/responses/NotFound'
```

### Pool Management

#### List Node Pools
```yaml
GET /nodes/pools:
  summary: List node pools
  description: Retrieve a list of all node pools
  tags: [Pools]
  parameters:
    - name: page
      in: query
      schema:
        type: integer
        minimum: 1
        default: 1
    - name: limit
      in: query
      schema:
        type: integer
        minimum: 1
        maximum: 100
        default: 20
  responses:
    '200':
      description: List of pools retrieved successfully
      content:
        application/json:
          schema:
            type: object
            properties:
              pools:
                type: array
                items:
                  $ref: '#/components/schemas/NodePool'
              pagination:
                $ref: '#/components/schemas/Pagination'
```

#### Create Node Pool
```yaml
POST /nodes/pools:
  summary: Create node pool
  description: Create a new node pool
  tags: [Pools]
  requestBody:
    required: true
    content:
      application/json:
        schema:
          $ref: '#/components/schemas/NodePoolCreateRequest'
  responses:
    '201':
      description: Pool created successfully
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/NodePool'
    '400':
      $ref: '#/components/responses/BadRequest'
    '409':
      description: Pool already exists
```

#### Add Node to Pool
```yaml
POST /nodes/pools/{pool_id}/nodes:
  summary: Add node to pool
  description: Add a node to a specific pool
  tags: [Pools]
  parameters:
    - name: pool_id
      in: path
      required: true
      schema:
        type: string
        pattern: '^pool_[a-zA-Z0-9_-]+$'
  requestBody:
    required: true
    content:
      application/json:
        schema:
          type: object
          properties:
            node_id:
              type: string
              pattern: '^node_[a-zA-Z0-9_-]+$'
            priority:
              type: integer
              minimum: 1
              maximum: 100
              default: 50
  responses:
    '200':
      description: Node added to pool successfully
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/NodePool'
    '400':
      $ref: '#/components/responses/BadRequest'
    '404':
      $ref: '#/components/responses/NotFound'
```

### Resource Monitoring

#### Get Node Resources
```yaml
GET /nodes/{node_id}/resources:
  summary: Get node resources
  description: Retrieve current resource utilization for a node
  tags: [Resources]
  parameters:
    - name: node_id
      in: path
      required: true
      schema:
        type: string
        pattern: '^node_[a-zA-Z0-9_-]+$'
    - name: time_range
      in: query
      schema:
        type: string
        enum: [1h, 6h, 24h, 7d]
        default: 1h
  responses:
    '200':
      description: Resource data retrieved successfully
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/NodeResources'
    '404':
      $ref: '#/components/responses/NotFound'
```

#### Get Resource Metrics
```yaml
GET /nodes/{node_id}/resources/metrics:
  summary: Get resource metrics
  description: Retrieve detailed resource metrics for a node
  tags: [Resources]
  parameters:
    - name: node_id
      in: path
      required: true
      schema:
        type: string
        pattern: '^node_[a-zA-Z0-9_-]+$'
    - name: metric_type
      in: query
      schema:
        type: string
        enum: [cpu, memory, disk, network]
    - name: granularity
      in: query
      schema:
        type: string
        enum: [1m, 5m, 15m, 1h]
        default: 5m
    - name: start_time
      in: query
      schema:
        type: string
        format: date-time
    - name: end_time
      in: query
      schema:
        type: string
        format: date-time
  responses:
    '200':
      description: Metrics retrieved successfully
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/ResourceMetrics'
    '404':
      $ref: '#/components/responses/NotFound'
```

### PoOT Operations

#### Get PoOT Score
```yaml
GET /nodes/{node_id}/poot/score:
  summary: Get PoOT score
  description: Retrieve the current PoOT score for a node
  tags: [PoOT]
  parameters:
    - name: node_id
      in: path
      required: true
      schema:
        type: string
        pattern: '^node_[a-zA-Z0-9_-]+$'
  responses:
    '200':
      description: PoOT score retrieved successfully
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/PoOTScore'
    '404':
      $ref: '#/components/responses/NotFound'
```

#### Validate PoOT
```yaml
POST /nodes/{node_id}/poot/validate:
  summary: Validate PoOT
  description: Validate the PoOT for a specific node
  tags: [PoOT]
  parameters:
    - name: node_id
      in: path
      required: true
      schema:
        type: string
        pattern: '^node_[a-zA-Z0-9_-]+$'
  requestBody:
    required: true
    content:
      application/json:
        schema:
          type: object
          properties:
            output_data:
              type: string
              description: Base64 encoded output data
            timestamp:
              type: string
              format: date-time
            nonce:
              type: string
  responses:
    '200':
      description: PoOT validation completed
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/PoOTValidation'
    '400':
      $ref: '#/components/responses/BadRequest'
    '404':
      $ref: '#/components/responses/NotFound'
```

#### Batch Validate PoOT
```yaml
POST /nodes/poot/batch-validate:
  summary: Batch validate PoOT
  description: Validate PoOT for multiple nodes in a single request
  tags: [PoOT]
  requestBody:
    required: true
    content:
      application/json:
        schema:
          type: object
          properties:
            validations:
              type: array
              items:
                type: object
                properties:
                  node_id:
                    type: string
                    pattern: '^node_[a-zA-Z0-9_-]+$'
                  output_data:
                    type: string
                  timestamp:
                    type: string
                    format: date-time
                  nonce:
                    type: string
  responses:
    '200':
      description: Batch validation completed
      content:
        application/json:
          schema:
            type: object
            properties:
              results:
                type: array
                items:
                  $ref: '#/components/schemas/PoOTValidation'
              summary:
                type: object
                properties:
                  total:
                    type: integer
                  valid:
                    type: integer
                  invalid:
                    type: integer
                  errors:
                    type: integer
```

### Payout Management

#### Get Node Payouts
```yaml
GET /nodes/{node_id}/payouts:
  summary: Get node payouts
  description: Retrieve payout history for a specific node
  tags: [Payouts]
  parameters:
    - name: node_id
      in: path
      required: true
      schema:
        type: string
        pattern: '^node_[a-zA-Z0-9_-]+$'
    - name: page
      in: query
      schema:
        type: integer
        minimum: 1
        default: 1
    - name: limit
      in: query
      schema:
        type: integer
        minimum: 1
        maximum: 100
        default: 20
    - name: status
      in: query
      schema:
        type: string
        enum: [pending, processing, completed, failed]
  responses:
    '200':
      description: Payouts retrieved successfully
      content:
        application/json:
          schema:
            type: object
            properties:
              payouts:
                type: array
                items:
                  $ref: '#/components/schemas/Payout'
              pagination:
                $ref: '#/components/schemas/Pagination'
    '404':
      $ref: '#/components/responses/NotFound'
```

#### Process Batch Payouts
```yaml
POST /nodes/payouts/batch:
  summary: Process batch payouts
  description: Process payouts for multiple nodes
  tags: [Payouts]
  requestBody:
    required: true
    content:
      application/json:
        schema:
          type: object
          properties:
            payout_requests:
              type: array
              items:
                type: object
                properties:
                  node_id:
                    type: string
                    pattern: '^node_[a-zA-Z0-9_-]+$'
                  amount:
                    type: number
                    format: decimal
                  currency:
                    type: string
                    enum: [USDT, LUCID]
                  wallet_address:
                    type: string
            batch_id:
              type: string
              description: Unique batch identifier
  responses:
    '202':
      description: Batch payout processing initiated
      content:
        application/json:
          schema:
            type: object
            properties:
              batch_id:
                type: string
              status:
                type: string
                enum: [processing, queued]
              estimated_completion:
                type: string
                format: date-time
    '400':
      $ref: '#/components/responses/BadRequest'
```

## Data Models

### Node
```yaml
Node:
  type: object
  required: [node_id, name, status, created_at]
  properties:
    node_id:
      type: string
      pattern: '^node_[a-zA-Z0-9_-]+$'
      description: Unique node identifier
    name:
      type: string
      maxLength: 100
      description: Human-readable node name
    status:
      type: string
      enum: [active, inactive, maintenance, error, starting, stopping]
      description: Current node status
    node_type:
      type: string
      enum: [worker, validator, storage, compute]
      description: Type of node
    pool_id:
      type: string
      pattern: '^pool_[a-zA-Z0-9_-]+$'
      description: Pool this node belongs to
    hardware_info:
      $ref: '#/components/schemas/HardwareInfo'
    location:
      $ref: '#/components/schemas/NodeLocation'
    created_at:
      type: string
      format: date-time
    updated_at:
      type: string
      format: date-time
    last_heartbeat:
      type: string
      format: date-time
    poot_score:
      type: number
      format: decimal
      minimum: 0
      maximum: 100
```

### NodePool
```yaml
NodePool:
  type: object
  required: [pool_id, name, created_at]
  properties:
    pool_id:
      type: string
      pattern: '^pool_[a-zA-Z0-9_-]+$'
      description: Unique pool identifier
    name:
      type: string
      maxLength: 100
      description: Human-readable pool name
    description:
      type: string
      maxLength: 500
      description: Pool description
    node_count:
      type: integer
      minimum: 0
      description: Number of nodes in pool
    max_nodes:
      type: integer
      minimum: 1
      description: Maximum nodes allowed in pool
    resource_limits:
      $ref: '#/components/schemas/ResourceLimits'
    created_at:
      type: string
      format: date-time
    updated_at:
      type: string
      format: date-time
```

### PoOTScore
```yaml
PoOTScore:
  type: object
  required: [node_id, score, calculated_at]
  properties:
    node_id:
      type: string
      pattern: '^node_[a-zA-Z0-9_-]+$'
    score:
      type: number
      format: decimal
      minimum: 0
      maximum: 100
      description: PoOT score (0-100)
    calculated_at:
      type: string
      format: date-time
    output_hash:
      type: string
      description: Hash of the output data
    validation_status:
      type: string
      enum: [valid, invalid, pending]
    confidence:
      type: number
      format: decimal
      minimum: 0
      maximum: 1
      description: Confidence level of the score
```

### Payout
```yaml
Payout:
  type: object
  required: [payout_id, node_id, amount, status, created_at]
  properties:
    payout_id:
      type: string
      pattern: '^payout_[a-zA-Z0-9_-]+$'
      description: Unique payout identifier
    node_id:
      type: string
      pattern: '^node_[a-zA-Z0-9_-]+$'
    amount:
      type: number
      format: decimal
      minimum: 0
      description: Payout amount
    currency:
      type: string
      enum: [USDT, LUCID]
      default: USDT
    wallet_address:
      type: string
      description: Destination wallet address
    status:
      type: string
      enum: [pending, processing, completed, failed, cancelled]
    transaction_hash:
      type: string
      description: Blockchain transaction hash
    batch_id:
      type: string
      description: Batch identifier for grouped payouts
    created_at:
      type: string
      format: date-time
    processed_at:
      type: string
      format: date-time
    completed_at:
      type: string
      format: date-time
```

## Error Responses

### Standard Error Format
```yaml
ErrorResponse:
  type: object
  required: [error]
  properties:
    error:
      type: object
      required: [code, message, request_id, timestamp]
      properties:
        code:
          type: string
          pattern: '^LUCID_ERR_[0-9]{4}$'
          description: Error code
        message:
          type: string
          description: Human-readable error message
        details:
          type: object
          description: Additional error details
        request_id:
          type: string
          format: uuid
          description: Request identifier for tracing
        timestamp:
          type: string
          format: date-time
          description: Error timestamp
```

### Common Error Codes
- `LUCID_ERR_5001`: Node not found
- `LUCID_ERR_5002`: Pool not found
- `LUCID_ERR_5003`: Invalid node status
- `LUCID_ERR_5004`: Resource limit exceeded
- `LUCID_ERR_5005`: PoOT validation failed
- `LUCID_ERR_5006`: Payout processing failed
- `LUCID_ERR_5007`: Node already exists
- `LUCID_ERR_5008`: Pool already exists
- `LUCID_ERR_5009`: Invalid resource allocation
- `LUCID_ERR_5010`: Batch operation failed
