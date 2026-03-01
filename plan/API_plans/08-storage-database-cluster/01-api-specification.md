# Storage Database Cluster - API Specification

## OpenAPI 3.0 Specification

```yaml
openapi: 3.0.3
info:
  title: Lucid Storage Database API
  description: Database management, backup, and storage operations for Lucid blockchain system
  version: 1.0.0
  contact:
    name: Lucid Development Team
    email: dev@lucid-blockchain.org
  license:
    name: MIT
    url: https://opensource.org/licenses/MIT

servers:
  - url: https://storage.lucid-blockchain.org/api/v1
    description: Production storage server
  - url: https://storage-dev.lucid-blockchain.org/api/v1
    description: Development storage server
  - url: http://localhost:8089/api/v1
    description: Local development server

security:
  - BearerAuth: []
  - ApiKeyAuth: []

paths:
  # Database Management Endpoints
  /database/health:
    get:
      tags: [Database]
      summary: Get database health status
      description: Returns comprehensive health status of all database services
      security:
        - BearerAuth: []
      responses:
        '200':
          description: Database health status retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/DatabaseHealthResponse'
        '503':
          description: Database service unhealthy
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /database/stats:
    get:
      tags: [Database]
      summary: Get database statistics
      description: Returns comprehensive statistics for all database services
      security:
        - BearerAuth: []
      responses:
        '200':
          description: Database statistics retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/DatabaseStatsResponse'

  /database/collections:
    get:
      tags: [Database]
      summary: List all collections
      description: Returns a list of all database collections with metadata
      security:
        - BearerAuth: []
      responses:
        '200':
          description: Collections list retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CollectionListResponse'

    post:
      tags: [Database]
      summary: Create new collection
      description: Creates a new database collection with specified configuration
      security:
        - BearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CollectionCreateRequest'
      responses:
        '201':
          description: Collection created successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CollectionResponse'
        '400':
          description: Invalid collection configuration
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '409':
          description: Collection already exists
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /database/collections/{collection_name}:
    get:
      tags: [Database]
      summary: Get collection details
      description: Returns detailed information about a specific collection
      security:
        - BearerAuth: []
      parameters:
        - name: collection_name
          in: path
          required: true
          schema:
            type: string
            minLength: 1
            maxLength: 100
      responses:
        '200':
          description: Collection details retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CollectionResponse'
        '404':
          description: Collection not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

    delete:
      tags: [Database]
      summary: Drop collection
      description: Drops an existing collection and all its data
      security:
        - BearerAuth: []
      parameters:
        - name: collection_name
          in: path
          required: true
          schema:
            type: string
            minLength: 1
            maxLength: 100
        - name: confirm
          in: query
          required: true
          schema:
            type: boolean
      responses:
        '204':
          description: Collection dropped successfully
        '400':
          description: Confirmation required or invalid collection name
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '404':
          description: Collection not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /database/collections/{collection_name}/indexes:
    get:
      tags: [Database]
      summary: List collection indexes
      description: Returns all indexes for a specific collection
      security:
        - BearerAuth: []
      parameters:
        - name: collection_name
          in: path
          required: true
          schema:
            type: string
            minLength: 1
            maxLength: 100
      responses:
        '200':
          description: Indexes retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/IndexListResponse'

    post:
      tags: [Database]
      summary: Create collection index
      description: Creates a new index for a specific collection
      security:
        - BearerAuth: []
      parameters:
        - name: collection_name
          in: path
          required: true
          schema:
            type: string
            minLength: 1
            maxLength: 100
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/IndexCreateRequest'
      responses:
        '201':
          description: Index created successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/IndexResponse'
        '400':
          description: Invalid index configuration
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /database/collections/{collection_name}/indexes/{index_name}:
    delete:
      tags: [Database]
      summary: Drop collection index
      description: Drops an existing index from a collection
      security:
        - BearerAuth: []
      parameters:
        - name: collection_name
          in: path
          required: true
          schema:
            type: string
            minLength: 1
            maxLength: 100
        - name: index_name
          in: path
          required: true
          schema:
            type: string
            minLength: 1
            maxLength: 100
      responses:
        '204':
          description: Index dropped successfully
        '404':
          description: Index not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  # Sharding Management Endpoints
  /database/sharding/status:
    get:
      tags: [Sharding]
      summary: Get sharding status
      description: Returns the current sharding configuration and status
      security:
        - BearerAuth: []
      responses:
        '200':
          description: Sharding status retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ShardingStatusResponse'

  /database/sharding/enable:
    post:
      tags: [Sharding]
      summary: Enable sharding
      description: Enables sharding for the database cluster
      security:
        - BearerAuth: []
      responses:
        '200':
          description: Sharding enabled successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ShardingOperationResponse'

  /database/sharding/shard-collection:
    post:
      tags: [Sharding]
      summary: Shard collection
      description: Enables sharding for a specific collection
      security:
        - BearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ShardCollectionRequest'
      responses:
        '200':
          description: Collection sharding enabled successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ShardingOperationResponse'
        '400':
          description: Invalid sharding configuration
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /database/sharding/balancer:
    get:
      tags: [Sharding]
      summary: Get balancer status
      description: Returns the current status of the shard balancer
      security:
        - BearerAuth: []
      responses:
        '200':
          description: Balancer status retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/BalancerStatusResponse'

  /database/sharding/balancer/start:
    post:
      tags: [Sharding]
      summary: Start balancer
      description: Starts the shard balancer
      security:
        - BearerAuth: []
      responses:
        '200':
          description: Balancer started successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ShardingOperationResponse'

  /database/sharding/balancer/stop:
    post:
      tags: [Sharding]
      summary: Stop balancer
      description: Stops the shard balancer
      security:
        - BearerAuth: []
      responses:
        '200':
          description: Balancer stopped successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ShardingOperationResponse'

  # Backup Management Endpoints
  /backups:
    get:
      tags: [Backups]
      summary: List available backups
      description: Returns a list of all available database backups
      security:
        - BearerAuth: []
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
        - name: type
          in: query
          schema:
            type: string
            enum: [full, incremental, differential]
        - name: status
          in: query
          schema:
            type: string
            enum: [completed, failed, in_progress, cancelled]
      responses:
        '200':
          description: Backups list retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/BackupListResponse'

    post:
      tags: [Backups]
      summary: Create new backup
      description: Creates a new database backup with specified configuration
      security:
        - BearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/BackupCreateRequest'
      responses:
        '201':
          description: Backup created successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/BackupResponse'
        '400':
          description: Invalid backup configuration
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /backups/{backup_id}:
    get:
      tags: [Backups]
      summary: Get backup details
      description: Returns detailed information about a specific backup
      security:
        - BearerAuth: []
      parameters:
        - name: backup_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Backup details retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/BackupResponse'
        '404':
          description: Backup not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

    delete:
      tags: [Backups]
      summary: Delete backup
      description: Deletes an existing backup and its associated files
      security:
        - BearerAuth: []
      parameters:
        - name: backup_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '204':
          description: Backup deleted successfully
        '404':
          description: Backup not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /backups/{backup_id}/restore:
    post:
      tags: [Backups]
      summary: Restore from backup
      description: Restores database from a specific backup
      security:
        - BearerAuth: []
      parameters:
        - name: backup_id
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
              $ref: '#/components/schemas/RestoreRequest'
      responses:
        '202':
          description: Restore operation started successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/RestoreResponse'
        '400':
          description: Invalid restore configuration
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '404':
          description: Backup not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /backups/schedules:
    get:
      tags: [Backups]
      summary: List backup schedules
      description: Returns all configured backup schedules
      security:
        - BearerAuth: []
      responses:
        '200':
          description: Backup schedules retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ScheduleListResponse'

    post:
      tags: [Backups]
      summary: Create backup schedule
      description: Creates a new automated backup schedule
      security:
        - BearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ScheduleCreateRequest'
      responses:
        '201':
          description: Backup schedule created successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ScheduleResponse'
        '400':
          description: Invalid schedule configuration
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key

  schemas:
    # Database Health and Stats Schemas
    DatabaseHealthResponse:
      type: object
      properties:
        status:
          type: string
          enum: [healthy, unhealthy, degraded]
        timestamp:
          type: string
          format: date-time
        services:
          type: object
          properties:
            mongodb:
              $ref: '#/components/schemas/ServiceHealth'
            redis:
              $ref: '#/components/schemas/ServiceHealth'
            elasticsearch:
              $ref: '#/components/schemas/ServiceHealth'
        uptime:
          type: integer
          description: "Uptime in seconds"

    ServiceHealth:
      type: object
      properties:
        status:
          type: string
          enum: [healthy, unhealthy, degraded]
        version:
          type: string
        response_time:
          type: number
        last_check:
          type: string
          format: date-time

    DatabaseStatsResponse:
      type: object
      properties:
        mongodb:
          $ref: '#/components/schemas/MongoDBStats'
        redis:
          $ref: '#/components/schemas/RedisStats'
        elasticsearch:
          $ref: '#/components/schemas/ElasticsearchStats'
        timestamp:
          type: string
          format: date-time

    MongoDBStats:
      type: object
      properties:
        collections:
          type: integer
        documents:
          type: integer
        data_size:
          type: integer
        storage_size:
          type: integer
        indexes:
          type: integer
        index_size:
          type: integer
        connections:
          type: object
          properties:
            current:
              type: integer
            available:
              type: integer
        operations:
          type: object
          properties:
            insert:
              type: integer
            query:
              type: integer
            update:
              type: integer
            delete:
              type: integer

    RedisStats:
      type: object
      properties:
        connected_clients:
          type: integer
        used_memory:
          type: integer
        used_memory_human:
          type: string
        total_commands_processed:
          type: integer
        keyspace_hits:
          type: integer
        keyspace_misses:
          type: integer
        hit_rate:
          type: number

    ElasticsearchStats:
      type: object
      properties:
        cluster_name:
          type: string
        cluster_status:
          type: string
        indices:
          type: integer
        documents:
          type: integer
        store_size:
          type: integer
        nodes:
          type: integer

    # Collection Management Schemas
    CollectionListResponse:
      type: object
      properties:
        collections:
          type: array
          items:
            $ref: '#/components/schemas/CollectionResponse'
        pagination:
          $ref: '#/components/schemas/PaginationInfo'

    CollectionResponse:
      type: object
      properties:
        name:
          type: string
        database:
          type: string
        document_count:
          type: integer
        data_size:
          type: integer
        storage_size:
          type: integer
        index_count:
          type: integer
        index_size:
          type: integer
        created_at:
          type: string
          format: date-time
        updated_at:
          type: string
          format: date-time

    CollectionCreateRequest:
      type: object
      required: [name]
      properties:
        name:
          type: string
          minLength: 1
          maxLength: 100
        database:
          type: string
          default: "lucid_blockchain"
        options:
          type: object
          properties:
            capped:
              type: boolean
              default: false
            size:
              type: integer
              minimum: 0
            max:
              type: integer
              minimum: 0

    # Index Management Schemas
    IndexListResponse:
      type: object
      properties:
        indexes:
          type: array
          items:
            $ref: '#/components/schemas/IndexResponse'

    IndexResponse:
      type: object
      properties:
        name:
          type: string
        collection:
          type: string
        key:
          type: object
          additionalProperties:
            type: integer
            enum: [1, -1, "2d", "2dsphere", "text", "hashed"]
        unique:
          type: boolean
        sparse:
          type: boolean
        background:
          type: boolean
        size:
          type: integer
        created_at:
          type: string
          format: date-time

    IndexCreateRequest:
      type: object
      required: [key]
      properties:
        key:
          type: object
          additionalProperties:
            type: integer
            enum: [1, -1, "2d", "2dsphere", "text", "hashed"]
        name:
          type: string
        unique:
          type: boolean
          default: false
        sparse:
          type: boolean
          default: false
        background:
          type: boolean
          default: true

    # Sharding Schemas
    ShardingStatusResponse:
      type: object
      properties:
        enabled:
          type: boolean
        config_servers:
          type: array
          items:
            type: string
        shards:
          type: array
          items:
            $ref: '#/components/schemas/ShardInfo'
        databases:
          type: array
          items:
            $ref: '#/components/schemas/DatabaseShardInfo'

    ShardInfo:
      type: object
      properties:
        id:
          type: string
        host:
          type: string
        state:
          type: string
          enum: [up, down, starting, unknown]
        tags:
          type: array
          items:
            type: string

    DatabaseShardInfo:
      type: object
      properties:
        database:
          type: string
        primary:
          type: string
        partitioned:
          type: boolean

    ShardCollectionRequest:
      type: object
      required: [collection, shard_key]
      properties:
        collection:
          type: string
        shard_key:
          type: object
          additionalProperties:
            type: string
            enum: ["hashed", "1", "-1"]
        unique:
          type: boolean
          default: false
        num_initial_chunks:
          type: integer
          minimum: 1
          default: 1

    BalancerStatusResponse:
      type: object
      properties:
        mode:
          type: string
          enum: [full, off]
        in_balancer_round:
          type: boolean
        num_balancer_rounds:
          type: integer
        time_of_last_balancer_start:
          type: string
          format: date-time
        time_of_last_balancer_end:
          type: string
          format: date-time

    ShardingOperationResponse:
      type: object
      properties:
        success:
          type: boolean
        message:
          type: string
        operation_id:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time

    # Backup Management Schemas
    BackupListResponse:
      type: object
      properties:
        backups:
          type: array
          items:
            $ref: '#/components/schemas/BackupResponse'
        pagination:
          $ref: '#/components/schemas/PaginationInfo'

    BackupResponse:
      type: object
      properties:
        backup_id:
          type: string
          format: uuid
        name:
          type: string
        type:
          type: string
          enum: [full, incremental, differential]
        status:
          type: string
          enum: [in_progress, completed, failed, cancelled]
        size_bytes:
          type: integer
        created_at:
          type: string
          format: date-time
        completed_at:
          type: string
          format: date-time
        expires_at:
          type: string
          format: date-time
        collections:
          type: array
          items:
            type: string
        compression:
          type: boolean
        encryption:
          type: boolean

    BackupCreateRequest:
      type: object
      required: [name, type]
      properties:
        name:
          type: string
          minLength: 1
          maxLength: 255
        type:
          type: string
          enum: [full, incremental, differential]
        collections:
          type: array
          items:
            type: string
        compression:
          type: boolean
          default: true
        encryption:
          type: boolean
          default: true
        retention_days:
          type: integer
          minimum: 1
          maximum: 365
          default: 30

    RestoreRequest:
      type: object
      required: [target_database]
      properties:
        target_database:
          type: string
        collections:
          type: array
          items:
            type: string
        drop_existing:
          type: boolean
          default: false
        point_in_time:
          type: string
          format: date-time

    RestoreResponse:
      type: object
      properties:
        restore_id:
          type: string
          format: uuid
        status:
          type: string
          enum: [started, in_progress, completed, failed]
        message:
          type: string
        started_at:
          type: string
          format: date-time
        estimated_completion:
          type: string
          format: date-time

    # Schedule Management Schemas
    ScheduleListResponse:
      type: object
      properties:
        schedules:
          type: array
          items:
            $ref: '#/components/schemas/ScheduleResponse'

    ScheduleResponse:
      type: object
      properties:
        schedule_id:
          type: string
          format: uuid
        name:
          type: string
        cron_expression:
          type: string
        backup_type:
          type: string
          enum: [full, incremental, differential]
        enabled:
          type: boolean
        last_run:
          type: string
          format: date-time
        next_run:
          type: string
          format: date-time
        created_at:
          type: string
          format: date-time

    ScheduleCreateRequest:
      type: object
      required: [name, cron_expression, backup_type]
      properties:
        name:
          type: string
          minLength: 1
          maxLength: 255
        cron_expression:
          type: string
          pattern: '^(\*|([0-5]?\d)) (\*|([01]?\d|2[0-3])) (\*|([012]?\d|3[01])) (\*|([0]?\d|1[0-2])) (\*|([0-6]))$'
        backup_type:
          type: string
          enum: [full, incremental, differential]
        collections:
          type: array
          items:
            type: string
        retention_days:
          type: integer
          minimum: 1
          maximum: 365
          default: 30

    # Common Schemas
    PaginationInfo:
      type: object
      properties:
        page:
          type: integer
        limit:
          type: integer
        total:
          type: integer
        pages:
          type: integer

    ErrorResponse:
      type: object
      properties:
        error:
          type: object
          properties:
            code:
              type: string
              example: "LUCID_ERR_5001"
            message:
              type: string
              example: "Database connection failed"
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
              example: "storage-database"
            version:
              type: string
              example: "v1"

tags:
  - name: Database
    description: Database management and administration
  - name: Sharding
    description: MongoDB sharding operations
  - name: Backups
    description: Backup and restore operations
```

## Rate Limiting Specifications

### Database Operation Rate Limits
```yaml
rate_limits:
  database_operations:
    requests_per_minute: 500
    burst_size: 1000
    endpoints:
      - "/api/v1/database/*"
  
  backup_operations:
    requests_per_minute: 10
    burst_size: 20
    endpoints:
      - "/api/v1/backups/*"
  
  sharding_operations:
    requests_per_minute: 5
    burst_size: 10
    endpoints:
      - "/api/v1/database/sharding/*"
```

## Error Code Registry

### Database Errors (LUCID_ERR_5XXX)
- `LUCID_ERR_5001`: Database connection failed
- `LUCID_ERR_5002`: Collection not found
- `LUCID_ERR_5003`: Index creation failed
- `LUCID_ERR_5004`: Sharding operation failed
- `LUCID_ERR_5005`: Backup operation failed
- `LUCID_ERR_5006`: Restore operation failed
- `LUCID_ERR_5007`: Database query timeout
- `LUCID_ERR_5008`: Insufficient disk space
- `LUCID_ERR_5009`: Database lock timeout
- `LUCID_ERR_5010`: Replication lag exceeded

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-01-10  
**Next Review**: 2025-02-10
