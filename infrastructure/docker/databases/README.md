# LUCID Database Services - Infrastructure

This directory contains the complete database infrastructure for the Lucid project, including MongoDB 7 with replica set support, backup services, monitoring, and health checks. All services are built using distroless containers for enhanced security and minimal attack surface.

## 🏗️ Architecture

The database infrastructure follows the LUCID-STRICT Layer 0 Core Infrastructure specifications:

- **MongoDB 7**: Primary database with replica set support
- **Database Backup**: Automated backup and restore services
- **Database Monitoring**: Real-time monitoring and health checks
- **Database Migration**: Schema migration and versioning
- **Health Checks**: Comprehensive health monitoring

## 🔧 Separation of Concerns

This directory structure maintains clear separation between:
- **`infrastructure/docker/databases/`**: Docker build artifacts, Dockerfiles, and configuration files
- **`database/services/`**: Python source code for database services
- **`database/`**: Database initialization scripts and shared database components

## 📁 Directory Structure

```
infrastructure/docker/databases/
├── build-env.sh                    # Environment generation script
├── Dockerfile.mongodb              # MongoDB 7 distroless container
├── Dockerfile.database-backup      # Backup service container
├── Dockerfile.database-monitoring  # Monitoring service container
├── mongod.conf                     # MongoDB configuration
├── mongodb-init.js                 # MongoDB initialization script
├── mongodb-health.sh               # Health check script
└── env/                           # Generated environment files
    ├── mongodb.env
    ├── mongodb-init.env
    ├── database-backup.env
    ├── database-restore.env
    ├── database-monitoring.env
    └── database-migration.env

database/services/                  # Python source code (separate from Docker build context)
├── backup/
│   ├── main.py                     # Database backup service
│   └── requirements-backup.txt     # Python dependencies for backup service
├── monitoring/
│   ├── main.py                     # Database monitoring service
│   └── requirements-monitoring.txt # Python dependencies for monitoring service
└── migration/
    └── (future migration service files)
```

## 🚀 Quick Start

### 1. Generate Environment Files

```bash
cd infrastructure/docker/databases
chmod +x build-env.sh
./build-env.sh
```

### 2. Build Database Services

```bash
# Build MongoDB 7 container
docker build -f Dockerfile.mongodb -t pickme/lucid:mongodb .

# Build backup service (copies from database/services/backup/)
docker build -f Dockerfile.database-backup -t pickme/lucid:database-backup .

# Build monitoring service (copies from database/services/monitoring/)
docker build -f Dockerfile.database-monitoring -t pickme/lucid:database-monitoring .
```

### 3. Run Database Services

```bash
# Start MongoDB with replica set
docker run -d \
  --name lucid_mongo \
  --network lucid_core_net \
  -p 27017:27017 \
  -v mongo_data:/data/db \
  -v mongo_config:/data/configdb \
  pickme/lucid:mongodb

# Start backup service
docker run -d \
  --name lucid_backup \
  --network lucid_core_net \
  -p 8089:8089 \
  -v backup_data:/data/backups \
  pickme/lucid:database-backup

# Start monitoring service
docker run -d \
  --name lucid_monitoring \
  --network lucid_core_net \
  -p 8091:8091 \
  -p 9216:9216 \
  pickme/lucid:database-monitoring
```

## 🔧 Configuration

### MongoDB Configuration

The MongoDB service is configured with:

- **Replica Set**: `rs0` for high availability
- **Authentication**: Enabled with `lucid` user
- **Storage**: WiredTiger with optimized cache size for Pi
- **Security**: SSL support, authentication required
- **Performance**: Optimized for Pi 5 hardware

### Environment Variables

Key environment variables for each service:

#### MongoDB
- `MONGO_INITDB_ROOT_USERNAME`: Admin username (default: lucid)
- `MONGO_INITDB_ROOT_PASSWORD`: Admin password (default: lucid)
- `MONGO_REPLICA_SET`: Replica set name (default: rs0)
- `MONGO_OPLOG_SIZE`: Oplog size in MB (default: 128)

#### Backup Service
- `BACKUP_SCHEDULE`: Cron schedule for backups (default: "0 2 * * *")
- `BACKUP_RETENTION_DAYS`: Backup retention period (default: 30)
- `BACKUP_COMPRESSION`: Enable compression (default: true)
- `BACKUP_ENCRYPTION`: Enable encryption (default: true)

#### Monitoring Service
- `MONITORING_INTERVAL`: Monitoring interval in seconds (default: 30)
- `METRICS_PORT`: Prometheus metrics port (default: 9216)
- `PROMETHEUS_ENABLED`: Enable Prometheus metrics (default: true)

## 📊 Monitoring

### Health Checks

All services include comprehensive health checks:

- **MongoDB**: Connectivity, authentication, replica set status
- **Backup Service**: Service status, backup job status
- **Monitoring Service**: Database connectivity, metrics collection

### Metrics

The monitoring service exposes Prometheus metrics:

- `mongodb_connections`: Number of database connections
- `mongodb_operations_total`: Total database operations
- `mongodb_query_duration_seconds`: Query duration histogram
- `mongodb_collection_size_bytes`: Collection sizes
- `database_health_status`: Database health status

### API Endpoints

#### Backup Service (Port 8089)
- `GET /health`: Health check
- `POST /backup`: Create backup job
- `GET /backup/{job_id}`: Get backup status
- `GET /backups`: List all backups
- `DELETE /backup/{job_id}`: Cancel backup job

#### Monitoring Service (Port 8091)
- `GET /health`: Health check
- `GET /metrics`: Prometheus metrics
- `POST /monitor`: Start monitoring
- `GET /stats`: Get current statistics
- `GET /alerts`: Get current alerts

## 🔒 Security

### Distroless Containers

All services use distroless base images for:

- **Minimal Attack Surface**: No shell, package manager, or unnecessary tools
- **Reduced Vulnerabilities**: Fewer components to exploit
- **Immutable Runtime**: Cannot be modified at runtime
- **Security Scanning**: Easier to scan for vulnerabilities

### Security Features

- **Authentication**: MongoDB authentication enabled
- **Encryption**: Backup encryption support
- **Network Security**: Internal network communication only
- **User Isolation**: Non-root user execution
- **Resource Limits**: CPU and memory limits configured

## 🐳 Docker Compose Integration

The database services integrate with the main Lucid Docker Compose stack:

```yaml
# Add to docker-compose.core.yaml
services:
  lucid_mongo:
    image: pickme/lucid:mongodb
    container_name: lucid_mongo
    # ... configuration

  database-backup:
    image: pickme/lucid:database-backup
    container_name: lucid_backup
    # ... configuration

  database-monitoring:
    image: pickme/lucid:database-monitoring
    container_name: lucid_monitoring
    # ... configuration
```

## 🔄 Backup and Restore

### Automated Backups

The backup service provides:

- **Scheduled Backups**: Daily backups at 2 AM
- **Compression**: Zstandard compression for efficiency
- **Encryption**: AES-256-GCM encryption for security
- **Retention**: Configurable retention periods
- **Verification**: Backup integrity verification

### Manual Backups

```bash
# Create immediate backup
curl -X POST http://localhost:8089/backup \
  -H "Content-Type: application/json" \
  -d '{
    "database": "lucid",
    "collections": ["sessions", "authentication"],
    "compression": true,
    "encryption": true
  }'

# Check backup status
curl http://localhost:8089/backup/backup_20250109_020000
```

## 🚨 Troubleshooting

### Common Issues

1. **MongoDB Connection Failed**
   - Check network connectivity
   - Verify authentication credentials
   - Ensure replica set is initialized

2. **Backup Service Not Starting**
   - Check MongoDB connectivity
   - Verify backup directory permissions
   - Check environment variables

3. **Monitoring Service Issues**
   - Verify MongoDB connection
   - Check Prometheus metrics endpoint
   - Review monitoring logs

### Logs

View service logs:

```bash
# MongoDB logs
docker logs lucid_mongo

# Backup service logs
docker logs lucid_backup

# Monitoring service logs
docker logs lucid_monitoring
```

## 📈 Performance Optimization

### Pi 5 Optimization

The database services are optimized for Raspberry Pi 5:

- **Memory Limits**: Optimized cache sizes
- **CPU Limits**: Resource constraints for Pi hardware
- **Storage**: Efficient storage engine configuration
- **Network**: Optimized network settings

### Scaling

For production deployments:

- **Replica Set**: Add more MongoDB nodes
- **Sharding**: Implement MongoDB sharding
- **Load Balancing**: Use MongoDB load balancer
- **Monitoring**: Scale monitoring service

## 🔗 Integration

### API Integration

The database services integrate with:

- **API Gateway**: Database connectivity
- **Authentication Service**: User data storage
- **Blockchain Services**: Transaction data
- **Session Pipeline**: Session data storage

### External Tools

Compatible with:

- **MongoDB Compass**: Database management
- **Prometheus**: Metrics collection
- **Grafana**: Monitoring dashboards
- **MongoDB Tools**: Backup and restore utilities

## 📝 Development

### Local Development

For local development:

```bash
# Start development environment
docker-compose -f infrastructure/compose/lucid-dev.yaml up -d

# Run tests
pytest tests/database/

# Check health
curl http://localhost:27017/health
```

### Contributing

When contributing to database services:

1. Follow LUCID-STRICT standards
2. Use distroless containers
3. Include comprehensive tests
4. Update documentation
5. Follow security best practices

## 📚 References

- [MongoDB 7 Documentation](https://docs.mongodb.com/v7.0/)
- [Distroless Containers](https://github.com/GoogleContainerTools/distroless)
- [Prometheus Monitoring](https://prometheus.io/docs/)
- [LUCID-STRICT Standards](docs/guides/LUCID_STRICT.md)
