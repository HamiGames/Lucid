# Missing Components Analysis - Lucid RDP

## Based on Spec-1b, Spec-1c, Spec-1d Analysis

### **CRITICAL MISSING PYTHON MODULES**

#### **1. Session System (Per Spec-1b Architecture)**
- `chunker.py` - 8-16MB chunking with Zstd compression
- `encryptor.py` - XChaCha20-Poly1305 per-chunk encryption  
- `merkle_builder.py` - BLAKE3 Merkle tree construction
- `session_manager.py` - Centralized session orchestration

#### **2. Blockchain Core (Dual-chain per Spec-1b)**
- `on_system_chain_client.py` - LucidAnchors, LucidChunkStore contracts
- `tron_node_client.py` - Isolated TRON service (TronWeb 6)
- `wallet_daemon.py` - Hardware/Software wallet management
- `payout_manager.py` - PayoutRouterV0/PRKYC integration

#### **3. Admin & Management (Per Spec-1c)**
- `admin_ui_backend.py` - Next.js backend API handlers
- `key_rotation.py` - Multisig key rotation system
- `governance_client.py` - LucidGovernor + Timelock integration
- `params_registry.py` - Bounded parameter management

#### **4. DHT/CRDT Network (Per Spec-1b)**
- `dht_node.py` - Encrypted metadata overlay
- `crdt_manager.py` - Conflict-free replicated data
- `peer_discovery.py` - Tor-based node discovery
- `work_credits.py` - PoOT work calculation

#### **5. MongoDB Integration (Per Spec)**
- `mongo_sharding.py` - Chunks sharding on {session_id, idx}
- `collections_manager.py` - sessions/chunks/payouts schemas
- `consensus_collections.py` - task_proofs/work_tally/leader_schedule

#### **6. Client Controls (Per Spec-1c)**
- `control_policy.py` - Trust-nothing policy enforcement
- `session_controls.py` - JIT permission management
- `privacy_shield.py` - Client data redaction

### **CRITICAL MISSING BASH SCRIPTS**

#### **1. Build System (Per Spec-1d)**
- `build_ffmpeg_pi.sh` - Cross-compile FFmpeg with V4L2
- `build_contracts.sh` - Solidity compile & deploy
- `build_pi_image.sh` - Flashable appliance image
- `build_multi_arch.sh` - ARM64/x86_64 Docker images

#### **2. Service Management**
- `start_recording_service.sh` - xrdp + ffmpeg orchestration
- `start_blockchain_service.sh` - On-system chain startup
- `start_tron_service.sh` - Isolated TRON node
- `rotate_onion_keys.sh` - Tor hidden service rotation

#### **3. MongoDB Operations**
- `setup_mongo_sharding.sh` - Configure sharding for chunks
- `mongo_backup.sh` - S3-compatible encrypted backups
- `mongo_restore.sh` - Disaster recovery

#### **4. Testing & Verification (Per Spec-1d)**
- `test_tor_connectivity.sh` - .onion service verification
- `test_hardware_encoding.sh` - Pi V4L2 FFmpeg validation
- `test_blockchain_integration.sh` - End-to-end anchor+payout
- `chaos_testing.sh` - Failure injection for resilience

#### **5. PoOT Consensus (Per Spec-1b)**
- `collect_work_proofs.sh` - Relay/storage/validation metrics
- `calculate_work_credits.sh` - Monthly PoOT tally
- `leader_selection.sh` - Block publisher selection
- `uptime_beacon.sh` - Time-sealed heartbeats

### **CROSS-MODULE DEPENDENCY ISSUES**

#### **Import Path Problems:**
1. `src/session_recorder.py` imports don't align with monorepo structure
2. Missing `__init__.py` files in service directories
3. Hardcoded paths instead of environment variables
4. No proper service discovery/registry

#### **Required Directory Structure (Per Spec-1d):**
```
/apps/
  /admin-ui/ (Next.js)
  /recorder/ (daemon + ffmpeg/xrdp)
  /chunker/ (native addon or Python)  
  /encryptor/ (libsodium binding)
  /merkle/ (BLAKE3 binding)
  /chain-client/ (Node service)
  /tron-node/ (Node service using TronWeb)
  /walletd/ (key mgmt)
  /dht-node/ (CRDT/DHT)
  /exporter/ (S3 backups)
```

### **CONFIGURATION ALIGNMENT ISSUES**

#### **Environment Variables Missing:**
- `LUCID_ANCHOR_CONTRACT_ADDRESS` 
- `PAYOUT_ROUTER_V0_ADDRESS`
- `PAYOUT_ROUTER_KYC_ADDRESS`
- `ON_SYSTEM_CHAIN_RPC_URL`
- `TRON_ENERGY_STAKING_ADDRESS`
- `COMPLIANCE_SIGNER_KEY`

#### **Docker Compose Gaps:**
- No `chain-client` service definition
- No `tron-node` service isolation
- Missing hardware device mapping for Pi
- No proper network segmentation per spec

### **BUILD SYSTEM GAPS**

#### **Per Spec-1d Missing:**
- Cross-compilation setup for Pi ARM64
- Contract deployment to Shasta/Mainnet
- OTA update mechanism
- Performance monitoring integration

### **PRIORITY IMPLEMENTATION ORDER**

1. **P0 - Core Architecture**: Fix directory structure & imports
2. **P1 - Session Pipeline**: chunker → encryptor → merkle → anchor
3. **P2 - Blockchain Integration**: on-chain + TRON services  
4. **P3 - PoOT Consensus**: work credits & leader selection
5. **P4 - Admin & Controls**: UI backend & policy enforcement
6. **P5 - Testing & Deployment**: comprehensive test suite

This analysis shows significant gaps between current implementation and specification requirements. The project needs substantial modular restructuring to meet LUCID-STRICT compliance.