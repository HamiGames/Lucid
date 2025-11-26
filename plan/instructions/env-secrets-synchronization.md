# Environment Secrets Synchronization Guide

This document describes the process to consolidate and synchronize all secret values across all `.env.*` files in the Lucid project. This ensures consistency and prevents configuration errors when services reference different secret values.

## Problem Statement

When secrets (passwords, keys, tokens) are defined inconsistently across multiple `.env.*` files, services may fail to authenticate or operate correctly. This guide consolidates all secrets into a single source of truth (`.env.secrets`) and synchronizes all other environment files to use the same values.

## Prerequisites

- Access to `/mnt/myssd/Lucid/Lucid/configs/environment/` directory
- All `.env.*` files exist (or will be created)
- `openssl` available for generating new secrets if needed

## Step 1: Identify Existing Secret Values

First, search for all secret-related variables across all `.env.*` files to see what values exist:

```bash
grep -h "^MONGODB_PASSWORD=\|^REDIS_PASSWORD=\|^JWT_SECRET_KEY=\|^JWT_SECRET=\|^ENCRYPTION_KEY=\|^TOR_CONTROL_PASSWORD=\|^TOR_PASSWORD=\|^ELASTICSEARCH_PASSWORD=\|^SESSION_SECRET=\|^API_GATEWAY_SECRET=" /mnt/myssd/Lucid/Lucid/configs/environment/.env.* 2>/dev/null | sort -u
```

This will show you:
- Which secrets exist
- Which files contain them
- Any inconsistencies (multiple different values for the same secret)

## Step 2: Create or Update .env.secrets File

The `.env.secrets` file serves as the single source of truth for all secrets. Create or update it with all required secrets:

```bash
# Generate any missing secrets first
MONGODB_PW=$(openssl rand -base64 32 | tr -d '\n')
ELASTICSEARCH_PW=$(openssl rand -base64 32 | tr -d '\n')
ENCRYPTION_KEY_VAL=$(openssl rand -hex 32)
TOR_PW=$(openssl rand -base64 32 | tr -d '\n')
SESSION_SECRET_VAL=$(openssl rand -base64 32 | tr -d '\n')
API_GATEWAY_SECRET_VAL=$(openssl rand -base64 32 | tr -d '\n')

# Create the complete .env.secrets file
cat > /mnt/myssd/Lucid/Lucid/configs/environment/.env.secrets << EOF
# =============================================================================
# LUCID PROJECT - SECRETS CONFIGURATION
# =============================================================================
# WARNING: This file contains sensitive credentials
# NEVER commit this file to version control
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# =============================================================================

# Database Passwords
MONGODB_PASSWORD=$MONGODB_PW
REDIS_PASSWORD=bHPJH0vKjNIiKZeYfxffqVpn0bP55SX+2Xy+Vxv1dJg=
ELASTICSEARCH_PASSWORD=$ELASTICSEARCH_PW

# JWT Secrets
JWT_SECRET_KEY=w+p9+dr7IeOhTRlj6f9R7UqH1q9bCeZii2h4ZjgTBUo=

# Encryption Keys
ENCRYPTION_KEY=$ENCRYPTION_KEY_VAL

# Tor Control Authentication
TOR_CONTROL_PASSWORD=$TOR_PW
TOR_PASSWORD=$TOR_PW

# Additional Security Keys
SESSION_SECRET=$SESSION_SECRET_VAL
API_GATEWAY_SECRET=$API_GATEWAY_SECRET_VAL
EOF
```

**Note:** Replace the example values above with your actual existing secrets, or use the generated values if creating new secrets.

## Step 3: Extract Values from .env.secrets

Extract all secret values from the consolidated `.env.secrets` file into shell variables:

```bash
MONGODB_PW=$(grep "^MONGODB_PASSWORD=" /mnt/myssd/Lucid/Lucid/configs/environment/.env.secrets | cut -d= -f2-)
REDIS_PW=$(grep "^REDIS_PASSWORD=" /mnt/myssd/Lucid/Lucid/configs/environment/.env.secrets | cut -d= -f2-)
JWT_SECRET=$(grep "^JWT_SECRET_KEY=" /mnt/myssd/Lucid/Lucid/configs/environment/.env.secrets | cut -d= -f2-)
ENCRYPTION_KEY_VAL=$(grep "^ENCRYPTION_KEY=" /mnt/myssd/Lucid/Lucid/configs/environment/.env.secrets | cut -d= -f2-)
ELASTICSEARCH_PW=$(grep "^ELASTICSEARCH_PASSWORD=" /mnt/myssd/Lucid/Lucid/configs/environment/.env.secrets | cut -d= -f2-)
TOR_PW=$(grep "^TOR_PASSWORD=" /mnt/myssd/Lucid/Lucid/configs/environment/.env.secrets | cut -d= -f2-)
SESSION_SECRET_VAL=$(grep "^SESSION_SECRET=" /mnt/myssd/Lucid/Lucid/configs/environment/.env.secrets | cut -d= -f2-)
API_GATEWAY_SECRET_VAL=$(grep "^API_GATEWAY_SECRET=" /mnt/myssd/Lucid/Lucid/configs/environment/.env.secrets | cut -d= -f2-)
```

## Step 4: Synchronize All .env.* Files

Update all `.env.*` files (except `.env.secrets` itself) to use the values from `.env.secrets`:

```bash
for envfile in /mnt/myssd/Lucid/Lucid/configs/environment/.env.*; do
  [ "$envfile" = "/mnt/myssd/Lucid/Lucid/configs/environment/.env.secrets" ] && continue
  
  [ -f "$envfile" ] && grep -q "^MONGODB_PASSWORD=" "$envfile" && sed -i "s~^MONGODB_PASSWORD=.*$~MONGODB_PASSWORD=$MONGODB_PW~" "$envfile"
  [ -f "$envfile" ] && grep -q "^REDIS_PASSWORD=" "$envfile" && sed -i "s~^REDIS_PASSWORD=.*$~REDIS_PASSWORD=$REDIS_PW~" "$envfile"
  [ -f "$envfile" ] && grep -q "^JWT_SECRET_KEY=" "$envfile" && sed -i "s~^JWT_SECRET_KEY=.*$~JWT_SECRET_KEY=$JWT_SECRET~" "$envfile"
  [ -f "$envfile" ] && grep -q "^JWT_SECRET=" "$envfile" && sed -i "s~^JWT_SECRET=.*$~JWT_SECRET=$JWT_SECRET~" "$envfile"
  [ -f "$envfile" ] && grep -q "^ENCRYPTION_KEY=" "$envfile" && sed -i "s~^ENCRYPTION_KEY=.*$~ENCRYPTION_KEY=$ENCRYPTION_KEY_VAL~" "$envfile"
  [ -f "$envfile" ] && grep -q "^ELASTICSEARCH_PASSWORD=" "$envfile" && sed -i "s~^ELASTICSEARCH_PASSWORD=.*$~ELASTICSEARCH_PASSWORD=$ELASTICSEARCH_PW~" "$envfile"
  [ -f "$envfile" ] && grep -q "^TOR_PASSWORD=" "$envfile" && sed -i "s~^TOR_PASSWORD=.*$~TOR_PASSWORD=$TOR_PW~" "$envfile"
  [ -f "$envfile" ] && grep -q "^TOR_CONTROL_PASSWORD=" "$envfile" && sed -i "s~^TOR_CONTROL_PASSWORD=.*$~TOR_CONTROL_PASSWORD=$TOR_PW~" "$envfile"
  [ -f "$envfile" ] && grep -q "^SESSION_SECRET=" "$envfile" && sed -i "s~^SESSION_SECRET=.*$~SESSION_SECRET=$SESSION_SECRET_VAL~" "$envfile"
  [ -f "$envfile" ] && grep -q "^API_GATEWAY_SECRET=" "$envfile" && sed -i "s~^API_GATEWAY_SECRET=.*$~API_GATEWAY_SECRET=$API_GATEWAY_SECRET_VAL~" "$envfile"
done
```

**What this does:**
- Iterates through all `.env.*` files in the environment directory
- Skips `.env.secrets` (the source of truth)
- For each file, if it contains a secret variable, updates it to match the value from `.env.secrets`
- Only updates files that already contain the variable (doesn't add new variables)

## Step 5: Verify Synchronization

Verify that all `.env.*` files now have the same secret values:

```bash
# Check MONGODB_PASSWORD
grep "^MONGODB_PASSWORD=" /mnt/myssd/Lucid/Lucid/configs/environment/.env.* 2>/dev/null | sort -u

# Check REDIS_PASSWORD
grep "^REDIS_PASSWORD=" /mnt/myssd/Lucid/Lucid/configs/environment/.env.* 2>/dev/null | sort -u

# Check JWT_SECRET_KEY
grep "^JWT_SECRET_KEY=" /mnt/myssd/Lucid/Lucid/configs/environment/.env.* 2>/dev/null | sort -u

# Check ENCRYPTION_KEY
grep "^ENCRYPTION_KEY=" /mnt/myssd/Lucid/Lucid/configs/environment/.env.* 2>/dev/null | sort -u

# Check ELASTICSEARCH_PASSWORD
grep "^ELASTICSEARCH_PASSWORD=" /mnt/myssd/Lucid/Lucid/configs/environment/.env.* 2>/dev/null | sort -u

# Check TOR_PASSWORD
grep "^TOR_PASSWORD=" /mnt/myssd/Lucid/Lucid/configs/environment/.env.* 2>/dev/null | sort -u

# Check SESSION_SECRET
grep "^SESSION_SECRET=" /mnt/myssd/Lucid/Lucid/configs/environment/.env.* 2>/dev/null | sort -u

# Check API_GATEWAY_SECRET
grep "^API_GATEWAY_SECRET=" /mnt/myssd/Lucid/Lucid/configs/environment/.env.* 2>/dev/null | sort -u
```

**Expected Result:** Each command should return only **one unique line** (all files have the same value). If you see multiple different values, some files weren't updated correctly.

## Step 6: Quick Verification Summary

Run a single command to check all secrets at once:

```bash
echo "=== MONGODB_PASSWORD ===" && grep "^MONGODB_PASSWORD=" /mnt/myssd/Lucid/Lucid/configs/environment/.env.* 2>/dev/null | sort -u && \
echo "=== REDIS_PASSWORD ===" && grep "^REDIS_PASSWORD=" /mnt/myssd/Lucid/Lucid/configs/environment/.env.* 2>/dev/null | sort -u && \
echo "=== JWT_SECRET_KEY ===" && grep "^JWT_SECRET_KEY=" /mnt/myssd/Lucid/Lucid/configs/environment/.env.* 2>/dev/null | sort -u && \
echo "=== ENCRYPTION_KEY ===" && grep "^ENCRYPTION_KEY=" /mnt/myssd/Lucid/Lucid/configs/environment/.env.* 2>/dev/null | sort -u
```

## Troubleshooting

### Multiple Different Values Still Appear

If verification shows multiple different values:

1. **Check if .env.secrets has the correct value:**
   ```bash
   grep "^MONGODB_PASSWORD=" /mnt/myssd/Lucid/Lucid/configs/environment/.env.secrets
   ```

2. **Re-run Step 3 and Step 4** to ensure variables were extracted correctly and files were updated.

3. **Check for files with special characters** that might break sed:
   ```bash
   grep -l "MONGODB_PASSWORD" /mnt/myssd/Lucid/Lucid/configs/environment/.env.* | xargs ls -la
   ```

### Files Not Being Updated

If some files aren't being updated:

1. **Check file permissions:**
   ```bash
   ls -la /mnt/myssd/Lucid/Lucid/configs/environment/.env.*
   ```

2. **Verify the file contains the variable:**
   ```bash
   grep "^MONGODB_PASSWORD=" /mnt/myssd/Lucid/Lucid/configs/environment/.env.foundation
   ```

3. **Manually update if needed:**
   ```bash
   sed -i "s~^MONGODB_PASSWORD=.*$~MONGODB_PASSWORD=$MONGODB_PW~" /mnt/myssd/Lucid/Lucid/configs/environment/.env.foundation
   ```

## Important Notes

1. **Full Paths Required:** All commands use full absolute paths (`/mnt/myssd/Lucid/Lucid/...`) to avoid "getcwd" errors when the external drive has I/O issues.

2. **Source of Truth:** `.env.secrets` is the single source of truth. Always update `.env.secrets` first, then synchronize other files.

3. **Backup First:** Before running synchronization, consider backing up your environment files:
   ```bash
   cp -r /mnt/myssd/Lucid/Lucid/configs/environment /mnt/myssd/Lucid/Lucid/configs/environment.backup.$(date +%Y%m%d_%H%M%S)
   ```

4. **Security:** Never commit `.env.secrets` or any `.env.*` files containing actual secrets to version control.

## Summary

The synchronization process ensures:
- ✅ All secrets are defined in `.env.secrets` (single source of truth)
- ✅ All `.env.*` files use the same secret values
- ✅ Services can authenticate correctly
- ✅ No configuration inconsistencies

After completing this process, all Docker Compose services will reference consistent secret values, preventing authentication failures and configuration errors.

