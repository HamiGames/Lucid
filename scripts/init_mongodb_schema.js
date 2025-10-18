// MongoDB Schema Initialization for Lucid RDP Session Pipeline
// Based on LUCID-STRICT Layer 1 Core Infrastructure requirements
// Generated: 2025-10-05

// Connect to Lucid database
db = db.getSiblingDB('lucid');

print("🚀 Initializing Lucid RDP MongoDB Schema...");

// Drop existing collections for clean initialization
print("🧹 Cleaning existing collections...");
db.sessions.drop();
db.chunks.drop(); 
db.encrypted_chunks.drop();
db.session_metadata.drop();
db.authentication.drop();
db.work_proofs.drop();
db.merkle_proofs.drop();

// ========================================
// SESSION PIPELINE COLLECTIONS
// ========================================

print("📋 Creating sessions collection...");
// Main sessions collection with validation schema
db.createCollection("sessions", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["_id", "owner_address", "node_id", "pipeline_state", "created_at"],
      properties: {
        _id: {
          bsonType: "string",
          description: "Session ID - must be a string"
        },
        owner_address: {
          bsonType: "string",
          pattern: "^T[A-Za-z0-9]{33}$",
          description: "TRON address - must match TRON format"
        },
        node_id: {
          bsonType: "string",
          description: "Node ID hosting this session"
        },
        pipeline_state: {
          bsonType: "string",
          enum: ["initialized", "chunking", "encrypting", "merkle_building", "anchoring", "completed", "failed"],
          description: "Current pipeline processing state"
        },
        created_at: {
          bsonType: "date",
          description: "Session creation timestamp"
        },
        updated_at: {
          bsonType: "date",
          description: "Last update timestamp"
        },
        total_chunks: {
          bsonType: "int",
          minimum: 0,
          description: "Total number of chunks processed"
        },
        total_bytes: {
          bsonType: "long",
          minimum: 0,
          description: "Total bytes processed in session"
        },
        merkle_root: {
          bsonType: ["string", "null"],
          description: "BLAKE3 merkle root hash (64 hex chars)"
        },
        anchor_txid: {
          bsonType: ["string", "null"],
          description: "Blockchain anchor transaction ID"
        },
        error_message: {
          bsonType: ["string", "null"],
          description: "Error message if session failed"
        }
      }
    }
  }
});

print("🧩 Creating chunks collection...");
// Compressed chunks metadata
db.createCollection("chunks", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["_id", "session_id", "sequence_number", "original_size", "compressed_size", "chunk_hash"],
      properties: {
        _id: {
          bsonType: "string",
          description: "Chunk ID"
        },
        session_id: {
          bsonType: "string",
          description: "Parent session ID"
        },
        sequence_number: {
          bsonType: "int",
          minimum: 0,
          description: "Chunk sequence number in session"
        },
        original_size: {
          bsonType: "int",
          minimum: 1,
          description: "Original uncompressed size in bytes"
        },
        compressed_size: {
          bsonType: "int", 
          minimum: 1,
          description: "Compressed size in bytes"
        },
        compression_ratio: {
          bsonType: ["double", "null"],
          description: "Compression ratio (compressed/original)"
        },
        chunk_hash: {
          bsonType: "string",
          description: "BLAKE3 hash of original chunk data"
        },
        created_at: {
          bsonType: "date",
          description: "Chunk creation timestamp"
        }
      }
    }
  }
});

print("🔐 Creating encrypted_chunks collection...");
// Encrypted chunks metadata
db.createCollection("encrypted_chunks", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["_id", "session_id", "sequence_number", "encrypted_size", "nonce", "ciphertext_sha256"],
      properties: {
        _id: {
          bsonType: "string",
          description: "Encrypted chunk ID"
        },
        session_id: {
          bsonType: "string",
          description: "Parent session ID"
        },
        sequence_number: {
          bsonType: "int",
          minimum: 0,
          description: "Chunk sequence number"
        },
        original_size: {
          bsonType: "int",
          minimum: 1,
          description: "Original uncompressed size"
        },
        compressed_size: {
          bsonType: "int",
          minimum: 1, 
          description: "Compressed size before encryption"
        },
        encrypted_size: {
          bsonType: "int",
          minimum: 1,
          description: "Final encrypted size"
        },
        nonce: {
          bsonType: "string",
          description: "XChaCha20-Poly1305 nonce (hex)"
        },
        ciphertext_sha256: {
          bsonType: "string",
          description: "SHA256 hash of ciphertext for integrity"
        },
        local_path: {
          bsonType: "string",
          description: "Local storage path for encrypted chunk"
        },
        created_at: {
          bsonType: "date",
          description: "Encryption timestamp"
        }
      }
    }
  }
});

print("🆔 Creating session_metadata collection...");
// Session generator metadata
db.createCollection("session_metadata", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["_id", "type", "created_at", "expires_at", "status"],
      properties: {
        _id: {
          bsonType: "string",
          description: "Session ID"
        },
        type: {
          bsonType: "string",
          enum: ["rdp_user", "rdp_admin", "api_user", "api_admin", "api_node", "blockchain", "temp_upload"],
          description: "Session type"
        },
        owner_address: {
          bsonType: ["string", "null"],
          pattern: "^T[A-Za-z0-9]{33}$",
          description: "TRON address of owner"
        },
        node_id: {
          bsonType: ["string", "null"],
          description: "Node ID for node sessions"
        },
        public_key: {
          bsonType: "string",
          description: "Ephemeral Ed25519 public key (hex)"
        },
        created_at: {
          bsonType: "date",
          description: "Session creation time"
        },
        expires_at: {
          bsonType: "date",
          description: "Session expiration time"
        },
        single_use: {
          bsonType: "bool",
          description: "Whether session is single-use"
        },
        replayable: {
          bsonType: "bool", 
          description: "Whether session is replayable"
        },
        status: {
          bsonType: "string",
          enum: ["active", "expired", "used", "revoked"],
          description: "Session status"
        }
      }
    }
  }
});

// ========================================
// AUTHENTICATION COLLECTIONS
// ========================================

print("🔐 Creating authentication collection...");
// User authentication data
db.createCollection("authentication", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["_id", "role", "last_login"],
      properties: {
        _id: {
          bsonType: "string",
          pattern: "^T[A-Za-z0-9]{33}$",
          description: "TRON address as user ID"
        },
        role: {
          bsonType: "string",
          enum: ["user", "node_operator", "admin", "observer"],
          description: "User role for RBAC"
        },
        permissions: {
          bsonType: "array",
          items: {
            bsonType: "string"
          },
          description: "List of user permissions"
        },
        last_login: {
          bsonType: "date",
          description: "Last successful login timestamp"
        },
        login_count: {
          bsonType: "int",
          minimum: 0,
          description: "Total login count"
        },
        session_tokens: {
          bsonType: "array",
          items: {
            bsonType: "object",
            properties: {
              jwt_token_hash: {
                bsonType: "string",
                description: "SHA256 hash of JWT token"
              },
              issued_at: {
                bsonType: "date"
              },
              expires_at: {
                bsonType: "date"
              },
              device_info: {
                bsonType: ["string", "null"],
                description: "Device information"
              }
            }
          },
          description: "Active session tokens"
        },
        hardware_wallet: {
          bsonType: "object",
          properties: {
            enabled: {
              bsonType: "bool",
              description: "Hardware wallet verification enabled"
            },
            wallet_type: {
              bsonType: ["string", "null"],
              enum: ["ledger", "trezor", "keepkey", null],
              description: "Hardware wallet type"
            },
            device_id: {
              bsonType: ["string", "null"],
              description: "Hardware device identifier"
            },
            last_verified: {
              bsonType: ["date", "null"],
              description: "Last hardware verification timestamp"
            }
          },
          description: "Hardware wallet configuration"
        },
        created_at: {
          bsonType: "date",
          description: "Account creation timestamp"
        },
        updated_at: {
          bsonType: "date",
          description: "Last update timestamp"
        }
      }
    }
  }
});

// ========================================
// PROOF-OF-ONGOING-TASKS (PoOT) COLLECTIONS
// ========================================

print("⛓️ Creating work_proofs collection...");
// Work proofs for PoOT consensus
db.createCollection("work_proofs", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["_id", "node_id", "slot", "proof_type", "signature", "timestamp"],
      properties: {
        _id: {
          bsonType: "string",
          description: "Composite ID: node_id_slot_type"
        },
        node_id: {
          bsonType: "string",
          description: "Node identifier submitting proof"
        },
        slot: {
          bsonType: "int",
          minimum: 0,
          description: "Consensus slot number"
        },
        proof_type: {
          bsonType: "string",
          enum: ["relay_bandwidth", "storage_availability", "validation_signature", "uptime_beacon"],
          description: "Type of work proof"
        },
        proof_data: {
          bsonType: "object",
          description: "Proof-specific data (varies by type)"
        },
        signature: {
          bsonType: "string",
          description: "Ed25519 signature of proof data"
        },
        public_key: {
          bsonType: "string",
          description: "Node's public key for verification"
        },
        timestamp: {
          bsonType: "date",
          description: "Proof submission timestamp"
        },
        verified: {
          bsonType: "bool",
          description: "Whether proof has been verified"
        },
        verification_result: {
          bsonType: ["object", "null"],
          description: "Verification result details"
        }
      }
    }
  }
});

// ========================================
// MERKLE PROOF COLLECTIONS
// ========================================

print("🌳 Creating merkle_proofs collection...");
// Merkle proofs for chunk verification
db.createCollection("merkle_proofs", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["_id", "session_id", "chunk_id", "root_hash", "proof_hashes", "positions"],
      properties: {
        _id: {
          bsonType: "string",
          description: "Proof ID: session_id_chunk_index"
        },
        session_id: {
          bsonType: "string",
          description: "Session containing the chunk"
        },
        chunk_id: {
          bsonType: "string",
          description: "Chunk being proven"
        },
        chunk_index: {
          bsonType: "int",
          minimum: 0,
          description: "Chunk index in session"
        },
        chunk_hash: {
          bsonType: "string",
          description: "Hash of the chunk being proven"
        },
        root_hash: {
          bsonType: "string",
          description: "Merkle root hash"
        },
        proof_hashes: {
          bsonType: "array",
          items: {
            bsonType: "string"
          },
          description: "Sibling hashes for proof path"
        },
        positions: {
          bsonType: "array",
          items: {
            bsonType: "bool"
          },
          description: "Position indicators (true=right, false=left)"
        },
        created_at: {
          bsonType: "date",
          description: "Proof generation timestamp"
        },
        verified: {
          bsonType: "bool",
          description: "Whether proof has been verified"
        }
      }
    }
  }
});

// ========================================
// CREATE INDEXES FOR PERFORMANCE
// ========================================

print("⚡ Creating performance indexes...");

// Sessions collection indexes
db.sessions.createIndex({ "owner_address": 1 });
db.sessions.createIndex({ "node_id": 1 });
db.sessions.createIndex({ "pipeline_state": 1 });
db.sessions.createIndex({ "created_at": -1 });
db.sessions.createIndex({ "updated_at": -1 });

// Chunks collection indexes  
db.chunks.createIndex({ "session_id": 1, "sequence_number": 1 });
db.chunks.createIndex({ "created_at": -1 });
db.chunks.createIndex({ "chunk_hash": 1 });

// Encrypted chunks collection indexes
db.encrypted_chunks.createIndex({ "session_id": 1, "sequence_number": 1 });
db.encrypted_chunks.createIndex({ "created_at": -1 });
db.encrypted_chunks.createIndex({ "ciphertext_sha256": 1 });

// Session metadata indexes
db.session_metadata.createIndex({ "owner_address": 1 });
db.session_metadata.createIndex({ "node_id": 1 });
db.session_metadata.createIndex({ "type": 1 });
db.session_metadata.createIndex({ "status": 1 });
db.session_metadata.createIndex({ "expires_at": 1 });
db.session_metadata.createIndex({ "created_at": -1 });

// Authentication collection indexes
db.authentication.createIndex({ "role": 1 });
db.authentication.createIndex({ "last_login": -1 });
db.authentication.createIndex({ "session_tokens.expires_at": 1 });
db.authentication.createIndex({ "hardware_wallet.enabled": 1 });

// Work proofs collection indexes (for PoOT consensus)
db.work_proofs.createIndex({ "node_id": 1, "slot": -1 });
db.work_proofs.createIndex({ "proof_type": 1, "timestamp": -1 });
db.work_proofs.createIndex({ "slot": 1 });
db.work_proofs.createIndex({ "verified": 1 });

// Merkle proofs collection indexes
db.merkle_proofs.createIndex({ "session_id": 1, "chunk_index": 1 });
db.merkle_proofs.createIndex({ "chunk_id": 1 });
db.merkle_proofs.createIndex({ "verified": 1 });

// ========================================
// SHARDING CONFIGURATION (for scale)
// ========================================

print("🚀 Configuring sharding...");

// Enable sharding on the lucid database
try {
  sh.enableSharding("lucid");
  print("✅ Sharding enabled on lucid database");
} catch (e) {
  print("⚠️ Sharding not available or already configured: " + e.message);
}

// Shard sessions collection on session_id (even distribution)
try {
  sh.shardCollection("lucid.sessions", { "_id": 1 });
  print("✅ Sharded sessions collection");
} catch (e) {
  print("⚠️ Sessions sharding not available: " + e.message);
}

// Shard chunks collection on session_id (co-locate with sessions)
try {
  sh.shardCollection("lucid.chunks", { "session_id": 1, "sequence_number": 1 });
  print("✅ Sharded chunks collection");
} catch (e) {
  print("⚠️ Chunks sharding not available: " + e.message);
}

// Shard encrypted chunks similarly
try {
  sh.shardCollection("lucid.encrypted_chunks", { "session_id": 1, "sequence_number": 1 });
  print("✅ Sharded encrypted_chunks collection");
} catch (e) {
  print("⚠️ Encrypted chunks sharding not available: " + e.message);
}

// Shard work proofs on node_id for PoOT consensus
try {
  sh.shardCollection("lucid.work_proofs", { "node_id": 1, "slot": 1 });
  print("✅ Sharded work_proofs collection");
} catch (e) {
  print("⚠️ Work proofs sharding not available: " + e.message);
}

// ========================================
// SEED INITIAL DATA
// ========================================

print("🌱 Seeding initial configuration data...");

// Create admin user
db.authentication.insertOne({
  _id: "TLucidAdminAddress123456789012345678",
  role: "admin",
  permissions: [
    "session_create", "session_join", "session_observe", "session_manage",
    "node_manage", "user_manage", "system_admin", "payout_manage"
  ],
  last_login: new Date(),
  login_count: 0,
  session_tokens: [],
  hardware_wallet: {
    enabled: false,
    wallet_type: null,
    device_id: null,
    last_verified: null
  },
  created_at: new Date(),
  updated_at: new Date()
});

// Create default node operator
db.authentication.insertOne({
  _id: "TLucidNodeOperator123456789012345",
  role: "node_operator", 
  permissions: [
    "session_create", "session_join", "session_host",
    "node_manage", "payout_receive"
  ],
  last_login: new Date(),
  login_count: 0,
  session_tokens: [],
  hardware_wallet: {
    enabled: false,
    wallet_type: null,
    device_id: null,
    last_verified: null
  },
  created_at: new Date(),
  updated_at: new Date()
});

// Create test user
db.authentication.insertOne({
  _id: "TLucidTestUser12345678901234567890",
  role: "user",
  permissions: [
    "session_create", "session_join", "session_observe"
  ],
  last_login: new Date(),
  login_count: 0,
  session_tokens: [],
  hardware_wallet: {
    enabled: false,
    wallet_type: null,
    device_id: null,
    last_verified: null
  },
  created_at: new Date(),
  updated_at: new Date()
});

// ========================================
// VALIDATION AND SUMMARY
// ========================================

print("✅ Validating schema creation...");

// Count collections
const collections = db.runCommand("listCollections").cursor.firstBatch;
print("📊 Created collections:");
collections.forEach(function(collection) {
  const count = db.getCollection(collection.name).countDocuments();
  print(`   ${collection.name}: ${count} documents`);
});

// Validate indexes
print("🔍 Validating indexes:");
["sessions", "chunks", "encrypted_chunks", "session_metadata", "authentication", "work_proofs", "merkle_proofs"].forEach(function(collName) {
  const indexes = db.getCollection(collName).getIndexes();
  print(`   ${collName}: ${indexes.length} indexes`);
});

print("🎉 MongoDB schema initialization completed successfully!");
print("");
print("📋 Summary:");
print("   ✅ 7 collections created with validation schemas");
print("   ✅ Performance indexes created");
print("   ✅ Sharding configured (if available)");
print("   ✅ Initial users seeded");
print("   ✅ Schema ready for Lucid RDP Layer 1 Core Infrastructure");
print("");
print("🚀 Ready for session pipeline operations!");