# Node Management Cluster Data Models

## Request/Response Schemas

### Node Management Schemas

#### NodeCreateRequest
```json
{
  "name": {
    "type": "string",
    "maxLength": 100,
    "minLength": 3,
    "pattern": "^[a-zA-Z0-9_-]+$",
    "description": "Human-readable node name"
  },
  "node_type": {
    "type": "string",
    "enum": ["worker", "validator", "storage", "compute"],
    "description": "Type of node"
  },
  "hardware_info": {
    "$ref": "#/components/schemas/HardwareInfo"
  },
  "location": {
    "$ref": "#/components/schemas/NodeLocation"
  },
  "initial_pool_id": {
    "type": "string",
    "pattern": "^pool_[a-zA-Z0-9_-]+$",
    "description": "Initial pool assignment"
  },
  "configuration": {
    "$ref": "#/components/schemas/NodeConfiguration"
  }
}
```

#### NodeUpdateRequest
```json
{
  "name": {
    "type": "string",
    "maxLength": 100,
    "minLength": 3,
    "pattern": "^[a-zA-Z0-9_-]+$"
  },
  "node_type": {
    "type": "string",
    "enum": ["worker", "validator", "storage", "compute"]
  },
  "pool_id": {
    "type": "string",
    "pattern": "^pool_[a-zA-Z0-9_-]+$"
  },
  "configuration": {
    "$ref": "#/components/schemas/NodeConfiguration"
  },
  "status": {
    "type": "string",
    "enum": ["active", "inactive", "maintenance", "error"]
  }
}
```

#### NodePoolCreateRequest
```json
{
  "name": {
    "type": "string",
    "maxLength": 100,
    "minLength": 3,
    "pattern": "^[a-zA-Z0-9_-]+$"
  },
  "description": {
    "type": "string",
    "maxLength": 500
  },
  "max_nodes": {
    "type": "integer",
    "minimum": 1,
    "maximum": 1000,
    "default": 100
  },
  "resource_limits": {
    "$ref": "#/components/schemas/ResourceLimits"
  },
  "auto_scaling": {
    "type": "boolean",
    "default": false
  },
  "scaling_policy": {
    "$ref": "#/components/schemas/ScalingPolicy"
  }
}
```

### Resource Monitoring Schemas

#### ResourceMetrics
```json
{
  "node_id": {
    "type": "string",
    "pattern": "^node_[a-zA-Z0-9_-]+$"
  },
  "timestamp": {
    "type": "string",
    "format": "date-time"
  },
  "cpu": {
    "$ref": "#/components/schemas/CPUMetrics"
  },
  "memory": {
    "$ref": "#/components/schemas/MemoryMetrics"
  },
  "disk": {
    "$ref": "#/components/schemas/DiskMetrics"
  },
  "network": {
    "$ref": "#/components/schemas/NetworkMetrics"
  },
  "gpu": {
    "$ref": "#/components/schemas/GPUMetrics"
  }
}
```

#### CPUMetrics
```json
{
  "usage_percent": {
    "type": "number",
    "minimum": 0,
    "maximum": 100,
    "description": "CPU usage percentage"
  },
  "cores": {
    "type": "integer",
    "minimum": 1,
    "description": "Number of CPU cores"
  },
  "frequency_mhz": {
    "type": "number",
    "minimum": 0,
    "description": "CPU frequency in MHz"
  },
  "load_average": {
    "type": "array",
    "items": {
      "type": "number",
      "minimum": 0
    },
    "maxItems": 3,
    "description": "1min, 5min, 15min load averages"
  },
  "temperature_celsius": {
    "type": "number",
    "description": "CPU temperature"
  }
}
```

#### MemoryMetrics
```json
{
  "total_bytes": {
    "type": "integer",
    "minimum": 0,
    "description": "Total memory in bytes"
  },
  "used_bytes": {
    "type": "integer",
    "minimum": 0,
    "description": "Used memory in bytes"
  },
  "free_bytes": {
    "type": "integer",
    "minimum": 0,
    "description": "Free memory in bytes"
  },
  "cached_bytes": {
    "type": "integer",
    "minimum": 0,
    "description": "Cached memory in bytes"
  },
  "swap_total_bytes": {
    "type": "integer",
    "minimum": 0,
    "description": "Total swap in bytes"
  },
  "swap_used_bytes": {
    "type": "integer",
    "minimum": 0,
    "description": "Used swap in bytes"
  }
}
```

#### DiskMetrics
```json
{
  "total_bytes": {
    "type": "integer",
    "minimum": 0,
    "description": "Total disk space in bytes"
  },
  "used_bytes": {
    "type": "integer",
    "minimum": 0,
    "description": "Used disk space in bytes"
  },
  "free_bytes": {
    "type": "integer",
    "minimum": 0,
    "description": "Free disk space in bytes"
  },
  "read_iops": {
    "type": "integer",
    "minimum": 0,
    "description": "Read operations per second"
  },
  "write_iops": {
    "type": "integer",
    "minimum": 0,
    "description": "Write operations per second"
  },
  "read_throughput_mbps": {
    "type": "number",
    "minimum": 0,
    "description": "Read throughput in MB/s"
  },
  "write_throughput_mbps": {
    "type": "number",
    "minimum": 0,
    "description": "Write throughput in MB/s"
  }
}
```

#### NetworkMetrics
```json
{
  "interfaces": {
    "type": "array",
    "items": {
      "$ref": "#/components/schemas/NetworkInterface"
    }
  },
  "total_bytes_in": {
    "type": "integer",
    "minimum": 0,
    "description": "Total bytes received"
  },
  "total_bytes_out": {
    "type": "integer",
    "minimum": 0,
    "description": "Total bytes sent"
  },
  "packets_in": {
    "type": "integer",
    "minimum": 0,
    "description": "Total packets received"
  },
  "packets_out": {
    "type": "integer",
    "minimum": 0,
    "description": "Total packets sent"
  },
  "errors_in": {
    "type": "integer",
    "minimum": 0,
    "description": "Receive errors"
  },
  "errors_out": {
    "type": "integer",
    "minimum": 0,
    "description": "Transmit errors"
  }
}
```

### PoOT Schemas

#### PoOTValidation
```json
{
  "node_id": {
    "type": "string",
    "pattern": "^node_[a-zA-Z0-9_-]+$"
  },
  "validation_id": {
    "type": "string",
    "format": "uuid"
  },
  "is_valid": {
    "type": "boolean",
    "description": "Whether PoOT is valid"
  },
  "score": {
    "type": "number",
    "minimum": 0,
    "maximum": 100,
    "description": "PoOT score"
  },
  "confidence": {
    "type": "number",
    "minimum": 0,
    "maximum": 1,
    "description": "Validation confidence"
  },
  "output_hash": {
    "type": "string",
    "pattern": "^[a-f0-9]{64}$",
    "description": "SHA-256 hash of output data"
  },
  "timestamp": {
    "type": "string",
    "format": "date-time"
  },
  "validation_time_ms": {
    "type": "integer",
    "minimum": 0,
    "description": "Validation time in milliseconds"
  },
  "errors": {
    "type": "array",
    "items": {
      "type": "string"
    },
    "description": "Validation errors if any"
  }
}
```

### Payout Schemas

#### PayoutRequest
```json
{
  "node_id": {
    "type": "string",
    "pattern": "^node_[a-zA-Z0-9_-]+$"
  },
  "amount": {
    "type": "number",
    "format": "decimal",
    "minimum": 0.000001,
    "maximum": 1000000
  },
  "currency": {
    "type": "string",
    "enum": ["USDT", "LUCID"],
    "default": "USDT"
  },
  "wallet_address": {
    "type": "string",
    "pattern": "^[a-zA-Z0-9]{34}$",
    "description": "TRON wallet address for USDT, LUCID address for LUCID"
  },
  "priority": {
    "type": "string",
    "enum": ["low", "normal", "high", "urgent"],
    "default": "normal"
  },
  "scheduled_at": {
    "type": "string",
    "format": "date-time",
    "description": "Optional scheduled execution time"
  }
}
```

#### BatchPayoutRequest
```json
{
  "batch_id": {
    "type": "string",
    "pattern": "^batch_[a-zA-Z0-9_-]+$"
  },
  "payout_requests": {
    "type": "array",
    "items": {
      "$ref": "#/components/schemas/PayoutRequest"
    },
    "minItems": 1,
    "maxItems": 1000
  },
  "priority": {
    "type": "string",
    "enum": ["low", "normal", "high", "urgent"],
    "default": "normal"
  },
  "scheduled_at": {
    "type": "string",
    "format": "date-time"
  },
  "notification_url": {
    "type": "string",
    "format": "uri",
    "description": "Webhook URL for batch completion notification"
  }
}
```

## Validation Rules

### Node Validation Rules

#### Node ID Validation
- **Pattern**: `^node_[a-zA-Z0-9_-]+$`
- **Length**: 8-64 characters
- **Uniqueness**: Must be unique across all nodes
- **Reserved**: Cannot start with `node_system_`, `node_admin_`, or `node_test_`

#### Node Name Validation
- **Pattern**: `^[a-zA-Z0-9_-]+$`
- **Length**: 3-100 characters
- **Uniqueness**: Must be unique within the same pool
- **Case**: Case-sensitive

#### Hardware Info Validation
- **CPU Cores**: Minimum 1, Maximum 128
- **Memory**: Minimum 1GB, Maximum 1TB
- **Storage**: Minimum 10GB, Maximum 100TB
- **Network**: Must have at least one interface

### Pool Validation Rules

#### Pool ID Validation
- **Pattern**: `^pool_[a-zA-Z0-9_-]+$`
- **Length**: 8-64 characters
- **Uniqueness**: Must be unique across all pools
- **Reserved**: Cannot start with `pool_system_`, `pool_admin_`, or `pool_test_`

#### Pool Capacity Validation
- **Max Nodes**: Minimum 1, Maximum 1000
- **Resource Limits**: Must be positive integers
- **Auto Scaling**: Requires valid scaling policy if enabled

### PoOT Validation Rules

#### PoOT Score Validation
- **Range**: 0.0 to 100.0
- **Precision**: Maximum 2 decimal places
- **Calculation**: Must be based on valid output data
- **Timestamp**: Must be within last 24 hours

#### Output Data Validation
- **Hash**: Must be valid SHA-256 hash
- **Size**: Maximum 1MB per output
- **Format**: Must be base64 encoded
- **Integrity**: Must pass checksum validation

### Payout Validation Rules

#### Amount Validation
- **Minimum**: 0.000001 (1 micro-unit)
- **Maximum**: 1,000,000 per payout
- **Precision**: Maximum 6 decimal places for USDT, 8 for LUCID
- **Currency**: Must match supported currencies

#### Wallet Address Validation
- **USDT**: TRON address format (34 characters)
- **LUCID**: LUCID address format (42 characters)
- **Checksum**: Must pass address checksum validation
- **Blacklist**: Cannot be in blocked addresses list

## MongoDB Collections

### nodes Collection
```javascript
{
  "_id": ObjectId,
  "node_id": String, // Unique identifier
  "name": String,
  "status": String, // active, inactive, maintenance, error
  "node_type": String, // worker, validator, storage, compute
  "pool_id": String,
  "hardware_info": {
    "cpu": {
      "cores": Number,
      "frequency_mhz": Number,
      "architecture": String
    },
    "memory": {
      "total_bytes": Number,
      "type": String // DDR4, DDR5, etc.
    },
    "storage": {
      "total_bytes": Number,
      "type": String, // SSD, HDD, NVMe
      "interface": String // SATA, NVMe, etc.
    },
    "gpu": {
      "model": String,
      "memory_bytes": Number,
      "compute_capability": String
    },
    "network": [{
      "interface": String,
      "speed_mbps": Number,
      "mac_address": String
    }]
  },
  "location": {
    "country": String,
    "region": String,
    "city": String,
    "timezone": String,
    "coordinates": {
      "latitude": Number,
      "longitude": Number
    }
  },
  "configuration": {
    "max_sessions": Number,
    "resource_limits": {
      "cpu_percent": Number,
      "memory_bytes": Number,
      "disk_bytes": Number,
      "network_mbps": Number
    },
    "auto_scaling": Boolean,
    "maintenance_window": {
      "start_hour": Number, // 0-23
      "duration_hours": Number
    }
  },
  "poot_score": Number,
  "last_heartbeat": Date,
  "created_at": Date,
  "updated_at": Date,
  "indexes": [
    { "node_id": 1 },
    { "status": 1 },
    { "pool_id": 1 },
    { "node_type": 1 },
    { "last_heartbeat": 1 },
    { "poot_score": -1 },
    { "location.country": 1, "location.region": 1 }
  ]
}
```

### node_pools Collection
```javascript
{
  "_id": ObjectId,
  "pool_id": String,
  "name": String,
  "description": String,
  "node_count": Number,
  "max_nodes": Number,
  "resource_limits": {
    "cpu_percent": Number,
    "memory_bytes": Number,
    "disk_bytes": Number,
    "network_mbps": Number
  },
  "auto_scaling": Boolean,
  "scaling_policy": {
    "scale_up_threshold": Number, // CPU percentage
    "scale_down_threshold": Number,
    "min_nodes": Number,
    "max_nodes": Number,
    "cooldown_minutes": Number
  },
  "pricing": {
    "cost_per_hour": Number,
    "currency": String
  },
  "created_at": Date,
  "updated_at": Date,
  "indexes": [
    { "pool_id": 1 },
    { "name": 1 },
    { "auto_scaling": 1 }
  ]
}
```

### poot_validations Collection
```javascript
{
  "_id": ObjectId,
  "validation_id": String, // UUID
  "node_id": String,
  "output_data": String, // Base64 encoded
  "output_hash": String, // SHA-256
  "timestamp": Date,
  "score": Number,
  "confidence": Number,
  "is_valid": Boolean,
  "validation_time_ms": Number,
  "errors": [String],
  "batch_id": String, // For batch validations
  "created_at": Date,
  "indexes": [
    { "validation_id": 1 },
    { "node_id": 1, "timestamp": -1 },
    { "output_hash": 1 },
    { "is_valid": 1, "score": -1 },
    { "batch_id": 1 }
  ]
}
```

### payouts Collection
```javascript
{
  "_id": ObjectId,
  "payout_id": String,
  "node_id": String,
  "amount": Number,
  "currency": String,
  "wallet_address": String,
  "status": String, // pending, processing, completed, failed, cancelled
  "priority": String, // low, normal, high, urgent
  "transaction_hash": String, // Blockchain transaction hash
  "batch_id": String,
  "scheduled_at": Date,
  "processed_at": Date,
  "completed_at": Date,
  "error_message": String,
  "retry_count": Number,
  "max_retries": Number,
  "created_at": Date,
  "updated_at": Date,
  "indexes": [
    { "payout_id": 1 },
    { "node_id": 1, "created_at": -1 },
    { "status": 1 },
    { "batch_id": 1 },
    { "wallet_address": 1 },
    { "transaction_hash": 1 },
    { "scheduled_at": 1 }
  ]
}
```

### resource_metrics Collection
```javascript
{
  "_id": ObjectId,
  "node_id": String,
  "timestamp": Date,
  "cpu": {
    "usage_percent": Number,
    "cores": Number,
    "frequency_mhz": Number,
    "load_average": [Number],
    "temperature_celsius": Number
  },
  "memory": {
    "total_bytes": Number,
    "used_bytes": Number,
    "free_bytes": Number,
    "cached_bytes": Number,
    "swap_total_bytes": Number,
    "swap_used_bytes": Number
  },
  "disk": {
    "total_bytes": Number,
    "used_bytes": Number,
    "free_bytes": Number,
    "read_iops": Number,
    "write_iops": Number,
    "read_throughput_mbps": Number,
    "write_throughput_mbps": Number
  },
  "network": {
    "total_bytes_in": Number,
    "total_bytes_out": Number,
    "packets_in": Number,
    "packets_out": Number,
    "errors_in": Number,
    "errors_out": Number
  },
  "gpu": {
    "usage_percent": Number,
    "memory_used_bytes": Number,
    "memory_total_bytes": Number,
    "temperature_celsius": Number
  },
  "indexes": [
    { "node_id": 1, "timestamp": -1 },
    { "timestamp": -1 }, // TTL index for automatic cleanup
    { "node_id": 1, "cpu.usage_percent": 1 },
    { "node_id": 1, "memory.used_bytes": 1 }
  ]
}
```

## Data Relationships

### Node Relationships
- **One-to-Many**: Node → Payouts
- **One-to-Many**: Node → PoOT Validations
- **One-to-Many**: Node → Resource Metrics
- **Many-to-One**: Node → Pool

### Pool Relationships
- **One-to-Many**: Pool → Nodes
- **One-to-Many**: Pool → Payouts (aggregated)

### Batch Relationships
- **One-to-Many**: Batch → PoOT Validations
- **One-to-Many**: Batch → Payouts

## Data Retention Policies

### Resource Metrics
- **Retention**: 90 days for detailed metrics
- **Aggregation**: 1-year for hourly aggregates
- **TTL Index**: Automatic deletion after retention period

### PoOT Validations
- **Retention**: 1 year for individual validations
- **Archive**: Move to cold storage after 1 year
- **Aggregation**: Keep monthly aggregates indefinitely

### Payouts
- **Retention**: 7 years for compliance
- **Archive**: Move to cold storage after 2 years
- **Backup**: Daily backups with 30-day retention

### Node History
- **Retention**: 2 years for node status changes
- **Archive**: Move to cold storage after 1 year
- **Audit**: Keep audit logs for 7 years

## Data Consistency

### ACID Properties
- **Atomicity**: All operations within a transaction succeed or fail together
- **Consistency**: Database constraints ensure data integrity
- **Isolation**: Concurrent operations don't interfere
- **Durability**: Committed data survives system failures

### Consistency Checks
- **Node Status**: Must be valid enum value
- **Resource Limits**: Cannot exceed hardware capabilities
- **PoOT Scores**: Must be within valid range
- **Payout Amounts**: Must be positive and within limits

### Data Validation
- **Schema Validation**: All documents must match defined schemas
- **Business Rules**: Custom validation for business logic
- **Referential Integrity**: Foreign key constraints
- **Data Quality**: Regular data quality checks and cleanup
