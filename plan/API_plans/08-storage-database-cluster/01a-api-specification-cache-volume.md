# Storage Database Cluster - API Specification (Cache & Volume Management)

## Cache Management Endpoints

```yaml
paths:
  # Cache Management Endpoints
  /cache/stats:
    get:
      tags: [Cache]
      summary: Get cache statistics
      description: Returns comprehensive statistics for Redis cache service
      security:
        - BearerAuth: []
      responses:
        '200':
          description: Cache statistics retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CacheStatsResponse'

  /cache/keys:
    get:
      tags: [Cache]
      summary: List cache keys
      description: Returns a paginated list of cache keys with metadata
      security:
        - BearerAuth: []
      parameters:
        - name: pattern
          in: query
          schema:
            type: string
            default: "*"
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
            maximum: 1000
            default: 100
      responses:
        '200':
          description: Cache keys retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CacheKeyListResponse'

  /cache/keys/{key}:
    get:
      tags: [Cache]
      summary: Get cache value
      description: Returns the value for a specific cache key
      security:
        - BearerAuth: []
      parameters:
        - name: key
          in: path
          required: true
          schema:
            type: string
        - name: format
          in: query
          schema:
            type: string
            enum: [json, raw, base64]
            default: json
      responses:
        '200':
          description: Cache value retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CacheValueResponse'
        '404':
          description: Cache key not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

    put:
      tags: [Cache]
      summary: Set cache value
      description: Sets a value for a specific cache key
      security:
        - BearerAuth: []
      parameters:
        - name: key
          in: path
          required: true
          schema:
            type: string
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CacheSetRequest'
      responses:
        '200':
          description: Cache value set successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CacheOperationResponse'

    delete:
      tags: [Cache]
      summary: Delete cache key
      description: Deletes a specific cache key and its value
      security:
        - BearerAuth: []
      parameters:
        - name: key
          in: path
          required: true
          schema:
            type: string
      responses:
        '204':
          description: Cache key deleted successfully
        '404':
          description: Cache key not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /cache/flush:
    post:
      tags: [Cache]
      summary: Flush entire cache
      description: Clears all cache data from Redis
      security:
        - BearerAuth: []
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                confirm:
                  type: boolean
                  default: false
      responses:
        '200':
          description: Cache flushed successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CacheOperationResponse'
        '400':
          description: Confirmation required
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /cache/memory:
    get:
      tags: [Cache]
      summary: Get memory usage statistics
      description: Returns detailed memory usage statistics for Redis
      security:
        - BearerAuth: []
      responses:
        '200':
          description: Memory statistics retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CacheMemoryResponse'

  # Volume Management Endpoints
  /volumes:
    get:
      tags: [Volumes]
      summary: List storage volumes
      description: Returns a list of all storage volumes with metadata
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
        - name: status
          in: query
          schema:
            type: string
            enum: [active, inactive, error, maintenance]
      responses:
        '200':
          description: Volumes list retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/VolumeListResponse'

    post:
      tags: [Volumes]
      summary: Create new volume
      description: Creates a new storage volume with specified configuration
      security:
        - BearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/VolumeCreateRequest'
      responses:
        '201':
          description: Volume created successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/VolumeResponse'
        '400':
          description: Invalid volume configuration
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /volumes/{volume_id}:
    get:
      tags: [Volumes]
      summary: Get volume details
      description: Returns detailed information about a specific volume
      security:
        - BearerAuth: []
      parameters:
        - name: volume_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Volume details retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/VolumeResponse'
        '404':
          description: Volume not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

    put:
      tags: [Volumes]
      summary: Update volume
      description: Updates volume configuration or metadata
      security:
        - BearerAuth: []
      parameters:
        - name: volume_id
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
              $ref: '#/components/schemas/VolumeUpdateRequest'
      responses:
        '200':
          description: Volume updated successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/VolumeResponse'
        '400':
          description: Invalid update data
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '404':
          description: Volume not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

    delete:
      tags: [Volumes]
      summary: Delete volume
      description: Deletes a storage volume and all its data
      security:
        - BearerAuth: []
      parameters:
        - name: volume_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
        - name: confirm
          in: query
          required: true
          schema:
            type: boolean
      responses:
        '204':
          description: Volume deleted successfully
        '400':
          description: Confirmation required
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '404':
          description: Volume not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /volumes/{volume_id}/resize:
    put:
      tags: [Volumes]
      summary: Resize volume
      description: Resizes a storage volume to new capacity
      security:
        - BearerAuth: []
      parameters:
        - name: volume_id
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
              $ref: '#/components/schemas/VolumeResizeRequest'
      responses:
        '200':
          description: Volume resize operation started
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/VolumeOperationResponse'
        '400':
          description: Invalid resize parameters
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '404':
          description: Volume not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /volumes/{volume_id}/usage:
    get:
      tags: [Volumes]
      summary: Get volume usage statistics
      description: Returns detailed usage statistics for a volume
      security:
        - BearerAuth: []
      parameters:
        - name: volume_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
        - name: period
          in: query
          schema:
            type: string
            enum: [1h, 24h, 7d, 30d]
            default: 24h
      responses:
        '200':
          description: Volume usage statistics retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/VolumeUsageResponse'
        '404':
          description: Volume not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /volumes/{volume_id}/migrate:
    post:
      tags: [Volumes]
      summary: Migrate volume data
      description: Migrates data from one volume to another
      security:
        - BearerAuth: []
      parameters:
        - name: volume_id
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
              $ref: '#/components/schemas/VolumeMigrationRequest'
      responses:
        '202':
          description: Volume migration started
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/VolumeOperationResponse'
        '400':
          description: Invalid migration parameters
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '404':
          description: Volume not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  # Search Management Endpoints
  /search/indices:
    get:
      tags: [Search]
      summary: List search indices
      description: Returns a list of all Elasticsearch indices
      security:
        - BearerAuth: []
      parameters:
        - name: pattern
          in: query
          schema:
            type: string
            default: "*"
      responses:
        '200':
          description: Search indices retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SearchIndexListResponse'

    post:
      tags: [Search]
      summary: Create search index
      description: Creates a new Elasticsearch index with specified mapping
      security:
        - BearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/SearchIndexCreateRequest'
      responses:
        '201':
          description: Search index created successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SearchIndexResponse'
        '400':
          description: Invalid index configuration
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /search/indices/{index_name}:
    get:
      tags: [Search]
      summary: Get search index details
      description: Returns detailed information about a specific index
      security:
        - BearerAuth: []
      parameters:
        - name: index_name
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Index details retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SearchIndexResponse'
        '404':
          description: Index not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

    delete:
      tags: [Search]
      summary: Delete search index
      description: Deletes an Elasticsearch index and all its data
      security:
        - BearerAuth: []
      parameters:
        - name: index_name
          in: path
          required: true
          schema:
            type: string
        - name: confirm
          in: query
          required: true
          schema:
            type: boolean
      responses:
        '204':
          description: Index deleted successfully
        '400':
          description: Confirmation required
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '404':
          description: Index not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /search/indices/{index_name}/reindex:
    post:
      tags: [Search]
      summary: Reindex data
      description: Reindexes data for a specific index
      security:
        - BearerAuth: []
      parameters:
        - name: index_name
          in: path
          required: true
          schema:
            type: string
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/SearchReindexRequest'
      responses:
        '202':
          description: Reindex operation started
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SearchOperationResponse'
        '400':
          description: Invalid reindex parameters
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '404':
          description: Index not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /search/indices/{index_name}/stats:
    get:
      tags: [Search]
      summary: Get index statistics
      description: Returns statistics for a specific index
      security:
        - BearerAuth: []
      parameters:
        - name: index_name
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Index statistics retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SearchIndexStatsResponse'
        '404':
          description: Index not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /search/query:
    post:
      tags: [Search]
      summary: Execute search query
      description: Executes a search query across specified indices
      security:
        - BearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/SearchQueryRequest'
      responses:
        '200':
          description: Search query executed successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SearchQueryResponse'
        '400':
          description: Invalid search query
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
```

## Cache Management Schemas

```yaml
components:
  schemas:
    # Cache Management Schemas
    CacheStatsResponse:
      type: object
      properties:
        total_keys:
          type: integer
        memory_usage:
          type: integer
        memory_usage_human:
          type: string
        hit_rate:
          type: number
        connected_clients:
          type: integer
        total_commands:
          type: integer
        keyspace_hits:
          type: integer
        keyspace_misses:
          type: integer
        uptime:
          type: integer
        timestamp:
          type: string
          format: date-time

    CacheKeyListResponse:
      type: object
      properties:
        keys:
          type: array
          items:
            $ref: '#/components/schemas/CacheKeyInfo'
        pagination:
          $ref: '#/components/schemas/PaginationInfo'

    CacheKeyInfo:
      type: object
      properties:
        key:
          type: string
        type:
          type: string
        ttl:
          type: integer
        size:
          type: integer
        created_at:
          type: string
          format: date-time

    CacheValueResponse:
      type: object
      properties:
        key:
          type: string
        value:
          oneOf:
            - type: string
            - type: object
            - type: array
            - type: number
            - type: boolean
        type:
          type: string
        ttl:
          type: integer
        size:
          type: integer

    CacheSetRequest:
      type: object
      required: [value]
      properties:
        value:
          oneOf:
            - type: string
            - type: object
            - type: array
            - type: number
            - type: boolean
        ttl:
          type: integer
          minimum: 1
          description: "Time to live in seconds"
        nx:
          type: boolean
          default: false
          description: "Set only if key does not exist"

    CacheOperationResponse:
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

    CacheMemoryResponse:
      type: object
      properties:
        used_memory:
          type: integer
        used_memory_human:
          type: string
        used_memory_rss:
          type: integer
        used_memory_peak:
          type: integer
        used_memory_peak_human:
          type: string
        mem_fragmentation_ratio:
          type: number
        maxmemory:
          type: integer
        maxmemory_human:
          type: string

    # Volume Management Schemas
    VolumeListResponse:
      type: object
      properties:
        volumes:
          type: array
          items:
            $ref: '#/components/schemas/VolumeResponse'
        pagination:
          $ref: '#/components/schemas/PaginationInfo'

    VolumeResponse:
      type: object
      properties:
        volume_id:
          type: string
          format: uuid
        name:
          type: string
        path:
          type: string
        size_bytes:
          type: integer
        used_bytes:
          type: integer
        available_bytes:
          type: integer
        usage_percentage:
          type: number
        status:
          type: string
          enum: [active, inactive, error, maintenance]
        type:
          type: string
          enum: [local, network, cloud]
        mount_point:
          type: string
        file_system:
          type: string
        created_at:
          type: string
          format: date-time
        updated_at:
          type: string
          format: date-time

    VolumeCreateRequest:
      type: object
      required: [name, size_bytes, type]
      properties:
        name:
          type: string
          minLength: 1
          maxLength: 255
        size_bytes:
          type: integer
          minimum: 1073741824  # 1GB minimum
        type:
          type: string
          enum: [local, network, cloud]
        mount_point:
          type: string
        file_system:
          type: string
          enum: [ext4, xfs, ntfs, fat32]
          default: ext4
        encryption:
          type: boolean
          default: false
        compression:
          type: boolean
          default: false

    VolumeUpdateRequest:
      type: object
      properties:
        name:
          type: string
          minLength: 1
          maxLength: 255
        status:
          type: string
          enum: [active, inactive, maintenance]
        encryption:
          type: boolean
        compression:
          type: boolean

    VolumeResizeRequest:
      type: object
      required: [new_size_bytes]
      properties:
        new_size_bytes:
          type: integer
          minimum: 1073741824  # 1GB minimum
        resize_type:
          type: string
          enum: [extend, shrink]
          default: extend

    VolumeUsageResponse:
      type: object
      properties:
        volume_id:
          type: string
          format: uuid
        period:
          type: string
        usage_history:
          type: array
          items:
            $ref: '#/components/schemas/VolumeUsagePoint'
        current_usage:
          $ref: '#/components/schemas/VolumeUsagePoint'

    VolumeUsagePoint:
      type: object
      properties:
        timestamp:
          type: string
          format: date-time
        used_bytes:
          type: integer
        available_bytes:
          type: integer
        usage_percentage:
          type: number
        iops:
          type: integer
        throughput:
          type: integer

    VolumeMigrationRequest:
      type: object
      required: [target_volume_id]
      properties:
        target_volume_id:
          type: string
          format: uuid
        migration_type:
          type: string
          enum: [copy, move]
          default: copy
        verify_integrity:
          type: boolean
          default: true

    VolumeOperationResponse:
      type: object
      properties:
        operation_id:
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

    # Search Management Schemas
    SearchIndexListResponse:
      type: object
      properties:
        indices:
          type: array
          items:
            $ref: '#/components/schemas/SearchIndexResponse'

    SearchIndexResponse:
      type: object
      properties:
        name:
          type: string
        health:
          type: string
          enum: [green, yellow, red]
        status:
          type: string
          enum: [open, closed]
        document_count:
          type: integer
        store_size:
          type: integer
        store_size_human:
          type: string
        created_at:
          type: string
          format: date-time
        mappings:
          type: object

    SearchIndexCreateRequest:
      type: object
      required: [name]
      properties:
        name:
          type: string
          pattern: '^[a-z][a-z0-9_-]*$'
        shards:
          type: integer
          minimum: 1
          default: 3
        replicas:
          type: integer
          minimum: 0
          default: 1
        mappings:
          type: object
        settings:
          type: object

    SearchReindexRequest:
      type: object
      properties:
        source_index:
          type: string
        dest_index:
          type: string
        query:
          type: object
        batch_size:
          type: integer
          minimum: 100
          default: 1000
        refresh:
          type: boolean
          default: true

    SearchIndexStatsResponse:
      type: object
      properties:
        name:
          type: string
        total:
          type: object
          properties:
            docs:
              type: object
              properties:
                count:
                  type: integer
                deleted:
                  type: integer
            store:
              type: object
              properties:
                size_in_bytes:
                  type: integer
            indexing:
              type: object
              properties:
                index_total:
                  type: integer
                index_time_in_millis:
                  type: integer
            search:
              type: object
              properties:
                query_total:
                  type: integer
                query_time_in_millis:
                  type: integer

    SearchQueryRequest:
      type: object
      required: [query]
      properties:
        indices:
          type: array
          items:
            type: string
        query:
          type: object
        size:
          type: integer
          minimum: 1
          maximum: 10000
          default: 10
        from:
          type: integer
          minimum: 0
          default: 0
        sort:
          type: array
          items:
            type: object
        fields:
          type: array
          items:
            type: string

    SearchQueryResponse:
      type: object
      properties:
        took:
          type: integer
        timed_out:
          type: boolean
        hits:
          type: object
          properties:
            total:
              type: object
              properties:
                value:
                  type: integer
                relation:
                  type: string
            max_score:
              type: number
            hits:
              type: array
              items:
                type: object
        aggregations:
          type: object

    SearchOperationResponse:
      type: object
      properties:
        operation_id:
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

tags:
  - name: Cache
    description: Redis cache management
  - name: Volumes
    description: Storage volume management
  - name: Search
    description: Elasticsearch search management
```

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-01-10  
**Next Review**: 2025-02-10
