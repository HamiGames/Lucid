# Genesis Block Creation Guide

## Overview

The genesis block is the first block (height 0) in the Lucid blockchain. It must be created manually before the blockchain engine starts, or the engine will auto-create a default genesis block. **Once created, the genesis block cannot be modified or replaced.**

---

## Requirements

### Mandatory Fields

| Field | Type | Value | Description |
|-------|------|-------|-------------|
| `height` | `int` | `0` | **MUST** be exactly 0 (fixed) |
| `previous_hash` | `str` | `"0" * 64` | **MUST** be 64 zeros: `0000000000000000000000000000000000000000000000000000000000000000` |
| `timestamp` | `datetime` | UTC ISO format | Current UTC timestamp (e.g., `2025-12-15T06:32:48.000Z`) |
| `hash` | `str` | 64 hex chars | Calculated after all fields are set (lowercase) |
| `merkle_root` | `str` | 64 hex chars | Calculated from transactions (lowercase) |
| `transactions` | `List[Dict]` | At least 1 | Must contain at least one genesis transaction |
| `producer` | `str` | Any | Producer/validator identifier |
| `signature` | `str` | Any | Block signature (recommended: cryptographic signature) |

### Genesis Transaction Requirements

Each transaction in the genesis block must have:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | `str` | Yes | Unique transaction ID (e.g., `genesis_{timestamp}`) |
| `from_address` | `str` | Yes | Sender address (can be zero address: `0x0000...0000`) |
| `to_address` | `str` | Yes | Recipient address (can be zero address) |
| `value` | `float` | Yes | Transaction value (typically `0` for genesis) |
| `data` | `Dict` | Yes | Transaction data (JSON object) |
| `timestamp` | `datetime` | Yes | UTC timestamp (ISO format) |
| `signature` | `str` | Yes | Transaction signature |

### Recommended Genesis Transaction Data Structure

```json
{
  "type": "genesis",
  "network": "<your_network_name>",
  "version": "<your_version>",
  "consensus": "<consensus_algorithm>",
  "created_at": "<iso_timestamp>"
}
```

---

## Restrictions & Validation Rules

### Block-Level Restrictions

1. **Height**: Must be exactly `0` (no other value allowed)
2. **Previous Hash**: Must be exactly 64 zeros (`"0" * 64`)
3. **Hash Format**: All hash fields must be:
   - 64 characters long
   - Valid hexadecimal (0-9, a-f)
   - Lowercase
4. **Timestamp**: Cannot be more than 5 minutes in the future
5. **Block Size**: Maximum 1 MB (1,048,576 bytes)
6. **Transaction Count**: Maximum 1,000 transactions per block
7. **Uniqueness**: Only one genesis block can exist (height 0 is unique in database)

### Transaction-Level Restrictions

1. **Transaction ID**: Must be unique (no duplicates)
2. **Addresses**: Must be at least 20 characters
3. **Value**: Cannot be negative
4. **Data**: Must be valid JSON if provided as string

### Validation Checks Performed

The system will validate:
- ✅ Block hash matches calculated hash
- ✅ Merkle root matches calculated root from transactions
- ✅ Previous hash is exactly 64 zeros
- ✅ Height is exactly 0
- ✅ Timestamp is valid (not too far in future)
- ✅ Block size is within limits
- ✅ All hash fields are valid hexadecimal
- ✅ Transaction count is within limits

---

## Creation Process

### Step 1: Prepare Genesis Transaction

1. Create a unique transaction ID (e.g., `genesis_{unix_timestamp}`)
2. Set addresses (zero address `0x0000...0000` is acceptable for genesis)
3. Set transaction value (typically `0`)
4. Create transaction data object with network information
5. Set timestamp to current UTC time
6. Generate transaction signature (recommended: cryptographic signature)

### Step 2: Calculate Merkle Root

The Merkle root is calculated using **Blake3** hashing algorithm:
- Each transaction ID is hashed using Blake3
- Hashes are paired and combined until a single root hash remains
- Result must be 64-character hexadecimal string (lowercase)

**Note**: The system uses `blake3.blake3(tx.id.encode()).hexdigest()` for transaction hashing.

### Step 3: Create Block Structure

1. Set `height = 0`
2. Set `previous_hash = "0" * 64` (64 zeros)
3. Set `timestamp` to current UTC time (ISO format)
4. Add genesis transaction(s) to `transactions` array
5. Calculate and set `merkle_root` from transactions
6. Set `producer` (your validator/producer identifier)
7. Set `signature` (recommended: cryptographic signature)
8. Set optional fields:
   - `nonce`: Default `0`
   - `difficulty`: Default `1.0`
   - `version`: Default `1`

### Step 4: Calculate Block Hash

The block hash is calculated using **Blake3** hashing algorithm with the following header data:

```
header_data = f"{height}{previous_hash}{timestamp.isoformat()}{merkle_root}{producer}{transaction_count}"
block_hash = blake3.blake3(header_data.encode()).hexdigest()
```

**Important**: The hash must be calculated **after** all other fields are set, as it includes those fields in the calculation.

### Step 5: Validate Block

Before importing, verify:
- ✅ All required fields are present
- ✅ Hash format is correct (64 hex chars, lowercase)
- ✅ Merkle root matches calculated value
- ✅ Block hash matches calculated value
- ✅ Timestamp is valid (not more than 5 minutes in future)
- ✅ Block size is within 1 MB limit

---

## Import Method

### Option 1: Direct MongoDB Insert (Recommended)

Insert the genesis block directly into MongoDB before starting the blockchain engine:

```bash
# Connect to MongoDB
mongosh mongodb://<connection_string>/lucid_blockchain

# Insert genesis block
db.blocks.insertOne({
  "_id": "<block_hash>",  # Use block hash as _id
  "height": 0,
  "hash": "<block_hash>",
  "previous_hash": "0000000000000000000000000000000000000000000000000000000000000000",
  "timestamp": "<iso_timestamp>",
  "transactions": [/* genesis transaction(s) */],
  "merkle_root": "<calculated_merkle_root>",
  "producer": "<producer_id>",
  "signature": "<block_signature>",
  "nonce": 0,
  "difficulty": 1.0,
  "version": 1
})
```

### Option 2: Python Script

Create a Python script to generate and insert the genesis block:

```python
# Example structure (not full implementation)
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
import blake3

async def create_genesis_block():
    # 1. Create genesis transaction
    # 2. Calculate merkle root
    # 3. Create block structure
    # 4. Calculate block hash
    # 5. Insert into MongoDB
    pass
```

### Option 3: API Endpoint (If Available)

If a POST endpoint exists for block creation, submit the genesis block via API:

```bash
curl -X POST http://localhost:8084/api/v1/blocks \
  -H "Content-Type: application/json" \
  -d @genesis-block.json
```

---

## Template Structure

### Minimal Genesis Block Template

```json
{
  "height": 0,
  "previous_hash": "0000000000000000000000000000000000000000000000000000000000000000",
  "timestamp": "2025-12-15T06:32:48.000Z",
  "transactions": [
    {
      "id": "genesis_1703123456",
      "from_address": "0x0000000000000000000000000000000000000000",
      "to_address": "0x0000000000000000000000000000000000000000",
      "value": 0,
      "data": {
        "type": "genesis",
        "network": "lucid_blocks",
        "version": "1.0.0",
        "consensus": "PoOT",
        "created_at": "2025-12-15T06:32:48.000Z"
      },
      "timestamp": "2025-12-15T06:32:48.000Z",
      "signature": "<transaction_signature>"
    }
  ],
  "merkle_root": "<calculated_from_transactions>",
  "producer": "<producer_identifier>",
  "signature": "<block_signature>",
  "hash": "<calculated_after_all_fields>",
  "nonce": 0,
  "difficulty": 1.0,
  "version": 1
}
```

### Production-Ready Genesis Block Considerations

For production use, consider:

1. **Cryptographic Signatures**: Use real cryptographic signatures instead of placeholders
2. **Network Configuration**: Use environment variables for network name, version, consensus
3. **Producer Identity**: Use actual validator/producer address or identifier
4. **Custom Data**: Include any custom initialization data needed for your blockchain
5. **Multiple Transactions**: Include multiple genesis transactions if needed (e.g., initial token distribution)

---

## Timing Considerations

### When to Create Genesis Block

1. **Before Engine Start**: Create and import genesis block **before** starting the blockchain engine
2. **Auto-Creation Prevention**: If genesis block exists, engine will skip auto-creation
3. **One-Time Operation**: Genesis block can only be created once per blockchain

### Auto-Creation Behavior

If no genesis block exists when the engine starts:
- Engine will auto-create a default genesis block
- Auto-created block uses hardcoded values (see `block_manager.py`)
- Once auto-created, it cannot be replaced

**Recommendation**: Always create your custom genesis block before first engine start.

---

## Verification

After importing the genesis block, verify:

1. **Database Check**: Query MongoDB to confirm genesis block exists:
   ```bash
   db.blocks.findOne({"height": 0})
   ```

2. **Hash Verification**: Verify block hash matches calculated hash

3. **Merkle Root Verification**: Verify merkle root matches calculated root

4. **Engine Startup**: Start blockchain engine and confirm it loads your genesis block (not auto-creating)

---

## Important Notes

⚠️ **Critical Warnings**:

1. **Immutable**: Once created, genesis block **cannot be modified or deleted**
2. **Unique**: Only one genesis block can exist (height 0 is unique)
3. **Hash Dependency**: Block hash depends on all other fields - calculate last
4. **Timing**: Create genesis block **before** engine startup to prevent auto-creation
5. **Validation**: Ensure all validation rules pass before importing

---

## References

- Block Manager: `blockchain/core/block_manager.py`
- Block Models: `blockchain/api/app/models/block.py`
- Hash Algorithm: Blake3 (see `_calculate_block_hash` method)
- Merkle Root: Blake3 (see `_calculate_merkle_root` method)
- Validation: `validate_block` method in `block_manager.py`

---

## Support

For issues or questions:
1. Check blockchain engine logs for validation errors
2. Verify all hash calculations match system expectations
3. Ensure timestamp is within acceptable range
4. Confirm all required fields are present and correctly formatted

