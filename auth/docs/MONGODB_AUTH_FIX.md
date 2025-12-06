# MongoDB Authentication Fix

## Date: 2025-01-24

## Issue

`lucid-auth-service` is failing with MongoDB authentication error:
```
pymongo.errors.OperationFailure: Authentication failed.
```

## Fix Applied

### 1. Updated `configs/docker/docker-compose.foundation.yml`

Added `environment` section to `lucid-mongodb` service to ensure MongoDB initialization credentials are set:

```yaml
lucid-mongodb:
  # ... existing config ...
  environment:
    # CRITICAL: MongoDB initialization credentials (only used on first run if database is empty)
    - MONGO_INITDB_ROOT_USERNAME=lucid
    - MONGO_INITDB_ROOT_PASSWORD=${MONGODB_PASSWORD}
    - MONGO_INITDB_DATABASE=lucid
```

## Important Notes

**If MongoDB is already initialized:**
- The `MONGO_INITDB_ROOT_PASSWORD` environment variable only works on **first initialization** (when `/data/db` is empty)
- If MongoDB already has data, the password was set during the first initialization
- The password in your `.env.foundation` file MUST match what MongoDB was initialized with

## Verification Steps (Pi Console)

### Step 1: Check MongoDB Logs
```bash
docker logs lucid-mongodb | grep -i "password\|auth\|authentication" | tail -20
```

### Step 2: Verify Environment Variable
```bash
# Check what MONGODB_PASSWORD is set to in the container
docker exec lucid-mongodb env | grep MONGODB_PASSWORD
```

### Step 3: Test MongoDB Connection
```bash
# Test connection with password from .env file
# (Replace PASSWORD with actual value from .env.foundation)
docker exec lucid-mongodb mongosh --quiet -u lucid -p "PASSWORD" --authenticationDatabase admin --eval "db.runCommand({ ping: 1 })"
```

### Step 4: Check Auth Service Connection String
```bash
# Check what MONGODB_URI the auth service is using
docker exec lucid-auth-service env | grep MONGODB_URI
```

## If Authentication Still Fails

### Option 1: Password Mismatch (Most Likely)

The password in `.env.foundation` doesn't match what MongoDB was initialized with.

**Solution**: Update the password in `.env.foundation` to match what MongoDB expects, OR reset MongoDB (if data can be lost):

```bash
# WARNING: This will delete all MongoDB data
docker stop lucid-auth-service lucid-mongodb
docker rm lucid-mongodb
docker volume rm lucid-mongodb-data  # If using named volume
# Then restart - MongoDB will reinitialize with new password
docker compose -f /mnt/myssd/Lucid/Lucid/configs/docker/docker-compose.foundation.yml up -d lucid-mongodb
```

### Option 2: Variable Not Resolving

The `${MONGODB_PASSWORD}` variable isn't being resolved from env files.

**Solution**: Verify env files are being loaded:

```bash
# Check if env files exist
ls -la /mnt/myssd/Lucid/Lucid/configs/environment/.env.foundation
ls -la /mnt/myssd/Lucid/Lucid/configs/environment/.env.secrets

# Check if MONGODB_PASSWORD is in the file
grep MONGODB_PASSWORD /mnt/myssd/Lucid/Lucid/configs/environment/.env.foundation
```

### Option 3: Restart Services

After fixing the password, restart the auth service:

```bash
docker compose -f /mnt/myssd/Lucid/Lucid/configs/docker/docker-compose.foundation.yml restart lucid-auth-service
```

## Current Configuration

**MongoDB Connection String** (in auth service):
```
mongodb://lucid:${MONGODB_PASSWORD}@lucid-mongodb:27017/lucid_auth?authSource=admin
```

**MongoDB Initialization** (in MongoDB service):
- Username: `lucid`
- Password: `${MONGODB_PASSWORD}` (from .env.foundation)
- Database: `lucid`
- Auth Source: `admin`

## Status

✅ **Fix Applied** - MongoDB environment section added  
⚠️ **Verification Required** - Password must match between .env file and MongoDB initialization

