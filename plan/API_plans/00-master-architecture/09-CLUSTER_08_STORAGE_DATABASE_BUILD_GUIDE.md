# Cluster 08: Storage Database - Detailed Build Guide

## Document Control

| Attribute | Value |
|-----------|-------|
| Cluster ID | 08-STORAGE-DATABASE |
| Build Phase | Phase 1 (Weeks 1-2) |
| Parallel Track | Track A |
| Version | 1.0.0 |

---

## Cluster Overview

### Services (Port 8088)
Database management and storage infrastructure

### Key Components
- MongoDB (primary database)
- Redis (caching)
- Elasticsearch (search)
- Backup management
- Volume management

### Dependencies
**None** - Foundation cluster, no dependencies

---

## MVP Files (50 files, ~7,000 lines)

### Database Management API (15 files, ~2,000 lines)
1. `storage/database/api/database_health.py` (200) - Health checks
2. `storage/database/api/database_stats.py` (220) - Statistics
3. `storage/database/api/collections.py` (250) - Collection mgmt
4. `storage/database/api/indexes.py` (200) - Index mgmt
5. `storage/database/api/backups.py` (300) - Backup operations
6. `storage/database/api/cache.py` (250) - Cache mgmt
7. `storage/database/api/volumes.py` (280) - Volume mgmt
8. `storage/database/api/search.py` (250) - Search operations

### Data Models (10 files, ~1,500 lines)
9. `storage/database/models/user.py` (200) - User model
10. `storage/database/models/session.py` (220) - Session model
11. `storage/database/models/block.py` (200) - Block model
12. `storage/database/models/transaction.py` (180) - Transaction model
13. `storage/database/models/trust_policy.py` (150) - Trust policy
14. `storage/database/models/wallet.py` (180) - Wallet model
15. `storage/database/schemas/common.py` (200) - Common schemas

### Services (10 files, ~2,000 lines)
16. `storage/database/services/mongodb_service.py` (350) - MongoDB ops
17. `storage/database/services/redis_service.py` (280) - Redis ops
18. `storage/database/services/elasticsearch_service.py` (300) - ES ops
19. `storage/database/services/backup_service.py` (350) - Backups
20. `storage/database/services/volume_service.py` (280) - Volumes

### Configuration (15 files, ~1,500 lines)
21. `configs/database/mongodb/mongod.conf` (200) - MongoDB config
22. `configs/database/redis/redis.conf` (150) - Redis config
23. `configs/database/elasticsearch/elasticsearch.yml` (180) - ES config
24. `scripts/database/init_mongodb_schema.js` (300) - Schema init
25. `scripts/database/create_indexes.js` (250) - Index creation
26. Dockerfiles, docker-compose (420)

---

## Build Sequence (10 days)

### Days 1-3: Database Setup
- Install and configure MongoDB
- Setup replica set
- Initialize schemas and collections
- Create indexes

### Days 4-5: Redis & Elasticsearch
- Setup Redis cluster
- Configure Elasticsearch
- Create search indices

### Days 6-7: API Implementation
- Build database management APIs
- Implement backup operations
- Add cache management

### Days 8-9: Services & Integration
- Implement service layer
- Test CRUD operations
- Performance testing

### Day 10: Container & Documentation
- Create Docker containers
- Write deployment docs
- Final testing

---

## Key Implementations

### MongoDB Service
```python
# storage/database/services/mongodb_service.py (350 lines)
from motor.motor_asyncio import AsyncIOMotorClient

class MongoDBService:
    def __init__(self, uri: str):
        self.client = AsyncIOMotorClient(uri)
        self.db = self.client.lucid
        
    async def create_indexes(self):
        # Create indexes for all collections
        await self.db.users.create_index([("email", 1)], unique=True)
        await self.db.sessions.create_index([("user_id", 1)])
        await self.db.blocks.create_index([("height", 1)], unique=True)
        
    async def health_check(self) -> bool:
        # Check MongoDB connection
        await self.client.admin.command('ping')
```

### Redis Service
```python
# storage/database/services/redis_service.py (280 lines)
import redis.asyncio as redis

class RedisService:
    def __init__(self, uri: str):
        self.client = redis.from_url(uri)
        
    async def cache_set(self, key: str, value: str, ttl: int):
        await self.client.setex(key, ttl, value)
        
    async def cache_get(self, key: str) -> str:
        return await self.client.get(key)
```

### Backup Service
```python
# storage/database/services/backup_service.py (350 lines)
import subprocess
from datetime import datetime

class BackupService:
    async def create_backup(self, collections: list):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f"/backups/backup_{timestamp}"
        
        # Use mongodump
        subprocess.run([
            "mongodump",
            "--uri", self.mongodb_uri,
            "--out", backup_path
        ])
```

---

## Database Schemas

### Users Collection
```javascript
// scripts/database/init_mongodb_schema.js
db.createCollection("users", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["user_id", "email", "tron_address", "created_at"],
      properties: {
        user_id: { bsonType: "string" },
        email: { bsonType: "string" },
        tron_address: { bsonType: "string" },
        hardware_wallet: { bsonType: "object" },
        created_at: { bsonType: "date" }
      }
    }
  }
});

// Indexes
db.users.createIndex({ "email": 1 }, { unique: true });
db.users.createIndex({ "tron_address": 1 }, { unique: true });
```

### Sessions Collection
```javascript
db.createCollection("sessions", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["session_id", "user_id", "status"],
      properties: {
        session_id: { bsonType: "string" },
        user_id: { bsonType: "string" },
        status: { enum: ["active", "completed", "failed"] },
        chunks: { bsonType: "array" },
        merkle_root: { bsonType: "string" },
        blockchain_anchor: { bsonType: "object" }
      }
    }
  }
});

db.sessions.createIndex({ "user_id": 1 });
db.sessions.createIndex({ "status": 1 });
db.sessions.createIndex({ "created_at": -1 });
```

### Blocks Collection
```javascript
db.createCollection("blocks", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["block_id", "height", "previous_hash", "merkle_root"],
      properties: {
        block_id: { bsonType: "string" },
        height: { bsonType: "int" },
        previous_hash: { bsonType: "string" },
        merkle_root: { bsonType: "string" },
        transactions: { bsonType: "array" },
        timestamp: { bsonType: "date" }
      }
    }
  }
});

db.blocks.createIndex({ "height": 1 }, { unique: true });
db.blocks.createIndex({ "block_id": 1 }, { unique: true });
```

---

## Environment Variables
```bash
# MongoDB Configuration
MONGODB_URI=mongodb://mongodb:27017/lucid
MONGODB_REPLICA_SET=rs0
MONGODB_DATABASE=lucid

# Redis Configuration
REDIS_URI=redis://redis:6379/0
REDIS_CLUSTER_ENABLED=true

# Elasticsearch Configuration
ELASTICSEARCH_URI=http://elasticsearch:9200
ELASTICSEARCH_INDEX_PREFIX=lucid

# Backup Configuration
BACKUP_ENABLED=true
BACKUP_SCHEDULE="0 2 * * *"  # Daily at 2 AM
BACKUP_RETENTION_DAYS=30

# Volume Configuration
VOLUME_MOUNT_PATH=/data
VOLUME_SIZE_LIMIT_GB=500
```

---

## Docker Compose
```yaml
version: '3.8'
services:
  mongodb:
    image: mongo:7.0
    container_name: lucid-mongodb
    ports:
      - "27017:27017"
    command: ["mongod", "--replSet", "rs0", "--bind_ip_all"]
    volumes:
      - mongodb_data:/data/db
      - ./scripts/database/init_mongodb_schema.js:/docker-entrypoint-initdb.d/init.js
    networks:
      - lucid-network

  redis:
    image: redis:7.0
    container_name: lucid-redis
    ports:
      - "6379:6379"
    command: ["redis-server", "/etc/redis/redis.conf"]
    volumes:
      - redis_data:/data
      - ./configs/database/redis/redis.conf:/etc/redis/redis.conf
    networks:
      - lucid-network

  elasticsearch:
    image: elasticsearch:8.11.0
    container_name: lucid-elasticsearch
    ports:
      - "9200:9200"
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
    networks:
      - lucid-network

volumes:
  mongodb_data:
  redis_data:
  elasticsearch_data:
```

---

## Testing Strategy

### Database Tests
- Schema validation
- Index performance
- Query optimization
- Replication

### Backup Tests
- Backup creation
- Restore operations
- Backup integrity

### Performance Tests
- Query latency: <10ms p95
- Write throughput: >1000 ops/sec
- Cache hit rate: >80%

---

## Success Criteria

- [ ] MongoDB replica set operational
- [ ] All schemas and indexes created
- [ ] Redis cluster caching working
- [ ] Elasticsearch indices created
- [ ] Backup system operational
- [ ] All database APIs responding
- [ ] Performance benchmarks met
- [ ] Health checks passing

---

**Build Time**: 10 days (2 developers)  
**Critical Path**: YES - Required by all other clusters

