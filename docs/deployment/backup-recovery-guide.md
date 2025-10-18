# Lucid System Backup & Recovery Guide

## Document Control

| Attribute | Value |
|-----------|-------|
| Document ID | LUCID-BACKUP-001 |
| Version | 1.0.0 |
| Status | ACTIVE |
| Last Updated | 2025-01-14 |
| Based On | Master Build Plan v1.0.0 |

---

## Overview

This comprehensive backup and recovery guide covers all data stores and system components in the Lucid blockchain system. The guide provides automated backup procedures, recovery strategies, and disaster recovery plans for all 10 service clusters.

### Backup Strategy Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Backup Storage Layer                    │
│  Local Storage + Cloud Storage + Offsite Backup            │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────┴───────────────────────────────────────────┐
│                Database Backup Layer                      │
│  MongoDB: Full + Incremental + Point-in-time            │
│  Redis: RDB + AOF + Cluster State                        │
│  Elasticsearch: Snapshot + Index Backup                  │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────┴───────────────────────────────────────────┐
│                Application Data Layer                     │
│  Session Data: Chunk Storage + Metadata                  │
│  Blockchain Data: Block Storage + Merkle Trees           │
│  Configuration: Service Configs + Secrets                │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────┴───────────────────────────────────────────┐
│                System State Layer                         │
│  Container Images: Registry Backup                        │
│  Volumes: Persistent Volume Snapshots                     │
│  Network: Configuration Backup                           │
└─────────────────────────────────────────────────────────────┘
```

---

## MongoDB Backup & Recovery

### MongoDB Backup Strategy

#### Full Backup Script

```bash
#!/bin/bash
# scripts/backup/mongodb-backup.sh

set -e

# Configuration
BACKUP_DIR="/opt/lucid/backups/mongodb"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="lucid_mongo_backup_${DATE}.gz"
RETENTION_DAYS=30
MONGO_CONTAINER="lucid-mongodb"
MONGO_USER="lucid"
MONGO_PASSWORD="${MONGO_PASSWORD}"

echo "Starting MongoDB backup process..."

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Check MongoDB connectivity
echo "Checking MongoDB connectivity..."
docker exec "$MONGO_CONTAINER" mongosh --eval "db.runCommand({ping: 1})" --quiet

# Perform full backup
echo "Performing full MongoDB backup..."
docker exec "$MONGO_CONTAINER" mongodump \
  --username="$MONGO_USER" \
  --password="$MONGO_PASSWORD" \
  --authenticationDatabase="admin" \
  --gzip \
  --archive="/tmp/$BACKUP_FILE"

# Copy backup from container
echo "Copying backup from container..."
docker cp "$MONGO_CONTAINER:/tmp/$BACKUP_FILE" "$BACKUP_DIR/$BACKUP_FILE"

# Clean up container backup
docker exec "$MONGO_CONTAINER" rm "/tmp/$BACKUP_FILE"

# Verify backup
echo "Verifying backup..."
docker exec "$MONGO_CONTAINER" mongorestore --dryRun \
  --gzip \
  --archive < "$BACKUP_DIR/$BACKUP_FILE" \
  --quiet

# Calculate backup size
BACKUP_SIZE=$(du -h "$BACKUP_DIR/$BACKUP_FILE" | cut -f1)
echo "Backup completed: $BACKUP_DIR/$BACKUP_FILE (Size: $BACKUP_SIZE)"

# Cleanup old backups
echo "Cleaning up old backups..."
find "$BACKUP_DIR" -name "lucid_mongo_backup_*.gz" -mtime +$RETENTION_DAYS -delete

# Upload to cloud storage (optional)
if [ "$CLOUD_BACKUP_ENABLED" = "true" ]; then
    echo "Uploading backup to cloud storage..."
    aws s3 cp "$BACKUP_DIR/$BACKUP_FILE" "s3://lucid-backups/mongodb/$BACKUP_FILE"
    echo "Backup uploaded to cloud storage"
fi

echo "MongoDB backup process completed successfully!"
```

#### Incremental Backup Script

```bash
#!/bin/bash
# scripts/backup/mongodb-incremental-backup.sh

set -e

# Configuration
BACKUP_DIR="/opt/lucid/backups/mongodb/incremental"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="lucid_mongo_incremental_${DATE}.gz"
RETENTION_DAYS=7
MONGO_CONTAINER="lucid-mongodb"
MONGO_USER="lucid"
MONGO_PASSWORD="${MONGO_PASSWORD}"

echo "Starting MongoDB incremental backup process..."

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Get last backup timestamp
LAST_BACKUP_TIMESTAMP=$(find "$BACKUP_DIR" -name "lucid_mongo_incremental_*.gz" -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2)
if [ -n "$LAST_BACKUP_TIMESTAMP" ]; then
    LAST_BACKUP_TIME=$(stat -c %Y "$LAST_BACKUP_TIMESTAMP")
    echo "Last backup timestamp: $LAST_BACKUP_TIME"
else
    echo "No previous incremental backup found, performing full backup..."
    ./scripts/backup/mongodb-backup.sh
    exit 0
fi

# Perform incremental backup
echo "Performing incremental MongoDB backup..."
docker exec "$MONGO_CONTAINER" mongodump \
  --username="$MONGO_USER" \
  --password="$MONGO_PASSWORD" \
  --authenticationDatabase="admin" \
  --gzip \
  --archive="/tmp/$BACKUP_FILE" \
  --query='{"_id": {"$gte": ObjectId.fromDate(new Date('$LAST_BACKUP_TIME' * 1000))}}'

# Copy backup from container
echo "Copying backup from container..."
docker cp "$MONGO_CONTAINER:/tmp/$BACKUP_FILE" "$BACKUP_DIR/$BACKUP_FILE"

# Clean up container backup
docker exec "$MONGO_CONTAINER" rm "/tmp/$BACKUP_FILE"

# Verify backup
echo "Verifying backup..."
docker exec "$MONGO_CONTAINER" mongorestore --dryRun \
  --gzip \
  --archive < "$BACKUP_DIR/$BACKUP_FILE" \
  --quiet

# Calculate backup size
BACKUP_SIZE=$(du -h "$BACKUP_DIR/$BACKUP_FILE" | cut -f1)
echo "Incremental backup completed: $BACKUP_DIR/$BACKUP_FILE (Size: $BACKUP_SIZE)"

# Cleanup old incremental backups
echo "Cleaning up old incremental backups..."
find "$BACKUP_DIR" -name "lucid_mongo_incremental_*.gz" -mtime +$RETENTION_DAYS -delete

echo "MongoDB incremental backup process completed successfully!"
```

#### Point-in-Time Recovery Setup

```bash
#!/bin/bash
# scripts/backup/mongodb-pitr-setup.sh

set -e

# Configuration
MONGO_CONTAINER="lucid-mongodb"
MONGO_USER="lucid"
MONGO_PASSWORD="${MONGO_PASSWORD}"

echo "Setting up MongoDB point-in-time recovery..."

# Enable oplog
echo "Enabling oplog for point-in-time recovery..."
docker exec "$MONGO_CONTAINER" mongosh --eval "
use local;
db.createCollection('oplog.rs', {
  capped: true,
  size: 1000000000,  // 1GB
  max: 1000000       // 1M documents
});
"

# Create oplog backup script
cat > /opt/lucid/scripts/backup/mongodb-oplog-backup.sh << 'EOF'
#!/bin/bash
# MongoDB oplog backup script

set -e

BACKUP_DIR="/opt/lucid/backups/mongodb/oplog"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="lucid_mongo_oplog_${DATE}.gz"
MONGO_CONTAINER="lucid-mongodb"
MONGO_USER="lucid"
MONGO_PASSWORD="${MONGO_PASSWORD}"

mkdir -p "$BACKUP_DIR"

# Backup oplog
docker exec "$MONGO_CONTAINER" mongodump \
  --username="$MONGO_USER" \
  --password="$MONGO_PASSWORD" \
  --authenticationDatabase="admin" \
  --db="local" \
  --collection="oplog.rs" \
  --gzip \
  --archive="/tmp/$BACKUP_FILE"

# Copy backup from container
docker cp "$MONGO_CONTAINER:/tmp/$BACKUP_FILE" "$BACKUP_DIR/$BACKUP_FILE"

# Clean up container backup
docker exec "$MONGO_CONTAINER" rm "/tmp/$BACKUP_FILE"

echo "Oplog backup completed: $BACKUP_DIR/$BACKUP_FILE"
EOF

chmod +x /opt/lucid/scripts/backup/mongodb-oplog-backup.sh

# Setup cron job for oplog backup (every 5 minutes)
echo "*/5 * * * * /opt/lucid/scripts/backup/mongodb-oplog-backup.sh" | crontab -

echo "MongoDB point-in-time recovery setup completed!"
```

### MongoDB Recovery Procedures

#### Full Database Recovery

```bash
#!/bin/bash
# scripts/recovery/mongodb-restore.sh

set -e

# Configuration
BACKUP_FILE="$1"
MONGO_CONTAINER="lucid-mongodb"
MONGO_USER="lucid"
MONGO_PASSWORD="${MONGO_PASSWORD}"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    echo "Example: $0 /opt/lucid/backups/mongodb/lucid_mongo_backup_20240101_120000.gz"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "Starting MongoDB restore from: $BACKUP_FILE"

# Stop application services to prevent data corruption
echo "Stopping application services..."
docker-compose stop lucid-api-gateway lucid-auth-service lucid-session-api

# Restore database
echo "Restoring database..."
docker exec -i "$MONGO_CONTAINER" mongorestore \
  --drop \
  --gzip \
  --archive < "$BACKUP_FILE"

# Restart application services
echo "Restarting application services..."
docker-compose start lucid-api-gateway lucid-auth-service lucid-session-api

# Verify restore
echo "Verifying restore..."
docker exec "$MONGO_CONTAINER" mongosh --eval "db.runCommand({dbStats: 1})"

echo "MongoDB restore completed successfully!"
```

#### Point-in-Time Recovery

```bash
#!/bin/bash
# scripts/recovery/mongodb-pitr-restore.sh

set -e

# Configuration
TARGET_TIME="$1"  # Format: YYYY-MM-DD HH:MM:SS
MONGO_CONTAINER="lucid-mongodb"
MONGO_USER="lucid"
MONGO_PASSWORD="${MONGO_PASSWORD}"

if [ -z "$TARGET_TIME" ]; then
    echo "Usage: $0 <target_time>"
    echo "Example: $0 '2024-01-01 12:00:00'"
    exit 1
fi

echo "Starting MongoDB point-in-time recovery to: $TARGET_TIME"

# Convert target time to timestamp
TARGET_TIMESTAMP=$(date -d "$TARGET_TIME" +%s)
echo "Target timestamp: $TARGET_TIMESTAMP"

# Stop application services
echo "Stopping application services..."
docker-compose stop lucid-api-gateway lucid-auth-service lucid-session-api

# Find the latest full backup before target time
LATEST_FULL_BACKUP=$(find /opt/lucid/backups/mongodb -name "lucid_mongo_backup_*.gz" -newermt "$TARGET_TIME" | sort | tail -1)
if [ -z "$LATEST_FULL_BACKUP" ]; then
    echo "Error: No full backup found before target time"
    exit 1
fi

echo "Using full backup: $LATEST_FULL_BACKUP"

# Restore from full backup
echo "Restoring from full backup..."
docker exec -i "$MONGO_CONTAINER" mongorestore \
  --drop \
  --gzip \
  --archive < "$LATEST_FULL_BACKUP"

# Apply oplog entries up to target time
echo "Applying oplog entries up to target time..."
for oplog_backup in $(find /opt/lucid/backups/mongodb/oplog -name "lucid_mongo_oplog_*.gz" -newermt "$TARGET_TIME" | sort); do
    echo "Applying oplog backup: $oplog_backup"
    docker exec -i "$MONGO_CONTAINER" mongorestore \
      --gzip \
      --archive < "$oplog_backup"
done

# Restart application services
echo "Restarting application services..."
docker-compose start lucid-api-gateway lucid-auth-service lucid-session-api

# Verify restore
echo "Verifying restore..."
docker exec "$MONGO_CONTAINER" mongosh --eval "db.runCommand({dbStats: 1})"

echo "MongoDB point-in-time recovery completed successfully!"
```

---

## Redis Backup & Recovery

### Redis Backup Strategy

#### RDB Backup Script

```bash
#!/bin/bash
# scripts/backup/redis-backup.sh

set -e

# Configuration
BACKUP_DIR="/opt/lucid/backups/redis"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="lucid_redis_backup_${DATE}.rdb"
RETENTION_DAYS=7
REDIS_CONTAINER="lucid-redis"
REDIS_PASSWORD="${REDIS_PASSWORD}"

echo "Starting Redis backup process..."

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Check Redis connectivity
echo "Checking Redis connectivity..."
docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$REDIS_PASSWORD" ping

# Perform RDB backup
echo "Performing Redis RDB backup..."
docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$REDIS_PASSWORD" --rdb "/tmp/$BACKUP_FILE"

# Copy backup from container
echo "Copying backup from container..."
docker cp "$REDIS_CONTAINER:/tmp/$BACKUP_FILE" "$BACKUP_DIR/$BACKUP_FILE"

# Clean up container backup
docker exec "$REDIS_CONTAINER" rm "/tmp/$BACKUP_FILE"

# Verify backup
echo "Verifying backup..."
docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$REDIS_PASSWORD" --rdb "/tmp/verify_$BACKUP_FILE"
docker exec "$REDIS_CONTAINER" rm "/tmp/verify_$BACKUP_FILE"

# Calculate backup size
BACKUP_SIZE=$(du -h "$BACKUP_DIR/$BACKUP_FILE" | cut -f1)
echo "Backup completed: $BACKUP_DIR/$BACKUP_FILE (Size: $BACKUP_SIZE)"

# Cleanup old backups
echo "Cleaning up old backups..."
find "$BACKUP_DIR" -name "lucid_redis_backup_*.rdb" -mtime +$RETENTION_DAYS -delete

# Upload to cloud storage (optional)
if [ "$CLOUD_BACKUP_ENABLED" = "true" ]; then
    echo "Uploading backup to cloud storage..."
    aws s3 cp "$BACKUP_DIR/$BACKUP_FILE" "s3://lucid-backups/redis/$BACKUP_FILE"
    echo "Backup uploaded to cloud storage"
fi

echo "Redis backup process completed successfully!"
```

#### AOF Backup Script

```bash
#!/bin/bash
# scripts/backup/redis-aof-backup.sh

set -e

# Configuration
BACKUP_DIR="/opt/lucid/backups/redis/aof"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="lucid_redis_aof_${DATE}.aof"
RETENTION_DAYS=3
REDIS_CONTAINER="lucid-redis"
REDIS_PASSWORD="${REDIS_PASSWORD}"

echo "Starting Redis AOF backup process..."

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Check Redis connectivity
echo "Checking Redis connectivity..."
docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$REDIS_PASSWORD" ping

# Perform AOF backup
echo "Performing Redis AOF backup..."
docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$REDIS_PASSWORD" bgrewriteaof

# Wait for AOF rewrite to complete
echo "Waiting for AOF rewrite to complete..."
while [ "$(docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$REDIS_PASSWORD" info persistence | grep aof_rewrite_in_progress | cut -d: -f2 | tr -d '\r')" = "1" ]; do
    sleep 1
done

# Copy AOF file from container
echo "Copying AOF file from container..."
docker cp "$REDIS_CONTAINER:/data/appendonly.aof" "$BACKUP_DIR/$BACKUP_FILE"

# Calculate backup size
BACKUP_SIZE=$(du -h "$BACKUP_DIR/$BACKUP_FILE" | cut -f1)
echo "AOF backup completed: $BACKUP_DIR/$BACKUP_FILE (Size: $BACKUP_SIZE)"

# Cleanup old AOF backups
echo "Cleaning up old AOF backups..."
find "$BACKUP_DIR" -name "lucid_redis_aof_*.aof" -mtime +$RETENTION_DAYS -delete

echo "Redis AOF backup process completed successfully!"
```

### Redis Recovery Procedures

#### RDB Recovery

```bash
#!/bin/bash
# scripts/recovery/redis-restore.sh

set -e

# Configuration
BACKUP_FILE="$1"
REDIS_CONTAINER="lucid-redis"
REDIS_PASSWORD="${REDIS_PASSWORD}"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    echo "Example: $0 /opt/lucid/backups/redis/lucid_redis_backup_20240101_120000.rdb"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "Starting Redis restore from: $BACKUP_FILE"

# Stop Redis service
echo "Stopping Redis service..."
docker-compose stop lucid-redis

# Copy backup to container
echo "Copying backup to container..."
docker cp "$BACKUP_FILE" "$REDIS_CONTAINER:/data/dump.rdb"

# Start Redis service
echo "Starting Redis service..."
docker-compose start lucid-redis

# Wait for Redis to start
echo "Waiting for Redis to start..."
sleep 10

# Verify restore
echo "Verifying restore..."
docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$REDIS_PASSWORD" ping
docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$REDIS_PASSWORD" info keyspace

echo "Redis restore completed successfully!"
```

#### AOF Recovery

```bash
#!/bin/bash
# scripts/recovery/redis-aof-restore.sh

set -e

# Configuration
BACKUP_FILE="$1"
REDIS_CONTAINER="lucid-redis"
REDIS_PASSWORD="${REDIS_PASSWORD}"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    echo "Example: $0 /opt/lucid/backups/redis/aof/lucid_redis_aof_20240101_120000.aof"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "Starting Redis AOF restore from: $BACKUP_FILE"

# Stop Redis service
echo "Stopping Redis service..."
docker-compose stop lucid-redis

# Copy AOF backup to container
echo "Copying AOF backup to container..."
docker cp "$BACKUP_FILE" "$REDIS_CONTAINER:/data/appendonly.aof"

# Start Redis service
echo "Starting Redis service..."
docker-compose start lucid-redis

# Wait for Redis to start
echo "Waiting for Redis to start..."
sleep 10

# Verify restore
echo "Verifying restore..."
docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$REDIS_PASSWORD" ping
docker exec "$REDIS_CONTAINER" redis-cli --no-auth-warning -a "$REDIS_PASSWORD" info keyspace

echo "Redis AOF restore completed successfully!"
```

---

## Elasticsearch Backup & Recovery

### Elasticsearch Backup Strategy

#### Snapshot Backup Script

```bash
#!/bin/bash
# scripts/backup/elasticsearch-backup.sh

set -e

# Configuration
BACKUP_DIR="/opt/lucid/backups/elasticsearch"
DATE=$(date +%Y%m%d_%H%M%S)
SNAPSHOT_NAME="lucid_elasticsearch_${DATE}"
RETENTION_DAYS=30
ELASTICSEARCH_CONTAINER="lucid-elasticsearch"

echo "Starting Elasticsearch backup process..."

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Check Elasticsearch connectivity
echo "Checking Elasticsearch connectivity..."
curl -f http://localhost:9200/_cluster/health

# Create snapshot repository
echo "Creating snapshot repository..."
curl -X PUT "localhost:9200/_snapshot/lucid_backups" -H 'Content-Type: application/json' -d'
{
  "type": "fs",
  "settings": {
    "location": "/opt/lucid/backups/elasticsearch"
  }
}'

# Create snapshot
echo "Creating snapshot: $SNAPSHOT_NAME"
curl -X PUT "localhost:9200/_snapshot/lucid_backups/$SNAPSHOT_NAME" -H 'Content-Type: application/json' -d'
{
  "indices": "*",
  "ignore_unavailable": true,
  "include_global_state": true
}'

# Wait for snapshot to complete
echo "Waiting for snapshot to complete..."
while [ "$(curl -s "localhost:9200/_snapshot/lucid_backups/$SNAPSHOT_NAME" | jq -r '.snapshots[0].state')" != "SUCCESS" ]; do
    sleep 5
done

# Verify snapshot
echo "Verifying snapshot..."
curl -s "localhost:9200/_snapshot/lucid_backups/$SNAPSHOT_NAME" | jq '.snapshots[0]'

# Calculate backup size
BACKUP_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
echo "Backup completed: $SNAPSHOT_NAME (Size: $BACKUP_SIZE)"

# Cleanup old snapshots
echo "Cleaning up old snapshots..."
curl -X DELETE "localhost:9200/_snapshot/lucid_backups/$(curl -s "localhost:9200/_snapshot/lucid_backups/_all" | jq -r '.snapshots | sort_by(.start_time_in_millis) | .[0].snapshot')"

echo "Elasticsearch backup process completed successfully!"
```

### Elasticsearch Recovery Procedures

#### Snapshot Recovery

```bash
#!/bin/bash
# scripts/recovery/elasticsearch-restore.sh

set -e

# Configuration
SNAPSHOT_NAME="$1"
ELASTICSEARCH_CONTAINER="lucid-elasticsearch"

if [ -z "$SNAPSHOT_NAME" ]; then
    echo "Usage: $0 <snapshot_name>"
    echo "Example: $0 lucid_elasticsearch_20240101_120000"
    exit 1
fi

echo "Starting Elasticsearch restore from snapshot: $SNAPSHOT_NAME"

# Check Elasticsearch connectivity
echo "Checking Elasticsearch connectivity..."
curl -f http://localhost:9200/_cluster/health

# Check if snapshot exists
echo "Checking if snapshot exists..."
curl -s "localhost:9200/_snapshot/lucid_backups/$SNAPSHOT_NAME" | jq '.snapshots[0]'

# Close all indices
echo "Closing all indices..."
curl -X POST "localhost:9200/_all/_close"

# Restore snapshot
echo "Restoring snapshot..."
curl -X POST "localhost:9200/_snapshot/lucid_backups/$SNAPSHOT_NAME/_restore" -H 'Content-Type: application/json' -d'
{
  "indices": "*",
  "ignore_unavailable": true,
  "include_global_state": true
}'

# Wait for restore to complete
echo "Waiting for restore to complete..."
while [ "$(curl -s "localhost:9200/_snapshot/lucid_backups/$SNAPSHOT_NAME/_status" | jq '.snapshots[0].state')" != "SUCCESS" ]; do
    sleep 5
done

# Open all indices
echo "Opening all indices..."
curl -X POST "localhost:9200/_all/_open"

# Verify restore
echo "Verifying restore..."
curl -s "localhost:9200/_cluster/health" | jq '.status'
curl -s "localhost:9200/_cat/indices?v"

echo "Elasticsearch restore completed successfully!"
```

---

## Application Data Backup

### Session Data Backup

#### Session Data Backup Script

```bash
#!/bin/bash
# scripts/backup/session-data-backup.sh

set -e

# Configuration
BACKUP_DIR="/opt/lucid/backups/session-data"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="lucid_session_data_${DATE}.tar.gz"
RETENTION_DAYS=30

echo "Starting session data backup process..."

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Stop session services to ensure data consistency
echo "Stopping session services..."
docker-compose stop lucid-session-recorder lucid-chunk-processor lucid-session-storage

# Backup session data
echo "Backing up session data..."
tar -czf "$BACKUP_DIR/$BACKUP_FILE" \
  -C /opt/lucid/volumes \
  lucid-session-data \
  lucid-chunk-data \
  lucid-session-storage-data

# Restart session services
echo "Restarting session services..."
docker-compose start lucid-session-recorder lucid-chunk-processor lucid-session-storage

# Calculate backup size
BACKUP_SIZE=$(du -h "$BACKUP_DIR/$BACKUP_FILE" | cut -f1)
echo "Session data backup completed: $BACKUP_DIR/$BACKUP_FILE (Size: $BACKUP_SIZE)"

# Cleanup old backups
echo "Cleaning up old backups..."
find "$BACKUP_DIR" -name "lucid_session_data_*.tar.gz" -mtime +$RETENTION_DAYS -delete

# Upload to cloud storage (optional)
if [ "$CLOUD_BACKUP_ENABLED" = "true" ]; then
    echo "Uploading backup to cloud storage..."
    aws s3 cp "$BACKUP_DIR/$BACKUP_FILE" "s3://lucid-backups/session-data/$BACKUP_FILE"
    echo "Backup uploaded to cloud storage"
fi

echo "Session data backup process completed successfully!"
```

### Blockchain Data Backup

#### Blockchain Data Backup Script

```bash
#!/bin/bash
# scripts/backup/blockchain-data-backup.sh

set -e

# Configuration
BACKUP_DIR="/opt/lucid/backups/blockchain-data"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="lucid_blockchain_data_${DATE}.tar.gz"
RETENTION_DAYS=90

echo "Starting blockchain data backup process..."

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Stop blockchain services to ensure data consistency
echo "Stopping blockchain services..."
docker-compose stop lucid-blockchain-engine lucid-session-anchoring

# Backup blockchain data
echo "Backing up blockchain data..."
tar -czf "$BACKUP_DIR/$BACKUP_FILE" \
  -C /opt/lucid/volumes \
  lucid-blockchain-data \
  lucid-merkle-data

# Restart blockchain services
echo "Restarting blockchain services..."
docker-compose start lucid-blockchain-engine lucid-session-anchoring

# Calculate backup size
BACKUP_SIZE=$(du -h "$BACKUP_DIR/$BACKUP_FILE" | cut -f1)
echo "Blockchain data backup completed: $BACKUP_DIR/$BACKUP_FILE (Size: $BACKUP_SIZE)"

# Cleanup old backups
echo "Cleaning up old backups..."
find "$BACKUP_DIR" -name "lucid_blockchain_data_*.tar.gz" -mtime +$RETENTION_DAYS -delete

# Upload to cloud storage (optional)
if [ "$CLOUD_BACKUP_ENABLED" = "true" ]; then
    echo "Uploading backup to cloud storage..."
    aws s3 cp "$BACKUP_DIR/$BACKUP_FILE" "s3://lucid-backups/blockchain-data/$BACKUP_FILE"
    echo "Backup uploaded to cloud storage"
fi

echo "Blockchain data backup process completed successfully!"
```

---

## Configuration Backup

### Configuration Backup Script

```bash
#!/bin/bash
# scripts/backup/configuration-backup.sh

set -e

# Configuration
BACKUP_DIR="/opt/lucid/backups/configuration"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="lucid_configuration_${DATE}.tar.gz"
RETENTION_DAYS=30

echo "Starting configuration backup process..."

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup configuration files
echo "Backing up configuration files..."
tar -czf "$BACKUP_DIR/$BACKUP_FILE" \
  -C /opt/lucid \
  configs \
  .env.production \
  docker-compose.yml \
  docker-compose.*.yml

# Calculate backup size
BACKUP_SIZE=$(du -h "$BACKUP_DIR/$BACKUP_FILE" | cut -f1)
echo "Configuration backup completed: $BACKUP_DIR/$BACKUP_FILE (Size: $BACKUP_SIZE)"

# Cleanup old backups
echo "Cleaning up old backups..."
find "$BACKUP_DIR" -name "lucid_configuration_*.tar.gz" -mtime +$RETENTION_DAYS -delete

# Upload to cloud storage (optional)
if [ "$CLOUD_BACKUP_ENABLED" = "true" ]; then
    echo "Uploading backup to cloud storage..."
    aws s3 cp "$BACKUP_DIR/$BACKUP_FILE" "s3://lucid-backups/configuration/$BACKUP_FILE"
    echo "Backup uploaded to cloud storage"
fi

echo "Configuration backup process completed successfully!"
```

---

## Complete System Backup

### Full System Backup Script

```bash
#!/bin/bash
# scripts/backup/full-system-backup.sh

set -e

# Configuration
BACKUP_DIR="/opt/lucid/backups/full-system"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="lucid_full_system_${DATE}.tar.gz"
RETENTION_DAYS=7

echo "Starting full system backup process..."

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Stop all services
echo "Stopping all services..."
docker-compose down

# Backup all data
echo "Backing up all data..."
tar -czf "$BACKUP_DIR/$BACKUP_FILE" \
  -C /opt/lucid \
  volumes \
  configs \
  .env.production \
  docker-compose.yml \
  docker-compose.*.yml

# Start all services
echo "Starting all services..."
docker-compose up -d

# Calculate backup size
BACKUP_SIZE=$(du -h "$BACKUP_DIR/$BACKUP_FILE" | cut -f1)
echo "Full system backup completed: $BACKUP_DIR/$BACKUP_FILE (Size: $BACKUP_SIZE)"

# Cleanup old backups
echo "Cleaning up old backups..."
find "$BACKUP_DIR" -name "lucid_full_system_*.tar.gz" -mtime +$RETENTION_DAYS -delete

# Upload to cloud storage (optional)
if [ "$CLOUD_BACKUP_ENABLED" = "true" ]; then
    echo "Uploading backup to cloud storage..."
    aws s3 cp "$BACKUP_DIR/$BACKUP_FILE" "s3://lucid-backups/full-system/$BACKUP_FILE"
    echo "Backup uploaded to cloud storage"
fi

echo "Full system backup process completed successfully!"
```

---

## Disaster Recovery

### Disaster Recovery Plan

#### Complete System Recovery

```bash
#!/bin/bash
# scripts/recovery/disaster-recovery.sh

set -e

# Configuration
BACKUP_FILE="$1"
RECOVERY_DIR="/opt/lucid/recovery"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    echo "Example: $0 /opt/lucid/backups/full-system/lucid_full_system_20240101_120000.tar.gz"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "Starting disaster recovery process..."

# Create recovery directory
mkdir -p "$RECOVERY_DIR"

# Stop all services
echo "Stopping all services..."
docker-compose down

# Remove existing data
echo "Removing existing data..."
rm -rf /opt/lucid/volumes/*
rm -rf /opt/lucid/configs/*

# Restore from backup
echo "Restoring from backup..."
tar -xzf "$BACKUP_FILE" -C /opt/lucid

# Set proper permissions
echo "Setting proper permissions..."
chown -R 1000:1000 /opt/lucid/volumes
chmod -R 755 /opt/lucid/volumes

# Start all services
echo "Starting all services..."
docker-compose up -d

# Wait for services to start
echo "Waiting for services to start..."
sleep 60

# Verify recovery
echo "Verifying recovery..."
./scripts/health/check-all-services.sh

echo "Disaster recovery process completed successfully!"
```

#### Partial System Recovery

```bash
#!/bin/bash
# scripts/recovery/partial-recovery.sh

set -e

# Configuration
COMPONENT="$1"
BACKUP_FILE="$2"

if [ -z "$COMPONENT" ] || [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <component> <backup_file>"
    echo "Components: mongodb, redis, elasticsearch, session-data, blockchain-data, configuration"
    echo "Example: $0 mongodb /opt/lucid/backups/mongodb/lucid_mongo_backup_20240101_120000.gz"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "Starting partial recovery for component: $COMPONENT"

case "$COMPONENT" in
    "mongodb")
        echo "Recovering MongoDB..."
        ./scripts/recovery/mongodb-restore.sh "$BACKUP_FILE"
        ;;
    "redis")
        echo "Recovering Redis..."
        ./scripts/recovery/redis-restore.sh "$BACKUP_FILE"
        ;;
    "elasticsearch")
        echo "Recovering Elasticsearch..."
        ./scripts/recovery/elasticsearch-restore.sh "$BACKUP_FILE"
        ;;
    "session-data")
        echo "Recovering session data..."
        docker-compose stop lucid-session-recorder lucid-chunk-processor lucid-session-storage
        tar -xzf "$BACKUP_FILE" -C /opt/lucid/volumes
        docker-compose start lucid-session-recorder lucid-chunk-processor lucid-session-storage
        ;;
    "blockchain-data")
        echo "Recovering blockchain data..."
        docker-compose stop lucid-blockchain-engine lucid-session-anchoring
        tar -xzf "$BACKUP_FILE" -C /opt/lucid/volumes
        docker-compose start lucid-blockchain-engine lucid-session-anchoring
        ;;
    "configuration")
        echo "Recovering configuration..."
        tar -xzf "$BACKUP_FILE" -C /opt/lucid
        ;;
    *)
        echo "Error: Unknown component: $COMPONENT"
        exit 1
        ;;
esac

echo "Partial recovery for $COMPONENT completed successfully!"
```

---

## Backup Automation

### Automated Backup Schedule

```bash
#!/bin/bash
# scripts/backup/setup-backup-schedule.sh

set -e

echo "Setting up automated backup schedule..."

# Create backup directory
mkdir -p /opt/lucid/scripts/backup

# Setup cron jobs
echo "Setting up cron jobs..."

# MongoDB full backup (daily at 2 AM)
echo "0 2 * * * /opt/lucid/scripts/backup/mongodb-backup.sh" | crontab -

# MongoDB incremental backup (every 6 hours)
echo "0 */6 * * * /opt/lucid/scripts/backup/mongodb-incremental-backup.sh" | crontab -

# Redis backup (daily at 3 AM)
echo "0 3 * * * /opt/lucid/scripts/backup/redis-backup.sh" | crontab -

# Elasticsearch backup (daily at 4 AM)
echo "0 4 * * * /opt/lucid/scripts/backup/elasticsearch-backup.sh" | crontab -

# Session data backup (daily at 5 AM)
echo "0 5 * * * /opt/lucid/scripts/backup/session-data-backup.sh" | crontab -

# Blockchain data backup (daily at 6 AM)
echo "0 6 * * * /opt/lucid/scripts/backup/blockchain-data-backup.sh" | crontab -

# Configuration backup (daily at 7 AM)
echo "0 7 * * * /opt/lucid/scripts/backup/configuration-backup.sh" | crontab -

# Full system backup (weekly on Sunday at 1 AM)
echo "0 1 * * 0 /opt/lucid/scripts/backup/full-system-backup.sh" | crontab -

echo "Automated backup schedule setup completed!"
```

### Backup Monitoring

```bash
#!/bin/bash
# scripts/backup/monitor-backups.sh

set -e

echo "=== Lucid System Backup Monitoring ==="

# Check backup status
echo "=== Backup Status ==="
echo "MongoDB backups:"
ls -la /opt/lucid/backups/mongodb/ | tail -5

echo "Redis backups:"
ls -la /opt/lucid/backups/redis/ | tail -5

echo "Elasticsearch backups:"
ls -la /opt/lucid/backups/elasticsearch/ | tail -5

echo "Session data backups:"
ls -la /opt/lucid/backups/session-data/ | tail -5

echo "Blockchain data backups:"
ls -la /opt/lucid/backups/blockchain-data/ | tail -5

echo "Configuration backups:"
ls -la /opt/lucid/backups/configuration/ | tail -5

echo "Full system backups:"
ls -la /opt/lucid/backups/full-system/ | tail -5

# Check backup sizes
echo "=== Backup Sizes ==="
du -sh /opt/lucid/backups/*

# Check backup integrity
echo "=== Backup Integrity ==="
echo "Checking MongoDB backup integrity..."
find /opt/lucid/backups/mongodb -name "*.gz" -exec gunzip -t {} \;

echo "Checking Redis backup integrity..."
find /opt/lucid/backups/redis -name "*.rdb" -exec file {} \;

echo "Checking Elasticsearch backup integrity..."
find /opt/lucid/backups/elasticsearch -name "*.gz" -exec gunzip -t {} \;

echo "Backup monitoring completed!"
```

---

## References

- [Deployment Guide](./deployment-guide.md)
- [Troubleshooting Guide](./troubleshooting-guide.md)
- [Scaling Guide](./scaling-guide.md)
- [Security Hardening Guide](./security-hardening-guide.md)
- [Master Build Plan](../plan/API_plans/00-master-architecture/01-MASTER_BUILD_PLAN.md)

---

**Document Version**: 1.0.0  
**Status**: ACTIVE  
**Last Updated**: 2025-01-14
