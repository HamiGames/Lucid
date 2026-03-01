# MongoDB User Setup Guide

## Purpose

This guide explains how to set up the MongoDB `lucid` user for the Lucid Authentication Service.

## Problem

The `lucid-auth-service` requires a MongoDB user named `lucid` with authentication credentials. If MongoDB was initialized without this user, authentication will fail.

## Solution

Run the setup script **once** to create the MongoDB user:

```bash
cd /mnt/myssd/Lucid/Lucid
./scripts/database/setup-mongodb-user.sh
```

## What the Script Does

1. Reads `MONGODB_PASSWORD` from `.env.secrets`
2. Checks if MongoDB container is running
3. Checks if `lucid` user already exists
4. Creates the user if it doesn't exist
5. Verifies authentication works

## Requirements

- MongoDB container (`lucid-mongodb`) must be running
- `.env.secrets` file must contain `MONGODB_PASSWORD`
- MongoDB must be accessible (healthcheck passing)

## If Script Fails with "AUTH_REQUIRED"

If MongoDB is running with `--auth` but no users exist, you'll need to:

1. **Stop MongoDB:**
   ```bash
   docker stop lucid-mongodb
   ```

2. **Temporarily remove `--auth` from docker-compose.foundation.yml:**
   - Edit `configs/docker/docker-compose.foundation.yml`
   - Remove `- --auth` from line ~166 in the `lucid-mongodb` command section

3. **Start MongoDB without auth:**
   ```bash
   docker compose -f /mnt/myssd/Lucid/Lucid/configs/docker/docker-compose.foundation.yml --env-file /mnt/myssd/Lucid/Lucid/configs/environment/.env.foundation --env-file /mnt/myssd/Lucid/Lucid/configs/environment/.env.support --env-file /mnt/myssd/Lucid/Lucid/configs/environment/.env.distroless --env-file /mnt/myssd/Lucid/Lucid/configs/environment/.env.secrets up -d lucid-mongodb
   ```

4. **Run the setup script:**
   ```bash
   ./scripts/database/setup-mongodb-user.sh
   ```

5. **Re-add `--auth` to docker-compose.foundation.yml** (add it back to line ~166)

6. **Restart MongoDB with auth:**
   ```bash
   docker stop lucid-mongodb
   docker compose -f /mnt/myssd/Lucid/Lucid/configs/docker/docker-compose.foundation.yml --env-file /mnt/myssd/Lucid/Lucid/configs/environment/.env.foundation --env-file /mnt/myssd/Lucid/Lucid/configs/environment/.env.support --env-file /mnt/myssd/Lucid/Lucid/configs/environment/.env.distroless --env-file /mnt/myssd/Lucid/Lucid/configs/environment/.env.secrets up -d lucid-mongodb
   ```

## Verification

After setup, verify the user works:

```bash
MONGODB_PASSWORD=$(grep "^MONGODB_PASSWORD=" /mnt/myssd/Lucid/Lucid/configs/environment/.env.secrets | cut -d= -f2)
docker exec lucid-mongodb mongosh --quiet -u lucid -p "$MONGODB_PASSWORD" --authenticationDatabase admin --eval "db.runCommand({ connectionStatus: 1 })"
```

## After Setup

Once the user is created, `lucid-auth-service` should connect successfully. Restart the auth service:

```bash
docker compose -f /mnt/myssd/Lucid/Lucid/configs/docker/docker-compose.foundation.yml --env-file /mnt/myssd/Lucid/Lucid/configs/environment/.env.foundation --env-file /mnt/myssd/Lucid/Lucid/configs/environment/.env.support --env-file /mnt/myssd/Lucid/Lucid/configs/environment/.env.distroless --env-file /mnt/myssd/Lucid/Lucid/configs/environment/.env.secrets up -d lucid-auth-service
```

## Notes

- This is a **one-time setup** - once the user exists, you don't need to run the script again
- The user password comes from `MONGODB_PASSWORD` in `.env.secrets`
- The connection string in `docker-compose.foundation.yml` uses this password automatically
- All changes are permanent - no temporary modifications needed after initial setup

