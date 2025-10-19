# Lucid Node Operator Guide

## Document Control

| Attribute | Value |
|-----------|-------|
| Document ID | LUCID-NODE-001 |
| Version | 1.0.0 |
| Status | ACTIVE |
| Last Updated | 2025-01-14 |
| Based On | Master Build Plan v1.0.0 |

---

## Overview

This comprehensive guide provides node operators with detailed instructions for managing Lucid blockchain nodes. It covers node setup, configuration, monitoring, maintenance, and troubleshooting procedures.

### Node Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Node Management Layer                   │
│  Node Setup + Configuration + Monitoring + Maintenance     │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────┴───────────────────────────────────────────┐
│                Node Operations Layer                      │
│  Consensus + Validation + Block Production + Sync         │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────┴───────────────────────────────────────────┐
│                Network Communication Layer                │
│  P2P + API + WebSocket + REST + GraphQL                   │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────┴───────────────────────────────────────────┐
│                Storage & Security Layer                   │
│  Blockchain Data + State + Keys + Encryption              │
└─────────────────────────────────────────────────────────────┘
```

---

## Node Setup

### Prerequisites

#### System Requirements

- **Operating System**: Ubuntu 20.04+ / CentOS 8+ / RHEL 8+
- **CPU**: 4 cores minimum, 8 cores recommended
- **Memory**: 8GB RAM minimum, 16GB recommended
- **Storage**: 100GB SSD minimum, 500GB recommended
- **Network**: 100 Mbps minimum, 1 Gbps recommended

#### Software Dependencies

```bash
# Install required packages
sudo apt-get update
sudo apt-get install -y \
    curl \
    wget \
    git \
    build-essential \
    python3 \
    python3-pip \
    docker.io \
    docker-compose \
    nginx \
    certbot

# Verify installations
python3 --version
docker --version
docker-compose --version
```

### Node Installation

#### Download and Install

```bash
# Create lucid user
sudo useradd -m -s /bin/bash lucid
sudo usermod -aG docker lucid
sudo usermod -aG sudo lucid

# Switch to lucid user
sudo su - lucid

# Create node directory
mkdir -p /home/lucid/lucid-node
cd /home/lucid/lucid-node

# Download Lucid node software
wget https://github.com/HamiGames/Lucid/releases/latest/download/lucid-node-linux-amd64.tar.gz
tar -xzf lucid-node-linux-amd64.tar.gz

# Set permissions
chmod +x lucid-node
sudo chown -R lucid:lucid /home/lucid/lucid-node
```

#### Node Configuration

```bash
# Create configuration directory
mkdir -p /home/lucid/lucid-node/config

# Generate node configuration
./lucid-node init --config-dir /home/lucid/lucid-node/config

# Edit configuration file
nano /home/lucid/lucid-node/config/config.yaml
```

#### Configuration File

```yaml
# /home/lucid/lucid-node/config/config.yaml
node:
  name: "lucid-node-1"
  type: "full_node"  # full_node, validator_node, archive_node
  network: "mainnet"  # mainnet, testnet, devnet
  
  # Node identity
  identity:
    node_id: "auto_generate"
    private_key: "auto_generate"
    
  # Network settings
  network:
    listen_address: "0.0.0.0:8080"
    external_address: "YOUR_PUBLIC_IP:8080"
    max_connections: 100
    peer_discovery: true
    
  # Blockchain settings
  blockchain:
    data_dir: "/home/lucid/lucid-node/data"
    genesis_file: "/home/lucid/lucid-node/config/genesis.json"
    sync_mode: "full"  # full, fast, light
    
  # Consensus settings
  consensus:
    algorithm: "proof_of_stake"
    validator_key: "auto_generate"
    stake_amount: 1000000  # Minimum stake in LUCID tokens
    
  # API settings
  api:
    enabled: true
    listen_address: "127.0.0.1:8081"
    cors_enabled: true
    rate_limit: 1000
    
  # RPC settings
  rpc:
    enabled: true
    listen_address: "127.0.0.1:8082"
    methods: ["eth", "net", "web3", "personal"]
    
  # Logging
  logging:
    level: "info"
    format: "json"
    output: "file"
    file: "/home/lucid/lucid-node/logs/node.log"
    
  # Monitoring
  monitoring:
    enabled: true
    metrics_port: 8083
    health_check_interval: 30
```

### Node Startup

#### Systemd Service

```bash
# Create systemd service file
sudo nano /etc/systemd/system/lucid-node.service
```

```ini
[Unit]
Description=Lucid Blockchain Node
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=lucid
Group=lucid
WorkingDirectory=/home/lucid/lucid-node
ExecStart=/home/lucid/lucid-node/lucid-node --config /home/lucid/lucid-node/config/config.yaml
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/home/lucid/lucid-node

[Install]
WantedBy=multi-user.target
```

#### Start Node Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable lucid-node

# Start service
sudo systemctl start lucid-node

# Check status
sudo systemctl status lucid-node

# View logs
sudo journalctl -u lucid-node -f
```

---

## Node Operations

### Node Management

#### Basic Operations

```bash
# Start node
sudo systemctl start lucid-node

# Stop node
sudo systemctl stop lucid-node

# Restart node
sudo systemctl restart lucid-node

# Check status
sudo systemctl status lucid-node

# View logs
sudo journalctl -u lucid-node -f

# Check node info
./lucid-node info --config /home/lucid/lucid-node/config/config.yaml
```

#### Node Status

```bash
# Get node status
curl -X GET http://localhost:8081/api/v1/node/status

# Response
{
  "node_id": "node_123456789",
  "name": "lucid-node-1",
  "status": "running",
  "version": "1.0.0",
  "network": "mainnet",
  "sync_status": "synced",
  "block_height": 125000,
  "peer_count": 15,
  "uptime": "7d 12h 30m"
}
```

### Blockchain Operations

#### Synchronization

```bash
# Check sync status
curl -X GET http://localhost:8081/api/v1/blockchain/sync

# Response
{
  "sync_status": "syncing",
  "current_block": 120000,
  "target_block": 125000,
  "sync_percentage": 96.0,
  "blocks_remaining": 5000,
  "estimated_time": "2h 30m"
}

# Force sync restart
curl -X POST http://localhost:8081/api/v1/blockchain/sync/restart

# Check blockchain info
curl -X GET http://localhost:8081/api/v1/blockchain/info

# Response
{
  "chain_id": "lucid-mainnet",
  "genesis_hash": "0x1234567890abcdef...",
  "current_block": 125000,
  "block_hash": "0xabcdef1234567890...",
  "total_difficulty": "1.5e15",
  "network_hashrate": "1.2TH/s"
}
```

#### Block Operations

```bash
# Get latest block
curl -X GET http://localhost:8081/api/v1/blockchain/blocks/latest

# Get specific block
curl -X GET http://localhost:8081/api/v1/blockchain/blocks/125000

# Get block by hash
curl -X GET http://localhost:8081/api/v1/blockchain/blocks/0xabcdef1234567890...

# Response
{
  "block_number": 125000,
  "block_hash": "0xabcdef1234567890...",
  "parent_hash": "0x1234567890abcdef...",
  "timestamp": 1640995200,
  "transactions": [
    {
      "hash": "0xtx1234567890abcdef...",
      "from": "0xalice1234567890...",
      "to": "0xbob1234567890...",
      "value": "1000000000000000000",
      "gas_used": 21000
    }
  ],
  "gas_used": 21000,
  "gas_limit": 30000000,
  "difficulty": "1000000"
}
```

### Transaction Operations

#### Transaction Management

```bash
# Get pending transactions
curl -X GET http://localhost:8081/api/v1/transactions/pending

# Get transaction by hash
curl -X GET http://localhost:8081/api/v1/transactions/0xtx1234567890abcdef...

# Submit transaction
curl -X POST http://localhost:8081/api/v1/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "from": "0xalice1234567890...",
    "to": "0xbob1234567890...",
    "value": "1000000000000000000",
    "gas": 21000,
    "gas_price": "20000000000",
    "nonce": 1,
    "signature": "0xsignature1234567890..."
  }'

# Response
{
  "transaction_hash": "0xtx1234567890abcdef...",
  "status": "pending",
  "block_number": null,
  "gas_used": null
}
```

#### Transaction Pool

```bash
# Get transaction pool status
curl -X GET http://localhost:8081/api/v1/transactions/pool

# Response
{
  "pending_transactions": 150,
  "queued_transactions": 25,
  "total_transactions": 175,
  "pool_size_mb": 2.5
}
```

---

## Network Management

### Peer Management

#### Peer Operations

```bash
# Get connected peers
curl -X GET http://localhost:8081/api/v1/network/peers

# Response
{
  "peers": [
    {
      "peer_id": "peer_123456789",
      "address": "192.168.1.10:8080",
      "version": "1.0.0",
      "connected_at": "2024-01-14T10:30:00Z",
      "last_seen": "2024-01-14T11:45:00Z",
      "latency": "15ms",
      "bytes_sent": 1024000,
      "bytes_received": 2048000
    }
  ],
  "total_peers": 15,
  "max_peers": 100
}

# Add peer manually
curl -X POST http://localhost:8081/api/v1/network/peers \
  -H "Content-Type: application/json" \
  -d '{
    "address": "192.168.1.20:8080",
    "persistent": true
  }'

# Remove peer
curl -X DELETE http://localhost:8081/api/v1/network/peers/peer_123456789
```

#### Network Configuration

```bash
# Get network configuration
curl -X GET http://localhost:8081/api/v1/network/config

# Response
{
  "listen_address": "0.0.0.0:8080",
  "external_address": "YOUR_PUBLIC_IP:8080",
  "max_connections": 100,
  "peer_discovery": true,
  "bootstrap_nodes": [
    "192.168.1.10:8080",
    "192.168.1.11:8080"
  ]
}

# Update network configuration
curl -X PUT http://localhost:8081/api/v1/network/config \
  -H "Content-Type: application/json" \
  -d '{
    "max_connections": 150,
    "peer_discovery": true
  }'
```

### Network Monitoring

#### Network Statistics

```bash
# Get network statistics
curl -X GET http://localhost:8081/api/v1/network/stats

# Response
{
  "network_stats": {
    "total_peers": 15,
    "active_peers": 12,
    "bytes_sent": 1024000000,
    "bytes_received": 2048000000,
    "packets_sent": 50000,
    "packets_received": 75000,
    "connection_errors": 5
  },
  "bandwidth": {
    "upload_rate": "1.2MB/s",
    "download_rate": "2.4MB/s",
    "total_upload": "1.2GB",
    "total_download": "2.4GB"
  }
}
```

---

## Consensus Operations

### Validator Operations

#### Validator Status

```bash
# Get validator status
curl -X GET http://localhost:8081/api/v1/consensus/validator

# Response
{
  "validator_address": "0xvalidator1234567890...",
  "status": "active",
  "stake_amount": "1000000000000000000000000",
  "commission_rate": "0.05",
  "delegated_stake": "5000000000000000000000000",
  "total_stake": "6000000000000000000000000",
  "voting_power": "0.15",
  "last_proposal": "2024-01-14T11:30:00Z"
}
```

#### Staking Operations

```bash
# Delegate stake
curl -X POST http://localhost:8081/api/v1/consensus/stake/delegate \
  -H "Content-Type: application/json" \
  -d '{
    "amount": "1000000000000000000000000",
    "validator": "0xvalidator1234567890..."
  }'

# Undelegate stake
curl -X POST http://localhost:8081/api/v1/consensus/stake/undelegate \
  -H "Content-Type: application/json" \
  -d '{
    "amount": "500000000000000000000000",
    "validator": "0xvalidator1234567890..."
  }'

# Claim rewards
curl -X POST http://localhost:8081/api/v1/consensus/stake/claim-rewards \
  -H "Content-Type: application/json" \
  -d '{
    "validator": "0xvalidator1234567890..."
  }'
```

### Block Production

#### Block Production Status

```bash
# Get block production status
curl -X GET http://localhost:8081/api/v1/consensus/blocks

# Response
{
  "block_production": {
    "status": "active",
    "last_block_time": "2024-01-14T11:45:00Z",
    "next_block_time": "2024-01-14T11:45:10Z",
    "blocks_produced": 1250,
    "blocks_missed": 5,
    "success_rate": "99.6%"
  },
  "validator_info": {
    "validator_address": "0xvalidator1234567890...",
    "proposer_priority": 0.15,
    "voting_power": "6000000000000000000000000"
  }
}
```

---

## Monitoring and Maintenance

### Node Monitoring

#### Performance Metrics

```bash
# Get node metrics
curl -X GET http://localhost:8083/metrics

# Response (Prometheus format)
# HELP node_cpu_usage CPU usage percentage
# TYPE node_cpu_usage gauge
node_cpu_usage 25.5

# HELP node_memory_usage Memory usage in bytes
# TYPE node_memory_usage gauge
node_memory_usage 8589934592

# HELP node_disk_usage Disk usage percentage
# TYPE node_disk_usage gauge
node_disk_usage 45.2

# HELP blockchain_block_height Current block height
# TYPE blockchain_block_height counter
blockchain_block_height 125000

# HELP network_peer_count Number of connected peers
# TYPE network_peer_count gauge
network_peer_count 15
```

#### Health Checks

```bash
# Get node health
curl -X GET http://localhost:8081/api/v1/node/health

# Response
{
  "status": "healthy",
  "checks": {
    "database": "healthy",
    "network": "healthy",
    "consensus": "healthy",
    "storage": "healthy"
  },
  "timestamp": "2024-01-14T11:45:00Z"
}
```

### Log Management

#### Log Access

```bash
# View node logs
sudo journalctl -u lucid-node -f

# View specific log level
sudo journalctl -u lucid-node --since "1 hour ago" | grep ERROR

# Export logs
sudo journalctl -u lucid-node --since "2024-01-14" --until "2024-01-15" > node-logs-2024-01-14.log
```

#### Log Configuration

```bash
# Update log configuration
curl -X PUT http://localhost:8081/api/v1/node/logging \
  -H "Content-Type: application/json" \
  -d '{
    "level": "debug",
    "format": "json",
    "output": "file",
    "file": "/home/lucid/lucid-node/logs/node.log"
  }'
```

### Maintenance Operations

#### Database Maintenance

```bash
# Compact database
curl -X POST http://localhost:8081/api/v1/node/database/compact

# Check database integrity
curl -X GET http://localhost:8081/api/v1/node/database/integrity

# Response
{
  "integrity_check": "passed",
  "corrupted_blocks": 0,
  "missing_blocks": 0,
  "database_size": "2.5GB"
}
```

#### Storage Management

```bash
# Get storage information
curl -X GET http://localhost:8081/api/v1/node/storage

# Response
{
  "storage_info": {
    "total_space": "500GB",
    "used_space": "225GB",
    "free_space": "275GB",
    "usage_percentage": 45.0
  },
  "data_directories": {
    "blockchain_data": "200GB",
    "state_data": "20GB",
    "logs": "5GB"
  }
}

# Clean old data
curl -X POST http://localhost:8081/api/v1/node/storage/cleanup \
  -H "Content-Type: application/json" \
  -d '{
    "cleanup_logs": true,
    "cleanup_temp_files": true,
    "retention_days": 30
  }'
```

---

## Security Management

### Key Management

#### Key Operations

```bash
# Generate new key pair
curl -X POST http://localhost:8081/api/v1/keys/generate

# Response
{
  "public_key": "0xpublickey1234567890...",
  "private_key": "0xprivatekey1234567890...",
  "address": "0xaddress1234567890..."
}

# Import key
curl -X POST http://localhost:8081/api/v1/keys/import \
  -H "Content-Type: application/json" \
  -d '{
    "private_key": "0xprivatekey1234567890...",
    "name": "my-key"
  }'

# List keys
curl -X GET http://localhost:8081/api/v1/keys

# Response
{
  "keys": [
    {
      "name": "my-key",
      "address": "0xaddress1234567890...",
      "public_key": "0xpublickey1234567890...",
      "created_at": "2024-01-14T10:30:00Z"
    }
  ]
}
```

#### Security Configuration

```bash
# Get security settings
curl -X GET http://localhost:8081/api/v1/node/security

# Response
{
  "security_settings": {
    "encryption_enabled": true,
    "key_rotation_days": 90,
    "access_control": "enabled",
    "audit_logging": true
  }
}

# Update security settings
curl -X PUT http://localhost:8081/api/v1/node/security \
  -H "Content-Type: application/json" \
  -d '{
    "encryption_enabled": true,
    "key_rotation_days": 60,
    "access_control": "enabled"
  }'
```

---

## Troubleshooting

### Common Issues

#### Node Won't Start

```bash
# Check service status
sudo systemctl status lucid-node

# Check logs
sudo journalctl -u lucid-node --since "10 minutes ago"

# Check configuration
./lucid-node validate-config --config /home/lucid/lucid-node/config/config.yaml

# Check ports
sudo netstat -tuln | grep 8080
sudo netstat -tuln | grep 8081
```

#### Sync Issues

```bash
# Check sync status
curl -X GET http://localhost:8081/api/v1/blockchain/sync

# Force sync restart
curl -X POST http://localhost:8081/api/v1/blockchain/sync/restart

# Check peer connections
curl -X GET http://localhost:8081/api/v1/network/peers

# Reset sync (caution: this will re-download blockchain)
curl -X POST http://localhost:8081/api/v1/blockchain/sync/reset
```

#### Performance Issues

```bash
# Check system resources
htop
df -h
free -h

# Check node metrics
curl -X GET http://localhost:8083/metrics

# Check network connectivity
ping 8.8.8.8
curl -X GET http://localhost:8081/api/v1/network/stats
```

### Diagnostic Tools

#### Node Diagnostics

```bash
# Run node diagnostics
curl -X POST http://localhost:8081/api/v1/node/diagnostics

# Response
{
  "diagnostics": {
    "system_health": "healthy",
    "issues_found": 0,
    "recommendations": [
      "Consider increasing memory allocation",
      "Monitor disk usage - currently at 75%"
    ],
    "performance_score": 85
  }
}
```

#### Network Diagnostics

```bash
# Test network connectivity
curl -X POST http://localhost:8081/api/v1/network/test

# Response
{
  "network_test": {
    "connectivity": "good",
    "latency": "15ms",
    "bandwidth": "100Mbps",
    "packet_loss": "0%"
  }
}
```

---

## Best Practices

### Operational Best Practices

1. **Regular Monitoring**
   - Monitor node status daily
   - Check logs for errors
   - Monitor system resources

2. **Backup Strategy**
   - Regular database backups
   - Configuration backups
   - Key backups (secure storage)

3. **Security**
   - Keep software updated
   - Use strong passwords
   - Secure key storage

4. **Performance**
   - Monitor resource usage
   - Optimize configuration
   - Regular maintenance

### Maintenance Schedule

#### Daily Tasks
- Check node status
- Review logs
- Monitor metrics

#### Weekly Tasks
- Update software
- Clean old logs
- Check disk space

#### Monthly Tasks
- Full system backup
- Security audit
- Performance review

---

## References

- [Admin User Guide](./admin-user-guide.md)
- [Deployment Guide](../deployment/deployment-guide.md)
- [Troubleshooting Guide](../deployment/troubleshooting-guide.md)
- [Security Hardening Guide](../deployment/security-hardening-guide.md)
- [Master Build Plan](../../plan/API_plans/00-master-architecture/01-MASTER_BUILD_PLAN.md)

---

**Document Version**: 1.0.0  
**Status**: ACTIVE  
**Last Updated**: 2025-01-14
