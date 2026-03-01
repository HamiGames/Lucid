# Step 3: Redis & Elasticsearch Setup - Quick Reference

## 🎯 Deployment Quick Start

### Local Development (Windows/Linux)

```bash
# Navigate to project root
cd /opt/lucid  # or C:\Users\...\Lucid

# 1. Initialize Redis
bash scripts/database/init_redis.sh

# 2. Initialize Elasticsearch
bash scripts/database/init_elasticsearch.sh

# 3. Verify Services
redis-cli ping  # Should return: PONG
curl http://localhost:9200/_cluster/health  # Should return: {"status":"green" or "yellow"}
```

### Docker Deployment

```bash
# Using docker-compose
docker-compose -f configs/docker/docker-compose.foundation.yml up -d redis elasticsearch

# Verify
docker ps | grep -E "redis|elasticsearch"
```

### Raspberry Pi Deployment

```bash
# SSH to Pi
ssh pickme@192.168.0.75

# Run initialization
cd /opt/lucid/staging
./scripts/database/init_redis.sh
./scripts/database/init_elasticsearch.sh
```

---

## 📁 Files Created (6 files)

```
✅ configs/database/redis/redis.conf
✅ configs/database/elasticsearch/elasticsearch.yml
✅ database/services/backup_service.py
✅ database/services/volume_service.py
✅ scripts/database/init_redis.sh (executable)
✅ scripts/database/init_elasticsearch.sh (executable)
```

---

## 🔧 Configuration Highlights

### Redis (redis.conf)
- Port: 6379
- Max Memory: 2GB
- Persistence: AOF + RDB
- Eviction: allkeys-lru
- I/O Threads: 4
- Databases: 16 (0-15)

### Elasticsearch (elasticsearch.yml)
- Port: 9200
- Cluster: lucid-elasticsearch
- Discovery: single-node
- Shards: 1
- Replicas: 0

---

## 📊 Indices Created

### 1. lucid_sessions
- session_id (keyword)
- user_id (keyword)
- status (keyword)
- merkle_root (keyword)
- created_at (date)
- Refresh: 5s

### 2. lucid_blocks
- block_id (keyword)
- block_height (long)
- block_hash (keyword)
- merkle_root (keyword)
- timestamp (date)
- Refresh: 10s

### 3. lucid_users
- user_id (keyword)
- email (text + keyword)
- tron_address (keyword)
- roles (keyword)
- status (keyword)
- Refresh: 30s

---

## 🔍 Validation Commands

```bash
# Redis
redis-cli ping
redis-cli info
redis-cli CONFIG GET maxmemory
redis-cli DBSIZE

# Elasticsearch
curl http://localhost:9200/_cluster/health?pretty
curl http://localhost:9200/_cat/indices?v
curl http://localhost:9200/_cat/nodes?v
curl http://localhost:9200/_cluster/stats?pretty
```

---

## 💾 Backup Operations

### Using backup_service.py

```python
from database.services.backup_service import get_backup_service

# Initialize
backup_service = await get_backup_service()

# Backup Redis
redis_backup = await backup_service.backup_redis()

# Backup Elasticsearch
es_backup = await backup_service.backup_elasticsearch()

# Full system backup
full_backup = await backup_service.create_full_backup()

# List backups
backups = await backup_service.list_backups()

# Cleanup old backups (>30 days)
cleanup_stats = await backup_service.cleanup_old_backups()
```

---

## 📦 Volume Management

### Using volume_service.py

```python
from database.services.volume_service import get_volume_service

# Initialize
volume_service = await get_volume_service()

# Get volume stats
stats = await volume_service.get_volume_stats()

# Health check
health = await volume_service.get_volume_health()

# Check space
has_space = await volume_service.check_volume_space("redis", required_gb=10)

# Cleanup
cleanup = await volume_service.cleanup_volume("redis", older_than_days=30)

# Monitor growth
growth = await volume_service.monitor_volume_growth("elasticsearch", 60)
```

---

## 🗄️ Redis Database Allocation

```
DB 0: Session Tokens & Rate Limiting
  - session:token:{token}
  - session:refresh:{token}
  - ratelimit:user:{user_id}
  - ratelimit:ip:{ip}

DB 1: Authentication
  - auth:user:{user_id}
  - auth:jwt:{token_hash}

DB 2: Node Metrics
  - node:metrics:{node_id}
  - node:status:{node_id}
  - node:poot:{node_id}

DB 3: Cache
  - cache:blockchain:info
  - cache:block:{height}
  - cache:session:{session_id}
```

---

## ⚠️ Production Checklist

### Redis
- [ ] Enable requirepass authentication
- [ ] Configure TLS/SSL
- [ ] Update bind address for production
- [ ] Review maxmemory policy
- [ ] Enable cluster mode (if needed)
- [ ] Setup sentinel for HA

### Elasticsearch
- [ ] Enable X-Pack security
- [ ] Configure SSL/TLS
- [ ] Setup authentication
- [ ] Configure snapshot repository
- [ ] Enable audit logging
- [ ] Review index templates
- [ ] Setup monitoring (Kibana)

---

## 🔗 Integration Points

- **Cluster 01 (API Gateway)**: Rate limiting, caching
- **Cluster 02 (Blockchain)**: Block indexing, caching
- **Cluster 03 (Sessions)**: Session search, metadata cache
- **Cluster 09 (Auth)**: Session tokens, JWT cache

---

## 📚 Additional Resources

- Redis Configuration: `configs/database/redis/redis.conf`
- Elasticsearch Configuration: `configs/database/elasticsearch/elasticsearch.yml`
- Step 3 Summary: `plan/API_plans/00-master-architecture/STEP_03_COMPLETION_SUMMARY.md`
- Build Guide: `plan/API_plans/00-master-architecture/13-BUILD_REQUIREMENTS_GUIDE.md`

---

## 🆘 Troubleshooting

### Redis won't start
```bash
# Check logs
tail -f /var/log/redis/redis.log

# Check configuration
redis-server /path/to/redis.conf --test-memory 1

# Verify port
netstat -tuln | grep 6379
```

### Elasticsearch won't start
```bash
# Check logs
tail -f /var/log/elasticsearch/lucid-elasticsearch.log

# Check Java version
java -version  # Should be Java 17+

# Verify memory settings
cat /proc/meminfo | grep -i mem
```

### Health check fails
```bash
# Redis
redis-cli --raw INFO replication

# Elasticsearch
curl -X GET "localhost:9200/_cat/health?v"
curl -X GET "localhost:9200/_nodes/stats"
```

---

**Status**: ✅ COMPLETE  
**Next Step**: Step 4 - Authentication Service Core  
**Last Updated**: 2025-10-14

