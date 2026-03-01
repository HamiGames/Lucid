# Lucid System Troubleshooting Guide

## Document Control

| Attribute | Value |
|-----------|-------|
| Document ID | LUCID-TROUBLESHOOT-001 |
| Version | 1.0.0 |
| Status | ACTIVE |
| Last Updated | 2025-01-14 |
| Based On | Master Build Plan v1.0.0 |

---

## Overview

This comprehensive troubleshooting guide covers common issues, diagnostic procedures, and solutions for the Lucid blockchain system across all 10 service clusters. The guide follows a systematic approach to identify and resolve problems quickly.

### Troubleshooting Methodology

1. **Identify the Problem**: Gather symptoms and error messages
2. **Check System Health**: Verify service status and connectivity
3. **Analyze Logs**: Review relevant log files for errors
4. **Apply Solutions**: Implement fixes based on problem type
5. **Verify Resolution**: Confirm the issue is resolved
6. **Document**: Record the solution for future reference

---

## Foundation Services Troubleshooting

### MongoDB Issues

#### Problem: MongoDB Connection Failures

**Symptoms:**
- Services cannot connect to MongoDB
- Error: "MongoDB connection failed"
- Authentication errors

**Diagnostic Steps:**
```bash
# Check MongoDB container status
docker ps | grep lucid-mongodb

# Check MongoDB logs
docker logs lucid-mongodb --tail 50

# Test MongoDB connectivity
docker exec lucid-mongodb mongosh --eval "db.runCommand({ping: 1})"

# Check replica set status
docker exec lucid-mongodb mongosh --eval "rs.status()"

# Verify authentication
docker exec lucid-mongodb mongosh --eval "db.runCommand({connectionStatus: 1})"
```

**Solutions:**
```bash
# Restart MongoDB service
docker-compose restart lucid-mongodb

# Initialize replica set if needed
docker exec lucid-mongodb mongosh --eval "rs.initiate()"

# Reset MongoDB password
docker exec lucid-mongodb mongosh --eval "
use admin;
db.changeUserPassword('lucid', 'new-password');
"

# Check MongoDB configuration
docker exec lucid-mongodb cat /etc/mongod.conf
```

#### Problem: MongoDB Performance Issues

**Symptoms:**
- Slow query responses
- High memory usage
- Connection timeouts

**Diagnostic Steps:**
```bash
# Check MongoDB performance metrics
docker exec lucid-mongodb mongosh --eval "db.runCommand({serverStatus: 1}).metrics"

# Check current operations
docker exec lucid-mongodb mongosh --eval "db.currentOp()"

# Check database stats
docker exec lucid-mongodb mongosh --eval "db.stats()"

# Check index usage
docker exec lucid-mongodb mongosh --eval "db.users.getIndexes()"
```

**Solutions:**
```bash
# Optimize MongoDB configuration
docker exec lucid-mongodb mongosh --eval "
db.runCommand({compact: 'users'});
db.runCommand({compact: 'sessions'});
"

# Add missing indexes
docker exec lucid-mongodb mongosh --eval "
db.users.createIndex({email: 1});
db.sessions.createIndex({user_id: 1, created_at: 1});
"

# Increase MongoDB memory limits
docker-compose down
# Edit docker-compose.yml to increase memory limits
docker-compose up -d
```

### Redis Issues

#### Problem: Redis Connection Failures

**Symptoms:**
- Rate limiting not working
- Cache misses
- Redis connection errors

**Diagnostic Steps:**
```bash
# Check Redis container status
docker ps | grep lucid-redis

# Check Redis logs
docker logs lucid-redis --tail 50

# Test Redis connectivity
docker exec lucid-redis redis-cli ping

# Check Redis info
docker exec lucid-redis redis-cli info

# Check Redis memory usage
docker exec lucid-redis redis-cli info memory
```

**Solutions:**
```bash
# Restart Redis service
docker-compose restart lucid-redis

# Clear Redis cache if needed
docker exec lucid-redis redis-cli flushall

# Check Redis configuration
docker exec lucid-redis cat /usr/local/etc/redis/redis.conf

# Optimize Redis memory
docker exec lucid-redis redis-cli config set maxmemory 1gb
docker exec lucid-redis redis-cli config set maxmemory-policy allkeys-lru
```

#### Problem: Redis Memory Issues

**Symptoms:**
- Redis out of memory errors
- Slow Redis operations
- High memory usage

**Diagnostic Steps:**
```bash
# Check Redis memory usage
docker exec lucid-redis redis-cli info memory | grep used_memory

# Check Redis keys
docker exec lucid-redis redis-cli dbsize

# Check key expiration
docker exec lucid-redis redis-cli info stats | grep expired
```

**Solutions:**
```bash
# Set Redis memory limits
docker exec lucid-redis redis-cli config set maxmemory 2gb
docker exec lucid-redis redis-cli config set maxmemory-policy allkeys-lru

# Clear expired keys
docker exec lucid-redis redis-cli --scan --pattern "*" | xargs docker exec lucid-redis redis-cli del

# Restart Redis with new configuration
docker-compose restart lucid-redis
```

### Elasticsearch Issues

#### Problem: Elasticsearch Cluster Health Issues

**Symptoms:**
- Search functionality not working
- Elasticsearch cluster red status
- Index creation failures

**Diagnostic Steps:**
```bash
# Check Elasticsearch container status
docker ps | grep lucid-elasticsearch

# Check cluster health
curl -X GET "localhost:9200/_cluster/health?pretty"

# Check node status
curl -X GET "localhost:9200/_nodes/stats?pretty"

# Check indices
curl -X GET "localhost:9200/_cat/indices?v"
```

**Solutions:**
```bash
# Restart Elasticsearch service
docker-compose restart lucid-elasticsearch

# Check Elasticsearch logs
docker logs lucid-elasticsearch --tail 100

# Recreate problematic indices
curl -X DELETE "localhost:9200/problematic_index"
curl -X PUT "localhost:9200/problematic_index" -H 'Content-Type: application/json' -d'
{
  "mappings": {
    "properties": {
      "field": {"type": "text"}
    }
  }
}
'
```

---

## Authentication Service Troubleshooting

### JWT Token Issues

#### Problem: JWT Token Validation Failures

**Symptoms:**
- "Invalid token" errors
- Authentication failures
- Token expiration issues

**Diagnostic Steps:**
```bash
# Check auth service logs
docker logs lucid-auth-service --tail 50

# Test JWT token validation
curl -H "Authorization: Bearer <token>" http://localhost:8089/verify

# Check JWT secret configuration
docker exec lucid-auth-service env | grep JWT_SECRET
```

**Solutions:**
```bash
# Restart auth service
docker-compose restart lucid-auth-service

# Regenerate JWT secret
JWT_SECRET=$(openssl rand -base64 64)
docker-compose down
# Update .env file with new JWT_SECRET
docker-compose up -d

# Check token expiration settings
docker exec lucid-auth-service cat /app/config/auth.json
```

#### Problem: Hardware Wallet Connection Issues

**Symptoms:**
- Hardware wallet not detected
- Ledger/Trezor connection failures
- Wallet signature verification errors

**Diagnostic Steps:**
```bash
# Check hardware wallet service logs
docker logs lucid-auth-service | grep -i "hardware\|ledger\|trezor"

# Test hardware wallet detection
docker exec lucid-auth-service python -c "
from auth.hardware_wallet import HardwareWalletManager
manager = HardwareWalletManager()
print(manager.list_devices())
"

# Check USB device permissions
docker exec lucid-auth-service lsusb
```

**Solutions:**
```bash
# Restart auth service with USB access
docker-compose down
docker-compose up -d --privileged

# Check hardware wallet drivers
docker exec lucid-auth-service pip list | grep -E "(ledger|trezor|keepkey)"

# Update hardware wallet configuration
docker exec lucid-auth-service cat /app/config/hardware_wallet.json
```

---

## API Gateway Troubleshooting

### Rate Limiting Issues

#### Problem: Rate Limiting Not Working

**Symptoms:**
- No rate limit enforcement
- Rate limit errors when not expected
- Inconsistent rate limiting behavior

**Diagnostic Steps:**
```bash
# Check API Gateway logs
docker logs lucid-api-gateway --tail 50

# Test rate limiting
for i in {1..110}; do curl http://localhost:8080/api/v1/test; done

# Check Redis rate limit data
docker exec lucid-redis redis-cli keys "*rate*"

# Check rate limiter service
docker logs lucid-rate-limiter --tail 50
```

**Solutions:**
```bash
# Restart rate limiter service
docker-compose restart lucid-rate-limiter

# Clear rate limit data
docker exec lucid-redis redis-cli flushdb

# Check rate limiter configuration
docker exec lucid-rate-limiter cat /app/config/rate_limit.json

# Verify Redis connectivity
docker exec lucid-api-gateway python -c "
import redis
r = redis.Redis(host='lucid-redis', port=6379, password='${REDIS_PASSWORD}')
print(r.ping())
"
```

### CORS Issues

#### Problem: CORS Errors

**Symptoms:**
- Browser CORS errors
- Preflight request failures
- Cross-origin request blocked

**Diagnostic Steps:**
```bash
# Check CORS configuration
docker exec lucid-api-gateway cat /app/config/cors.json

# Test CORS headers
curl -H "Origin: http://localhost:3000" \
     -H "Access-Control-Request-Method: GET" \
     -H "Access-Control-Request-Headers: X-Requested-With" \
     -X OPTIONS http://localhost:8080/api/v1/test

# Check API Gateway logs for CORS errors
docker logs lucid-api-gateway | grep -i cors
```

**Solutions:**
```bash
# Update CORS configuration
docker exec lucid-api-gateway cat > /app/config/cors.json << EOF
{
  "allow_origins": ["http://localhost:3000", "https://lucid.onion"],
  "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
  "allow_headers": ["*"],
  "allow_credentials": true
}
EOF

# Restart API Gateway
docker-compose restart lucid-api-gateway

# Test CORS configuration
curl -H "Origin: http://localhost:3000" \
     -H "Access-Control-Request-Method: GET" \
     -H "Access-Control-Request-Headers: X-Requested-With" \
     -X OPTIONS http://localhost:8080/api/v1/test
```

---

## Blockchain Core Troubleshooting

### Consensus Issues

#### Problem: Consensus Failures

**Symptoms:**
- Blocks not being created
- Consensus round failures
- PoOT validation errors

**Diagnostic Steps:**
```bash
# Check blockchain engine logs
docker logs lucid-blockchain-engine --tail 50

# Check consensus status
curl http://localhost:8084/api/v1/consensus/status

# Check block creation
curl http://localhost:8084/api/v1/blocks/latest

# Check PoOT scores
curl http://localhost:8084/api/v1/consensus/poot-scores
```

**Solutions:**
```bash
# Restart blockchain engine
docker-compose restart lucid-blockchain-engine

# Check consensus configuration
docker exec lucid-blockchain-engine cat /app/config/consensus.json

# Reset consensus state if needed
docker exec lucid-mongodb mongosh --eval "
use lucid_blocks;
db.consensus_rounds.deleteMany({});
db.consensus_votes.deleteMany({});
"

# Check node participation
curl http://localhost:8084/api/v1/consensus/participants
```

### Session Anchoring Issues

#### Problem: Session Anchoring Failures

**Symptoms:**
- Sessions not being anchored
- Merkle tree construction failures
- Anchoring service errors

**Diagnostic Steps:**
```bash
# Check session anchoring logs
docker logs lucid-session-anchoring --tail 50

# Check anchoring status
curl http://localhost:8085/api/v1/anchoring/status

# Check Merkle tree construction
curl http://localhost:8085/api/v1/anchoring/merkle-trees

# Check blockchain connectivity
curl http://localhost:8085/api/v1/anchoring/blockchain-status
```

**Solutions:**
```bash
# Restart session anchoring service
docker-compose restart lucid-session-anchoring

# Check anchoring configuration
docker exec lucid-session-anchoring cat /app/config/anchoring.json

# Verify blockchain engine connectivity
docker exec lucid-session-anchoring curl http://lucid-blockchain-engine:8084/health

# Check Merkle tree storage
docker exec lucid-session-anchoring ls -la /data/merkle/
```

---

## Session Management Troubleshooting

### Session Pipeline Issues

#### Problem: Session Pipeline Failures

**Symptoms:**
- Sessions not being processed
- Pipeline state machine errors
- Session recording failures

**Diagnostic Steps:**
```bash
# Check session pipeline logs
docker logs lucid-session-pipeline --tail 50

# Check pipeline status
curl http://localhost:8083/api/v1/pipeline/status

# Check session states
curl http://localhost:8083/api/v1/pipeline/sessions

# Check pipeline configuration
docker exec lucid-session-pipeline cat /app/config/pipeline.json
```

**Solutions:**
```bash
# Restart session pipeline
docker-compose restart lucid-session-pipeline

# Reset pipeline state if needed
docker exec lucid-mongodb mongosh --eval "
use lucid;
db.sessions.updateMany({}, {\$set: {pipeline_state: 'initialized'}});
"

# Check pipeline dependencies
docker exec lucid-session-pipeline curl http://lucid-api-gateway:8080/health
```

### Chunk Processing Issues

#### Problem: Chunk Processing Failures

**Symptoms:**
- Chunks not being processed
- Encryption failures
- Merkle tree construction errors

**Diagnostic Steps:**
```bash
# Check chunk processor logs
docker logs lucid-chunk-processor --tail 50

# Check processing status
curl http://localhost:8085/api/v1/processing/status

# Check chunk queue
curl http://localhost:8085/api/v1/processing/queue

# Check encryption status
curl http://localhost:8085/api/v1/processing/encryption-status
```

**Solutions:**
```bash
# Restart chunk processor
docker-compose restart lucid-chunk-processor

# Check chunk storage
docker exec lucid-chunk-processor ls -la /data/chunks/

# Verify encryption keys
docker exec lucid-chunk-processor cat /app/config/encryption.json

# Check Merkle tree builder
docker exec lucid-chunk-processor python -c "
from chunk_processor.merkle_builder import MerkleTreeBuilder
builder = MerkleTreeBuilder()
print('Merkle tree builder initialized successfully')
"
```

---

## RDP Services Troubleshooting

### RDP Connection Issues

#### Problem: RDP Connection Failures

**Symptoms:**
- RDP connections not working
- XRDP service errors
- Port allocation failures

**Diagnostic Steps:**
```bash
# Check RDP manager logs
docker logs lucid-rdp-manager --tail 50

# Check XRDP logs
docker logs lucid-xrdp --tail 50

# Check port allocation
curl http://localhost:8090/api/v1/ports/status

# Check RDP service status
curl http://localhost:8090/api/v1/rdp/status
```

**Solutions:**
```bash
# Restart RDP services
docker-compose restart lucid-rdp-manager lucid-xrdp

# Check port configuration
docker exec lucid-rdp-manager cat /app/config/ports.json

# Verify XRDP configuration
docker exec lucid-xrdp cat /etc/xrdp/xrdp.ini

# Check port availability
netstat -tuln | grep -E "(13389|14389)"
```

### Resource Monitoring Issues

#### Problem: Resource Monitoring Failures

**Symptoms:**
- Resource metrics not being collected
- Monitoring service errors
- Performance data missing

**Diagnostic Steps:**
```bash
# Check resource monitor logs
docker logs lucid-resource-monitor --tail 50

# Check monitoring status
curl http://localhost:8093/api/v1/monitoring/status

# Check metrics collection
curl http://localhost:8093/api/v1/monitoring/metrics

# Check system resources
docker exec lucid-resource-monitor cat /proc/meminfo
```

**Solutions:**
```bash
# Restart resource monitor
docker-compose restart lucid-resource-monitor

# Check monitoring configuration
docker exec lucid-resource-monitor cat /app/config/monitoring.json

# Verify system access
docker exec lucid-resource-monitor ls -la /host/proc/
docker exec lucid-resource-monitor ls -la /host/sys/

# Check metrics storage
docker exec lucid-resource-monitor ls -la /data/metrics/
```

---

## Node Management Troubleshooting

### Node Registration Issues

#### Problem: Node Registration Failures

**Symptoms:**
- Nodes not registering
- Registration service errors
- Node status not updating

**Diagnostic Steps:**
```bash
# Check node management logs
docker logs lucid-node-management --tail 50

# Check node registration status
curl http://localhost:8095/api/v1/nodes/status

# Check registered nodes
curl http://localhost:8095/api/v1/nodes/list

# Check node health
curl http://localhost:8095/api/v1/nodes/health
```

**Solutions:**
```bash
# Restart node management service
docker-compose restart lucid-node-management

# Check node configuration
docker exec lucid-node-management cat /app/config/nodes.json

# Clear node registration data if needed
docker exec lucid-mongodb mongosh --eval "
use lucid;
db.nodes.deleteMany({});
"

# Check node connectivity
docker exec lucid-node-management curl http://lucid-api-gateway:8080/health
```

### PoOT Calculation Issues

#### Problem: PoOT Score Calculation Failures

**Symptoms:**
- PoOT scores not being calculated
- Score calculation errors
- Invalid PoOT scores

**Diagnostic Steps:**
```bash
# Check PoOT calculation logs
docker logs lucid-node-management | grep -i poot

# Check PoOT scores
curl http://localhost:8095/api/v1/poot/scores

# Check PoOT configuration
docker exec lucid-node-management cat /app/config/poot.json

# Check node participation data
curl http://localhost:8095/api/v1/poot/participation
```

**Solutions:**
```bash
# Restart node management service
docker-compose restart lucid-node-management

# Check PoOT algorithm
docker exec lucid-node-management python -c "
from node.poot.poot_calculator import PoOTCalculator
calculator = PoOTCalculator()
print('PoOT calculator initialized successfully')
"

# Reset PoOT scores if needed
docker exec lucid-mongodb mongosh --eval "
use lucid;
db.poot_scores.deleteMany({});
"
```

---

## Admin Interface Troubleshooting

### Admin Dashboard Issues

#### Problem: Admin Dashboard Not Loading

**Symptoms:**
- Admin interface not accessible
- Dashboard errors
- UI components not loading

**Diagnostic Steps:**
```bash
# Check admin interface logs
docker logs lucid-admin-interface --tail 50

# Check admin service status
curl http://localhost:8083/health

# Check admin configuration
docker exec lucid-admin-interface cat /app/config/admin.json

# Check UI assets
docker exec lucid-admin-interface ls -la /app/static/
```

**Solutions:**
```bash
# Restart admin interface
docker-compose restart lucid-admin-interface

# Check admin interface dependencies
docker exec lucid-admin-interface curl http://lucid-api-gateway:8080/health

# Verify admin permissions
curl -H "Authorization: Bearer <admin-token>" http://localhost:8083/api/v1/admin/permissions

# Check admin UI assets
docker exec lucid-admin-interface find /app/static -name "*.js" -o -name "*.css"
```

### RBAC Issues

#### Problem: RBAC Permission Errors

**Symptoms:**
- Permission denied errors
- Role assignment failures
- Access control not working

**Diagnostic Steps:**
```bash
# Check RBAC logs
docker logs lucid-admin-interface | grep -i rbac

# Check user roles
curl http://localhost:8083/api/v1/admin/users/roles

# Check permission matrix
curl http://localhost:8083/api/v1/admin/permissions/matrix

# Check role assignments
curl http://localhost:8083/api/v1/admin/roles/assignments
```

**Solutions:**
```bash
# Restart admin interface
docker-compose restart lucid-admin-interface

# Check RBAC configuration
docker exec lucid-admin-interface cat /app/config/rbac.json

# Reset RBAC data if needed
docker exec lucid-mongodb mongosh --eval "
use lucid;
db.user_roles.deleteMany({});
db.role_permissions.deleteMany({});
"

# Recreate default roles
curl -X POST http://localhost:8083/api/v1/admin/roles/create-default
```

---

## TRON Payment Troubleshooting

### TRON Network Issues

#### Problem: TRON Network Connection Failures

**Symptoms:**
- TRON client connection errors
- Network timeout errors
- API endpoint failures

**Diagnostic Steps:**
```bash
# Check TRON client logs
docker logs lucid-tron-client --tail 50

# Check TRON network status
curl http://localhost:8085/api/v1/tron/network-status

# Check TRON API connectivity
curl http://localhost:8085/api/v1/tron/connectivity

# Check TRON configuration
docker exec lucid-tron-client cat /app/config/tron.json
```

**Solutions:**
```bash
# Restart TRON client
docker-compose restart lucid-tron-client

# Check TRON network configuration
docker exec lucid-tron-client cat /app/config/network.json

# Verify TRON API endpoints
docker exec lucid-tron-client curl https://api.trongrid.io/wallet/getnowblock

# Check TRON network isolation
docker network ls | grep lucid-tron-network
```

### Wallet Management Issues

#### Problem: Wallet Management Failures

**Symptoms:**
- Wallet creation failures
- Wallet access errors
- Private key management issues

**Diagnostic Steps:**
```bash
# Check wallet manager logs
docker logs lucid-wallet-manager --tail 50

# Check wallet status
curl http://localhost:8087/api/v1/wallets/status

# Check wallet storage
docker exec lucid-wallet-manager ls -la /data/wallets/

# Check wallet configuration
docker exec lucid-wallet-manager cat /app/config/wallet.json
```

**Solutions:**
```bash
# Restart wallet manager
docker-compose restart lucid-wallet-manager

# Check wallet storage permissions
docker exec lucid-wallet-manager ls -la /data/wallets/

# Verify wallet encryption
docker exec lucid-wallet-manager python -c "
from wallet_manager.encryption import WalletEncryption
encryption = WalletEncryption()
print('Wallet encryption initialized successfully')
"

# Check wallet backup
docker exec lucid-wallet-manager ls -la /data/wallets/backup/
```

### USDT Transaction Issues

#### Problem: USDT Transaction Failures

**Symptoms:**
- USDT transfers failing
- Transaction confirmation errors
- USDT balance issues

**Diagnostic Steps:**
```bash
# Check USDT manager logs
docker logs lucid-usdt-manager --tail 50

# Check USDT transaction status
curl http://localhost:8088/api/v1/usdt/transactions/status

# Check USDT balance
curl http://localhost:8088/api/v1/usdt/balance

# Check USDT configuration
docker exec lucid-usdt-manager cat /app/config/usdt.json
```

**Solutions:**
```bash
# Restart USDT manager
docker-compose restart lucid-usdt-manager

# Check USDT contract address
docker exec lucid-usdt-manager cat /app/config/contract.json

# Verify USDT contract interaction
docker exec lucid-usdt-manager python -c "
from usdt_manager.contract import USDTContract
contract = USDTContract()
print('USDT contract initialized successfully')
"

# Check USDT transaction history
curl http://localhost:8088/api/v1/usdt/transactions/history
```

---

## System-Wide Troubleshooting

### Network Connectivity Issues

#### Problem: Inter-Service Communication Failures

**Symptoms:**
- Services cannot communicate
- Network timeouts
- DNS resolution failures

**Diagnostic Steps:**
```bash
# Check network connectivity
docker network ls | grep lucid

# Test inter-service communication
docker exec lucid-api-gateway ping lucid-mongodb
docker exec lucid-api-gateway ping lucid-redis

# Check DNS resolution
docker exec lucid-api-gateway nslookup lucid-mongodb
docker exec lucid-api-gateway nslookup lucid-redis

# Check network configuration
docker network inspect lucid-network
```

**Solutions:**
```bash
# Restart network
docker network rm lucid-network
docker network create lucid-network --subnet=172.20.0.0/16

# Restart all services
docker-compose down
docker-compose up -d

# Check network connectivity
docker exec lucid-api-gateway curl http://lucid-mongodb:27017
docker exec lucid-api-gateway curl http://lucid-redis:6379
```

### Performance Issues

#### Problem: System Performance Degradation

**Symptoms:**
- Slow response times
- High CPU usage
- Memory leaks

**Diagnostic Steps:**
```bash
# Check system resources
docker stats --no-stream

# Check service performance
curl http://localhost:8080/health
curl http://localhost:8084/health

# Check database performance
docker exec lucid-mongodb mongosh --eval "db.runCommand({serverStatus: 1}).metrics"

# Check Redis performance
docker exec lucid-redis redis-cli info stats
```

**Solutions:**
```bash
# Optimize container resources
docker-compose down
# Edit docker-compose.yml to increase resource limits
docker-compose up -d

# Optimize database performance
docker exec lucid-mongodb mongosh --eval "
db.runCommand({compact: 'users'});
db.runCommand({compact: 'sessions'});
"

# Clear Redis cache
docker exec lucid-redis redis-cli flushall

# Restart services
docker-compose restart
```

### Log Analysis

#### Problem: Log Analysis and Error Detection

**Symptoms:**
- Errors in logs
- Performance issues
- System instability

**Diagnostic Steps:**
```bash
# Analyze error logs
docker logs lucid-api-gateway 2>&1 | grep -i error | tail -20
docker logs lucid-blockchain-engine 2>&1 | grep -i error | tail -20

# Check error patterns
docker logs lucid-api-gateway --since 1h | grep -o "LUCID_ERR_[0-9]*" | sort | uniq -c | sort -nr

# Check performance logs
docker logs lucid-api-gateway --since 1h | grep -E "slow|timeout|duration" | tail -10

# Check authentication logs
docker logs lucid-auth-service --since 1h | grep -E "(auth|login|token)" | tail -10
```

**Solutions:**
```bash
# Create log analysis script
cat > scripts/logs/analyze-logs.sh << 'EOF'
#!/bin/bash
echo "=== Lucid System Log Analysis ==="

echo "=== API Gateway Log Analysis ==="
docker logs lucid-api-gateway --since 1h | grep -E "(ERROR|WARN|CRITICAL)" | tail -20

echo "=== Error Pattern Analysis ==="
docker logs lucid-api-gateway --since 24h | grep -o "LUCID_ERR_[0-9]*" | sort | uniq -c | sort -nr

echo "=== Performance Analysis ==="
docker logs lucid-api-gateway --since 1h | grep -E "slow|timeout|duration" | tail -10

echo "=== Authentication Issues ==="
docker logs lucid-auth-service --since 1h | grep -E "(auth|login|token)" | tail -10
EOF

chmod +x scripts/logs/analyze-logs.sh
./scripts/logs/analyze-logs.sh
```

---

## Emergency Procedures

### System Recovery

#### Problem: Complete System Failure

**Symptoms:**
- All services down
- Database corruption
- System unresponsive

**Emergency Steps:**
```bash
# Stop all services
docker-compose down

# Check system resources
df -h
free -h
docker system df

# Clean up Docker resources
docker system prune -f
docker volume prune -f

# Restore from backup
./scripts/backup/restore-system.sh

# Restart services
docker-compose up -d

# Verify system health
./scripts/health/check-all-services.sh
```

### Data Recovery

#### Problem: Data Loss or Corruption

**Symptoms:**
- Missing data
- Database corruption
- Inconsistent data

**Recovery Steps:**
```bash
# Stop affected services
docker-compose stop lucid-mongodb lucid-redis

# Restore database from backup
./scripts/backup/mongodb-restore.sh /opt/lucid/backups/mongodb/latest_backup.gz

# Restore Redis from backup
./scripts/backup/redis-restore.sh /opt/lucid/backups/redis/latest_backup.rdb

# Restart services
docker-compose start lucid-mongodb lucid-redis

# Verify data integrity
docker exec lucid-mongodb mongosh --eval "db.runCommand({dbStats: 1})"
docker exec lucid-redis redis-cli info
```

---

## Monitoring and Alerting

### Health Check Scripts

```bash
#!/bin/bash
# scripts/health/check-all-services.sh

set -e

echo "=== Lucid System Health Check ==="

# Foundation services
echo "Checking foundation services..."
curl -f http://localhost:27017/ || echo "MongoDB: FAILED"
curl -f http://localhost:6379/ || echo "Redis: FAILED"
curl -f http://localhost:9200/_cluster/health || echo "Elasticsearch: FAILED"

# Authentication
echo "Checking authentication..."
curl -f http://localhost:8089/health || echo "Auth Service: FAILED"

# API Gateway
echo "Checking API Gateway..."
curl -f http://localhost:8080/health || echo "API Gateway: FAILED"

# Blockchain Core
echo "Checking blockchain core..."
curl -f http://localhost:8084/health || echo "Blockchain Engine: FAILED"
curl -f http://localhost:8085/health || echo "Session Anchoring: FAILED"

# Session Management
echo "Checking session management..."
curl -f http://localhost:8083/health || echo "Session Pipeline: FAILED"
curl -f http://localhost:8084/health || echo "Session Recorder: FAILED"
curl -f http://localhost:8085/health || echo "Chunk Processor: FAILED"
curl -f http://localhost:8086/health || echo "Session Storage: FAILED"
curl -f http://localhost:8087/health || echo "Session API: FAILED"

# RDP Services
echo "Checking RDP services..."
curl -f http://localhost:8090/health || echo "RDP Manager: FAILED"
curl -f http://localhost:8091/health || echo "XRDP: FAILED"
curl -f http://localhost:8092/health || echo "Session Controller: FAILED"
curl -f http://localhost:8093/health || echo "Resource Monitor: FAILED"

# Node Management
echo "Checking node management..."
curl -f http://localhost:8095/health || echo "Node Management: FAILED"

# Admin Interface
echo "Checking admin interface..."
curl -f http://localhost:8083/health || echo "Admin Interface: FAILED"

# TRON Payment (Isolated)
echo "Checking TRON payment services..."
curl -f http://localhost:8085/health || echo "TRON Client: FAILED"
curl -f http://localhost:8086/health || echo "Payout Router: FAILED"
curl -f http://localhost:8087/health || echo "Wallet Manager: FAILED"
curl -f http://localhost:8088/health || echo "USDT Manager: FAILED"
curl -f http://localhost:8089/health || echo "TRX Staking: FAILED"
curl -f http://localhost:8090/health || echo "Payment Gateway: FAILED"

echo "=== Health Check Complete ==="
```

### Performance Monitoring

```bash
#!/bin/bash
# scripts/monitoring/performance-check.sh

echo "=== Lucid System Performance Check ==="

# Check service response times
echo "=== Service Health Check ==="
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8080/health

# Check database performance
echo "=== Database Performance ==="
docker exec lucid-mongodb mongosh --eval "db.runCommand({serverStatus: 1}).metrics.command"

# Check Redis performance
echo "=== Redis Performance ==="
docker exec lucid-redis redis-cli info stats | grep -E "(instantaneous_ops_per_sec|keyspace_hits|keyspace_misses)"

# Check memory usage
echo "=== Memory Usage ==="
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"
```

---

## References

- [Deployment Guide](./deployment-guide.md)
- [Scaling Guide](./scaling-guide.md)
- [Backup Recovery Guide](./backup-recovery-guide.md)
- [Security Hardening Guide](./security-hardening-guide.md)
- [Master Build Plan](../plan/API_plans/00-master-architecture/01-MASTER_BUILD_PLAN.md)

---

**Document Version**: 1.0.0  
**Status**: ACTIVE  
**Last Updated**: 2025-01-14
