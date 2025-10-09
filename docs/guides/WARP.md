# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Build Context Reference Documents

This WARP.md is created based on the following specification documents located in `./Build_guide_docs/`:

- **Spec-1 — Table of Contents (lucid Rdp).txt** - Complete specification overview and requirement index
- **Spec-1a — Lucid Rdp_ Background & Requirements.txt** - Background, Must/Should/Could/Won't have requirements (R-MUST-001 through R-WONT-002)
- **Spec-1b — Lucid Rdp_ Method, Governance & Consensus.txt** - High-level architecture, blockchain contracts, governance, and Proof of Operational Tasks (PoOT) consensus
- **Spec-1c — Lucid Rdp_ Tokenomics, Wallet, Client Controls & Execution.txt** - Reward policy, tokenomics, wallet implementation, and client controls
- **Spec-1d — Lucid Rdp_ Build, Test, Run & Connectivity Outline.txt** - Build system, testing strategy, and implementation steps
- **Spec-2 — Lucid Rdp Gui Distributables.txt** - GUI client applications (User, Admin, Node GUIs)
- **mode_LUCID-STRICT.md** - Development mode guidelines and response format requirements

## Project Overview

**Lucid RDP** is a blockchain-integrated Remote Desktop program with unique single-use ID system for remote access sessions and a trust-nothing security model. It operates as a decentralized remote access network where nodes get paid monthly for providing services.

### Key Characteristics
- **Target Platform**: Raspberry Pi 5 (8GB RAM) running Ubuntu Server 64-bit
- **Network**: Tor-only operation (.onion services, no clearnet ingress)
- **Blockchain**: Dual-chain architecture - On-System Data Chain + TRON (Mainnet/Testnet)
- **Database**: MongoDB 7 only (no SQL permitted)
- **Build Environment**: Windows 11 console → Raspberry Pi via SSH

## Architecture Overview

### Core Components Structure
```
Raspberry Pi 5 (Ubuntu Server)
├── Admin UI (.onion, Next.js/Node 20)
├── RDP Host (xrdp/Wayland)
├── Session Recorder → Chunker+Compressor (Zstd)
├── Encryptor (XChaCha20-Poly1305) → Merkle Builder (BLAKE3)
├── On-System Chain Client
├── Tron-Node Client (TronWeb 6) - isolated service
├── Wallet Daemon (Hardware/Software vault)
├── MongoDB 7 (WiredTiger)
├── DHT/CRDT Node (encrypted metadata overlay)
└── Tor HS & SOCKS Proxy
```

### Multi-Service Architecture
- **03-api-gateway**: Main API gateway (FastAPI) - authentication, user management, blockchain proxying
- **04-blockchain-core**: Blockchain integration service (Tron network operations)
- **02-network-security**: Tor proxy and tunneling services
- **06-orchestration-runtime**: Docker Compose configurations
- **src/**: Core application modules
- **wallet/**: Wallet management components
- **blockchain/**: Blockchain interaction modules

### Data Flow
1. **Session Recording**: RDP → Recorder → Chunker (8-16MB) → Zstd compression
2. **Encryption**: XChaCha20-Poly1305 per-chunk with session-derived keys
3. **Anchoring**: Merkle root (BLAKE3) → On-System Data Chain (LucidAnchors)
4. **Payouts**: Monthly USDT-TRC20 via PayoutRouterV0/PRKYC on TRON

## Development Commands

### Environment Setup
```bash
# Start full development stack
docker-compose -f _compose_resolved.yaml --profile dev up -d

# Alternative: Manual container setup (Windows)
.\run-lucid-dev.ps1

# DevContainer setup (VS Code)
# Uses .devcontainer/devcontainer.json with ARM64 platform targeting
```

### Python Development
```bash
# Install dependencies from pyproject.toml
pip install -e .

# Install with dev dependencies
pip install -e ".[dev]"

# Core testing
pytest                          # Run all tests
pytest --cov                    # With coverage
pytest tests/api-gateway/       # Specific service tests
pytest tests/test_auth.py       # Single test file

# Code quality
ruff check .                    # Linting
ruff format .                   # Formatting (replaces black)
black .                         # Alternative formatter
mypy 03-api-gateway/api         # Type checking

# Security scanning
bandit -r 03-api-gateway/api 04-blockchain-core/api

# Pre-commit hooks
pre-commit run --all-files
pre-commit install
```

### Service-Specific Development
```bash
# API Gateway (port 8081)
cd 03-api-gateway/api
uvicorn app.main:app --reload --host 0.0.0.0 --port 8081

# Blockchain Core (port 8082)
cd 04-blockchain-core/api  
uvicorn app.main:app --reload --host 0.0.0.0 --port 8082
```

### Container & Build Commands
```bash
# Build ARM64 images for Raspberry Pi deployment
./build_and_push.sh

# Integrate compose files into DevContainer
./intergrate_lucid_dev.sh

# Clean up containers (Windows PowerShell)
.\Clean-LucidFromLists.ps1

# Force push all changes
./force_push_all.sh

# Pi bootstrap setup
./lucid_pi_bootstrap.sh
```

### Testing Strategy (Per Spec-1d)
```bash
# Unit tests by component
make test-unit                  # Unit tests
make test-integration          # Integration tests  
make test-e2e                  # End-to-end tests

# Component-specific testing
pytest tests/recorder/          # Session recording
pytest tests/chunker/           # Data chunking
pytest tests/encryptor/         # Encryption layer
pytest tests/merkle/            # Merkle tree building
pytest tests/chain-client/      # On-system chain
pytest tests/tron-node/         # TRON integration
pytest tests/contracts/         # Smart contracts
```

## Configuration Management

### Environment Variables (Critical Constants)
```bash
# Core system
LUCID_ENV=dev                   # Environment (dev/prod)
MONGO_URL=mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin
SERVICE_NAME=lucid-api
VERSION=0.1.0

# Blockchain integration
BLOCK_ONION=""                  # Blockchain onion service
BLOCK_RPC_URL=""               # Blockchain RPC endpoint
ONION=""                       # Service onion address
TOR_CONTROL_PASSWORD=""        # Tor control authentication

# Database
MONGO_INITDB_ROOT_USERNAME=Pickme_admin
MONGO_INITDB_ROOT_PASSWORD=[REDACTED]
```

### Key Configuration Files
- **pyproject.toml**: Python dependencies, tool configurations (black, ruff, mypy, pytest)
- **_compose_resolved.yaml**: Complete Docker Compose configuration
- **mypy.ini**: Type checking configuration with strict mode
- **pytest.ini**: Test configuration with quiet mode
- **.pre-commit-config.yaml**: Git hooks for code quality

## Smart Contracts & Blockchain Integration

### On-System Data Chain Contracts
- **LucidAnchors**: Session registration and manifest anchoring (immutable after deploy)
- **LucidChunkStore**: Encrypted chunk storage on-chain
- **PayoutRouterV0**: No-KYC USDT payouts (production)
- **PayoutRouterKYC**: KYC-gated payouts with compliance signatures
- **LucidGovernor + Timelock**: Governance system (one-node-one-vote)
- **ParamRegistry**: Bounded parameter adjustments only

### TRON Integration (Isolated Service)
- **Network**: Mainnet (production) / Shasta (testnet)
- **Token**: USDT-TRC20 for all payouts
- **Isolation**: Only Tron-Node System service interacts with TRON directly
- **Energy Management**: TRX staking for energy/bandwidth optimization

## Database Schema (MongoDB 7)

### Core Collections
```javascript
// Sessions
sessions: { 
  _id: UUID, owner_addr, started_at, ended_at, 
  manifest_hash, merkle_root, chunk_count, anchor_txid 
}

// Encrypted chunks (sharded)
chunks: { 
  _id, session_id: UUID, idx, local_path, 
  ciphertext_sha256, size_bytes 
} // Sharded on { session_id: 1, idx: 1 }

// Payouts
payouts: { 
  _id, session_id: UUID, to_addr, usdt_amount, 
  router, reason, txid 
}

// Consensus (PoOT)
task_proofs: { 
  _id, nodeId, poolId?, slot, type, value, sig, ts 
}
work_tally: { 
  _id: epoch, entityId, credits, liveScore, rank 
}
```

## Security Requirements

### Network Security (R-MUST-014, R-MUST-020)
- **Tor-only**: All GUIs/APIs exposed as .onion services
- **No clearnet**: Clearnet ingress completely disabled
- **Network isolation**: Separate Docker networks for different concerns
- **Firewall**: Ubuntu firewall rules enforced

### Cryptography
- **Session encryption**: XChaCha20-Poly1305 with per-chunk nonces
- **Key derivation**: HKDF-BLAKE2b for session keys
- **Hashing**: BLAKE3 for Merkle trees
- **Storage**: Hardware wallet (Ledger) for multisig, encrypted software keystore

### Trust-Nothing Policy (R-MUST-013)
- **Default-deny**: All input/clipboard/file transfer denied by default
- **JIT approvals**: Just-in-time permission grants
- **Policy verification**: Signed policy snapshot mismatches void sessions
- **Client-side enforcement**: Controls enforced at client level

## Consensus: Proof of Operational Tasks (PoOT)

### Work Credit Inputs (per 1-hour slots)
- Relay bandwidth served via Lucid Cloud Relay
- Storage availability proofs for encrypted chunks
- Validation signatures on On-System Chain blocks
- Uptime beacons (time-sealed heartbeats)

### Parameters (Immutable)
- **slotDurationSec**: 120s (max 30 blocks/hour)
- **slotTimeoutMs**: 5000 (5s to propose before fallback)
- **cooldownSlots**: 16 (prevent consecutive leadership)
- **leaderWindowDays**: 7 (sliding window for PoOT tally)

## GUI Development (Spec-2)

### Three Distributable GUIs
1. **User GUI**: Session initiation, client controls, proofs export
2. **Admin GUI**: Pi provisioning, manifests, payouts, key rotation
3. **Node GUI**: PoOT metrics, wallet management, payout batches

### Technology Stack
- **Language**: Python 3.11+ with Tkinter/ttk
- **Networking**: Requests + PySocks (SOCKS5 over Tor)
- **Cryptography**: cryptography package (Fernet/XChaCha20)
- **Data**: Pydantic models, orjson for serialization
- **Tor Integration**: Bundled tor binary with stem for control

## Development Rules (LUCID-STRICT Mode)

### Code Standards
- Use ONLY project files from this repository
- Use dockerhub and the content found in https://hub.docker.com/r/pickme/lucid for container build status
- Always check GitHub `HamiGames/Lucid` before operational changes
- Keep names consistent (e.g., `BLOCK_ONION`) across all files
- Cross-reference existing scripts before modifications
- Show full file paths when writing code

### Response Format Requirements
1. **SOURCES**: List exact files/paths used
2. **ASSUMPTIONS**: Must be "None" use build referrence materials (./Build_guide_docs/ *.txt and HamiGames/Lucid)
3. **PLAN/COMMANDS**: Numbered, minimal, copy-paste ready
4. **ACCEPTANCE**: Explicit checks/tests to prove success

### Failure Policy
- If requirements underspecified/conflict: "HALT — NEED" + list missing items
- Never invent values, paths, or environment variables
- Always process using chain-of-thought reasoning
- Wait for return data when instructions require testing

## Testing Requirements (R-MUST-019, Per Spec-1d)

### Test Environment
- All tests run on Raspberry Pi in CI
- Docker isolation for dependencies
- Integration/E2E tests route over Tor
- No SQL testing (MongoDB only)

### Test Categories
- **Unit**: Component isolation, golden tests, property tests
- **Integration**: Service-to-service over Docker networks
- **E2E**: Full session recording → anchoring → payout flows
- **Security**: Negative tests, signature validation, circuit breakers
- **Performance**: <300ms anchor latency, <2s USDT transfer initiation

## Build & Deployment

### Multi-Architecture Pipeline
- **Development**: Windows 11 console
- **Target**: Raspberry Pi 5 (ARM64) 
- **CI/CD**: Build on Pi using NVMe workspace
- **Images**: Multi-arch Docker images (ARM64)
- **Registry**: DockerHub (`pickme/lucid:*` tags)

### Deployment Environments
- **Sandbox/Test**: TRON Shasta, no-value payouts
- **Production**: TRON Mainnet, real USDT payouts via PayoutRouterV0/PRKYC

### Build Artifacts
- **Server**: Pi-flashable appliance image
- **Clients**: Cross-platform GUI distributables (Windows/macOS/Linux)
- **Containers**: ARM64 Docker images
- **Documentation**: Operator guides and API documentation

## File Structure Guidelines

### Monorepo Layout
```
/03-api-gateway/          # Main API service
/04-blockchain-core/      # Blockchain integration
/02-network-security/     # Tor/tunneling
/06-orchestration-runtime/ # Docker Compose configs
/src/                     # Core modules
/tests/                   # Test suites
/wallet/                  # Wallet components
/blockchain/              # Chain interactions
/Build_guide_docs/        # Specification documents
/.devcontainer/           # Development container
/.vscode/                 # VS Code settings
```

### Key Development Files
- **pyproject.toml**: Python project configuration
- **_compose_resolved.yaml**: Docker services definition
- **run-lucid-dev.ps1**: Windows development setup
- **build_and_push.sh**: ARM64 image building
- **mode_LUCID-STRICT.md**: Development guidelines

This WARP.md serves as the definitive guide for AI agents working within the Lucid RDP codebase, encompassing the complete architecture, development workflows, security requirements, and build processes as specified in the project documentation.