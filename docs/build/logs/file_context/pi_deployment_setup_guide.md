# Raspberry Pi Deployment Setup Guide

## Overview

This guide explains how to set up and use the GitHub Actions workflow for deploying Lucid services to a Raspberry Pi.

## Prerequisites

### 1. Raspberry Pi Setup

Ensure your Raspberry Pi has:
- **Docker** and **Docker Compose** installed
- **SSH** enabled and accessible
- **User account** with sudo privileges
- **Network connectivity** to GitHub Container Registry

### 2. SSH Key Generation

Generate an SSH key pair on your local machine (not on the Pi):

```bash
# Generate SSH key pair
ssh-keygen -t ed25519 -C "lucid-pi-deployment" -f ~/.ssh/lucid_pi_key

# This creates:
# ~/.ssh/lucid_pi_key (private key)
# ~/.ssh/lucid_pi_key.pub (public key)
```

### 3. SSH Key Installation on Pi

Copy the **public key** to your Raspberry Pi:

```bash
# Copy public key to Pi
ssh-copy-id -i ~/.ssh/lucid_pi_key.pub pi@your-pi-ip

# Or manually add to authorized_keys
cat ~/.ssh/lucid_pi_key.pub | ssh pi@your-pi-ip "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

### 4. Test SSH Connection

Verify SSH access works:

```bash
# Test SSH connection
ssh -i ~/.ssh/lucid_pi_key pi@your-pi-ip "echo 'SSH connection successful'"
```

## GitHub Secrets Configuration

### Required Secrets

Add these secrets to your GitHub repository:

#### 1. `PI_SSH_KEY`
- **Value**: The entire content of your **private key** file
- **How to get**:
  ```bash
  cat ~/.ssh/lucid_pi_key
  ```
- **Format**: Should include the full key with headers:
  ```
  -----BEGIN OPENSSH PRIVATE KEY-----
  b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
  ...
  -----END OPENSSH PRIVATE KEY-----
  ```

#### 2. `PI_USER`
- **Value**: The username on your Raspberry Pi (e.g., `pi`, `ubuntu`, `lucid`)
- **Example**: `pi`

#### 3. `GITHUB_TOKEN`
- **Value**: Automatically provided by GitHub Actions
- **Note**: This is used for Docker registry authentication

### Adding Secrets to GitHub

1. Go to your repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret with the exact name and value

## Workflow Usage

### 1. Manual Deployment

#### Via GitHub UI:
1. Go to **Actions** tab in your repository
2. Select **Raspberry Pi Deployment**
3. Click **Run workflow**
4. Configure parameters:
   - **Pi Host**: Your Pi's IP address or hostname
   - **Deployment Type**: `full`, `update`, `rollback`, or `health-check`
   - **Target Services**: Comma-separated list (optional)
   - **Force Deploy**: Whether to force deployment

#### Via GitHub CLI:
```bash
gh workflow run "Raspberry Pi Deployment" \
  --field pi_host="192.168.1.100" \
  --field deployment_type="full" \
  --field target_services="gui,blockchain,api"
```

### 2. Automatic Deployment

The workflow automatically runs on:
- **Push to main branch**
- **Tag creation** (v*)

### 3. Deployment Types

#### `full`
- Complete deployment of all services
- Creates backup of current deployment
- Pulls latest images from registry
- Deploys all services

#### `update`
- Updates existing services only
- Faster deployment for incremental changes
- No backup creation

#### `rollback`
- Restores previous deployment from backup
- Requires existing backup to be available

#### `health-check`
- Runs system health checks only
- No deployment performed
- Useful for monitoring

## Deployment Process

### 1. Pre-deployment Checks
- Validates SSH connection
- Checks required secrets
- Determines services to deploy

### 2. Preparation
- Creates deployment directory
- Backs up current deployment (if not rollback)
- Sets up SSH environment

### 3. Image Management
- Logs into GitHub Container Registry
- Pulls required Docker images
- Falls back to latest if specific version unavailable

### 4. Service Deployment
- Stops existing services
- Updates docker-compose.yml with new images
- Starts new services
- Verifies deployment success

### 5. Post-deployment
- Runs health checks
- Performs integration tests
- Cleans up old deployments and images

## Directory Structure on Pi

The deployment creates this structure on your Pi:

```
/opt/lucid/
├── current/                 # Current deployment files
├── deployments/            # Deployment history
│   └── deploy-YYYYMMDD-HHMMSS-commit/
├── backups/               # Backup history
│   └── backup-YYYYMMDD-HHMMSS/
└── docker-compose.yml     # Docker Compose configuration
```

## Troubleshooting

### Common Issues

#### 1. SSH Connection Failed
```
❌ Missing required secrets: PI_SSH_KEY or PI_USER
```

**Solution**:
- Verify `PI_SSH_KEY` secret contains the full private key
- Check `PI_USER` matches your Pi username
- Test SSH connection manually

#### 2. Docker Permission Denied
```
docker: permission denied while trying to connect to the Docker daemon socket
```

**Solution**:
- Add your Pi user to docker group:
  ```bash
  sudo usermod -aG docker $USER
  ```
- Log out and back in, or restart the Pi

#### 3. Registry Authentication Failed
```
Error response from daemon: unauthorized
```

**Solution**:
- Verify `GITHUB_TOKEN` is available (automatic)
- Check repository permissions for container registry
- Ensure Pi can access GitHub Container Registry

#### 4. Service Health Check Failed
```
❌ service: Not running
```

**Solution**:
- Check Docker logs: `docker logs lucid-service-1`
- Verify service configuration in docker-compose.yml
- Check resource constraints (memory, CPU)

### Debugging Commands

#### Check SSH Connection:
```bash
ssh -i ~/.ssh/lucid_pi_key pi@your-pi-ip "docker --version"
```

#### Check Pi System Status:
```bash
ssh -i ~/.ssh/lucid_pi_key pi@your-pi-ip "docker ps && df -h && free -h"
```

#### Manual Service Management:
```bash
ssh -i ~/.ssh/lucid_pi_key pi@your-pi-ip "cd /opt/lucid && docker-compose ps"
```

## Security Considerations

### 1. SSH Key Security
- Keep private key secure and never share
- Use strong passphrase for key generation
- Rotate keys regularly

### 2. Network Security
- Use VPN or secure network for Pi access
- Consider firewall rules for SSH access
- Monitor SSH access logs

### 3. Docker Security
- Keep Docker and Pi OS updated
- Use non-root user for services when possible
- Monitor container resource usage

## Monitoring and Maintenance

### 1. Regular Health Checks
Run health checks weekly:
```bash
gh workflow run "Raspberry Pi Deployment" \
  --field deployment_type="health-check"
```

### 2. Backup Management
- Backups are automatically created before deployments
- Keep last 10 backups (automatic cleanup)
- Test restore procedures regularly

### 3. Log Monitoring
Monitor deployment logs in GitHub Actions for:
- Deployment success/failure
- Service health status
- Resource usage warnings

## Advanced Configuration

### Custom Services
To deploy additional services:
1. Add service to `target_services` input
2. Ensure service image exists in registry
3. Update docker-compose.yml on Pi

### Environment Variables
Set Pi-specific environment variables in docker-compose.yml:
```yaml
services:
  lucid-gui:
    environment:
      - LUCID_ENV=production
      - PI_SPECIFIC_CONFIG=value
```

### Resource Limits
Configure resource limits in docker-compose.yml:
```yaml
services:
  lucid-blockchain:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
```

---

## Summary

The Raspberry Pi deployment workflow provides:
- ✅ **Automated deployment** of Lucid services
- ✅ **Health monitoring** and status checks
- ✅ **Backup and rollback** capabilities
- ✅ **Error handling** and troubleshooting
- ✅ **Security** with SSH key authentication
- ✅ **Flexibility** with multiple deployment types

For issues or questions, check the GitHub Actions logs and refer to this troubleshooting guide.
