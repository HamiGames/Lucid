# LUCID DEPLOYMENT GUIDE

## HamiGames/Lucid.git Repository Aligned & LUCID-STRICT Compliant

### DEPLOYMENT OPTIONS

#### 1. LOCAL DEVELOPMENT (Windows Host)
**Purpose**: Build and test on Windows development machine  
**Target**: Docker Desktop on Windows  
**Script**: `lucid-optimal-build-enhanced.ps1`

```powershell
# Verify environment only
.\scripts\deployment\lucid-optimal-build-enhanced.ps1 -VerifyOnly -SkipNetworkRecreate -NoCacheClean

# Build DevContainer only (Docker-in-Docker build factory)
.\scripts\deployment\lucid-optimal-build-enhanced.ps1 -DevContainerOnly -SkipNetworkRecreate

# Build Core Services only (MongoDB, Tor, APIs)
.\scripts\deployment\lucid-optimal-build-enhanced.ps1 -CoreServicesOnly -SkipNetworkRecreate

# Build both DevContainer and Core Services
.\scripts\deployment\lucid-optimal-build-enhanced.ps1
```

#### 2. PI PRODUCTION DEPLOYMENT (ARM64)
**Purpose**: Deploy to Raspberry Pi 5 for production use  
**Target**: `ssh pickme@192.168.0.75` (ARM64 Ubuntu)  
**Script**: `deploy-to-pi-enhanced.ps1`

```powershell
# Verify Pi deployment readiness
.\scripts\deployment\deploy-to-pi-enhanced.ps1 -VerifyOnly

# Fix Tor infrastructure only (troubleshooting)
.\scripts\deployment\deploy-to-pi-enhanced.ps1 -FixTorOnly

# Deploy Tor-proxy only to Pi
.\scripts\deployment\deploy-to-pi-enhanced.ps1 -TorProxyOnly

# Deploy Core Services only to Pi
.\scripts\deployment\deploy-to-pi-enhanced.ps1 -CoreServicesOnly

# Full deployment to Pi (complete infrastructure)
.\scripts\deployment\deploy-to-pi-enhanced.ps1 -FullDeploy

# Clean deployment (remove existing containers first)
.\scripts\deployment\deploy-to-pi-enhanced.ps1 -CleanDeploy
```

---

## INFRASTRUCTURE COMPONENTS

### DEVELOPMENT ENVIRONMENT
- **DevContainer**: `lucid-devcontainer` (Docker-in-Docker build factory)
- **Network**: `lucid-dev_lucid_net` (172.20.0.0/16)
- **SSH Access**: `localhost:2222` (password: lucid)
- **VS Code**: "Dev Containers: Attach to Running Container"

### PRODUCTION SERVICES (Pi)
- **MongoDB 7**: `192.168.0.75:27017`
- **Tor SOCKS**: `192.168.0.75:9050`
- **Tor Control**: `192.168.0.75:9051`  
- **API Server**: `192.168.0.75:8081`
- **API Gateway**: `192.168.0.75:8080`
- **Network**: `lucid_core_net` (172.21.0.0/16)

---

## TROUBLESHOOTING

### Common Issues

#### Environment Variable Warnings
If you see `MONGO_URL` variable warnings:
1. Ensure `infrastructure/compose/.env` exists
2. Run with `-VerifyOnly` first to check configuration

#### Network Already Exists Errors  
If network creation fails:
1. Use `-SkipNetworkRecreate` flag
2. Or manually remove: `docker network rm lucid_core_net`

#### SSH Connection Issues (Pi Deployment)
1. Test SSH manually: `ssh pickme@192.168.0.75`
2. Check Pi is powered on: `ping 192.168.0.75`
3. Verify SSH key permissions

#### Docker Build Failures
1. Use `-CleanDeploy` to start fresh
2. Check Docker Desktop is running
3. Verify sufficient disk space

### Health Checks

#### Local Services
```powershell
# Check DevContainer
docker compose -f infrastructure\containers\.devcontainer\docker-compose.dev.yml ps

# Check Core Services  
docker compose -f infrastructure\compose\lucid-dev.yaml ps

# Test API
curl http://localhost:8081/health
```

#### Pi Services
```powershell
# SSH to Pi and check services
ssh pickme@192.168.0.75 'cd /workspaces/Lucid && docker compose -f infrastructure/compose/lucid-dev.yaml ps'

# Test Tor health
ssh pickme@192.168.0.75 'docker exec tor_proxy /usr/local/bin/tor-health'

# Test API health
ssh pickme@192.168.0.75 'curl -s http://localhost:8081/health'
```

---

## DEVELOPMENT WORKFLOW

### 1. Initial Setup
```powershell
# First-time setup
.\scripts\deployment\lucid-optimal-build-enhanced.ps1 -VerifyOnly

# If verification passes, build development environment  
.\scripts\deployment\lucid-optimal-build-enhanced.ps1 -DevContainerOnly
```

### 2. Development Work
- Use VS Code with "Dev Containers: Attach to Running Container"
- Connect to `lucid-devcontainer-active` or similar
- Work inside `/workspaces/Lucid`

### 3. Testing & Deployment
```powershell
# Test locally first
.\scripts\deployment\lucid-optimal-build-enhanced.ps1 -CoreServicesOnly

# Once working, deploy to Pi
.\scripts\deployment\deploy-to-pi-enhanced.ps1 -VerifyOnly
.\scripts\deployment\deploy-to-pi-enhanced.ps1 -CoreServicesOnly
```

---

## FILE LOCATIONS

### Scripts
- **Local Build**: `scripts/deployment/lucid-optimal-build-enhanced.ps1`
- **Pi Deployment**: `scripts/deployment/deploy-to-pi-enhanced.ps1` 

### Configuration Files
- **Environment**: `infrastructure/compose/.env`
- **Core Services**: `infrastructure/compose/lucid-dev.yaml`
- **DevContainer**: `infrastructure/containers/.devcontainer/docker-compose.dev.yml`
- **Tor Config**: `02-network-security/tor/torrc`

### Key Directories
- **Infrastructure**: `infrastructure/`
- **Network Security**: `02-network-security/`
- **API Components**: `03-api-gateway/`

---

## ARCHITECTURE SUMMARY

```
Windows Development Machine
├── DevContainer (lucid-devcontainer)
│   ├── Docker-in-Docker build factory
│   ├── Network: 172.20.0.0/16
│   └── VS Code development environment
└── Core Services (local testing)
    ├── MongoDB 7
    ├── Tor Proxy  
    ├── API Server
    └── Network: 172.21.0.0/16

Raspberry Pi 5 (Production)
├── SSH: pickme@192.168.0.75
├── Architecture: ARM64 (aarch64)
├── OS: Ubuntu 24.04
└── Services: MongoDB, Tor, APIs
    └── Network: 172.21.0.0/16
```

This deployment system follows SPEC-4 clustered build stages and LUCID-STRICT mode requirements for professional, production-ready infrastructure.