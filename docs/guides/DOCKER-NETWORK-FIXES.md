# Docker Network Issues - Root Cause Analysis & Solutions

## Root Cause: DNS Resolution Timeout

**Error**: `dial tcp: lookup registry-1.docker.io on 127.0.0.11:53: read udp 127.0.0.1:43511->127.0.0.11:53: i/o timeout`

### Analysis

1. **Docker Desktop DNS Issue**: Docker's internal DNS server (127.0.0.11:53) cannot resolve `registry-1.docker.io`
2. **Network Configuration**: Windows networking conflicts with Docker's DNS resolution
3. **Firewall/Antivirus**: Windows Defender or third-party antivirus blocking Docker network requests
4. **Proxy/VPN**: Network proxy or VPN interfering with Docker registry access

## Immediate Solutions

### Option 1: Run Diagnostic Script (Recommended First Step)

```powershell
# Run the comprehensive diagnostic script
.\diagnose-docker-network.ps1
```

This script will:
- Test Docker daemon connectivity
- Check network and DNS resolution
- Apply DNS fixes automatically
- Test image pulling capability

### Option 2: Manual DNS Configuration

1. **Create/Edit Docker Daemon Configuration**:
   ```powershell
   # Create Docker config directory
   New-Item -Path "$env:USERPROFILE\.docker" -ItemType Directory -Force
   
   # Create daemon.json with DNS settings
   @{
       "dns" = @("8.8.8.8", "8.8.4.4", "1.1.1.1")
       "registry-mirrors" = @("https://mirror.gcr.io")
   } | ConvertTo-Json | Set-Content "$env:USERPROFILE\.docker\daemon.json"
   ```

2. **Restart Docker Desktop** (CRITICAL - MUST DO MANUALLY!):
   - **Method 1**: Right-click Docker Desktop icon in system tray → "Quit Docker Desktop" → Wait 10 seconds → Start Docker Desktop from Start Menu
   - **Method 2**: Close Docker Desktop completely → Reopen from Start Menu
   - **Wait for Docker to fully start** (green whale icon in system tray)

3. **Test the fix**:
   ```powershell
   docker pull hello-world
   docker pull python:3.12-slim
   ```

### Option 3: Use Network-Friendly Dockerfile

Switch to the network-optimized Dockerfile:

```powershell
# Copy the network-friendly version
Copy-Item ".devcontainer/Dockerfile.network-friendly" ".devcontainer/Dockerfile" -Force

# Test build
.\build-devcontainer.ps1 -TestOnly
```

## Step-by-Step Troubleshooting

### Step 1: Basic Docker Health Check

```powershell
# Check if Docker is running
docker info

# Test basic functionality
docker run --rm hello-world

# Check Docker version
docker version
```

### Step 2: Network Connectivity Test

```powershell
# Test internet connectivity
Test-NetConnection -ComputerName "8.8.8.8" -Port 53

# Test Docker registry connectivity  
Test-NetConnection -ComputerName "registry-1.docker.io" -Port 443

# Test DNS resolution
Resolve-DnsName registry-1.docker.io
```

### Step 3: Docker Desktop Reset (Nuclear Option)

1. Open Docker Desktop
2. Go to **Settings → Troubleshoot**
3. Click **Reset to factory defaults**
4. Restart Docker Desktop
5. Reconfigure as needed

### Step 4: Windows-Specific Fixes

#### Disable Windows Defender Temporarily
```powershell
# Run as Administrator
Set-MpPreference -DisableRealtimeMonitoring $true
# Test Docker build
# Re-enable: Set-MpPreference -DisableRealtimeMonitoring $false
```

#### Configure Windows Firewall
```powershell
# Allow Docker Desktop through firewall
New-NetFirewallRule -DisplayName "Docker Desktop" -Direction Inbound -Action Allow -Program "C:\Program Files\Docker\Docker\Docker Desktop.exe"
```

#### WSL2 Backend Issues (if applicable)
```powershell
# Restart WSL2
wsl --shutdown
# Restart Docker Desktop
```

## Alternative Solutions

### Solution 1: Use Alternative Registry

Update Dockerfile to use GitHub Container Registry:
```dockerfile
FROM ghcr.io/library/python:3.12-slim AS base
```

### Solution 2: Pre-pull Images

Before building, manually pull required images:
```powershell
docker pull python:3.12-slim
docker pull mongo:7.0
docker pull alpine:3.22.1
docker pull nginx:1.28-alpine
```

### Solution 3: Build with Different Network

```powershell
# Use host network for building (Linux only)
docker buildx build --network=host ...

# Or use a different builder
docker buildx create --name network-builder --driver docker-container --use
```

## Testing Your Fix

### Test 1: Basic Image Pull
```powershell
docker pull hello-world
docker pull python:3.12-slim
```

### Test 2: Devcontainer Build Test
```powershell
.\build-devcontainer.ps1 -TestOnly
```

### Test 3: Full Build and Push
```powershell
.\build-devcontainer.ps1
```

## Prevention Strategies

### 1. Network Configuration
- Configure Docker Desktop DNS settings permanently
- Use registry mirrors for better reliability
- Set up proper firewall exceptions

### 2. Build Optimization
- Use multi-stage builds with smaller base images
- Implement retry logic in build scripts
- Cache frequently used images locally

### 3. Development Workflow
- Use `.dockerignore` to reduce context size
- Pre-pull base images before building
- Use Docker BuildKit features for better caching

## Common Error Patterns and Solutions

| Error Pattern | Root Cause | Solution |
|--------------|------------|----------|
| `dial tcp: lookup registry-1.docker.io` | DNS resolution failure | Configure Docker DNS settings |
| `TLS handshake timeout` | Network/firewall blocking | Disable antivirus/firewall temporarily |
| `no space left on device` | Docker disk space full | `docker system prune -a` |
| `error checking context: no such file` | Incorrect build context | Check Dockerfile location |

## Environment-Specific Notes

### Windows 11 with Docker Desktop
- Most common issue is DNS configuration
- Windows Defender often blocks Docker network requests
- WSL2 backend can have networking conflicts

### Corporate Networks
- May require proxy configuration in Docker settings
- Registry mirrors might be necessary
- Contact IT for firewall exceptions

### VPN Users
- Disconnect VPN during build if possible
- Configure Docker to use VPN DNS servers
- Use split tunneling to exclude Docker traffic

## Success Verification

After applying fixes, you should see:
```
✓ Docker daemon running
✓ Basic internet connectivity working  
✓ Docker registry reachable
✓ DNS resolution working for all Docker domains
✓ Successfully pulled hello-world image
✓ Successfully pulled Python base image
```

Then your devcontainer build should work:
```powershell
.\build-devcontainer.ps1 -TestOnly
# Should complete without DNS errors
```

---

**Need Help?** 
1. Run `.\diagnose-docker-network.ps1` for automated diagnostics
2. Check Docker Desktop logs in: `%APPDATA%\Docker\log\vm\`
3. Review Windows Event Viewer for Docker-related errors