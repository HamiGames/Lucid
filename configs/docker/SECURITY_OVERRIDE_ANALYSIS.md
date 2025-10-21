# Docker Compose Security Override Analysis

**Analysis Date:** $(date)  
**Analyzed Files:** All docker-compose files in configs/docker/  
**Severity:** 🔴 **CRITICAL** - Secure values would be completely ignored

---

## 🔴 CRITICAL SECURITY ISSUES FOUND

### Issue #1: Hardcoded Weak Passwords in ALL Docker Compose Files

**Files Affected:** ALL docker-compose files

#### docker-compose.foundation.yml
```yaml
Line 21:  MONGO_URL: ${MONGO_URL:-mongodb://lucid:lucid@...}  # ← "lucid" hardcoded
Line 22:  REDIS_URL: ${REDIS_URL:-redis://:lucid@...}          # ← "lucid" hardcoded  
Line 41:  JWT_SECRET_KEY: ${JWT_SECRET_KEY:-}                  # ← Empty default
Line 42:  ENCRYPTION_KEY: ${ENCRYPTION_KEY:-}                  # ← Empty default
Line 80:  MONGO_INITDB_ROOT_PASSWORD: ${MONGODB_PASSWORD:-lucid}  # ← "lucid" default
Line 121: "--requirepass", "${REDIS_PASSWORD:-lucid}"         # ← "lucid" default
```

#### docker-compose.core.yml
```yaml
Line 28:  MONGODB_URI=mongodb://lucid:lucid@...  # ← HARDCODED "lucid" password
Line 29:  REDIS_URI=redis://lucid-redis:6379/0   # ← NO PASSWORD
Line 73:  MONGODB_URI=mongodb://lucid:lucid@...  # ← HARDCODED "lucid" password
Line 74:  REDIS_URI=redis://lucid-redis:6379/0   # ← NO PASSWORD
```

#### docker-compose.application.yml
```yaml
Line 26:  MONGODB_URI=mongodb://lucid:lucid@...  # ← HARDCODED "lucid" password
Line 27:  REDIS_URI=redis://lucid-redis:6379/0   # ← NO PASSWORD
Line 65:  MONGODB_URI=mongodb://lucid:lucid@...  # ← HARDCODED "lucid" password
Line 105: MONGODB_URI=mongodb://lucid:lucid@...  # ← HARDCODED "lucid" password
```

#### docker-compose.support.yml
```yaml
Line 25:  MONGODB_URI=mongodb://lucid:lucid@...  # ← HARDCODED "lucid" password
Line 26:  REDIS_URI=redis://lucid-redis:6379/0   # ← NO PASSWORD
Line 76:  TRON_NETWORK=${TRON_NETWORK:-shasta}   # ← Defaults to testnet
Line 79:  TRON_PRIVATE_KEY=${TRON_PRIVATE_KEY}   # ← No default (good) but won't fail if missing
```

#### docker-compose.all.yml
```yaml
Line 27:  JWT_SECRET_KEY=${JWT_SECRET_KEY:-lucid_jwt_secret_key_change_in_production}  # ← Weak default!
Line 25:  MONGODB_URI=mongodb://lucid:lucid@...  # ← HARDCODED "lucid" password everywhere
Line 62:  MONGO_INITDB_ROOT_PASSWORD=lucid       # ← HARDCODED "lucid" (no variable!)
```

---

## 🔍 Root Cause Analysis

### Problem 1: Docker Compose Variable Resolution Order

Docker Compose resolves variables in this order:
1. Shell environment variables
2. `--env-file` parameter
3. `.env` file in the same directory as docker-compose.yml
4. **Variables defined IN the docker-compose.yml** ← These override everything!
5. Defaults in `${VAR:-default}` syntax

**Current State:**
- Generated .env files are in `configs/environment/`
- Docker compose files are in `configs/docker/`
- **NO .env file in configs/docker/**, so defaults are used
- Hardcoded values in YAML completely bypass generated secure values

### Problem 2: Hardcoded URIs

Lines like:
```yaml
MONGODB_URI=mongodb://lucid:lucid@lucid-mongodb:27017/...
```

This is a **direct assignment**, not a variable reference. It will ALWAYS use "lucid" as the password, regardless of what's in .env files.

### Problem 3: Missing .env File Reference

The deployment scripts don't use `--env-file` parameter:
```bash
# Current (WRONG):
docker-compose -f configs/docker/docker-compose.foundation.yml up -d

# Should be:
docker-compose --env-file configs/environment/.env.foundation -f configs/docker/docker-compose.foundation.yml up -d
```

---

## ✅ COMPREHENSIVE FIX REQUIRED

### Fix 1: Update ALL Docker Compose Files (REQUIRED)

Change hardcoded values to variable references with error enforcement:

**Before:**
```yaml
MONGODB_URI=mongodb://lucid:lucid@lucid-mongodb:27017/lucid?authSource=admin
REDIS_URI=redis://lucid-redis:6379/0
JWT_SECRET_KEY=${JWT_SECRET_KEY:-}
MONGO_INITDB_ROOT_PASSWORD: ${MONGODB_PASSWORD:-lucid}
```

**After:**
```yaml
MONGODB_URI=mongodb://lucid:${MONGODB_PASSWORD:?ERROR: MONGODB_PASSWORD not set}@lucid-mongodb:27017/lucid?authSource=admin
REDIS_URI=redis://:${REDIS_PASSWORD:?ERROR: REDIS_PASSWORD not set}@lucid-redis:6379/0
JWT_SECRET_KEY=${JWT_SECRET_KEY:?ERROR: JWT_SECRET_KEY not set}
MONGO_INITDB_ROOT_PASSWORD: ${MONGODB_PASSWORD:?ERROR: MONGODB_PASSWORD not set}
```

The `:?ERROR MESSAGE` syntax will:
- ✅ FAIL deployment if variable is not set
- ✅ Prevent weak defaults from being used
- ✅ Force proper .env file loading
- ✅ Show clear error message

### Fix 2: Copy/Symlink .env Files to Compose Directory (OPTIONAL)

```bash
# Create symlinks in configs/docker/
ln -sf ../environment/.env.foundation configs/docker/.env.foundation
ln -sf ../environment/.env.core configs/docker/.env.core
ln -sf ../environment/.env.application configs/docker/.env.application
ln -sf ../environment/.env.support configs/docker/.env.support
```

### Fix 3: Update Deployment Scripts to Use --env-file (REQUIRED)

All deployment scripts must use:
```bash
docker-compose --env-file configs/environment/.env.foundation \
               -f configs/docker/docker-compose.foundation.yml up -d
```

---

## 📋 Files That Need Fixing

### Critical (Must Fix):
1. ✅ `configs/docker/docker-compose.foundation.yml` - 12+ hardcoded values
2. ✅ `configs/docker/docker-compose.core.yml` - 8+ hardcoded values
3. ✅ `configs/docker/docker-compose.application.yml` - 10+ hardcoded values
4. ✅ `configs/docker/docker-compose.support.yml` - 6+ hardcoded values
5. ✅ `configs/docker/docker-compose.all.yml` - 15+ hardcoded values

### Deployment Scripts (Must Update):
1. ✅ `scripts/deployment/deploy-phase1-pi.sh`
2. ✅ `scripts/deployment/deploy-phase2-pi.sh`
3. ✅ `scripts/deployment/deploy-phase3-pi.sh`
4. ✅ `scripts/deployment/deploy-phase4-pi.sh`
5. ✅ `scripts/deployment/deploy-all-systems.sh`

---

## 🎯 What generate-all-env.sh Actually Does

### File Paths Created:
```bash
configs/environment/.env.pi-build         ← Build configuration
configs/environment/.env.foundation       ← Phase 1 with REAL passwords
configs/environment/.env.core             ← Phase 2 with REAL passwords  
configs/environment/.env.application      ← Phase 3 with REAL passwords
configs/environment/.env.support          ← Phase 4 with REAL passwords
configs/environment/.env.gui              ← GUI integration
```

### Values Generated (lines 59-83):
```bash
MONGODB_PASSWORD=$(generate_secure_value 32)      # ← 32 bytes base64
REDIS_PASSWORD=$(generate_secure_value 32)        # ← 32 bytes base64
JWT_SECRET=$(generate_secure_value 64)            # ← 64 bytes base64
ENCRYPTION_KEY=$(generate_secure_value 32)        # ← 32 bytes base64
TOR_PASSWORD=$(generate_secure_value 32)          # ← 32 bytes base64
SESSION_SECRET=$(generate_secure_value 32)        # ← 32 bytes base64
API_SECRET=$(generate_secure_value 32)            # ← 32 bytes base64
```

### Values USED in .env files (lines 135-154):
```bash
# In .env.foundation:
MONGODB_PASSWORD=$MONGODB_PASSWORD                 # ← Actual generated value
MONGODB_URI=$MONGODB_URI                           # ← Uses generated password
REDIS_PASSWORD=$REDIS_PASSWORD                     # ← Actual generated value
JWT_SECRET=$JWT_SECRET                             # ← Actual generated value
ENCRYPTION_KEY=$ENCRYPTION_KEY                     # ← Actual generated value
```

**BUT:** These values are stored in `configs/environment/.env.foundation`, **NOT** loaded by docker-compose files!

---

## ❌ Current Workflow (BROKEN):

1. Run `generate-all-env.sh` → Creates secure values in `configs/environment/.env.*`
2. Run `docker-compose -f docker-compose.foundation.yml up -d`
3. Docker Compose looks for `.env` file in `configs/docker/` directory
4. **DOESN'T FIND IT**
5. Uses hardcoded defaults: `mongodb://lucid:lucid@...`
6. **Generated secure values are COMPLETELY IGNORED**

---

## ✅ Required Fix Workflow:

1. Generate secure values: `generate-all-env-complete.sh`
2. Update docker-compose files to use `${VAR:?ERROR}` syntax
3. Deploy with: `docker-compose --env-file configs/environment/.env.foundation ...`
4. Docker Compose **FAILS** if variables not set
5. **Secure values are ENFORCED**

---

## 🚨 SECURITY IMPACT

**Current Risk Level:** 🔴 **CRITICAL**

If deployed as-is:
- ❌ MongoDB password: `"lucid"` (weak, publicly known)
- ❌ Redis password: `"lucid"` or NO PASSWORD
- ❌ JWT secret: `""` (empty) or weak default
- ❌ Encryption key: `""` (empty)
- ❌ All generated secure values: IGNORED

**This would make the entire system completely insecure!**

---

## ✅ RECOMMENDED ACTION

**I will now fix ALL docker-compose files to:**
1. Replace ALL hardcoded passwords with `${VAR:?ERROR}` syntax
2. Ensure NO weak defaults exist
3. Force proper .env file loading
4. Add validation that fails deployment if secrets missing

**Proceed with fixes?**

