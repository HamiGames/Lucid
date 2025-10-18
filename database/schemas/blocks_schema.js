// Lucid Project - Blocks Collection Schema
// Defines the structure and validation rules for blockchain blocks in MongoDB.

// Collection Name: blocks
db.createCollection("blocks", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["block_height", "block_hash", "previous_hash", "timestamp", "transactions"],
      properties: {
        block_height: {
          bsonType: "long",
          minimum: 0,
          description: "Block height in the chain (starting from 0 for genesis)"
        },
        block_hash: {
          bsonType: "string",
          description: "Unique hash of the block (SHA-256)"
        },
        previous_hash: {
          bsonType: "string",
          description: "Hash of the previous block (SHA-256)"
        },
        timestamp: {
          bsonType: "date",
          description: "Block creation timestamp"
        },
        transactions: {
          bsonType: "array",
          items: {
            bsonType: "string",
            description: "Array of transaction IDs included in this block"
          },
          description: "List of transaction IDs in the block"
        },
        merkle_root: {
          bsonType: "string",
          description: "Merkle root of transactions in the block"
        },
        miner_id: {
          bsonType: ["string", "null"],
          description: "ID of the node that mined this block"
        },
        difficulty: {
          bsonType: "double",
          description: "Mining difficulty at the time of block creation"
        },
        nonce: {
          bsonType: "long",
          description: "Nonce value used in Proof of Work"
        },
        size: {
          bsonType: "long",
          description: "Size of the block in bytes"
        },
        version: {
          bsonType: "string",
          description: "Block format version"
        },
        extra_data: {
          bsonType: ["object", "null"],
          description: "Additional block metadata or custom data"
        }
      }
    }
  },
  validationLevel: "strict",
  validationAction: "error"
});

// Example document
/*
{
  "block_height": 100,
  "block_hash": "hash_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "previous_hash": "hash_yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy",
  "timestamp": ISODate("2025-01-01T12:00:00Z"),
  "transactions": [
    "tx_11111111111111111111111111111111",
    "tx_22222222222222222222222222222222"
  ],
  "merkle_root": "merkle_zzzzzzzzzzzzzzzzzzzzzzzzzzzzzz",
  "miner_id": "node_12345678-1234-5678-1234-567812345678",
  "difficulty": 4.5,
  "nonce": 123456789,
  "size": 1024,
  "version": "1.0.0",
  "extra_data": {
    "note": "Lucid blockchain block"
  }
}
*/