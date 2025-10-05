// MongoDB Schema Initialization
// LUCID-STRICT Layer 1 Core Infrastructure
// Generated: 2025-10-04

// Initialize database and collections
db = db.getSiblingDB('lucid');

// Enable sharding for scalability
try {
    sh.enableSharding("lucid");
    print("Sharding enabled for lucid database");
} catch (e) {
    print("Sharding already enabled or not available: " + e.message);
}

// Create sessions collection with validation schema
db.createCollection("sessions", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["_id", "owner_address", "started_at", "status", "chunks"],
            properties: {
                _id: {
                    bsonType: "string",
                    description: "Unique session identifier"
                },
                owner_address: {
                    bsonType: "string",
                    pattern: "^T[A-Za-z0-9]{33}$",
                    description: "TRON wallet address of session owner"
                },
                started_at: {
                    bsonType: "date",
                    description: "Session start timestamp"
                },
                completed_at: {
                    bsonType: "date",
                    description: "Session completion timestamp"
                },
                status: {
                    enum: ["pending", "processing", "active", "completed", "failed", "cancelled"],
                    description: "Current session status"
                },
                chunks: {
                    bsonType: "array",
                    items: {
                        bsonType: "object",
                        required: ["chunk_id", "index", "size_bytes", "compressed_size_bytes", "hash_blake3"],
                        properties: {
                            chunk_id: { bsonType: "string" },
                            index: { bsonType: "int" },
                            size_bytes: { bsonType: "int", minimum: 0 },
                            compressed_size_bytes: { bsonType: "int", minimum: 0 },
                            hash_blake3: { bsonType: "string", pattern: "^[a-fA-F0-9]{64}$" },
                            encryption_nonce: { bsonType: "string" },
                            encryption_key_id: { bsonType: "string" }
                        }
                    }
                },
                merkle_root: {
                    bsonType: "string",
                    pattern: "^[a-fA-F0-9]{64}$",
                    description: "BLAKE3 Merkle root of session"
                },
                anchor_txid: {
                    bsonType: "string",
                    pattern: "^[a-fA-F0-9]{64}$",
                    description: "Blockchain transaction ID for anchoring"
                },
                metadata: {
                    bsonType: "object",
                    properties: {
                        original_size: { bsonType: "long" },
                        compressed_size: { bsonType: "long" },
                        compression_ratio: { bsonType: "double", minimum: 0 },
                        encryption_time_ms: { bsonType: "int", minimum: 0 },
                        merkle_build_time_ms: { bsonType: "int", minimum: 0 }
                    }
                }
            }
        }
    }
});

// Create authentication collection with validation schema
db.createCollection("authentication", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["_id", "tron_address", "role", "created_at", "last_login"],
            properties: {
                _id: {
                    bsonType: "string",
                    description: "User identifier (TRON address)"
                },
                tron_address: {
                    bsonType: "string",
                    pattern: "^T[A-Za-z0-9]{33}$",
                    description: "TRON wallet address"
                },
                role: {
                    enum: ["user", "node_operator", "admin", "observer"],
                    description: "User role in the system"
                },
                permissions: {
                    bsonType: "array",
                    items: {
                        bsonType: "string",
                        enum: ["session_create", "session_join", "session_observe", 
                               "session_manage", "admin_access", "payout_manage",
                               "node_manage", "policy_manage"]
                    }
                },
                created_at: {
                    bsonType: "date",
                    description: "Account creation timestamp"
                },
                last_login: {
                    bsonType: "date",
                    description: "Last login timestamp"
                },
                login_count: {
                    bsonType: "int",
                    minimum: 0,
                    description: "Total login count"
                },
                hardware_wallet: {
                    bsonType: "object",
                    properties: {
                        enabled: { bsonType: "bool" },
                        device_type: { bsonType: "string" },
                        device_id: { bsonType: "string" },
                        last_verified: { bsonType: "date" }
                    }
                },
                session_tokens: {
                    bsonType: "array",
                    items: {
                        bsonType: "object",
                        required: ["token_id", "issued_at", "expires_at"],
                        properties: {
                            token_id: { bsonType: "string" },
                            issued_at: { bsonType: "date" },
                            expires_at: { bsonType: "date" },
                            device_info: { bsonType: "object" }
                        }
                    }
                },
                failed_attempts: {
                    bsonType: "int",
                    minimum: 0,
                    description: "Failed login attempts"
                },
                locked_until: {
                    bsonType: "date",
                    description: "Account lockout expiration"
                }
            }
        }
    }
});

// Create work_proofs collection for PoOT consensus
db.createCollection("work_proofs", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["_id", "node_id", "slot", "proof_type", "proof_data", "signature", "timestamp"],
            properties: {
                _id: {
                    bsonType: "string",
                    description: "Composite ID: node_id_slot_type"
                },
                node_id: {
                    bsonType: "string",
                    description: "Node identifier"
                },
                slot: {
                    bsonType: "int",
                    minimum: 0,
                    description: "Consensus slot number"
                },
                proof_type: {
                    enum: ["relay_bandwidth", "storage_availability", "validation_signature", "uptime_beacon"],
                    description: "Type of work proof"
                },
                proof_data: {
                    bsonType: "object",
                    description: "Proof-specific data"
                },
                signature: {
                    bsonType: "string",
                    pattern: "^[a-fA-F0-9]+$",
                    description: "Cryptographic signature"
                },
                timestamp: {
                    bsonType: "date",
                    description: "Proof submission timestamp"
                },
                reward_amount: {
                    bsonType: "decimal",
                    minimum: 0,
                    description: "Calculated reward amount"
                },
                verified: {
                    bsonType: "bool",
                    description: "Proof verification status"
                }
            }
        }
    }
});

// Create encryption_keys collection for key management
db.createCollection("encryption_keys", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["_id", "session_id", "key_id", "algorithm", "created_at"],
            properties: {
                _id: {
                    bsonType: "string",
                    description: "Unique key identifier"
                },
                session_id: {
                    bsonType: "string",
                    description: "Associated session ID"
                },
                key_id: {
                    bsonType: "string",
                    description: "Encryption key identifier"
                },
                algorithm: {
                    bsonType: "string",
                    description: "Encryption algorithm used"
                },
                key_data: {
                    bsonType: "string",
                    description: "Encrypted key data"
                },
                created_at: {
                    bsonType: "date",
                    description: "Key creation timestamp"
                },
                expires_at: {
                    bsonType: "date",
                    description: "Key expiration timestamp"
                },
                rotation_count: {
                    bsonType: "int",
                    minimum: 0,
                    description: "Number of times this key has been rotated"
                }
            }
        }
    }
});

// Create indexes for performance optimization
print("Creating indexes...");

// Sessions collection indexes
db.sessions.createIndex({ "owner_address": 1, "started_at": -1 });
db.sessions.createIndex({ "status": 1 });
db.sessions.createIndex({ "created_at": -1 });
db.sessions.createIndex({ "anchor_txid": 1 }, { sparse: true });
db.sessions.createIndex({ "merkle_root": 1 }, { sparse: true });

// Authentication collection indexes
db.authentication.createIndex({ "tron_address": 1 }, { unique: true });
db.authentication.createIndex({ "role": 1 });
db.authentication.createIndex({ "last_login": -1 });
db.authentication.createIndex({ "locked_until": 1 }, { sparse: true });

// Work proofs collection indexes
db.work_proofs.createIndex({ "node_id": 1, "slot": -1 });
db.work_proofs.createIndex({ "proof_type": 1, "timestamp": -1 });
db.work_proofs.createIndex({ "verified": 1, "timestamp": -1 });
db.work_proofs.createIndex({ "node_id": 1, "proof_type": 1, "slot": -1 });

// Encryption keys collection indexes
db.encryption_keys.createIndex({ "session_id": 1 });
db.encryption_keys.createIndex({ "key_id": 1 });
db.encryption_keys.createIndex({ "expires_at": 1 }, { expireAfterSeconds: 0 });

// Create compound indexes for complex queries
db.sessions.createIndex({ "owner_address": 1, "status": 1, "started_at": -1 });
db.work_proofs.createIndex({ "node_id": 1, "slot": 1, "proof_type": 1 }, { unique: true });

// Create text indexes for search functionality
db.sessions.createIndex({ "owner_address": "text" });
db.authentication.createIndex({ "tron_address": "text" });

print("MongoDB schema initialization completed successfully!");

// Display collection information
print("\nCollection Information:");
print("======================");
db.getCollectionNames().forEach(function(name) {
    var stats = db[name].stats();
    print(name + ": " + stats.count + " documents, " + stats.size + " bytes");
});

// Display index information
print("\nIndex Information:");
print("==================");
db.getCollectionNames().forEach(function(name) {
    print("\n" + name + " indexes:");
    db[name].getIndexes().forEach(function(index) {
        print("  " + index.name + ": " + JSON.stringify(index.key));
    });
});