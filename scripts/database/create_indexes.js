// Lucid Project - Database Index Creation Script
// Creates necessary indexes for performance optimization across collections.

// Users Collection Indexes
print("Creating indexes for 'users' collection...");
db.users.createIndex({ "user_id": 1 }, { unique: true });
db.users.createIndex({ "email": 1 }, { unique: true });
db.users.createIndex({ "tron_address": 1 }, { unique: true, sparse: true });
db.users.createIndex({ "roles": 1 });
db.users.createIndex({ "status": 1 });
db.users.createIndex({ "created_at": -1 });
print("Users indexes created.");

// Sessions Collection Indexes
print("Creating indexes for 'sessions' collection...");
db.sessions.createIndex({ "session_id": 1 }, { unique: true });
db.sessions.createIndex({ "user_id": 1 });
db.sessions.createIndex({ "status": 1 });
db.sessions.createIndex({ "created_at": -1 });
db.sessions.createIndex({ "ended_at": -1 }, { sparse: true });
db.sessions.createIndex({ "merkle_root": 1 }, { unique: true, sparse: true });
db.sessions.createIndex({ "blockchain_anchor.block_height": 1 }, { sparse: true });
print("Sessions indexes created.");

// Blocks Collection Indexes
print("Creating indexes for 'blocks' collection...");
db.blocks.createIndex({ "block_height": 1 }, { unique: true });
db.blocks.createIndex({ "block_hash": 1 }, { unique: true });
db.blocks.createIndex({ "previous_hash": 1 });
db.blocks.createIndex({ "timestamp": -1 });
db.blocks.createIndex({ "miner_id": 1 }, { sparse: true });
print("Blocks indexes created.");

// Transactions Collection Indexes
print("Creating indexes for 'transactions' collection...");
db.transactions.createIndex({ "tx_id": 1 }, { unique: true });
db.transactions.createIndex({ "tx_type": 1 });
db.transactions.createIndex({ "sender": 1 });
db.transactions.createIndex({ "status": 1 });
db.transactions.createIndex({ "timestamp": -1 });
db.transactions.createIndex({ "block_height": 1 }, { sparse: true });
db.transactions.createIndex({ "payload.session_id": 1 }, { sparse: true });
print("Transactions indexes created.");

// Trust Policies Collection Indexes
print("Creating indexes for 'trust_policies' collection...");
db.trust_policies.createIndex({ "policy_id": 1 }, { unique: true });
db.trust_policies.createIndex({ "creator_id": 1 });
db.trust_policies.createIndex({ "status": 1 });
db.trust_policies.createIndex({ "created_at": -1 });
print("Trust Policies indexes created.");

// Additional indexes can be added here as needed for other collections.
// Ensure indexes align with query patterns for optimal performance.

print("All indexes created successfully.");