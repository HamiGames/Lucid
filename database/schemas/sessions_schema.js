// Lucid Project - Sessions Collection Schema
// Defines the structure and validation rules for session data in MongoDB.

// Collection Name: sessions
db.createCollection("sessions", {
    validator: {
      $jsonSchema: {
        bsonType: "object",
        required: ["session_id", "user_id", "created_at", "status"],
        properties: {
          session_id: {
            bsonType: "string",
            description: "Unique identifier for the session (UUID format)"
          },
          user_id: {
            bsonType: "string",
            description: "Associated user ID (references users.user_id)"
          },
          created_at: {
            bsonType: "date",
            description: "Session creation timestamp"
          },
          updated_at: {
            bsonType: ["date", "null"],
            description: "Last update timestamp"
          },
          ended_at: {
            bsonType: ["date", "null"],
            description: "Session end timestamp"
          },
          status: {
            bsonType: "string",
            enum: ["active", "paused", "completed", "terminated", "error"],
            description: "Current status of the session"
          },
          duration: {
            bsonType: ["long", "null"],
            description: "Session duration in seconds"
          },
          chunk_count: {
            bsonType: "int",
            minimum: 0,
            description: "Number of data chunks in the session"
          },
          total_size: {
            bsonType: ["long", "null"],
            description: "Total size of session data in bytes"
          },
          merkle_root: {
            bsonType: ["string", "null"],
            description: "Merkle root hash of session chunks"
          },
          blockchain_anchor: {
            bsonType: ["object", "null"],
            properties: {
              block_height: { bsonType: "long" },
              block_hash: { bsonType: "string" },
              timestamp: { bsonType: "date" }
            },
            description: "Blockchain anchoring details"
          },
          rdp_details: {
            bsonType: ["object", "null"],
            properties: {
              server_ip: { bsonType: "string" },
              port: { bsonType: "int" },
              connection_id: { bsonType: "string" }
            },
            description: "RDP server connection details"
          },
          metadata: {
            bsonType: "object",
            description: "Additional session metadata"
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
    "session_id": "uuid-12345678-1234-5678-1234-567812345678",
    "user_id": "uuid-87654321-4321-8765-4321-876543218765",
    "created_at": ISODate("2025-01-01T10:00:00Z"),
    "updated_at": ISODate("2025-01-01T10:30:00Z"),
    "ended_at": null,
    "status": "active",
    "duration": 1800,
    "chunk_count": 10,
    "total_size": 104857600,
    "merkle_root": "hash_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "blockchain_anchor": null,
    "rdp_details": {
      "server_ip": "172.20.0.100",
      "port": 13389,
      "connection_id": "conn-12345"
    },
    "metadata": {
      "client_version": "1.0.0",
      "os": "Windows 10"
    }
  }
  */