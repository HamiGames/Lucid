# Rebuild Blockchain Engine - Remove TRON Core, Implement On-System Chain

## Overview

Rebuild `blockchain/core/blockchain_engine.py` to align with Spec-1a, Spec-1b, and Spec-1c specifications:

- **Core blockchain**: On-System Data Chain (EVM-compatible) for session anchoring and consensus
- **PoOT Consensus**: Proof of Operational Tasks with work credits (not TRON)
- **TRON**: Isolated payment service only (USDT-TRC20 payouts via PayoutRouterV0/PRKYC)
- **Dual-chain architecture**: On-System Data Chain (data/consensus) + TRON (payments only)

## Key Changes

### 1. Core Blockchain Architecture

**Current Problem**: TRON is embedded in core consensus

**Solution**: Replace with On-System Data Chain

- Use LucidAnchors contract for session manifest anchoring
- Use LucidChunkStore contract for encrypted chunk metadata
- EVM-compatible chain (not TRON Virtual Machine in core)
- Gas-efficient event-based anchoring (per Spec-1b lines 56-59)

### 2. Consensus Mechanism

**Current**: Mixed TRON/PoOT implementation

**Solution**: Pure PoOT consensus on On-System Chain

- Work credits from: relay bandwidth, storage proofs, validation signatures, uptime beacons (Spec-1b lines 129-134)
- Leader selection: top-ranked entity with cooldown (Spec-1b lines 135-157)
- Slot duration: 120s fixed (immutable per Spec-1b line 170)
- MongoDB collections: `task_proofs`, `work_tally`, `leader_schedule` (Spec-1b lines 164-167)

### 3. TRON Isolation

**Current**: TronNodeSystem embedded in blockchain engine

**Solution**: Extract to separate isolated service

- TRON only for USDT-TRC20 payouts (R-MUST-015)
- No TRON in consensus, block publishing, or anchoring
- PayoutRouterV0 (non-KYC) and PayoutRouterKYC (KYC-gated) for monthly payouts
- Energy/bandwidth management via TRX staking

## Implementation Plan

### Step 1: Rebuild Core Blockchain Classes

#### 1.1 Update SessionAnchor dataclass

- Remove TRON-specific fields
- Focus on On-System Chain anchoring (LucidAnchors contract)
- Fields: `session_id`, `manifest_hash`, `merkle_root`, `started_at`, `owner_address`, `chunk_count`, `block_number`, `txid`, `gas_used`, `status`

#### 1.2 Update TronPayout dataclass  

- Keep for payment operations only
- Mark as payment-layer only (not blockchain core)

#### 1.3 Rebuild OnSystemChainClient

- Primary blockchain client (not secondary)
- LucidAnchors contract integration: `registerSession(sessionId, manifestHash, startedAt, owner, merkleRoot, chunkCount)`
- LucidChunkStore contract integration for chunk metadata
- EVM JSON-RPC interface (not TRON API)
- Gas estimation and circuit breakers

#### 1.4 Isolate TronNodeSystem

- Extract from core blockchain engine
- Mark as payment service only
- Monthly payout distribution (R-MUST-018)
- Router selection: PayoutRouterV0 (non-KYC) vs PayoutRouterKYC (KYC-gated)

### Step 2: Rebuild PoOTConsensusEngine

#### 2.1 Work Credits System

- Inputs: relay_bandwidth, storage_availability, validation_signature, uptime_beacon
- MongoDB `task_proofs` collection: `{ _id, nodeId, poolId?, slot, type, value, sig, ts }`
- Sharding: `{ slot: 1, nodeId: 1 }` (Spec-1b line 165)
- Work formula: `W_t = max(S_t, ceil(B_t / BASE_MB_PER_SESSION))` where BASE_MB_PER_SESSION = 5MB

#### 2.2 Leader Selection

- Compute WorkCredits over sliding window (7 days default)
- Rank entities (node or pool)
- Primary leader = top-ranked, not in cooldown (16 slots)
- Fallbacks: next ranked entities
- VRF tie-breaking for equal credits
- MongoDB `leader_schedule`: `{ _id, slot, primary, fallbacks, result }`

#### 2.3 Consensus Parameters (Immutable)

```python
SLOT_DURATION_SEC = 120  # Fixed, immutable
SLOT_TIMEOUT_MS = 5000   # 5s leader timeout
COOLDOWN_SLOTS = 16      # 16 slot cooldown
LEADER_WINDOW_DAYS = 7   # 7-day PoOT window
D_MIN = 0.2             # Minimum density threshold
BASE_MB_PER_SESSION = 5  # 5MB base unit
```

### Step 3: Rebuild BlockchainEngine

#### 3.1 Initialize with On-System Chain as Primary

```python
def __init__(self):
    self.on_chain_client = OnSystemChainClient(
        ON_SYSTEM_CHAIN_RPC,
        {
            "LucidAnchors": LUCID_ANCHORS_ADDRESS,
            "LucidChunkStore": LUCID_CHUNK_STORE_ADDRESS
        }
    )
    self.tron_client = TronNodeSystem(TRON_NETWORK)  # Payment service only
    self.consensus_engine = PoOTConsensusEngine(self.db)
```

#### 3.2 Slot Timer (PoOT consensus)

- 120s slot duration
- Leader selection per slot
- Block publishing by primary leader
- Fallback mechanism on timeout
- Work credits calculation every epoch

#### 3.3 Session Anchoring (On-System Chain)

- Anchor to LucidAnchors contract (not TRON)
- Event-based anchoring (gas-efficient)
- MongoDB `sessions` collection storage
- Status monitoring loop

#### 3.4 Payment Processing (TRON isolated)

- Monthly payout distribution
- Router selection: PayoutRouterV0 vs PayoutRouterKYC
- USDT-TRC20 transfers only
- MongoDB `payouts` collection
- Status monitoring loop

### Step 4: Update MongoDB Schema

#### 4.1 Sessions Collection

```javascript
{
  _id: UUID,
  owner_addr: String,
  started_at: Timestamp,
  ended_at: Timestamp,
  manifest_hash: String,
  merkle_root: String,
  chunk_count: Number,
  anchor_txid: String,  // On-System Chain txid
  block_number: Number,
  gas_used: Number,
  status: String
}
```

#### 4.2 Chunks Collection (Sharded)

```javascript
{
  _id: String,
  session_id: UUID,
  idx: Number,
  local_path: String,
  ciphertext_sha256: String,
  size_bytes: Number
}
// Shard key: { session_id: 1, idx: 1 }
```

#### 4.3 Payouts Collection (TRON only)

```javascript
{
  _id: String,
  session_id: UUID,
  to_addr: String,
  usdt_amount: Number,
  router: String,  // "PayoutRouterV0" or "PayoutRouterKYC"
  reason: String,
  txid: String,    // TRON txid
  status: String,
  created_at: Timestamp,
  kyc_hash: String,
  compliance_sig: Object
}
```

#### 4.4 Consensus Collections

```javascript
// task_proofs (sharded on { slot: 1, nodeId: 1 })
{
  _id: String,
  nodeId: String,
  poolId: String,
  slot: Number,
  type: String,  // relay_bandwidth, storage_availability, validation_signature, uptime_beacon
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

### Step 5: Update Environment Variables

Remove TRON blockchain vars, add On-System Chain vars:

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

## Files to Update

### Primary File

1. **blockchain/core/blockchain_engine.py** - Complete rebuild
   - Remove TRON from core blockchain logic
   - Implement On-System Chain as primary
   - Rebuild PoOT consensus engine
   - Isolate TRON to payment service only

### Supporting Files (Follow-up Corrections)

2. **blockchain/blockchain_anchor.py**
   - Update to use On-System Chain primarily
   - Remove TRON anchoring logic
   - Keep TRON payment integration

3. **blockchain/on_system_chain/chain_client.py**
   - Ensure EVM compatibility
   - LucidAnchors and LucidChunkStore contract interfaces
   - Gas estimation and circuit breakers

4. **blockchain/chain-client/on_system_chain_client.py**
   - Align with new architecture
   - Remove TRON dependencies from core

5. **blockchain/api/app/config.py**
   - Update environment variables
   - Separate On-System Chain config from TRON config

6. **infrastructure/docker/blockchain/env/*.env**
   - Update all blockchain service environment files
   - Add On-System Chain RPC endpoints
   - Clarify TRON is payment-only

7. **docker-compose.yml** / **docker-compose.pi.yml**
   - Add On-System Chain service container
   - Separate TRON as payment service
   - Update service dependencies

8. **scripts/database/init_mongodb_schema.js**
   - Add consensus collections with proper indexes
   - Update sessions/chunks schema
   - Add payouts collection

## Testing Requirements

1. **Unit Tests**
   - PoOT consensus work credits calculation
   - Leader selection with cooldown
   - Session anchoring to On-System Chain
   - TRON payment isolation

2. **Integration Tests**
   - End-to-end session anchoring flow
   - PoOT consensus slot progression
   - Monthly payout distribution via TRON
   - MongoDB sharding and replication

3. **Acceptance Criteria**
   - On-System Chain anchors session manifests successfully
   - PoOT consensus selects leaders correctly
   - TRON payments work independently from blockchain core
   - No TRON imports in core consensus code
   - All MongoDB collections properly indexed

## Dependencies to Update

**Remove from core**:
- `tronpy` - move to isolated payment service

**Add/Update**:
- `httpx` - for On-System Chain RPC calls
- `blake3` - for Merkle root computation
- `motor` - MongoDB async driver (already present)

## Notes
- TRON is completely isolated from blockchain consensus
- On-System Data Chain is the core Lucid blockchain
- PoOT consensus runs on On-System Chain (not TRON)
- Monthly payouts use TRON as payment rail only
- All session anchoring uses LucidAnchors contract
- Governance and consensus are separate (one-node-one-vote)
