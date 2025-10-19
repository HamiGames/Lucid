# Lucid Pi Deployment Guide

This guide explains how to deploy Lucid services to your Raspberry Pi with automatic volume mount setup.

## 🚀 Quick Start

### Option 1: Automatic Deployment (Recommended)

Deploy with automatic volume setup in one command:

```bash
# Deploy Phase 1 (Foundation Services)
./scripts/deployment/deploy-with-volumes.sh configs/docker/docker-compose.foundation.yml

# Deploy Phase 2 (Core Services)
./scripts/deployment/deploy-with-volumes.sh configs/docker/docker-compose.core.yml

# Deploy Phase 3 (Application Services)
./scripts/deployment/deploy-with-volumes.sh configs/docker/docker-compose.application.yml

# Deploy Phase 4 (Support Services)
./scripts/deployment/deploy-with-volumes.sh configs/docker/docker-compose.support.yml

# Deploy All Services
./scripts/deployment/deploy-with-volumes.sh configs/docker/docker-compose.all.yml
```

### Option 2: Manual Setup

If you prefer to set up volumes manually:

```bash
# 1. Setup volumes first
./scripts/deployment/setup-pi-volumes.sh

# 2. Then deploy via SSH
ssh -i ~/.ssh/id_rsa pickme@192.168.0.75
cd /mnt/myssd/Lucid
docker-compose -f docker-compose.foundation.yml up -d
```

## 📋 Prerequisites

1. **SSH Access**: Ensure you can SSH to your Pi without password
2. **Docker**: Docker and Docker Compose installed on Pi
3. **SSH Key**: SSH key configured for passwordless access
4. **Storage**: `/mnt/myssd/Lucid` directory accessible (or update paths in scripts)

## 🔧 Configuration

### Environment Variables

```bash
export PI_USER="pickme"                    # Pi username
export PI_HOST="192.168.0.75"             # Pi IP/hostname
export PI_SSH_KEY_PATH="~/.ssh/id_rsa"    # SSH key path
```

### Custom Pi Settings

```bash
# Use custom Pi settings
./scripts/deployment/deploy-with-volumes.sh \
  -u pi \
  -H 192.168.1.100 \
  -k ~/.ssh/pi_key \
  configs/docker/docker-compose.foundation.yml
```

## 📁 Volume Structure

All data is stored under `/mnt/myssd/Lucid` on the Pi:

```
/mnt/myssd/Lucid/
├── data/                    # Service data
│   ├── mongodb/            # MongoDB data
│   ├── redis/              # Redis data
│   ├── elasticsearch/      # Elasticsearch data
│   ├── auth/               # Authentication data
│   ├── blockchain/         # Blockchain data
│   ├── session-*/          # Session management data
│   ├── rdp-*/              # RDP service data
│   ├── node-*/             # Node management data
│   ├── admin-*/            # Admin interface data
│   ├── tron-*/             # TRON payment data
│   └── storage/            # General storage
├── logs/                   # Service logs
│   ├── auth/               # Authentication logs
│   ├── api-gateway/        # API Gateway logs
│   ├── blockchain/         # Blockchain logs
│   └── ...                 # Other service logs
├── config/                 # Configuration files
├── backups/                # Backup files
└── certs/                  # SSL certificates
```

## 🛠️ Advanced Usage

### Build and Deploy

```bash
# Build images before deployment
./scripts/deployment/deploy-with-volumes.sh \
  --build \
  configs/docker/docker-compose.foundation.yml
```

### Skip Volume Setup

```bash
# Skip volume setup (assumes directories exist)
./scripts/deployment/deploy-with-volumes.sh \
  --skip-volumes \
  configs/docker/docker-compose.foundation.yml
```

### Interactive Mode

```bash
# Run in foreground (not detached)
./scripts/deployment/deploy-with-volumes.sh \
  --detach=false \
  configs/docker/docker-compose.foundation.yml
```

## 🔍 Troubleshooting

### SSH Connection Issues

```bash
# Test SSH connection
ssh -i ~/.ssh/id_rsa pickme@192.168.0.75 "echo 'SSH working'"

# Check SSH key permissions
chmod 600 ~/.ssh/id_rsa
```

### Volume Mount Issues

```bash
# Check if directories exist on Pi
ssh -i ~/.ssh/id_rsa pickme@192.168.0.75 "ls -la /mnt/myssd/Lucid"

# Recreate volume directories
./scripts/deployment/setup-pi-volumes.sh
```

### Docker Issues

```bash
# Check Docker on Pi
ssh -i ~/.ssh/id_rsa pickme@192.168.0.75 "docker --version && docker-compose --version"

# Check running containers
ssh -i ~/.ssh/id_rsa pickme@192.168.0.75 "docker ps"
```

## 📊 Monitoring

### Check Service Status

```bash
# View all containers
ssh -i ~/.ssh/id_rsa pickme@192.168.0.75 "docker ps"

# Check specific service logs
ssh -i ~/.ssh/id_rsa pickme@192.168.0.75 "docker logs lucid-mongodb"
```

### View Volume Usage

```bash
# Check disk usage
ssh -i ~/.ssh/id_rsa pickme@192.168.0.75 "df -h /mnt/myssd/Lucid"

# Check directory sizes
ssh -i ~/.ssh/id_rsa pickme@192.168.0.75 "du -sh /mnt/myssd/Lucid/*"
```

## 🔄 Updates and Maintenance

### Update Services

```bash
# Pull latest images and restart
./scripts/deployment/deploy-with-volumes.sh \
  --build \
  configs/docker/docker-compose.foundation.yml
```

### Backup Data

```bash
# Backup all data
ssh -i ~/.ssh/id_rsa pickme@192.168.0.75 "
  tar -czf /mnt/myssd/Lucid/backups/lucid-backup-\$(date +%Y%m%d).tar.gz \
    -C /mnt/myssd/Lucid data logs config
"
```

### Clean Up

```bash
# Remove unused containers and images
ssh -i ~/.ssh/id_rsa pickme@192.168.0.75 "
  docker system prune -f
  docker volume prune -f
"
```

## 📝 Notes

- **Volume Mounts**: All services use direct host path mounts for better performance on Pi
- **Permissions**: Directories are created with proper ownership for the Pi user
- **Security**: Sensitive directories (MongoDB, certs) have restricted permissions
- **Backup**: Regular backups are recommended for production deployments
- **Monitoring**: Use the verification commands to monitor service health

## 🆘 Support

If you encounter issues:

1. Check the troubleshooting section above
2. Verify SSH connectivity and permissions
3. Ensure Docker is running on the Pi
4. Check the Pi's disk space and memory
5. Review service logs for specific errors

For additional help, refer to the main project documentation or create an issue in the repository.
