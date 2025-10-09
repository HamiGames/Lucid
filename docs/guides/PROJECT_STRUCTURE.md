# Lucid RDP Project Structure

This document outlines the reorganized file structure for the Lucid RDP project according to container groups and operational functions.

## Directory Structure Overview

```
Lucid/
├── user_content/                 # Standard user operations
│   ├── client/                   # User client modules
│   ├── gui/                      # User GUI modules
│   └── wallet/                   # User wallet modules
│
├── node/                         # Node operator (worker) operations
│   ├── worker/                   # Node worker specific scripts
│   │   └── node_routes.py        # Node API routes
│   ├── economy/                  # Node economy modules
│   └── gui/                      # Node GUI modules
│
├── admin/                        # Administrator operations
│   ├── system/                   # Admin system modules
│   │   ├── admin_controller.py   # Main admin controller
│   │   └── admin_manager.py      # Admin manager
│   ├── governance/               # Governance modules
│   ├── policies/                 # Policy modules
│   └── keys/                     # Key management modules
│
├── sessions/                     # Session management and processing
│   ├── core/                     # Core session modules
│   │   ├── chunker.py           # Data chunking
│   │   └── merkle_builder.py    # Merkle tree building
│   ├── pipeline/                 # Session pipeline
│   │   └── pipeline_manager.py  # Main pipeline manager
│   ├── encryption/               # Session encryption
│   │   └── encryptor.py         # Encryption manager
│   └── storage/                  # Session storage
│
├── RDP/                          # RDP connection processes and protocols
│   ├── protocol/                 # RDP protocol implementation
│   │   └── rdp_session.py       # Main RDP session handler
│   ├── client/                   # RDP client modules
│   ├── server/                   # RDP server modules
│   └── security/                 # RDP security modules
│       └── trust_controller.py  # Trust-nothing policy controller
│
├── open-api/                     # OpenAPI systems
│   ├── openapi.yaml             # OpenAPI specification
│   ├── api/                     # API modules (copied from 03-api-gateway)
│   ├── docs/                    # API documentation
│   └── gateway/                 # API gateway modules
│
├── blockchain/                   # Blockchain system functions
│   ├── core/                    # Blockchain core modules
│   │   ├── blockchain_engine.py # Main blockchain engine
│   │   ├── block.py            # Block implementation
│   │   ├── consensus.py        # Consensus mechanisms
│   │   ├── crypto.py           # Cryptographic functions
│   │   ├── network.py          # Network layer
│   │   ├── node.py             # Blockchain node
│   │   ├── state.py            # State management
│   │   ├── storage.py          # Storage layer
│   │   └── transaction.py      # Transaction handling
│   ├── data-entry/             # Blockchain data entry
│   ├── transaction-data/        # Transaction data management
│   ├── vm-system/              # Blockchain VM system
│   ├── ledger/                 # Ledger management
│   └── api/                    # Blockchain API
│
├── wallet/                      # Wallet specific features
│   └── (wallet modules to be organized)
│
├── 02-network-security/         # Network security and Tor portal setup
│   ├── tor/                    # Tor configuration and scripts
│   └── tunnels/                # Tunnel management
│
├── 03-api-gateways/            # API gateway linking modules and scripts
│   └── (same structure as 03-api-gateway)
│
├── payment-systems/             # Payment distribution systems
│   ├── tron-node/              # TRON node implementation
│   │   └── tron_client.py      # TRON client service
│   ├── governance/             # Payment governance
│   └── distribution/           # Payment distribution
│
├── virtual-machine/            # Virtual machine system operations
│   └── (VM modules to be added)
│
├── gui/                        # GUI modules and distribution
│   └── (GUI modules to be organized)
│
├── dev-team/                   # Development team materials
│   └── (dev GUI and admin GUI materials not required for operation)
│
├── common/                     # Build materials and scripts used across containers
│   ├── *.ps1                  # PowerShell scripts
│   ├── *.sh                   # Shell scripts
│   └── (other common build materials)
│
└── (existing directories maintained)
    ├── 00-foundation/
    ├── 06-orchestration-runtime/
    ├── 08-quality/
    ├── Build_guide_docs/
    ├── .devcontainer/
    ├── .verify/
    └── .ssh/
```

## Container Groups Mapping

### node (may split into multiple containers)
- `node/worker/` - node_worker
- `node/economy/` - node_economy  
- `node/gui/` - node_gui

### admin (may split into multiple containers)
- `admin/system/` - admin_system-mechanisms
- `admin/governance/` - admin governance
- GUI components in `gui/` for admin_gui

### dev (may split into multiple containers)
- `dev-team/` - dev_gui, dev_access-systems, dev_economy, dev_backend

### user (may split into multiple containers)
- `user_content/client/` - user operations
- `user_content/gui/` - user_gui
- Gateway components for user_gateway

### lucid_api
- `open-api/` - OpenAPI systems

### lucid_api_gateway (may split into multiple containers)
- `03-api-gateways/` - user, node, admin, dev, blockchain gateways

### tor-proxy
- `02-network-security/tor/` - foundational connection settings

### tunnel-tools
- `02-network-security/tunnels/` - portal opening mechanism

### blockchain (may split into multiple containers)
- `blockchain/core/` - blockchain-core
- `blockchain/data-entry/` - blockchain-data-entry
- `blockchain/transaction-data/` - blockchain-transaction-data
- `blockchain/vm-system/` - blockchain-vm-system
- `blockchain/ledger/` - blockchain-ledger

### sessions (may split into multiple containers)
- `sessions/core/` - sessions-core-systems
- `sessions/pipeline/` - session data processing
- `sessions/encryption/` - session encryption
- `sessions/storage/` - session storage

### wallet (may split into multiple containers)
- `wallet/` - user_wallet, node_wallet, admin_wallet, dev_wallet

### payment-systems (may split into multiple containers)
- `payment-systems/tron-node/` - TRON integration
- `payment-systems/governance/` - payment governance
- `payment-systems/distribution/` - payment distribution

## Import Path Updates

All Python modules have been updated with correct import paths:

- `from blockchain.core.blockchain_engine import ...`
- `from sessions.pipeline.pipeline_manager import ...`
- `from sessions.core.chunker import ...`
- `from admin.system.admin_controller import ...`
- `from RDP.protocol.rdp_session import ...`
- `from RDP.security.trust_controller import ...`

## File Relocations Completed

### Moved from `apps/` to organized structure:
- `apps/blockchain_core/blockchain_engine.py` → `blockchain/core/blockchain_engine.py`
- `apps/session_pipeline/pipeline_manager.py` → `sessions/pipeline/pipeline_manager.py`
- `apps/rdp_protocol/rdp_session.py` → `RDP/protocol/rdp_session.py`
- `apps/admin_system/admin_controller.py` → `admin/system/admin_controller.py`
- `apps/client_control/trust_controller.py` → `RDP/security/trust_controller.py`
- `apps/encryptor/encryptor.py` → `sessions/encryption/encryptor.py`
- `apps/chunker/chunker.py` → `sessions/core/chunker.py`
- `apps/merkle/merkle_builder.py` → `sessions/core/merkle_builder.py`

### API Specification:
- `openapi.yaml` → `open-api/openapi.yaml`

### Build Scripts:
- `*.ps1` and `*.sh` files → `common/` (copied)

### Payment Systems:
- TRON client → `payment-systems/tron-node/tron_client.py`

### Node Operations:
- `api/routes/node_routes.py` → `node/worker/node_routes.py`

### Admin Operations:
- `admin/admin_manager.py` → `admin/system/admin_manager.py`

## Next Steps

1. Update all Docker Compose files to reference new paths
2. Update all Dockerfile references
3. Update shell scripts to use new directory structure
4. Test all import statements and cross-references
5. Update CI/CD pipelines to use new structure
6. Update documentation and README files

This reorganization provides clear separation of concerns based on operational function and container group architecture while maintaining all existing functionality.