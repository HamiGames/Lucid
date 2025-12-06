// MongoDB Initialization Script for Lucid Database Services
// LUCID-STRICT Layer 0 Core Infrastructure
// Creates replica set and initializes authentication

print("🚀 Starting Lucid MongoDB Initialization...");

// Wait for MongoDB to be ready
var maxAttempts = 30;
var attempt = 0;

while (attempt < maxAttempts) {
    try {
        db.runCommand({ ping: 1 });
        print("✅ MongoDB is ready for initialization");
        break;
    } catch (e) {
        attempt++;
        if (attempt >= maxAttempts) {
            print("❌ MongoDB initialization timeout");
            quit(1);
        }
        print("⏳ Waiting for MongoDB... (" + attempt + "/" + maxAttempts + ")");
        sleep(2000);
    }
}

// Initialize replica set if not already initialized
try {
    var config = {
        _id: "rs0",
        members: [
            { _id: 0, host: "localhost:27017" }
        ]
    };
    
    var result = rs.initiate(config);
    print("✅ Replica set initialized: " + JSON.stringify(result));
    
    // Wait for replica set to be ready
    var rsStatus = rs.status();
    while (rsStatus.members[0].state !== 1) {
        print("⏳ Waiting for replica set to be primary...");
        sleep(1000);
        rsStatus = rs.status();
    }
    print("✅ Replica set is ready");
    
} catch (e) {
    if (e.message.includes("already initialized")) {
        print("ℹ️ Replica set already initialized");
    } else {
        print("❌ Replica set initialization failed: " + e.message);
        quit(1);
    }
}

// Create admin user
// CRITICAL: Password should be passed via environment variable MONGODB_PASSWORD
// If not provided, this script will use a default (NOT RECOMMENDED FOR PRODUCTION)
// Usage: mongosh --eval "var MONGODB_PASSWORD='your-password'; load('mongodb-init.js')"
// Or: MONGO_INITDB_ROOT_PASSWORD environment variable (if using standard MongoDB entrypoint)
try {
    db = db.getSiblingDB('admin');
    
    // Get password from environment variable or use default
    // Note: MongoDB JavaScript can't directly access process.env, so password must be passed
    // via mongosh execution: mongosh --eval "var MONGODB_PASSWORD='password'; load('script.js')"
    // Or use MONGO_INITDB_ROOT_PASSWORD if running via standard MongoDB entrypoint
    var mongoPassword = typeof MONGODB_PASSWORD !== 'undefined' ? MONGODB_PASSWORD : 
                       (typeof MONGO_INITDB_ROOT_PASSWORD !== 'undefined' ? MONGO_INITDB_ROOT_PASSWORD : null);
    
    // If no password provided, this is an error in production
    if (!mongoPassword) {
        print("❌ ERROR: MONGODB_PASSWORD or MONGO_INITDB_ROOT_PASSWORD must be provided");
        print("💡 This script should be executed with password: mongosh --eval \"var MONGODB_PASSWORD='password'; load('mongodb-init.js')\"");
        quit(1);
    }
    
    // Check if admin user already exists
    var existingUser = db.getUser('lucid');
    if (existingUser) {
        print("ℹ️ Admin user 'lucid' already exists");
        // Update password if user exists but password might be wrong
        try {
            db.changeUserPassword('lucid', mongoPassword);
            print("✅ Admin user 'lucid' password updated");
        } catch (updateError) {
            print("⚠️ Could not update password (may require authentication): " + updateError.message);
        }
    } else {
        db.createUser({
            user: 'lucid',
            pwd: mongoPassword,
            roles: [
                { role: 'userAdminAnyDatabase', db: 'admin' },
                { role: 'readWriteAnyDatabase', db: 'admin' },
                { role: 'dbAdminAnyDatabase', db: 'admin' },
                { role: 'clusterAdmin', db: 'admin' }
            ]
        });
        print("✅ Admin user 'lucid' created successfully");
    }
} catch (e) {
    print("❌ Admin user creation failed: " + e.message);
    quit(1);
}

// Switch to lucid database
db = db.getSiblingDB('lucid');

// Create lucid database user
// Uses the same password as admin user (from MONGODB_PASSWORD or MONGO_INITDB_ROOT_PASSWORD)
try {
    // Reuse password variable from above
    if (!mongoPassword) {
        print("❌ ERROR: Password not available for database user creation");
        quit(1);
    }
    
    var existingUser = db.getUser('lucid');
    if (existingUser) {
        print("ℹ️ Database user 'lucid' already exists");
        // Update password if user exists
        try {
            db.changeUserPassword('lucid', mongoPassword);
            print("✅ Database user 'lucid' password updated");
        } catch (updateError) {
            print("⚠️ Could not update password (may require authentication): " + updateError.message);
        }
    } else {
        db.createUser({
            user: 'lucid',
            pwd: mongoPassword,
            roles: [
                { role: 'readWrite', db: 'lucid' },
                { role: 'dbAdmin', db: 'lucid' }
            ]
        });
        print("✅ Database user 'lucid' created successfully");
    }
} catch (e) {
    print("❌ Database user creation failed: " + e.message);
    quit(1);
}

print("🎉 MongoDB initialization completed successfully!");
