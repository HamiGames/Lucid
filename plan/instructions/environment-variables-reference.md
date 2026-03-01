# Lucid Project - Complete Environment Variables Reference

**Generated:** 2025-01-14  
**Total Variables:** 200+  
**Total .env Files:** 40

---

## Format Legend

- **STRING**: Text value
- **INT**: Integer number
- **BOOL**: Boolean (true/false)
- **URL**: Full URL format (http:// or https://)
- **URI**: Database connection string
- **IP**: IPv4 address
- **PORT**: Port number (1-65535)
- **HEX**: Hexadecimal string
- **BASE64**: Base64 encoded string
- **PATH**: File system path
- **CIDR**: Network CIDR notation (e.g., 172.20.0.0/16)
- **ONION**: Tor .onion address (56 chars, ends with .onion)

---

## Core Phase Files

### `.env.foundation` (Phase 1: Foundation Services)

| Variable Name | Format | Description |
|--------------|--------|-------------|
| `MONGODB_HOST` | IP | MongoDB host IP (e.g., 172.20.0.11) |
| `MONGODB_PORT` | PORT | MongoDB port (default: 27017) |
| `MONGODB_DATABASE` | STRING | Database name (e.g., lucid) |
| `MONGODB_USERNAME` | STRING | MongoDB username (e.g., lucid) |
| `MONGODB_PASSWORD` | BASE64 | 32 bytes base64 password |
| `MONGODB_URL` | URI | Full MongoDB connection string |
| `MONGODB_URI` | URI | Alternative MongoDB connection string |
| `MONGODB_AUTH_SOURCE` | STRING | Auth database (default: admin) |
| `REDIS_HOST` | IP | Redis host IP (e.g., 172.20.0.12) |
| `REDIS_PORT` | PORT | Redis port (default: 6379) |
| `REDIS_PASSWORD` | BASE64 | 32 bytes base64 password |
| `REDIS_URL` | URI | Full Redis connection string |
| `REDIS_URI` | URI | Alternative Redis connection string |
| `ELASTICSEARCH_HOST` | IP | Elasticsearch host IP (e.g., 172.20.0.13) |
| `ELASTICSEARCH_PORT` | PORT | Elasticsearch HTTP port (default: 9200) |
| `ELASTICSEARCH_TRANSPORT_PORT` | PORT | Transport port (default: 9300) |
| `ELASTICSEARCH_USERNAME` | STRING | Elasticsearch username (e.g., elastic) |
| `ELASTICSEARCH_PASSWORD` | BASE64 | 32 bytes base64 password |
| `ELASTICSEARCH_URL` | URL | Full Elasticsearch URL |
| `ES_JAVA_HEAP` | STRING | Java heap size (e.g., 256m) |
| `JWT_SECRET` | BASE64 | 64 bytes base64 JWT secret |
| `JWT_SECRET_KEY` | BASE64 | 64 bytes base64 JWT secret key |
| `JWT_ALGORITHM` | STRING | JWT algorithm (default: HS256) |
| `ENCRYPTION_KEY` | HEX | 32 bytes hex encryption key (64 hex chars) |
| `TOR_PASSWORD` | BASE64 | 32 bytes base64 Tor control password |
| `TOR_CONTROL_PASSWORD` | BASE64 | 32 bytes base64 Tor control password |
| `AUTH_SERVICE_HOST` | IP | Auth service IP (e.g., 172.20.0.14) |
| `AUTH_SERVICE_PORT` | PORT | Auth service port (default: 8089) |
| `AUTH_SERVICE_URL` | URL | Full auth service URL |
| `PROJECT_NAME` | STRING | Project name (default: Lucid) |
| `PROJECT_VERSION` | STRING | Project version (e.g., 0.1.0) |
| `ENVIRONMENT` | STRING | Environment (production/development/staging) |
| `DEBUG` | BOOL | Debug mode (true/false) |
| `LOG_LEVEL` | STRING | Log level (DEBUG/INFO/WARNING/ERROR/CRITICAL) |

### `.env.core` (Phase 2: Core Services)

| Variable Name | Format | Description |
|--------------|--------|-------------|
| `API_GATEWAY_HOST` | IP | API Gateway IP (e.g., 172.20.0.10) |
| `API_GATEWAY_PORT` | PORT | API Gateway port (default: 8080) |
| `API_GATEWAY_URL` | URL | Full API Gateway URL |
| `BLOCKCHAIN_ENGINE_HOST` | IP | Blockchain engine IP (e.g., 172.20.0.15) |
| `BLOCKCHAIN_ENGINE_PORT` | PORT | Blockchain engine port (default: 8084) |
| `BLOCKCHAIN_ENGINE_URL` | URL | Full blockchain engine URL |
| `BLOCKCHAIN_NETWORK` | STRING | Blockchain network (e.g., lucid-mainnet) |
| `BLOCKCHAIN_CONSENSUS` | STRING | Consensus algorithm (e.g., PoOT) |
| `SERVICE_MESH_HOST` | IP | Service mesh IP (e.g., 172.20.0.16) |
| `SERVICE_MESH_PORT` | PORT | Service mesh port (default: 8500) |
| `SERVICE_MESH_URL` | URL | Full service mesh URL |

### `.env.application` (Phase 3: Application Services)

| Variable Name | Format | Description |
|--------------|--------|-------------|
| `SESSION_SECRET` | BASE64 | 32 bytes base64 session secret |
| `SESSION_TIMEOUT` | INT | Session timeout in seconds (default: 1800) |
| `SESSION_API_HOST` | IP | Session API IP (e.g., 172.20.0.24) |
| `SESSION_API_PORT` | PORT | Session API port (default: 8087) |
| `SESSION_API_URL` | URL | Full session API URL |
| `SESSION_CHUNK_SIZE` | INT | Chunk size in bytes (default: 10485760) |
| `MAX_CHUNKS_PER_SESSION` | INT | Maximum chunks per session (default: 1000) |
| `MAX_SESSIONS` | INT | Maximum concurrent sessions (default: 10000) |

### `.env.support` (Phase 4: Support Services)

| Variable Name | Format | Description |
|--------------|--------|-------------|
| `TRON_PRIVATE_KEY` | HEX | 64 hex chars (32 bytes) TRON private key |
| `TRON_WALLET_ADDRESS` | STRING | TRON wallet address (34 chars, starts with T) |
| `TRON_NETWORK` | STRING | TRON network (mainnet/shasta/nile/testnet) |
| `TRON_RPC_URL` | URL | TRON RPC endpoint URL |
| `TRON_API_KEY` | BASE64 | TRON API key (32 bytes base64) |
| `USDT_CONTRACT_ADDRESS` | STRING | USDT contract address (34 chars, starts with T) |
| `RDP_SERVER_MANAGER_HOST` | IP | RDP server manager IP |
| `RDP_SERVER_MANAGER_PORT` | PORT | RDP server manager port (default: 8095) |
| `RDP_SERVER_MANAGER_URL` | URL | Full RDP server manager URL |

### `.env.secrets` (Master Secrets File - chmod 600)

| Variable Name | Format | Description |
|--------------|--------|-------------|
| `MONGODB_PASSWORD` | BASE64 | 32 bytes base64 MongoDB password |
| `REDIS_PASSWORD` | BASE64 | 32 bytes base64 Redis password |
| `ELASTICSEARCH_PASSWORD` | BASE64 | 32 bytes base64 Elasticsearch password |
| `JWT_SECRET` | BASE64 | 64 bytes base64 JWT secret |
| `JWT_SECRET_KEY` | BASE64 | 64 bytes base64 JWT secret key |
| `ENCRYPTION_KEY` | HEX | 32 bytes hex encryption key (64 hex chars) |
| `TOR_PASSWORD` | BASE64 | 32 bytes base64 Tor control password |
| `TOR_CONTROL_PASSWORD` | BASE64 | 32 bytes base64 Tor control password |
| `SESSION_SECRET` | BASE64 | 32 bytes base64 session secret |
| `API_SECRET` | BASE64 | 32 bytes base64 API secret |
| `BLOCKCHAIN_SECRET` | BASE64 | 32 bytes base64 blockchain secret |
| `ADMIN_SECRET` | BASE64 | 32 bytes base64 admin secret |
| `NODE_MANAGEMENT_SECRET` | BASE64 | 32 bytes base64 node management secret |
| `TRON_PAYMENT_SECRET` | BASE64 | 32 bytes base64 TRON payment secret |

### `.env.distroless` (Distroless Configuration)

| Variable Name | Format | Description |
|--------------|--------|-------------|
| `DISTROLESS_BASE_IMAGE` | STRING | Distroless base image name |
| `DISTROLESS_USER` | STRING | User:group (default: 65532:65532) |
| `CONTAINER_USER` | INT | Container user ID (default: 65532) |
| `CONTAINER_GROUP` | INT | Container group ID (default: 65532) |
| `CONTAINER_UID` | INT | Container UID (default: 65532) |
| `CONTAINER_GID` | INT | Container GID (default: 65532) |
| `SECURITY_OPT_NO_NEW_PRIVILEGES` | BOOL | No new privileges (default: true) |
| `SECURITY_OPT_READONLY_ROOTFS` | BOOL | Read-only root filesystem (default: true) |
| `CAP_DROP` | STRING | Capabilities to drop (default: ALL) |
| `CAP_ADD` | STRING | Capabilities to add (default: NET_BIND_SERVICE) |

### `.env.gui` (GUI Integration Services)

| Variable Name | Format | Description |
|--------------|--------|-------------|
| `GUI_API_BRIDGE_PORT` | PORT | GUI API bridge port (default: 8099) |
| `GUI_API_BRIDGE_HOST` | STRING | GUI API bridge hostname |
| `GUI_DOCKER_MANAGER_PORT` | PORT | GUI Docker manager port (default: 8100) |
| `GUI_DOCKER_MANAGER_HOST` | STRING | GUI Docker manager hostname |

### `.env.pi-build` (Raspberry Pi Build Configuration)

| Variable Name | Format | Description |
|--------------|--------|-------------|
| `BUILD_HOST` | STRING | Build host name |
| `BUILD_USER` | STRING | Build user name |
| `BUILD_DIR` | PATH | Build directory path |
| `PI_HOST` | IP | Raspberry Pi host IP (e.g., 192.168.0.75) |
| `PI_USER` | STRING | Raspberry Pi user (e.g., pickme) |
| `PI_DEPLOY_DIR` | PATH | Deployment directory on Pi |
| `PI_ARCH` | STRING | Pi architecture (arm64) |
| `PI_PLATFORM` | STRING | Platform (linux/arm64) |
| `BUILD_PLATFORM` | STRING | Build platform (linux/arm64) |
| `BUILD_ARCH` | STRING | Build architecture (arm64) |
| `BUILD_OS` | STRING | Build OS (linux) |
| `DOCKER_REGISTRY` | STRING | Docker registry (e.g., pickme/lucid) |
| `IMAGE_TAG` | STRING | Image tag (e.g., latest-arm64) |

---

## Foundation Services

### `.env.tor-proxy`

| Variable Name | Format | Description |
|--------------|--------|-------------|
| `SERVICE_NAME` | STRING | Service name (tor-proxy) |
| `SERVICE_PORT` | PORT | Service port (default: 9050) |
| `SERVICE_HOST` | IP | Service host (default: 0.0.0.0) |
| `TOR_CONTROL_PORT` | PORT | Tor control port (default: 9051) |
| `TOR_SOCKS_PORT` | PORT | Tor SOCKS port (default: 9050) |
| `TOR_CONTROL_PASSWORD` | BASE64 | 32 bytes base64 (from .env.foundation) |
| `TOR_HIDDEN_SERVICE_DIR` | PATH | Hidden service directory |
| `NETWORK_NAME` | STRING | Network name (lucid-pi-network) |
| `NETWORK_SUBNET` | CIDR | Network subnet (172.20.0.0/16) |

### `.env.server-tools`

| Variable Name | Format | Description |
|--------------|--------|-------------|
| `SERVICE_NAME` | STRING | Service name (server-tools) |
| `SERVICE_PORT` | PORT | Service port (default: 8086) |
| `SERVICE_HOST` | IP | Service host (default: 0.0.0.0) |
| `NETWORK_NAME` | STRING | Network name |

### `.env.authentication`

| Variable Name | Format | Description |
|--------------|--------|-------------|
| `AUTH_SERVICE_HOST` | IP | Auth service IP (e.g., 172.20.0.14) |
| `AUTH_SERVICE_PORT` | PORT | Auth service port (default: 8089) |
| `AUTH_SERVICE_URL` | URL | Full auth service URL |
| `MONGODB_URI` | URI | MongoDB connection (from .env.foundation) |
| `MONGODB_DATABASE` | STRING | Database name (lucid_auth) |
| `REDIS_URI` | URI | Redis connection (from .env.foundation) |
| `JWT_SECRET_KEY` | BASE64 | 64 bytes base64 (from .env.secrets) |
| `JWT_ALGORITHM` | STRING | JWT algorithm (HS256) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | INT | Access token expiry (default: 15) |
| `REFRESH_TOKEN_EXPIRE_DAYS` | INT | Refresh token expiry (default: 7) |
| `ENCRYPTION_KEY` | HEX | 32 bytes hex (from .env.secrets) |
| `BCRYPT_ROUNDS` | INT | Bcrypt rounds (default: 12) |
| `MAX_LOGIN_ATTEMPTS` | INT | Max login attempts (default: 5) |
| `LOGIN_COOLDOWN_MINUTES` | INT | Login cooldown (default: 15) |
| `PASSWORD_MIN_LENGTH` | INT | Minimum password length (default: 12) |
| `ENABLE_HARDWARE_WALLET` | BOOL | Hardware wallet enabled (default: true) |
| `LEDGER_SUPPORTED` | BOOL | Ledger support (default: true) |
| `TREZOR_SUPPORTED` | BOOL | Trezor support (default: true) |
| `KEEPKEY_SUPPORTED` | BOOL | KeepKey support (default: true) |
| `HW_WALLET_TIMEOUT_SECONDS` | INT | Hardware wallet timeout (default: 30) |
| `RATE_LIMIT_ENABLED` | BOOL | Rate limiting enabled (default: true) |
| `RATE_LIMIT_PUBLIC` | INT | Public rate limit (default: 100/min) |
| `RATE_LIMIT_AUTHENTICATED` | INT | Authenticated rate limit (default: 1000/min) |
| `RATE_LIMIT_ADMIN` | INT | Admin rate limit (default: 10000/min) |
| `CORS_ORIGINS` | STRING | CORS origins (comma-separated) |
| `CORS_ALLOW_CREDENTIALS` | BOOL | CORS credentials (default: true) |
| `AUDIT_LOG_ENABLED` | BOOL | Audit logging enabled (default: true) |
| `AUDIT_LOG_RETENTION_DAYS` | INT | Audit log retention (default: 90) |
| `SESSION_CLEANUP_INTERVAL_HOURS` | INT | Session cleanup interval (default: 1) |
| `SESSION_MAX_CONCURRENT_PER_USER` | INT | Max concurrent sessions per user (default: 5) |
| `SESSION_IDLE_TIMEOUT_MINUTES` | INT | Session idle timeout (default: 30) |
| `API_GATEWAY_URL` | URL | API Gateway URL |
| `SERVICE_MESH_ENABLED` | BOOL | Service mesh enabled (default: false) |
| `CONSUL_HOST` | STRING | Consul host (default: consul:8500) |
| `METRICS_ENABLED` | BOOL | Metrics enabled (default: true) |
| `METRICS_PORT` | PORT | Metrics port (default: 9090) |
| `HEALTH_CHECK_INTERVAL_SECONDS` | INT | Health check interval (default: 30) |
| `BACKUP_ENABLED` | BOOL | Backup enabled (default: true) |
| `BACKUP_INTERVAL_HOURS` | INT | Backup interval (default: 24) |
| `BACKUP_RETENTION_DAYS` | INT | Backup retention (default: 30) |

### `.env.authentication-service-distroless`

| Variable Name | Format | Description |
|--------------|--------|-------------|
| `SERVICE_NAME` | STRING | Service name (lucid-auth-service) |
| `SERVICE_PORT` | PORT | Service port (default: 8089) |
| `MONGODB_URL` | URI | MongoDB connection (from .env.foundation) |
| `MONGODB_URI` | URI | Alternative MongoDB connection |
| `REDIS_URL` | URI | Redis connection (from .env.foundation) |
| `JWT_SECRET_KEY` | BASE64 | 64 bytes base64 (from .env.secrets) |
| `ENCRYPTION_KEY` | HEX | 32 bytes hex (from .env.secrets) |

---

## API & Gateway Services

### `.env.api-gateway`

| Variable Name | Format | Description |
|--------------|--------|-------------|
| `SERVICE_NAME` | STRING | Service name (api-gateway) |
| `SERVICE_PORT` | PORT | Service port (default: 8080) |
| `SERVICE_HOST` | IP | Service IP (e.g., 172.20.0.10) |
| `SERVICE_URL` | URL | Full service URL |
| `API_GATEWAY_ONION` | ONION | Tor onion address (from tor-proxy container) |
| `RATE_LIMIT_ENABLED` | BOOL | Rate limiting enabled (default: true) |
| `RATE_LIMIT_REQUESTS` | INT | Rate limit requests (default: 1000) |
| `RATE_LIMIT_WINDOW` | INT | Rate limit window in seconds (default: 60) |
| `CORS_ORIGINS` | STRING | CORS origins (default: *) |
| `CORS_CREDENTIALS` | BOOL | CORS credentials (default: true) |

### `.env.api-server`

| Variable Name | Format | Description |
|--------------|--------|-------------|
| `SERVICE_NAME` | STRING | Service name (api-server) |
| `SERVICE_PORT` | PORT | Service port (default: 8081) |
| `SERVICE_HOST` | IP | Service IP (e.g., 172.20.0.11) |
| `SERVICE_URL` | URL | Full service URL |
| `API_GATEWAY_URL` | URL | API Gateway URL |

### `.env.openapi-gateway`

| Variable Name | Format | Description |
|--------------|--------|-------------|
| `SERVICE_NAME` | STRING | Service name (openapi-gateway) |
| `SERVICE_PORT` | PORT | Service port (default: 8082) |
| `SERVICE_HOST` | IP | Service IP (e.g., 172.20.0.12) |
| `SERVICE_URL` | URL | Full service URL |
| `OPENAPI_SPEC_PATH` | PATH | OpenAPI spec file path |
| `SWAGGER_UI_ENABLED` | BOOL | Swagger UI enabled (default: true) |

### `.env.openapi-server`

| Variable Name | Format | Description |
|--------------|--------|-------------|
| `SERVICE_NAME` | STRING | Service name (openapi-server) |
| `SERVICE_PORT` | PORT | Service port (default: 8083) |
| `SERVICE_HOST` | IP | Service IP (e.g., 172.20.0.13) |
| `SERVICE_URL` | URL | Full service URL |
| `OPENAPI_GATEWAY_URL` | URL | OpenAPI Gateway URL |

### `.env.api` (03-api-gateway/api/)

| Variable Name | Format | Description |
|--------------|--------|-------------|
| `SERVICE_NAME` | STRING | Service name (api) |
| `SERVICE_PORT` | PORT | Service port (default: 8084) |
| `SERVICE_HOST` | IP | Service host (default: 0.0.0.0) |

---

## Blockchain Services

### `.env.blockchain-api`

| Variable Name | Format | Description |
|--------------|--------|-------------|
| `SERVICE_NAME` | STRING | Service name (blockchain-api) |
| `SERVICE_PORT` | PORT | Service port (default: 8085) |
| `SERVICE_HOST` | IP | Service IP (e.g., 172.20.0.15) |
| `SERVICE_URL` | URL | Full service URL |
| `BLOCKCHAIN_NETWORK` | STRING | Network name (e.g., lucid-mainnet) |
| `BLOCKCHAIN_CONSENSUS` | STRING | Consensus (e.g., PoOT) |

### `.env.blockchain-governance`

| Variable Name | Format | Description |
|--------------|--------|-------------|
| `SERVICE_NAME` | STRING | Service name (blockchain-governance) |
| `SERVICE_PORT` | PORT | Service port (default: 8086) |
| `SERVICE_HOST` | IP | Service IP (e.g., 172.20.0.16) |
| `SERVICE_URL` | URL | Full service URL |
| `BLOCKCHAIN_NETWORK` | STRING | Network name |

### `.env.blockchain-sessions-data`

| Variable Name | Format | Description |
|--------------|--------|-------------|
| `SERVICE_NAME` | STRING | Service name (blockchain-sessions-data) |
| `SERVICE_PORT` | PORT | Service port (default: 8087) |
| `SERVICE_HOST` | IP | Service IP (e.g., 172.20.0.17) |
| `SERVICE_URL` | URL | Full service URL |
| `SESSION_TIMEOUT` | INT | Session timeout in seconds (default: 1800) |

### `.env.blockchain-vm`

| Variable Name | Format | Description |
|--------------|--------|-------------|
| `SERVICE_NAME` | STRING | Service name (blockchain-vm) |
| `SERVICE_PORT` | PORT | Service port (default: 8088) |
| `SERVICE_HOST` | IP | Service IP (e.g., 172.20.0.18) |
| `SERVICE_URL` | URL | Full service URL |
| `VM_MEMORY_LIMIT` | STRING | VM memory limit (e.g., 512M) |
| `VM_CPU_LIMIT` | STRING | VM CPU limit (e.g., 0.5) |

### `.env.blockchain-ledger`

| Variable Name | Format | Description |
|--------------|--------|-------------|
| `SERVICE_NAME` | STRING | Service name (blockchain-ledger) |
| `SERVICE_PORT` | PORT | Service port (default: 8089) |
| `SERVICE_HOST` | IP | Service IP (e.g., 172.20.0.19) |
| `SERVICE_URL` | URL | Full service URL |
| `LEDGER_STORAGE_PATH` | PATH | Ledger storage path |
| `LEDGER_BACKUP_ENABLED` | BOOL | Ledger backup enabled (default: true) |

### `.env.tron-node-client`

| Variable Name | Format | Description |
|--------------|--------|-------------|
| `SERVICE_NAME` | STRING | Service name (tron-node-client) |
| `SERVICE_PORT` | PORT | Service port (default: 8090) |
| `SERVICE_HOST` | IP | Service IP (e.g., 172.20.0.20) |
| `SERVICE_URL` | URL | Full service URL |
| `TRON_NETWORK` | STRING | TRON network (mainnet/shasta) |
| `TRON_RPC_URL` | URL | TRON RPC endpoint |

### `.env.contract-deployment`

| Variable Name | Format | Description |
|--------------|--------|-------------|
| `SERVICE_NAME` | STRING | Service name (contract-deployment) |
| `SERVICE_PORT` | PORT | Service port (default: 8091) |
| `SERVICE_HOST` | IP | Service IP (e.g., 172.20.0.21) |
| `SERVICE_URL` | URL | Full service URL |
| `CONTRACT_STORAGE_PATH` | PATH | Contract storage path |
| `SOLIDITY_COMPILER_VERSION` | STRING | Solidity version (e.g., 0.8.19) |

### `.env.contract-compiler`

| Variable Name | Format | Description |
|--------------|--------|-------------|
| `SERVICE_NAME` | STRING | Service name (contract-compiler) |
| `SERVICE_PORT` | PORT | Service port (default: 8092) |
| `SERVICE_HOST` | IP | Service IP (e.g., 172.20.0.22) |
| `SERVICE_URL` | URL | Full service URL |
| `SOLIDITY_VERSION` | STRING | Solidity version (e.g., 0.8.19) |
| `OPTIMIZATION_ENABLED` | BOOL | Optimization enabled (default: true) |
| `OPTIMIZATION_RUNS` | INT | Optimization runs (default: 200) |

### `.env.on-system-chain-client`

| Variable Name | Format | Description |
|--------------|--------|-------------|
| `SERVICE_NAME` | STRING | Service name (on-system-chain-client) |
| `SERVICE_PORT` | PORT | Service port (default: 8093) |
| `SERVICE_HOST` | IP | Service IP (e.g., 172.20.0.23) |
| `SERVICE_URL` | URL | Full service URL |
| `CHAIN_NETWORK` | STRING | Chain network name |

### `.env.deployment-orchestrator`

| Variable Name | Format | Description |
|--------------|--------|-------------|
| `SERVICE_NAME` | STRING | Service name (deployment-orchestrator) |
| `SERVICE_PORT` | PORT | Service port (default: 8094) |
| `SERVICE_HOST` | IP | Service IP (e.g., 172.20.0.24) |
| `SERVICE_URL` | URL | Full service URL |
| `ORCHESTRATION_MODE` | STRING | Orchestration mode (production/development) |
| `DEPLOYMENT_TIMEOUT` | INT | Deployment timeout in seconds (default: 300) |

---

## Session Services (sessions/core/)

### `.env.chunker`

| Variable Name | Format | Description |
|--------------|--------|-------------|
| `SERVICE_NAME` | STRING | Service name (chunker) |
| `SERVICE_PORT` | PORT | Service port (default: 8095) |
| `SERVICE_HOST` | IP | Service IP (e.g., 172.20.0.25) |
| `SERVICE_URL` | URL | Full service URL |
| `CHUNK_SIZE` | INT | Chunk size in bytes (default: 10485760) |
| `MAX_CHUNKS_PER_SESSION` | INT | Max chunks per session (default: 1000) |

### `.env.merkle_builder`

| Variable Name | Format | Description |
|--------------|--------|-------------|
| `SERVICE_NAME` | STRING | Service name (merkle_builder) |
| `SERVICE_PORT` | PORT | Service port (default: 8096) |
| `SERVICE_HOST` | IP | Service IP (e.g., 172.20.0.26) |
| `SERVICE_URL` | URL | Full service URL |
| `MERKLE_ALGORITHM` | STRING | Merkle algorithm (default: sha256) |
| `MERKLE_TREE_DEPTH` | INT | Merkle tree depth (default: 20) |

### `.env.orchestrator`

| Variable Name | Format | Description |
|--------------|--------|-------------|
| `SERVICE_NAME` | STRING | Service name (orchestrator) |
| `SERVICE_PORT` | PORT | Service port (default: 8097) |
| `SERVICE_HOST` | IP | Service IP (e.g., 172.20.0.27) |
| `SERVICE_URL` | URL | Full service URL |
| `SESSION_TIMEOUT` | INT | Session timeout in seconds (default: 1800) |
| `MAX_SESSIONS` | INT | Maximum sessions (default: 10000) |

### `.env.encryptor` (sessions/encryption/)

| Variable Name | Format | Description |
|--------------|--------|-------------|
| `SERVICE_NAME` | STRING | Service name (encryptor) |
| `SERVICE_PORT` | PORT | Service port (default: 8098) |
| `SERVICE_HOST` | IP | Service IP (e.g., 172.20.0.28) |
| `SERVICE_URL` | URL | Full service URL |
| `ENCRYPTION_ALGORITHM` | STRING | Encryption algorithm (AES-256-GCM) |

---

## TRON Payment Services

### `.env.tron-client`

| Variable Name | Format | Description |
|--------------|--------|-------------|
| `SERVICE_NAME` | STRING | Service name (tron-client) |
| `SERVICE_PORT` | PORT | Service port (default: 8091) |
| `SERVICE_HOST` | IP | Service IP (e.g., 172.21.0.10) |
| `SERVICE_URL` | URL | Full service URL |
| `TRON_NETWORK` | STRING | TRON network (mainnet/shasta) |
| `TRON_RPC_URL` | URL | TRON RPC endpoint |

### `.env.tron-payout-router`

| Variable Name | Format | Description |
|--------------|--------|-------------|
| `SERVICE_NAME` | STRING | Service name (tron-payout-router) |
| `SERVICE_PORT` | PORT | Service port (default: 8092) |
| `SERVICE_HOST` | IP | Service IP (e.g., 172.21.0.11) |
| `SERVICE_URL` | URL | Full service URL |
| `TRON_NETWORK` | STRING | TRON network |
| `TRON_RPC_URL` | URL | TRON RPC endpoint |

### `.env.tron-wallet-manager`

| Variable Name | Format | Description |
|--------------|--------|-------------|
| `SERVICE_NAME` | STRING | Service name (tron-wallet-manager) |
| `SERVICE_PORT` | PORT | Service port (default: 8093) |
| `SERVICE_HOST` | IP | Service IP (e.g., 172.21.0.12) |
| `SERVICE_URL` | URL | Full service URL |
| `TRON_NETWORK` | STRING | TRON network |
| `TRON_RPC_URL` | URL | TRON RPC endpoint |
| `WALLET_STORAGE_PATH` | PATH | Wallet storage path |
| `WALLET_ENCRYPTION_ENABLED` | BOOL | Wallet encryption enabled (default: true) |

### `.env.tron-usdt-manager`

| Variable Name | Format | Description |
|--------------|--------|-------------|
| `SERVICE_NAME` | STRING | Service name (tron-usdt-manager) |
| `SERVICE_PORT` | PORT | Service port (default: 8094) |
| `SERVICE_HOST` | IP | Service IP (e.g., 172.21.0.13) |
| `SERVICE_URL` | URL | Full service URL |
| `TRON_NETWORK` | STRING | TRON network |
| `TRON_RPC_URL` | URL | TRON RPC endpoint |
| `USDT_CONTRACT_ADDRESS` | STRING | USDT contract (34 chars, starts with T) |

### `.env.tron-staking`

| Variable Name | Format | Description |
|--------------|--------|-------------|
| `SERVICE_NAME` | STRING | Service name (tron-staking) |
| `SERVICE_PORT` | PORT | Service port (default: 8096) |
| `SERVICE_HOST` | IP | Service IP (e.g., 172.21.0.14) |
| `SERVICE_URL` | URL | Full service URL |
| `TRON_NETWORK` | STRING | TRON network |
| `TRON_RPC_URL` | URL | TRON RPC endpoint |
| `STAKING_MIN_AMOUNT` | INT | Minimum staking amount (default: 1000000) |
| `STAKING_REWARD_RATE` | STRING | Staking reward rate (default: 0.05) |

### `.env.tron-payment-gateway`

| Variable Name | Format | Description |
|--------------|--------|-------------|
| `SERVICE_NAME` | STRING | Service name (tron-payment-gateway) |
| `SERVICE_PORT` | PORT | Service port (default: 8097) |
| `SERVICE_HOST` | IP | Service IP (e.g., 172.21.0.15) |
| `SERVICE_URL` | URL | Full service URL |
| `TRON_NETWORK` | STRING | TRON network |
| `TRON_RPC_URL` | URL | TRON RPC endpoint |
| `USDT_CONTRACT_ADDRESS` | STRING | USDT contract address |
| `PAYMENT_TIMEOUT` | INT | Payment timeout in seconds (default: 300) |
| `PAYMENT_CONFIRMATION_BLOCKS` | INT | Confirmation blocks (default: 20) |

### `.env.tron-secrets` (chmod 600)

| Variable Name | Format | Description |
|--------------|--------|-------------|
| `TRON_PRIVATE_KEY` | HEX | 64 hex chars (32 bytes) from .env.support |
| `TRON_MASTER_PRIVATE_KEY` | HEX | 64 hex chars master private key |
| `TRON_WALLET_ADDRESS` | STRING | 34 chars, starts with T (from .env.support) |
| `TRON_MASTER_WALLET_ADDRESS` | STRING | 34 chars master wallet address |
| `TRON_API_KEY` | BASE64 | TRON API key (from .env.support) |
| `TRON_KEY_ENCRYPTION_KEY` | HEX | 32 bytes hex encryption key |

---

## Node & Admin Services

### `.env.node`

| Variable Name | Format | Description |
|--------------|--------|-------------|
| `SERVICE_NAME` | STRING | Service name (node) |
| `SERVICE_PORT` | PORT | Service port (default: 8099) |
| `SERVICE_HOST` | IP | Service IP (e.g., 172.20.0.29) |
| `SERVICE_URL` | URL | Full service URL |
| `NODE_ID` | STRING | Node identifier (hostname) |
| `NODE_REGION` | STRING | Node region (e.g., us-east) |

---

## Network Configuration Variables

| Variable Name | Format | Description | Expected File |
|--------------|--------|-------------|---------------|
| `LUCID_MAIN_NETWORK` | STRING | Main network name | .env.distroless |
| `LUCID_MAIN_SUBNET` | CIDR | Main subnet (172.20.0.0/16) | .env.distroless |
| `LUCID_MAIN_GATEWAY` | IP | Main gateway IP | .env.distroless |
| `LUCID_TRON_NETWORK` | STRING | TRON network name | .env.distroless |
| `LUCID_TRON_SUBNET` | CIDR | TRON subnet (172.21.0.0/16) | .env.distroless |
| `LUCID_TRON_GATEWAY` | IP | TRON gateway IP | .env.distroless |
| `LUCID_GUI_NETWORK` | STRING | GUI network name | .env.distroless |
| `LUCID_GUI_SUBNET` | CIDR | GUI subnet (172.22.0.0/16) | .env.distroless |
| `LUCID_GUI_GATEWAY` | IP | GUI gateway IP | .env.distroless |

---

## Health Check Configuration

| Variable Name | Format | Description | Expected File |
|--------------|--------|-------------|---------------|
| `HEALTH_CHECK_INTERVAL` | STRING | Interval (e.g., 30s) | .env.distroless |
| `HEALTH_CHECK_TIMEOUT` | STRING | Timeout (e.g., 10s) | .env.distroless |
| `HEALTH_CHECK_RETRIES` | INT | Retry count (default: 3) | .env.distroless |
| `HEALTH_CHECK_START_PERIOD` | STRING | Start period (e.g., 40s) | .env.distroless |
| `HEALTH_CHECK_ENABLED` | BOOL | Health check enabled | .env.distroless |

---

## Monitoring Configuration

| Variable Name | Format | Description | Expected File |
|--------------|--------|-------------|---------------|
| `METRICS_ENABLED` | BOOL | Metrics enabled | .env.distroless |
| `METRICS_PORT` | PORT | Metrics port (default: 9090) | .env.distroless |
| `METRICS_PATH` | PATH | Metrics path (default: /metrics) | .env.distroless |
| `PROMETHEUS_ENABLED` | BOOL | Prometheus enabled | .env.distroless |
| `GRAFANA_ENABLED` | BOOL | Grafana enabled | .env.distroless |

---

## Logging Configuration

| Variable Name | Format | Description | Expected File |
|--------------|--------|-------------|---------------|
| `LOG_LEVEL` | STRING | Log level (DEBUG/INFO/WARNING/ERROR/CRITICAL) | All files |
| `LOG_FORMAT` | STRING | Log format (json/text) | All files |
| `LOG_OUTPUT` | STRING | Log output (stdout/file) | All files |
| `LOG_FILE` | PATH | Log file path | All files |

---

## Notes

1. **Password Formats:**
   - `MONGODB_PASSWORD`, `REDIS_PASSWORD`, `ELASTICSEARCH_PASSWORD`: 32 bytes base64
   - `JWT_SECRET`, `JWT_SECRET_KEY`: 64 bytes base64
   - `ENCRYPTION_KEY`: 32 bytes hex (64 hex characters)
   - `TRON_PRIVATE_KEY`: 32 bytes hex (64 hex characters)

2. **Source File Priority:**
   - Secrets come from `.env.secrets` (chmod 600)
   - Foundation data (MongoDB, Redis, base containers) from `.env.foundation`
   - Core services from `.env.core`
   - Application services from `.env.application`
   - Support services (TRON, RDP) from `.env.support`
   - OpenAPI values from open-api system
   - Tor onion addresses from `pickme/lucid-tor-proxy:latest-arm64` container

3. **Variable Conflicts:**
   - When same variable exists in multiple files, docker-compose uses LAST file loaded
   - Service-specific files should NOT duplicate passwords/secrets
   - Use explicit source file references in comments

4. **TRON_PRIVATE_KEY:**
   - Format: 64 hex characters (32 bytes)
   - Generated: `openssl rand -hex 32`
   - NOT a password - it's a cryptographic private key
   - TRON network accepts any valid 64-hex-character value