-- Blockchain Migration Scripts
-- Database schema migration, data migration, and index creation
-- For Lucid blockchain rebuild with On-System Chain and PoOT consensus

-- ============================================================================
-- DATABASE INITIALIZATION
-- ============================================================================

-- Create Lucid database
USE lucid;

-- ============================================================================
-- SESSIONS COLLECTION SCHEMA
-- ============================================================================

-- Drop existing sessions collection if exists
db.sessions.drop();

-- Create sessions collection with proper schema
db.createCollection("sessions", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["_id", "owner_addr", "started_at", "manifest_hash", "merkle_root", "chunk_count", "status"],
            properties: {
                _id: {
                    bsonType: "string",
                    description: "Session UUID must be a string"
                },
                owner_addr: {
                    bsonType: "string",
                    pattern: "^0x[a-fA-F0-9]{40}$",
                    description: "Owner address must be a valid Ethereum address"
                },
                started_at: {
                    bsonType: "date",
                    description: "Session start time must be a date"
                },
                ended_at: {
                    bsonType: ["date", "null"],
                    description: "Session end time must be a date or null"
                },
                manifest_hash: {
                    bsonType: "string",
                    pattern: "^0x[a-fA-F0-9]{64}$",
                    description: "Manifest hash must be a valid SHA256 hash"
                },
                merkle_root: {
                    bsonType: "string",
                    pattern: "^0x[a-fA-F0-9]{64}$",
                    description: "Merkle root must be a valid SHA256 hash"
                },
                chunk_count: {
                    bsonType: "int",
                    minimum: 0,
                    description: "Chunk count must be a non-negative integer"
                },
                anchor_txid: {
                    bsonType: ["string", "null"],
                    description: "On-System Chain transaction ID"
                },
                block_number: {
                    bsonType: ["int", "null"],
                    minimum: 0,
                    description: "Block number must be a non-negative integer"
                },
                gas_used: {
                    bsonType: ["int", "null"],
                    minimum: 0,
                    description: "Gas used must be a non-negative integer"
                },
                status: {
                    bsonType: "string",
                    enum: ["pending", "active", "completed", "failed", "cancelled"],
                    description: "Session status must be one of the allowed values"
                }
            }
        }
    }
});

-- Create sessions collection indexes
db.sessions.createIndex({ "owner_addr": 1, "started_at": 1 }, { name: "owner_time_idx" });
db.sessions.createIndex({ "status": 1 }, { name: "status_idx" });
db.sessions.createIndex({ "anchor_txid": 1 }, { name: "anchor_txid_idx", sparse: true });
db.sessions.createIndex({ "block_number": 1 }, { name: "block_number_idx", sparse: true });
db.sessions.createIndex({ "manifest_hash": 1 }, { name: "manifest_hash_idx" });

-- ============================================================================
-- CHUNKS COLLECTION SCHEMA (SHARDED)
-- ============================================================================

-- Drop existing chunks collection if exists
db.chunks.drop();

-- Create chunks collection with proper schema
db.createCollection("chunks", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["_id", "session_id", "idx", "local_path", "ciphertext_sha256", "size_bytes"],
            properties: {
                _id: {
                    bsonType: "string",
                    description: "Chunk ID must be a string"
                },
                session_id: {
                    bsonType: "string",
                    description: "Session ID must be a string"
                },
                idx: {
                    bsonType: "int",
                    minimum: 0,
                    description: "Chunk index must be a non-negative integer"
                },
                local_path: {
                    bsonType: "string",
                    description: "Local file path must be a string"
                },
                ciphertext_sha256: {
                    bsonType: "string",
                    pattern: "^0x[a-fA-F0-9]{64}$",
                    description: "Ciphertext hash must be a valid SHA256 hash"
                },
                size_bytes: {
                    bsonType: "int",
                    minimum: 0,
                    description: "Size in bytes must be a non-negative integer"
                }
            }
        }
    }
});

-- Create chunks collection indexes (shard key)
db.chunks.createIndex({ "session_id": 1, "idx": 1 }, { name: "session_idx_idx", unique: true });
db.chunks.createIndex({ "ciphertext_sha256": 1 }, { name: "ciphertext_hash_idx" });
db.chunks.createIndex({ "size_bytes": 1 }, { name: "size_bytes_idx" });

-- ============================================================================
-- PAYOUTS COLLECTION SCHEMA (TRON PAYMENTS ONLY)
-- ============================================================================

-- Drop existing payouts collection if exists
db.payouts.drop();

-- Create payouts collection with proper schema
db.createCollection("payouts", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["_id", "session_id", "to_addr", "usdt_amount", "router", "reason", "status", "created_at"],
            properties: {
                _id: {
                    bsonType: "string",
                    description: "Payout ID must be a string"
                },
                session_id: {
                    bsonType: "string",
                    description: "Session ID must be a string"
                },
                to_addr: {
                    bsonType: "string",
                    pattern: "^T[a-zA-Z0-9]{33}$",
                    description: "TRON address must be a valid TRON address"
                },
                usdt_amount: {
                    bsonType: "double",
                    minimum: 0,
                    description: "USDT amount must be a non-negative number"
                },
                router: {
                    bsonType: "string",
                    enum: ["PayoutRouterV0", "PayoutRouterKYC"],
                    description: "Router must be one of the allowed values"
                },
                reason: {
                    bsonType: "string",
                    description: "Payout reason must be a string"
                },
                txid: {
                    bsonType: ["string", "null"],
                    description: "TRON transaction ID"
                },
                status: {
                    bsonType: "string",
                    enum: ["pending", "processing", "success", "failed", "cancelled"],
                    description: "Payout status must be one of the allowed values"
                },
                created_at: {
                    bsonType: "date",
                    description: "Creation time must be a date"
                },
                kyc_hash: {
                    bsonType: ["string", "null"],
                    description: "KYC hash for KYC-gated payouts"
                },
                compliance_sig: {
                    bsonType: ["object", "null"],
                    description: "Compliance signature for KYC-gated payouts"
                }
            }
        }
    }
});

-- Create payouts collection indexes
db.payouts.createIndex({ "session_id": 1 }, { name: "session_id_idx" });
db.payouts.createIndex({ "to_addr": 1 }, { name: "to_addr_idx" });
db.payouts.createIndex({ "router": 1 }, { name: "router_idx" });
db.payouts.createIndex({ "status": 1 }, { name: "payout_status_idx" });
db.payouts.createIndex({ "created_at": 1 }, { name: "created_at_idx" });
db.payouts.createIndex({ "txid": 1 }, { name: "txid_idx", sparse: true });

-- ============================================================================
-- CONSENSUS COLLECTIONS
-- ============================================================================

-- TASK_PROOFS COLLECTION (SHARDED)
db.task_proofs.drop();

db.createCollection("task_proofs", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["_id", "nodeId", "slot", "type", "value", "sig", "ts"],
            properties: {
                _id: {
                    bsonType: "string",
                    description: "Task proof ID must be a string"
                },
                nodeId: {
                    bsonType: "string",
                    description: "Node ID must be a string"
                },
                poolId: {
                    bsonType: ["string", "null"],
                    description: "Pool ID must be a string or null"
                },
                slot: {
                    bsonType: "int",
                    minimum: 0,
                    description: "Slot number must be a non-negative integer"
                },
                type: {
                    bsonType: "string",
                    enum: ["relay_bandwidth", "storage_availability", "validation_signature", "uptime_beacon"],
                    description: "Task type must be one of the allowed values"
                },
                value: {
                    bsonType: "object",
                    description: "Task proof value must be an object"
                },
                sig: {
                    bsonType: "string",
                    description: "Signature must be a string"
                },
                ts: {
                    bsonType: "date",
                    description: "Timestamp must be a date"
                }
            }
        }
    }
});

-- Create task_proofs indexes (shard key)
db.task_proofs.createIndex({ "slot": 1, "nodeId": 1 }, { name: "slot_node_idx" });
db.task_proofs.createIndex({ "nodeId": 1, "ts": 1 }, { name: "node_time_idx" });
db.task_proofs.createIndex({ "type": 1 }, { name: "type_idx" });

-- WORK_TALLY COLLECTION (REPLICATED)
db.work_tally.drop();

db.createCollection("work_tally", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["_id", "epoch", "entityId", "credits", "liveScore", "rank"],
            properties: {
                _id: {
                    bsonType: "string",
                    description: "Work tally ID must be a string"
                },
                epoch: {
                    bsonType: "int",
                    minimum: 0,
                    description: "Epoch number must be a non-negative integer"
                },
                entityId: {
                    bsonType: "string",
                    description: "Entity ID must be a string"
                },
                credits: {
                    bsonType: "double",
                    minimum: 0,
                    description: "Work credits must be a non-negative number"
                },
                liveScore: {
                    bsonType: "double",
                    minimum: 0,
                    maximum: 1,
                    description: "Live score must be between 0 and 1"
                },
                rank: {
                    bsonType: "int",
                    minimum: 1,
                    description: "Rank must be a positive integer"
                }
            }
        }
    }
});

-- Create work_tally indexes
db.work_tally.createIndex({ "epoch": 1, "rank": 1 }, { name: "epoch_rank_idx" });
db.work_tally.createIndex({ "entityId": 1, "epoch": 1 }, { name: "entity_epoch_idx" });
db.work_tally.createIndex({ "credits": -1 }, { name: "credits_desc_idx" });

-- LEADER_SCHEDULE COLLECTION (REPLICATED)
db.leader_schedule.drop();

db.createCollection("leader_schedule", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["_id", "slot", "primary", "fallbacks", "result"],
            properties: {
                _id: {
                    bsonType: "int",
                    description: "Slot number must be an integer"
                },
                slot: {
                    bsonType: "int",
                    minimum: 0,
                    description: "Slot number must be a non-negative integer"
                },
                primary: {
                    bsonType: ["string", "null"],
                    description: "Primary leader must be a string or null"
                },
                fallbacks: {
                    bsonType: "array",
                    items: {
                        bsonType: "string"
                    },
                    description: "Fallback leaders must be an array of strings"
                },
                result: {
                    bsonType: "object",
                    required: ["winner", "reason"],
                    properties: {
                        winner: {
                            bsonType: ["string", "null"],
                            description: "Winner must be a string or null"
                        },
                        reason: {
                            bsonType: "string",
                            description: "Selection reason must be a string"
                        }
                    }
                }
            }
        }
    }
});

-- Create leader_schedule indexes
db.leader_schedule.createIndex({ "slot": 1 }, { name: "slot_idx", unique: true });
db.leader_schedule.createIndex({ "primary": 1 }, { name: "primary_idx", sparse: true });

-- ============================================================================
-- SHARDING CONFIGURATION
-- ============================================================================

-- Enable sharding on lucid database
sh.enableSharding("lucid");

-- Shard chunks collection on session_id and idx
sh.shardCollection("lucid.chunks", { "session_id": 1, "idx": 1 });

-- Shard task_proofs collection on slot and nodeId
sh.shardCollection("lucid.task_proofs", { "slot": 1, "nodeId": 1 });

-- ============================================================================
-- DATA MIGRATION (if migrating from existing data)
-- ============================================================================

-- Migrate existing sessions data (if any)
-- db.sessions_old.find().forEach(function(doc) {
--     db.sessions.insertOne({
--         _id: doc._id,
--         owner_addr: doc.owner_address || doc.owner_addr,
--         started_at: doc.started_at || doc.start_time,
--         ended_at: doc.ended_at || doc.end_time,
--         manifest_hash: doc.manifest_hash,
--         merkle_root: doc.merkle_root,
--         chunk_count: doc.chunk_count || 0,
--         anchor_txid: doc.anchor_txid || doc.txid,
--         block_number: doc.block_number,
--         gas_used: doc.gas_used,
--         status: doc.status || "active"
--     });
-- });

-- Migrate existing chunks data (if any)
-- db.chunks_old.find().forEach(function(doc) {
--     db.chunks.insertOne({
--         _id: doc._id,
--         session_id: doc.session_id,
--         idx: doc.idx || doc.index,
--         local_path: doc.local_path || doc.path,
--         ciphertext_sha256: doc.ciphertext_sha256 || doc.hash,
--         size_bytes: doc.size_bytes || doc.size
--     });
-- });

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Verify collections were created
db.getCollectionNames();

-- Verify indexes were created
db.sessions.getIndexes();
db.chunks.getIndexes();
db.payouts.getIndexes();
db.task_proofs.getIndexes();
db.work_tally.getIndexes();
db.leader_schedule.getIndexes();

-- Verify sharding configuration
sh.status();

-- Verify data consistency
db.sessions.countDocuments();
db.chunks.countDocuments();
db.payouts.countDocuments();
db.task_proofs.countDocuments();
db.work_tally.countDocuments();
db.leader_schedule.countDocuments();

-- ============================================================================
-- CLEANUP (if needed)
-- ============================================================================

-- Uncomment to drop old collections after migration
-- db.sessions_old.drop();
-- db.chunks_old.drop();
-- db.payouts_old.drop();

print("Blockchain migration completed successfully!");
