// Lucid Project - Transactions Collection Schema
// Defines the structure and validation rules for blockchain transactions in MongoDB.

// Collection Name: transactions
db.createCollection("transactions", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["tx_id", "tx_type", "sender", "timestamp", "status"],
      properties: {
        tx_id: {
          bsonType: "string",
          description: "Unique transaction identifier (hash or UUID)"
        },
        tx_type: {
          bsonType: "string",
          enum: ["session_anchor", "node_registration", "payout_request", "consensus_vote", "trust_policy"],
          description: "Type of transaction"
        },
        sender: {
          bsonType: "string",
          description: "ID of the entity initiating the transaction (user or node ID)"
        },
        timestamp: {
          bsonType: "date",
          description: "Transaction creation timestamp"
        },
        status: {
          bsonType: "string",
          enum: ["pending", "confirmed", "rejected", "failed"],
          description: "Current status of the transaction"
        },
        block_height: {
          bsonType: ["long", "null"],
          description: "Block height where transaction is included (null if pending)"
        },
        block_hash: {
          bsonType: ["string", "null"],
          description: "Hash of the block containing this transaction (null if pending)"
        },
        payload: {
          bsonType: "object",
          description: "Transaction-specific data payload",
          properties: {
            session_id: { bsonType: ["string", "null"] },
            merkle_root: { bsonType: ["string", "null"] },
            node_id: { bsonType: ["string", "null"] },
            payout_amount: { bsonType: ["double", "null"] },
            vote_type: { bsonType: ["string", "null"] }
          }
        },
        signature: {
          bsonType: "string",
          description: "Digital signature of the transaction"
        },
        fee: {
          bsonType: ["double", "null"],
          description: "Transaction fee (if applicable)"
        },
        confirmations: {
          bsonType: "int",
          minimum: 0,
          description: "Number of confirmations received"
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
  "tx_id": "tx_11111111111111111111111111111111",
  "tx_type": "session_anchor",
  "sender": "user_12345678-1234-5678-1234-567812345678",
  "timestamp": ISODate("2025-01-01T11:30:00Z"),
  "status": "confirmed",
  "block_height": 100,
  "block_hash": "hash_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "payload": {
    "session_id": "session_98765432-4321-8765-4321-876543218765",
    "merkle_root": "merkle_zzzzzzzzzzzzzzzzzzzzzzzzzzzzzz"
  },
  "signature": "sig_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "fee": 0.001,
  "confirmations": 6
}
*/