# Blockchain Configuration - Environment Variables Reference

This document lists all environment variables that can be used to configure the blockchain services.

## Configuration Loading

The blockchain services support configuration via:
1. **Environment Variables** (highest priority)
2. **YAML Configuration Files** (with `${VAR_NAME}` or `${VAR_NAME:default}` syntax)
3. **Default Values** (lowest priority)

YAML files in `blockchain/config/` support environment variable substitution:
- `${VAR_NAME}` - Required variable (will raise error if not set)
- `${VAR_NAME:default_value}` - Optional variable with default

## Required Environment Variables

These must be set for the services to start:

### Database
- `MONGODB_URL` or `MONGO_URL` - MongoDB connection string
- `REDIS_URL` - Redis connection string

### Blockchain
- `ON_SYSTEM_CHAIN_RPC` or `ON_SYSTEM_CHAIN_RPC_URL` - On-System Chain RPC endpoint
- `LUCID_ANCHORS_ADDRESS` - LucidAnchors contract address
- `LUCID_CHUNK_STORE_ADDRESS` - LucidChunkStore contract address

### Security
- `BLOCKCHAIN_SECRET_KEY` or `SECRET_KEY` - Secret key for JWT/signing

## Optional Environment Variables

### Network Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `LUCID_NETWORK_ID` | `lucid-dev` | Network identifier |
| `LUCID_BLOCK_TIME` | `5` | Block time in seconds |
| `LUCID_MAX_BLOCK_TXS` | `100` | Maximum transactions per block |

### Service Ports
| Variable | Default | Description |
|----------|---------|-------------|
| `BLOCKCHAIN_ENGINE_PORT` | `8084` | Blockchain engine API port |
| `SESSION_ANCHORING_PORT` | `8085` | Session anchoring service port |
| `BLOCK_MANAGER_PORT` | `8086` | Block manager service port |
| `DATA_CHAIN_PORT` | `8087` | Data chain service port |

### Service URLs
| Variable | Default | Description |
|----------|---------|-------------|
| `BLOCKCHAIN_ENGINE_URL` | `http://blockchain-engine:8084` | Blockchain engine URL |
| `SESSION_ANCHORING_URL` | `http://session-anchoring:8085` | Session anchoring URL |
| `BLOCK_MANAGER_URL` | `http://block-manager:8086` | Block manager URL |
| `DATA_CHAIN_URL` | `http://data-chain:8087` | Data chain URL |
| `AUTH_SERVICE_URL` | `http://lucid-auth-service:8089` | Authentication service URL |

### Database Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `MONGO_DB` | `lucid` | MongoDB database name |
| `REDIS_HOST` | `localhost` | Redis host |
| `REDIS_PORT` | `6379` | Redis port |
| `REDIS_DB` | `0` | Redis database number |

### Anchoring Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `ANCHORING_ENABLED` | `true` | Enable anchoring service |
| `ANCHORING_METHOD` | `merkle_tree` | Anchoring method |
| `ANCHORING_BATCH_SIZE` | `100` | Batch size for anchoring |
| `ANCHORING_BATCH_TIMEOUT_SECONDS` | `300` | Batch timeout |
| `ANCHORING_GAS_LIMIT` | `100000` | Gas limit per anchor |
| `ANCHORING_MAX_GAS_PRICE` | `1000000000` | Max gas price (1 Gwei) |
| `ANCHORING_VERIFICATION_ENABLED` | `true` | Enable verification |
| `ANCHORING_VERIFICATION_TIMEOUT_SECONDS` | `60` | Verification timeout |
| `ANCHORING_REQUIRE_CONFIRMATION_BLOCKS` | `6` | Required confirmation blocks |
| `ANCHORING_MAX_RETRIES` | `3` | Maximum retry attempts |
| `ANCHORING_STORAGE_BACKEND` | `mongodb` | Storage backend |
| `ANCHORING_COMPRESSION_ENABLED` | `true` | Enable compression |

### Block Storage Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `BLOCK_STORAGE_BACKEND` | `mongodb` | Storage backend |
| `BLOCK_STORAGE_COMPRESSION_ENABLED` | `true` | Enable compression |
| `BLOCK_STORAGE_ENCRYPTION_ENABLED` | `false` | Enable encryption |
| `BLOCK_RETENTION_DAYS` | `365` | Block retention period |
| `BLOCK_ARCHIVE_AFTER_DAYS` | `90` | Archive blocks after days |
| `TRANSACTION_RETENTION_DAYS` | `365` | Transaction retention period |
| `STATE_RETENTION_DAYS` | `180` | State retention period |
| `BLOCK_BACKUP_ENABLED` | `true` | Enable backups |
| `BLOCK_BACKUP_INTERVAL_HOURS` | `24` | Backup interval |
| `BLOCK_BACKUP_RETENTION_DAYS` | `30` | Backup retention |
| `BLOCK_BACKUP_LOCATION` | `/backups/blocks` | Backup location |

### Consensus Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `CONSENSUS_ALGORITHM` | `PoOT` | Consensus algorithm |
| `CONSENSUS_ENABLED` | `true` | Enable consensus |
| `CONSENSUS_BLOCK_TIME_SECONDS` | `10` | Block time |
| `CONSENSUS_MAX_TXS_PER_BLOCK` | `1000` | Max transactions per block |
| `CONSENSUS_MIN_TXS_PER_BLOCK` | `1` | Min transactions per block |
| `CONSENSUS_BLOCK_SIZE_LIMIT_BYTES` | `1048576` | Block size limit (1MB) |
| `CONSENSUS_GAS_LIMIT_PER_BLOCK` | `8000000` | Gas limit per block |
| `CONSENSUS_LEADER_SELECTION_METHOD` | `weighted_random` | Leader selection method |
| `CONSENSUS_SELECTION_INTERVAL_SECONDS` | `10` | Selection interval |
| `CONSENSUS_CONFIRMATION_BLOCKS` | `6` | Confirmation blocks |
| `CONSENSUS_FINALITY_TIMEOUT_SECONDS` | `60` | Finality timeout |
| `CONSENSUS_MAJORITY_THRESHOLD` | `0.51` | Majority threshold |
| `CONSENSUS_MAX_PEERS` | `50` | Maximum peers |
| `CONSENSUS_MIN_PEERS` | `5` | Minimum peers |
| `CONSENSUS_DISCOVERY_INTERVAL_SECONDS` | `60` | Peer discovery interval |
| `CONSENSUS_MEMPOOL_MAX_SIZE` | `10000` | Mempool max size |
| `CONSENSUS_TX_TIMEOUT_SECONDS` | `300` | Transaction timeout |
| `CONSENSUS_STAKING_ENABLED` | `true` | Enable staking |
| `CONSENSUS_MIN_STAKE_AMOUNT` | `1000` | Minimum stake |
| `CONSENSUS_STAKING_PERIOD_DAYS` | `30` | Staking period |
| `CONSENSUS_UNSTAKING_COOLDOWN_DAYS` | `7` | Unstaking cooldown |
| `CONSENSUS_REWARD_PER_BLOCK` | `10` | Reward per block |
| `CONSENSUS_WORK_CREDITS_ENABLED` | `true` | Enable work credits |
| `CONSENSUS_CREDIT_EARN_RATE` | `1.0` | Credit earn rate |
| `CONSENSUS_CREDIT_DECAY_RATE` | `0.01` | Credit decay rate |
| `CONSENSUS_MIN_CREDITS_FOR_VALIDATION` | `100` | Min credits for validation |
| `CONSENSUS_MAX_CREDITS` | `10000` | Maximum credits |

### Data Chain Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `DATA_CHAIN_CHUNK_SIZE_BYTES` | `1048576` | Default chunk size (1MB) |
| `DATA_CHAIN_MAX_CHUNK_SIZE_BYTES` | `10485760` | Max chunk size (10MB) |
| `DATA_CHAIN_MIN_CHUNK_SIZE_BYTES` | `1024` | Min chunk size (1KB) |
| `DATA_CHAIN_COMPRESSION_ENABLED` | `true` | Enable compression |
| `DATA_CHAIN_ENCRYPTION_ENABLED` | `false` | Enable encryption |
| `DATA_CHAIN_STORAGE_BACKEND` | `mongodb` | Storage backend |
| `DATA_CHAIN_STORAGE_COMPRESSION_ALGORITHM` | `gzip` | Compression algorithm |
| `DATA_CHAIN_DEDUPLICATION_ENABLED` | `true` | Enable deduplication |
| `DATA_CHAIN_MERKLE_ALGORITHM` | `SHA256` | Merkle tree algorithm |
| `DATA_CHAIN_MERKLE_TREE_TYPE` | `binary` | Merkle tree type |
| `DATA_CHAIN_MERKLE_BATCH_SIZE` | `100` | Merkle batch size |
| `DATA_CHAIN_MERKLE_BATCH_TIMEOUT_SECONDS` | `300` | Merkle batch timeout |
| `DATA_CHAIN_CACHE_SIZE_MB` | `1000` | Cache size |
| `DATA_CHAIN_CACHE_TTL_SECONDS` | `3600` | Cache TTL |
| `DATA_CHAIN_MAX_WORKER_THREADS` | `8` | Max worker threads |

### API Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `API_HOST` | `0.0.0.0` | API host |
| `API_PORT` | `8084` | API port |
| `API_DEBUG` | `false` | Debug mode |
| `API_TITLE` | `Lucid Blockchain API` | API title |
| `API_VERSION` | `1.0.0` | API version |
| `CORS_ORIGINS` | `*` | CORS origins |
| `CORS_CREDENTIALS` | `true` | CORS credentials |
| `CORS_METHODS` | `*` | CORS methods |
| `CORS_HEADERS` | `*` | CORS headers |
| `RATE_LIMIT_ENABLED` | `true` | Enable rate limiting |
| `RATE_LIMIT_STORAGE` | `redis` | Rate limit storage |
| `RATE_LIMIT_MAX_REQUESTS_PER_SECOND` | `100` | Max requests per second |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Rate limit window |

### Logging Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Log level |
| `LOG_FORMAT` | `%(asctime)s - %(name)s - %(levelname)s - %(message)s` | Log format |

### Monitoring Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `MONITORING_ENABLED` | `true` | Enable monitoring |
| `METRICS_ENABLED` | `true` | Enable metrics |
| `HEALTH_CHECK_ENABLED` | `true` | Enable health checks |
| `HEALTH_CHECK_INTERVAL_SECONDS` | `30` | Health check interval |

### Performance Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `DB_CONNECTION_POOL_SIZE` | `20` | Database connection pool size |
| `DB_MAX_OVERFLOW` | `10` | Max pool overflow |
| `DB_POOL_TIMEOUT_SECONDS` | `30` | Pool timeout |
| `CACHE_ENABLED` | `true` | Enable caching |
| `CACHE_TTL_SECONDS` | `3600` | Cache TTL |
| `CACHE_MAX_SIZE_MB` | `500` | Max cache size |
| `BATCH_SIZE` | `100` | Default batch size |
| `BATCH_TIMEOUT_SECONDS` | `5` | Batch timeout |
| `MAX_CONCURRENT_OPERATIONS` | `10` | Max concurrent operations |

### Security Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Token expiration |
| `ALGORITHM` | `HS256` | JWT algorithm |
| `DDOS_PROTECTION_ENABLED` | `true` | Enable DDoS protection |
| `DDOS_MAX_REQUESTS_PER_SECOND` | `100` | Max requests per second |
| `DDOS_RATE_LIMIT_WINDOW_SECONDS` | `60` | Rate limit window |
| `SYBIL_PREVENTION_ENABLED` | `true` | Enable Sybil prevention |
| `SYBIL_MAX_NODES_PER_IP` | `5` | Max nodes per IP |
| `SYBIL_REPUTATION_THRESHOLD` | `0.5` | Reputation threshold |
| `CRYPTO_SIGNATURE_ALGORITHM` | `ECDSA` | Signature algorithm |
| `CRYPTO_HASH_ALGORITHM` | `SHA256` | Hash algorithm |
| `CRYPTO_KEY_SIZE_BITS` | `256` | Key size |

## Usage in YAML Files

YAML configuration files support environment variable substitution:

```yaml
storage:
  backend: "${DATA_CHAIN_STORAGE_BACKEND:mongodb}"
  compression: "${DATA_CHAIN_COMPRESSION_ENABLED:true}"
  
consensus:
  block_time_seconds: "${CONSENSUS_BLOCK_TIME_SECONDS:10}"
  max_txs_per_block: "${CONSENSUS_MAX_TXS_PER_BLOCK:1000}"
```

## Configuration Priority

1. **Environment Variables** (highest priority)
2. **YAML File Values** (with env var substitution)
3. **Default Values** (lowest priority)

## Notes

- All values can be overridden via environment variables
- Required variables must be set or the service will fail to start
- Secret keys should be stored in `.env.secrets` file (not committed to git)
- Production values should differ from development defaults
- Use `${VAR_NAME:default}` syntax in YAML for optional variables

