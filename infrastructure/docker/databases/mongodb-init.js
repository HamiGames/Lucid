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
try {
    db = db.getSiblingDB('admin');
    
    // Check if admin user already exists
    var existingUser = db.getUser('lucid');
    if (existingUser) {
        print("ℹ️ Admin user 'lucid' already exists");
    } else {
        db.createUser({
            user: 'lucid',
            pwd: 'lucid',
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
try {
    var existingUser = db.getUser('lucid');
    if (existingUser) {
        print("ℹ️ Database user 'lucid' already exists");
    } else {
        db.createUser({
            user: 'lucid',
            pwd: 'lucid',
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
