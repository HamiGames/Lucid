# LUCID Node Environment Variables

This document lists all environment variables used across the node directory, standardized with the `LUCID_` prefix for consistency and security.

## Consensus System

### Leader Selection
- `LUCID_LEADER_SELECTION_INTERVAL` - Leader selection interval in seconds (default: 30)
- `LUCID_CONSENSUS_ROUND_DURATION` - Consensus round duration in seconds (default: 10)
- `LUCID_MINIMUM_STAKE_THRESHOLD` - Minimum stake threshold for leader selection (default: 1000.0)
- `LUCID_LEADER_SELECTION_ALGORITHM` - Leader selection algorithm (default: weighted_random)
- `LUCID_NETWORK_SIZE_ESTIMATE` - Estimated network size (default: 100)

### Task Proofs
- `LUCID_TASK_PROOF_TIMEOUT` - Task proof timeout in seconds (default: 300)
- `LUCID_MINIMUM_PROOF_COUNT` - Minimum proof count required (default: 3)
- `LUCID_PROOF_VERIFICATION_TIMEOUT` - Proof verification timeout in seconds (default: 60)
- `LUCID_TASK_DIFFICULTY_LEVEL` - Task difficulty level for hashing (default: 4)
- `LUCID_PROOF_STORAGE_PATH` - Path for storing proof data (default: /data/consensus/proofs)

### Uptime Beacon
- `LUCID_NODE_ID` - Unique node identifier (default: node-001)
- `LUCID_MONGODB_URL` - MongoDB connection URL (default: mongodb://lucid:lucid@lucid_mongo:27017/lucid)
- `LUCID_CONSENSUS_API_URL` - Consensus API endpoint (default: http://consensus-api:8080)
- `LUCID_BEACON_INTERVAL` - Beacon interval in seconds (default: 60)
- `LUCID_BEACON_TIMEOUT` - Beacon timeout in seconds (default: 30)
- `LUCID_MAX_CONSECUTIVE_FAILURES` - Maximum consecutive failures allowed (default: 5)
- `LUCID_UPTIME_THRESHOLD` - Uptime threshold percentage (default: 0.8)

## Pool System

### Pool Configuration
- `LUCID_MIN_POOL_SIZE` - Minimum nodes per pool (default: 3)
- `LUCID_MAX_POOL_SIZE` - Maximum nodes per pool (default: 50)
- `LUCID_POOL_SYNC_INTERVAL_SEC` - Pool synchronization interval in seconds (default: 30)
- `LUCID_POOL_HEALTH_CHECK_SEC` - Pool health check interval in seconds (default: 120)
- `LUCID_REWARD_DISTRIBUTION_THRESHOLD` - Reward distribution threshold in USDT (default: 1.0)

## Registration Protocol

### Registration Settings
- `LUCID_REGISTRATION_TIMEOUT_SEC` - Registration timeout in seconds (default: 300)
- `LUCID_MIN_STAKE_REQUIREMENT_USDT` - Minimum stake requirement in USDT (default: 100.0)
- `LUCID_MAX_PENDING_REGISTRATIONS` - Maximum pending registrations (default: 1000)
- `LUCID_CHALLENGE_VALIDITY_SEC` - Challenge validity period in seconds (default: 120)

## Shard Management

### Shard Creation
- `LUCID_SHARD_SIZE_MB` - Shard size in MB (default: 64)
- `LUCID_REPLICATION_FACTOR` - Number of replicas per shard (default: 3)
- `LUCID_MIN_STORAGE_NODES` - Minimum storage nodes required (default: 5)
- `LUCID_SHARD_TIMEOUT_SEC` - Shard operation timeout in seconds (default: 300)
- `LUCID_MAX_SHARDS_PER_NODE` - Maximum shards per node (default: 1000)

### Shard Management
- `LUCID_HEALTH_CHECK_INTERVAL_SEC` - Health check interval in seconds (default: 60)
- `LUCID_PERFORMANCE_WINDOW_HOURS` - Performance monitoring window in hours (default: 24)
- `LUCID_DEGRADED_THRESHOLD_FAILURES` - Threshold for marking node as degraded (default: 3)
- `LUCID_MAINTENANCE_WINDOW_HOURS` - Maintenance window duration in hours (default: 2)
- `LUCID_BACKUP_REDUNDANCY_FACTOR` - Additional backup copies factor (default: 2)

## Sync System

### Operator Sync
- `LUCID_SYNC_HEARTBEAT_INTERVAL_SEC` - Sync heartbeat interval in seconds (default: 30)
- `LUCID_OPERATOR_TIMEOUT_MINUTES` - Operator timeout in minutes (default: 5)
- `LUCID_CONFLICT_RESOLUTION_TIMEOUT_SEC` - Conflict resolution timeout in seconds (default: 60)
- `LUCID_MAX_SYNC_RETRIES` - Maximum sync retry attempts (default: 3)
- `LUCID_STATE_CHECKPOINT_INTERVAL_MINUTES` - State checkpoint interval in minutes (default: 15)
- `LUCID_OPERATION_BATCH_SIZE` - Operations per batch (default: 100)

## Tor Network

### Tor Configuration
- `LUCID_NODE_ID` - Unique node identifier (default: node-001)
- `LUCID_TOR_CONTROL_PORT` - Tor control port (default: 9051)
- `LUCID_TOR_SOCKS_PORT` - Tor SOCKS proxy port (default: 9050)

## Validation System

### PoOT Validation
- `LUCID_POOT_CHALLENGE_VALIDITY_MINUTES` - Challenge validity period in minutes (default: 15)
- `LUCID_POOT_PROOF_CACHE_MINUTES` - Proof cache duration in minutes (default: 60)
- `LUCID_MIN_TOKEN_STAKE_AMOUNT` - Minimum token stake amount (default: 100.0)
- `LUCID_MAX_VALIDATION_ATTEMPTS` - Maximum validation attempts per period (default: 3)
- `LUCID_FRAUD_DETECTION_WINDOW_HOURS` - Fraud detection window in hours (default: 24)
- `LUCID_CHALLENGE_COMPLEXITY_BYTES` - Challenge complexity in bytes (default: 32)

## Worker System

### Node Worker
- `LUCID_MAX_CONCURRENT_SESSIONS` - Maximum concurrent sessions (default: 10)
- `LUCID_SESSION_TIMEOUT` - Session timeout in seconds (default: 7200)
- `LUCID_BANDWIDTH_LIMIT_MBPS` - Bandwidth limit in Mbps (default: 100.0)
- `LUCID_MIN_STORAGE_GB` - Minimum storage requirement in GB (default: 50.0)

## Security Considerations

1. **Prefix Standardization**: All environment variables use the `LUCID_` prefix to avoid conflicts with system variables
2. **Default Values**: Sensible defaults are provided for all variables
3. **Type Safety**: Proper type conversion is applied (int, float, Decimal, Path)
4. **Validation**: Environment variables are validated at startup
5. **Documentation**: All variables are documented with their purpose and default values

## Usage Example

```bash
# Set environment variables for a node
export LUCID_NODE_ID="node-001"
export LUCID_MONGODB_URL="mongodb://lucid:lucid@lucid_mongo:27017/lucid"
export LUCID_MAX_CONCURRENT_SESSIONS="20"
export LUCID_BEACON_INTERVAL="30"
export LUCID_MIN_STAKE_REQUIREMENT_USDT="500.0"

# Start the node
python -m node.node_manager
```

## Notes

- All environment variables are optional and have sensible defaults
- Variables can be set in `.env` files or as system environment variables
- The system will log warnings for any missing critical variables
- Some variables may require restart of the node to take effect
