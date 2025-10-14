// Lucid Project - Users Collection Schema
// Defines the structure and validation rules for user data in MongoDB.

// Collection Name: users
db.createCollection("users", {
    validator: {
      $jsonSchema: {
        bsonType: "object",
        required: ["user_id", "email", "created_at", "updated_at", "status"],
        properties: {
          user_id: {
            bsonType: "string",
            description: "Unique identifier for the user (UUID format)"
          },
          email: {
            bsonType: "string",
            pattern: "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
            description: "User's email address"
          },
          username: {
            bsonType: ["string", "null"],
            description: "Optional username or alias"
          },
          password_hash: {
            bsonType: ["string", "null"],
            description: "Hashed password (if not using hardware wallet)"
          },
          tron_address: {
            bsonType: ["string", "null"],
            description: "User's TRON wallet address for authentication"
          },
          hardware_wallet: {
            bsonType: ["object", "null"],
            properties: {
              type: { bsonType: "string", enum: ["Ledger", "Trezor", "KeepKey"] },
              public_key: { bsonType: "string" }
            },
            description: "Hardware wallet details if used for authentication"
          },
          roles: {
            bsonType: "array",
            items: {
              bsonType: "string",
              enum: ["User", "NodeOperator", "Admin", "SuperAdmin"]
            },
            description: "User's roles for RBAC"
          },
          status: {
            bsonType: "string",
            enum: ["active", "inactive", "suspended", "pending_verification"],
            description: "Account status"
          },
          created_at: {
            bsonType: "date",
            description: "Account creation timestamp"
          },
          updated_at: {
            bsonType: "date",
            description: "Last update timestamp"
          },
          last_login: {
            bsonType: ["date", "null"],
            description: "Last successful login timestamp"
          },
          preferences: {
            bsonType: "object",
            description: "User preferences and settings"
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
    "user_id": "uuid-12345678-1234-5678-1234-567812345678",
    "email": "user@example.com",
    "username": "luciduser",
    "tron_address": "Txxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "roles": ["User"],
    "status": "active",
    "created_at": ISODate("2025-01-01T00:00:00Z"),
    "updated_at": ISODate("2025-01-01T00:00:00Z"),
    "last_login": ISODate("2025-01-01T00:00:00Z"),
    "preferences": {
      "theme": "dark",
      "notifications": true
    }
  }
  */