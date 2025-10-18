// MongoDB initialization script for RDP services
// This script creates the necessary collections and indexes for RDP services

// Switch to the lucid_rdp database
db = db.getSiblingDB('lucid_rdp');

// Create collections
db.createCollection('rdp_sessions');
db.createCollection('rdp_connections');
db.createCollection('rdp_servers');
db.createCollection('rdp_metrics');
db.createCollection('rdp_alerts');

// Create indexes for rdp_sessions collection
db.rdp_sessions.createIndex({ "session_id": 1 }, { unique: true });
db.rdp_sessions.createIndex({ "user_id": 1 });
db.rdp_sessions.createIndex({ "server_id": 1 });
db.rdp_sessions.createIndex({ "status": 1 });
db.rdp_sessions.createIndex({ "created_at": 1 });
db.rdp_sessions.createIndex({ "last_activity": 1 });
db.rdp_sessions.createIndex({ "user_id": 1, "status": 1 });

// Create indexes for rdp_connections collection
db.rdp_connections.createIndex({ "connection_id": 1 }, { unique: true });
db.rdp_connections.createIndex({ "session_id": 1 });
db.rdp_connections.createIndex({ "server_id": 1 });
db.rdp_connections.createIndex({ "status": 1 });
db.rdp_connections.createIndex({ "created_at": 1 });

// Create indexes for rdp_servers collection
db.rdp_servers.createIndex({ "server_id": 1 }, { unique: true });
db.rdp_servers.createIndex({ "name": 1 });
db.rdp_servers.createIndex({ "host": 1 });
db.rdp_servers.createIndex({ "status": 1 });
db.rdp_servers.createIndex({ "created_at": 1 });

// Create indexes for rdp_metrics collection
db.rdp_metrics.createIndex({ "session_id": 1 });
db.rdp_metrics.createIndex({ "timestamp": 1 });
db.rdp_metrics.createIndex({ "session_id": 1, "timestamp": 1 });
db.rdp_metrics.createIndex({ "timestamp": 1 }, { expireAfterSeconds: 86400 }); // TTL: 24 hours

// Create indexes for rdp_alerts collection
db.rdp_alerts.createIndex({ "alert_id": 1 }, { unique: true });
db.rdp_alerts.createIndex({ "session_id": 1 });
db.rdp_alerts.createIndex({ "alert_type": 1 });
db.rdp_alerts.createIndex({ "severity": 1 });
db.rdp_alerts.createIndex({ "created_at": 1 });
db.rdp_alerts.createIndex({ "resolved_at": 1 });
db.rdp_alerts.createIndex({ "session_id": 1, "resolved_at": 1 });

// Create compound indexes for better query performance
db.rdp_sessions.createIndex({ "user_id": 1, "created_at": -1 });
db.rdp_sessions.createIndex({ "status": 1, "last_activity": 1 });
db.rdp_connections.createIndex({ "session_id": 1, "status": 1 });
db.rdp_metrics.createIndex({ "session_id": 1, "timestamp": -1 });

// Insert initial configuration documents
db.rdp_servers.insertOne({
    "server_id": ObjectId(),
    "name": "default-rdp-server",
    "host": "localhost",
    "port": 3389,
    "status": "active",
    "created_at": new Date(),
    "config": {
        "max_sessions": 100,
        "session_timeout": 3600,
        "idle_timeout": 1800
    },
    "metadata": {
        "description": "Default RDP server configuration",
        "version": "1.0.0"
    }
});

print("RDP database initialization completed successfully");
