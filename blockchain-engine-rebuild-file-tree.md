# Lucid Blockchain Engine Rebuild - Complete File Tree

This document shows the complete file tree structure after implementing the blockchain engine rebuild as specified in `plan/rebuild-blockchain-engine.md`.

## Complete Project Structure

```
Lucid/
├── 📁 build/                          # Build artifacts and logs
│   ├── artifacts/                     # Build outputs
│   └── logs/                         # Build logs
│
├── 📁 configs/                       # Configuration files
│   ├── docker/                       # Docker configurations
│   ├── environment/                  # Environment files (.env.*)
│   │   ├── .env.blockchain           # Blockchain-specific environment
│   │   ├── .env.on-system-chain      # On-System Chain configuration
│   │   ├── .env.tron-payments        # TRON payment service only
│   │   └── .env.poot-consensus       # PoOT consensus parameters
│   ├── ssh/                         # SSH keys and configuration
│   └── *.yaml                       # Global configuration files
│
├── 📁 docs/                          # Documentation
│   ├── build-docs/                   # Build guides and specifications
│   ├── guides/                       # User guides and manuals
│   ├── specs/                        # Technical specifications
│   │   ├── spec-1a.md                # On-System Data Chain specification
│   │   ├── spec-1b.md                # PoOT Consensus specification
│   │   └── spec-1c.md                # TRON Payment isolation specification
│   └── verification/                 # Testing and verification reports
│
├── 📁 infrastructure/                # Infrastructure as Code
│   ├── compose/                      # Docker Compose files
│   │   ├── docker-compose.yml        # Main production compose
│   │   ├── docker-compose.pi.yml     # Raspberry Pi deployment
│   │   ├── docker-compose.test.yml   # Testing environment
│   │   └── docker-compose.dev.yml    # Development environment
│   ├── containers/                   # Container configurations
│   │   ├── .devcontainer/            # Development container
│   │   │   ├── devcontainer.json
│   │   │   └── docker-compose.dev.yml
│   │   ├── distroless/               # Distroless containers
│   │   │   ├── base/                 # Base distroless image
│   │   │   └── services/             # Service-specific distroless
│   │   └── multi-stage/              # Multi-stage builds
│   │       ├── Dockerfile.gui
│   │       ├── Dockerfile.blockchain
│   │       ├── Dockerfile.rdp
│   │       ├── Dockerfile.node
│   │       ├── Dockerfile.storage
│   │       ├── Dockerfile.database
│   │       └── Dockerfile.vm
│   └── docker/                       # Docker service configurations
│       ├── blockchain/               # Blockchain service configs
│       │   ├── env/                  # Environment files
│       │   │   ├── .env.on-chain     # On-System Chain config
│       │   │   ├── .env.tron         # TRON payment config
│       │   │   └── .env.consensus    # PoOT consensus config
│       │   └── Dockerfile            # Blockchain container
│       └── on-chain-distroless/      # On-System Chain node
│           ├── Dockerfile
│           └── config/
│
├── 📁 scripts/                       # Automation scripts
│   ├── build/                        # Build automation
│   │   ├── build-services.sh         # Service build script
│   │   ├── optimize-layers.py        # Layer optimization
│   │   └── build-distroless.sh       # Distroless build script
│   ├── deployment/                   # Deployment scripts
│   │   ├── deploy-pi.sh              # Raspberry Pi deployment
│   │   ├── rollback.sh               # Rollback script
│   │   └── health-check.sh           # Health monitoring
│   ├── devcontainer/                 # Development container scripts
│   │   └── setup-build-factory.sh    # Build factory setup
│   ├── database/                     # Database management
│   │   ├── init_mongodb_schema.js    # MongoDB schema initialization
│   │   ├── create_shards.js          # Sharding setup
│   │   └── backup_restore.sh         # Backup and restore
│   ├── network/                      # Network and security scripts
│   └── testing/                      # Testing scripts
│       ├── test-data-generator.py    # Test data generation
│       ├── integration-tests.sh      # Integration test runner
│       └── performance-tests.sh      # Performance test runner
│
├── 📁 blockchain/                    # Blockchain system functions (REBUILT)
│   ├── __init__.py                   # Updated blockchain module init
│   ├── core/                         # Core blockchain modules (REBUILT)
│   │   ├── __init__.py               # Core module init
│   │   ├── blockchain_engine.py      # REBUILT: Main blockchain engine
│   │   │                             # - On-System Chain as primary
│   │   │                             # - TRON isolated for payments only
│   │   │                             # - PoOT consensus implementation
│   │   │                             # - Session anchoring to LucidAnchors
│   │   ├── models.py                 # Updated data models
│   │   │                             # - SessionAnchor (On-System Chain)
│   │   │                             # - TronPayout (payment only)
│   │   │                             # - PoOT consensus models
│   │   ├── consensus.py              # PoOT consensus engine
│   │   │                             # - Work credits calculation
│   │   │                             # - Leader selection
│   │   │                             # - Slot management (120s)
│   │   ├── block.py                  # Block implementation
│   │   ├── crypto.py                 # Cryptographic functions
│   │   ├── network.py                # Network layer
│   │   ├── node.py                   # Blockchain node
│   │   ├── state.py                  # State management
│   │   ├── storage.py                # Storage layer
│   │   └── transaction.py            # Transaction handling
│   │
│   ├── on_system_chain/              # On-System Data Chain (PRIMARY)
│   │   ├── __init__.py               # On-System Chain module init
│   │   ├── chain_client.py           # REBUILT: Primary blockchain client
│   │   │                             # - EVM-compatible JSON-RPC
│   │   │                             # - LucidAnchors contract integration
│   │   │                             # - LucidChunkStore contract integration
│   │   │                             # - Gas estimation and circuit breakers
│   │   ├── contracts/                # Smart contracts
│   │   │   ├── LucidAnchors.sol      # Session anchoring contract
│   │   │   ├── LucidChunkStore.sol   # Chunk metadata contract
│   │   │   └── abi/                  # Contract ABIs
│   │   │       ├── LucidAnchors.json
│   │   │       └── LucidChunkStore.json
│   │   ├── deployment/               # Contract deployment
│   │   │   ├── deploy_contracts.py   # Contract deployment script
│   │   │   └── verify_contracts.py   # Contract verification
│   │   └── config.py                 # On-System Chain configuration
│   │
│   ├── chain-client/                 # Chain client implementations
│   │   ├── __init__.py
│   │   └── on_system_chain_client.py # REBUILT: Aligned with new architecture
│   │                                 # - Remove TRON dependencies from core
│   │                                 # - Focus on On-System Chain
│   │
│   ├── tron_node/                    # TRON payment service (ISOLATED)
│   │   ├── __init__.py               # TRON module init (payment only)
│   │   ├── tron_client.py            # REBUILT: Payment service only
│   │   │                             # - USDT-TRC20 transfers
│   │   │                             # - PayoutRouterV0 (non-KYC)
│   │   │                             # - PayoutRouterKYC (KYC-gated)
│   │   │                             # - Monthly payout distribution
│   │   │                             # - NO consensus or anchoring
│   │   ├── payout_router.py          # Payout router implementation
│   │   ├── kyc_validator.py          # KYC validation for payouts
│   │   └── energy_manager.py         # TRX staking for energy/bandwidth
│   │
│   ├── blockchain_anchor.py          # REBUILT: Session anchoring
│   │                                 # - Use On-System Chain primarily
│   │                                 # - Remove TRON anchoring logic
│   │                                 # - Keep TRON payment integration
│   │
│   ├── deployment/                   # Contract deployment
│   │   ├── contract_deployment.py    # Smart contract deployment service
│   │   └── deployment_manager.py     # Deployment management
│   │
│   ├── data-entry/                   # Blockchain data entry
│   ├── transaction-data/             # Transaction data management
│   ├── vm-system/                    # Blockchain VM system
│   ├── ledger/                       # Ledger management
│   └── api/                          # Blockchain API
│       ├── __init__.py
│       ├── app.py                    # FastAPI application
│       ├── routes/                   # API routes
│       │   ├── __init__.py
│       │   ├── sessions.py           # Session management endpoints
│       │   ├── consensus.py          # Consensus endpoints
│       │   ├── anchoring.py          # Anchoring endpoints
│       │   └── payouts.py            # Payment endpoints (TRON only)
│       ├── middleware/               # API middleware
│       └── config.py                 # REBUILT: Updated environment variables
│                                 # - Separate On-System Chain config
│                                 # - Separate TRON config
│
├── 📁 sessions/                      # Session management and processing
│   ├── core/                         # Core session modules
│   │   ├── chunker.py               # Data chunking
│   │   └── merkle_builder.py        # Merkle tree building
│   ├── pipeline/                     # Session pipeline
│   │   └── pipeline_manager.py      # Main pipeline manager
│   ├── encryption/                   # Session encryption
│   │   └── encryptor.py             # Encryption manager
│   └── storage/                      # Session storage
│
├── 📁 RDP/                           # RDP connection processes and protocols
│   ├── protocol/                     # RDP protocol implementation
│   │   └── rdp_session.py           # Main RDP session handler
│   ├── client/                       # RDP client modules
│   ├── server/                       # RDP server modules
│   └── security/                     # RDP security modules
│       └── trust_controller.py      # Trust-nothing policy controller
│
├── 📁 open-api/                      # OpenAPI systems
│   ├── openapi.yaml                 # OpenAPI specification
│   ├── api/                         # API modules
│   ├── docs/                        # API documentation
│   └── gateway/                     # API gateway modules
│
├── 📁 user_content/                  # Standard user operations
│   ├── client/                       # User client modules
│   ├── gui/                          # User GUI modules
│   └── wallet/                       # User wallet modules
│
├── 📁 node/                          # Node operator (worker) operations
│   ├── worker/                       # Node worker specific scripts
│   │   └── node_routes.py           # Node API routes
│   ├── economy/                      # Node economy modules
│   └── gui/                          # Node GUI modules
│
├── 📁 admin/                         # Administrator operations
│   ├── system/                       # Admin system modules
│   │   ├── admin_controller.py      # Main admin controller
│   │   └── admin_manager.py         # Admin manager
│   ├── governance/                   # Governance modules
│   ├── policies/                     # Policy modules
│   └── keys/                         # Key management modules
│
├── 📁 wallet/                        # Wallet specific features
│
├── 📁 payment-systems/               # Payment distribution
│   ├── tron-node/                    # TRON payment node
│   ├── governance/                   # Payment governance
│   └── distribution/                 # Payment distribution
│
├── 📁 virtual-machine/               # VM system operations
│
├── 📁 gui/                           # GUI modules and distribution
│
├── 📁 dev-team/                      # Development team materials
│
├── 📁 02-network-security/           # Core networking components
│   ├── tor/                          # Tor proxy with multi-onion support
│   │   ├── torrc.dev                 # Development Tor config
│   │   ├── torrc.prod                # Production Tor config
│   │   └── torrc.pi                  # Raspberry Pi Tor config
│   └── tunnels/                      # Portal opening mechanism
│
├── 📁 tests/                         # Test suites
│   ├── unit/                         # Unit tests
│   │   ├── blockchain/               # Blockchain unit tests
│   │   │   ├── test_blockchain_engine.py
│   │   │   ├── test_poot_consensus.py
│   │   │   ├── test_on_system_chain.py
│   │   │   └── test_tron_payments.py
│   │   ├── sessions/                 # Session unit tests
│   │   ├── rdp/                      # RDP unit tests
│   │   └── api/                      # API unit tests
│   ├── integration/                  # Integration tests
│   │   ├── blockchain-integration/   # Blockchain integration tests
│   │   │   ├── test_session_anchoring.py
│   │   │   ├── test_consensus_flow.py
│   │   │   └── test_payment_isolation.py
│   │   ├── api-integration/          # API integration tests
│   │   ├── rdp-integration/          # RDP integration tests
│   │   ├── session-integration/      # Session integration tests
│   │   ├── storage-integration/      # Storage integration tests
│   │   ├── vm-integration/           # VM integration tests
│   │   ├── gui-integration/          # GUI integration tests
│   │   └── end-to-end/               # End-to-end tests
│   ├── performance/                  # Performance tests
│   │   ├── benchmark/                # Benchmark tests
│   │   └── load-testing/             # Load testing
│   │       └── locustfile.py         # Locust load test configuration
│   └── fixtures/                     # Test fixtures and data
│
├── 📁 .github/                       # GitHub Actions workflows
│   └── workflows/
│       ├── build-distroless.yml      # Multi-stage distroless builds
│       ├── deploy-pi.yml             # Raspberry Pi deployment
│       ├── test-integration.yml      # Integration testing
│       └── security-scan.yml         # Security scanning
│
├── 📁 .devcontainer/                 # Development container
│   ├── devcontainer.json             # Dev container configuration
│   └── docker-compose.dev.yml        # Dev container compose
│
├── 📄 README.md                      # Project documentation
├── 📄 .gitignore                     # Git ignore rules
├── 📄 pyproject.toml                 # Python project configuration
├── 📄 requirements.txt               # Python dependencies
├── 📄 docker-compose.yml             # Main Docker Compose
├── 📄 docker-compose.pi.yml          # Raspberry Pi Docker Compose
└── 📄 plan/                          # Project planning documents
    ├── rebuild-blockchain-engine.md  # Blockchain engine rebuild plan
    └── blockchain-engine-rebuild-file-tree.md  # This file
```

## Key Changes from Current Structure

### 🔄 **REBUILT Files**

1. **`blockchain/core/blockchain_engine.py`**
   - Complete rebuild with On-System Chain as primary
   - TRON isolated to payment service only
   - PoOT consensus implementation
   - Session anchoring to LucidAnchors contract

2. **`blockchain/on_system_chain/chain_client.py`**
   - REBUILT as primary blockchain client
   - EVM-compatible JSON-RPC interface
   - LucidAnchors and LucidChunkStore contract integration
   - Gas estimation and circuit breakers

3. **`blockchain/tron_node/tron_client.py`**
   - REBUILT as payment service only
   - USDT-TRC20 transfers via PayoutRouterV0/PRKYC
   - Monthly payout distribution
   - NO consensus or anchoring logic

4. **`blockchain/core/models.py`**
   - Updated SessionAnchor for On-System Chain
   - TronPayout marked as payment-only
   - New PoOT consensus models

5. **`blockchain/core/consensus.py`**
   - New PoOT consensus engine
   - Work credits calculation
   - Leader selection with cooldown
   - 120s slot duration (immutable)

6. **`blockchain/api/app/config.py`**
   - Updated environment variables
   - Separate On-System Chain config
   - Separate TRON config

### ➕ **NEW Files**

1. **`blockchain/on_system_chain/contracts/`**
   - `LucidAnchors.sol` - Session anchoring contract
   - `LucidChunkStore.sol` - Chunk metadata contract
   - Contract ABIs and deployment scripts

2. **`blockchain/core/consensus.py`**
   - New PoOT consensus implementation
   - Work credits system
   - Leader selection algorithm

3. **Environment Configuration Files**
   - `.env.on-system-chain` - On-System Chain configuration
   - `.env.tron-payments` - TRON payment service config
   - `.env.poot-consensus` - PoOT consensus parameters

4. **Database Schema Updates**
   - `scripts/database/init_mongodb_schema.js` - Updated with consensus collections
   - New MongoDB collections: `task_proofs`, `work_tally`, `leader_schedule`

### 🗑️ **REMOVED/ISOLATED**

1. **TRON Dependencies from Core**
   - `tronpy` moved to isolated payment service
   - No TRON imports in core consensus code
   - TRON blockchain logic completely isolated

2. **Mixed Consensus Logic**
   - Removed TRON/PoOT mixed implementation
   - Pure PoOT consensus on On-System Chain only

### 📊 **MongoDB Collections (Updated Schema)**

```javascript
// sessions (updated)
{
  _id: UUID,
  owner_addr: String,
  started_at: Timestamp,
  ended_at: Timestamp,
  manifest_hash: String,
  merkle_root: String,
  chunk_count: Number,
  anchor_txid: String,      // On-System Chain txid
  block_number: Number,
  gas_used: Number,
  status: String
}

// chunks (sharded)
{
  _id: String,
  session_id: UUID,
  idx: Number,
  local_path: String,
  ciphertext_sha256: String,
  size_bytes: Number
}
// Shard key: { session_id: 1, idx: 1 }

// payouts (TRON only)
{
  _id: String,
  session_id: UUID,
  to_addr: String,
  usdt_amount: Number,
  router: String,           // "PayoutRouterV0" or "PayoutRouterKYC"
  reason: String,
  txid: String,             // TRON txid
  status: String,
  created_at: Timestamp,
  kyc_hash: String,
  compliance_sig: Object
}

// task_proofs (sharded on { slot: 1, nodeId: 1 })
{
  _id: String,
  nodeId: String,
  poolId: String,
  slot: Number,
  type: String,             // relay_bandwidth, storage_availability, validation_signature, uptime_beacon
  value: Object,
  sig: String,
  ts: Timestamp
}

// work_tally (replicated)
{
  _id: String,
  epoch: Number,
  entityId: String,
  credits: Number,
  liveScore: Number,
  rank: Number
}

// leader_schedule (replicated)
{
  _id: Number,
  slot: Number,
  primary: String,
  fallbacks: Array,
  result: { winner: String, reason: String }
}
```

## Environment Variables (Updated)

```bash
# On-System Data Chain (Core Blockchain)
ON_SYSTEM_CHAIN_RPC=http://on-chain-distroless:8545
LUCID_ANCHORS_ADDRESS=0x...
LUCID_CHUNK_STORE_ADDRESS=0x...

# TRON (Payment Layer Only)
TRON_NETWORK=shasta  # or mainnet
USDT_TRC20_MAINNET=TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t
USDT_TRC20_SHASTA=TG3XXyExBkPp9nzdajDZsozEu4BkaSJozs
PAYOUT_ROUTER_V0_ADDRESS=T...
PAYOUT_ROUTER_KYC_ADDRESS=T...

# PoOT Consensus Parameters
SLOT_DURATION_SEC=120
SLOT_TIMEOUT_MS=5000
COOLDOWN_SLOTS=16
LEADER_WINDOW_DAYS=7
D_MIN=0.2
BASE_MB_PER_SESSION=5

# MongoDB
MONGO_URI=mongodb://lucid:lucid@mongo-distroless:27019/lucid?authSource=admin&retryWrites=false&directConnection=true
```

## Testing Structure

The testing structure has been expanded to cover all aspects of the rebuilt blockchain engine:

- **Unit Tests**: Individual component testing
- **Integration Tests**: Cross-component testing
- **End-to-End Tests**: Full system testing
- **Performance Tests**: Load and benchmark testing
- **Security Tests**: Vulnerability scanning

## Deployment Structure

The deployment structure supports:
- **Development**: Local development with Docker-in-Docker
- **Testing**: Automated testing environments
- **Production**: Distroless containers for production
- **Raspberry Pi**: ARM64 optimized deployment

This file tree represents the complete structure after implementing the blockchain engine rebuild as specified in the plan document.
