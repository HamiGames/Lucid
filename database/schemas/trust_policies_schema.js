// Lucid Project - Trust Policies Collection Schema
// Defines the structure and validation rules for trust policies in MongoDB.

// Collection Name: trust_policies
db.createCollection("trust_policies", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["policy_id", "creator_id", "name", "created_at", "status"],
      properties: {
        policy_id: {
          bsonType: "string",
          description: "Unique identifier for the trust policy (UUID format)"
        },
        creator_id: {
          bsonType: "string",
          description: "ID of the user or entity creating the policy"
        },
        name: {
          bsonType: "string",
          description: "Human-readable name of the policy"
        },
        description: {
          bsonType: ["string", "null"],
          description: "Detailed description of the policy"
        },
        created_at: {
          bsonType: "date",
          description: "Policy creation timestamp"
        },
        updated_at: {
          bsonType: ["date", "null"],
          description: "Last update timestamp"
        },
        status: {
          bsonType: "string",
          enum: ["draft", "active", "inactive", "revoked"],
          description: "Current status of the policy"
        },
        version: {
          bsonType: "string",
          description: "Policy version (semantic versioning format)"
        },
        rules: {
          bsonType: "array",
          items: {
            bsonType: "object",
            required: ["rule_type", "condition", "action"],
            properties: {
              rule_type: { bsonType: "string", enum: ["access", "data", "node", "transaction"] },
              condition: { bsonType: "string" },
              action: { bsonType: "string", enum: ["allow", "deny", "require_approval"] },
              parameters: { bsonType: ["object", "null"] }
            }
          },
          description: "List of rules defining the trust policy"
        },
        scope: {
          bsonType: "object",
          properties: {
            applies_to: { bsonType: "array", items: { bsonType: "string" } },
            excluded: { bsonType: "array", items: { bsonType: "string" } }
          },
          description: "Scope of policy application (users, nodes, etc.)"
        },
        signature: {
          bsonType: ["string", "null"],
          description: "Digital signature for policy integrity"
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
  "policy_id": "policy_12345678-1234-5678-1234-567812345678",
  "creator_id": "user_98765432-4321-8765-4321-876543218765",
  "name": "Default Session Access Policy",
  "description": "Standard policy for session data access control",
  "created_at": ISODate("2025-01-01T09:00:00Z"),
  "updated_at": null,
  "status": "active",
  "version": "1.0.0",
  "rules": [
    {
      "rule_type": "access",
      "condition": "user_role == 'User'",
      "action": "allow",
      "parameters": {
        "resource": "session_data",
        "operation": "read"
      }
    },
    {
      "rule_type": "access",
      "condition": "user_role == 'Admin'",
      "action": "allow",
      "parameters": {
        "resource": "session_data",
        "operation": "write"
      }
    }
  ],
  "scope": {
    "applies_to": ["all_users"],
    "excluded": ["suspended_users"]
  },
  "signature": "sig_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}
*/