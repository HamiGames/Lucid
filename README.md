# Lucid - Professional Multi-Onion Infrastructure Platform

A comprehensive Docker-based development platform with advanced Tor multi-onion capabilities, optimized for both development and Raspberry Pi deployment.

## 🏗️ Project Structure

```
Lucid/
├── 📁 build/                          # Build artifacts and logs
│   ├── artifacts/                     # Build outputs
│   └── logs/                         # Build logs
├── 📁 configs/                       # Configuration files
│   ├── docker/                       # Docker configurations
│   ├── environment/                  # Environment files (.env.*)
│   ├── ssh/                         # SSH keys and configuration
│   └── *.yaml                       # Global configuration files
├── 📁 docs/                          # Documentation
│   ├── build-docs/                   # Build guides and specifications
│   ├── guides/                       # User guides and manuals
│   ├── specs/                        # Technical specifications
│   └── verification/                 # Testing and verification reports
├── 📁 infrastructure/                # Infrastructure as Code
│   ├── compose/                      # Docker Compose files
│   └── containers/                   # Container configurations
├── 📁 scripts/                       # Automation scripts
│   ├── build/                        # Build automation
│   ├── deployment/                   # Deployment scripts
│   ├── devcontainer/                 # Development container scripts
│   └── network/                      # Network and security scripts
├── 📁 02-network-security/           # Core networking components
│   ├── tor/                          # Tor proxy with multi-onion support
│   └── tunnels/                      # Network tunneling tools
├── 📁 03-api-gateway/                # API services
│   ├── api/                          # Core API server
│   └── gateway/                      # API gateway (NGINX)
└── 📁 common/                        # Shared components
    └── server-tools/                 # Utility services
```

## 🚀 Quick Start

### Prerequisites
- Docker Desktop (with WSL2 on Windows)
- VS Code with Remote-Containers extension
- Git

### 1. Development Environment Setup

```bash
# Clone the repository
git clone https://github.com/HamiGames/Lucid.git
cd Lucid

# Open in VS Code Dev Container
code .
# Then: Ctrl+Shift+P -> "Dev Containers: Reopen in Container"
```

### 2. Start Core Services

```bash
# Navigate to compose directory
cd infrastructure/compose

# Start the core support stack
docker compose -f lucid-dev.yaml up -d

# Check service status
docker compose -f lucid-dev.yaml ps
```

## 🔐 Multi-Onion System

Lucid features an advanced **multi-onion architecture** with both static and dynamic onion creation capabilities:

### Static Core Services (5 Onions)
- **API Gateway** - `ONION_API_GATEWAY`
- **API Server** - `ONION_API_SERVER` 
- **Tunnel Service** - `ONION_TUNNEL`
- **MongoDB Proxy** - `ONION_MONGO`
- **Tor Control** - `ONION_TOR_CONTROL`

### Dynamic Onion Creation
Create onions on-demand for wallets and runtime services:

```bash
# Create wallet onion with secure defaults
./02-network-security/tor/scripts/create_dynamic_onion.sh --wallet wallet-primary

# Create custom service onion
./02-network-security/tor/scripts/create_dynamic_onion.sh \
  --target-host payment-api --target-port 8443 --onion-port 443 payments

# List all dynamic onions
./02-network-security/tor/scripts/create_dynamic_onion.sh --list

# Rotate (refresh) an onion address
./02-network-security/tor/scripts/create_dynamic_onion.sh --rotate wallet-primary
```

## 🛠️ Development

### Core Services
- **MongoDB 7** - Replica set database (172.21.0.10)
- **Tor Proxy** - Multi-onion controller (172.21.0.11)
- **API Server** - FastAPI/Python service (172.21.0.12)
- **API Gateway** - NGINX reverse proxy (172.21.0.13)
- **Tunnel Tools** - Network security (172.21.0.14)
- **Server Tools** - Utilities and diagnostics (172.21.0.15)

### Network Architecture
- **Internal Network** (`lucid_core_net`): 172.21.0.0/16 - Isolated ops plane
- **External Network** (`lucid_dev_net`): Development container connectivity
- **Dual-plane isolation**: Internal services + external accessibility

## 📦 Build System

### Multi-platform Support
All services support both AMD64 and ARM64 architectures for Raspberry Pi deployment:

```bash
# Build for multiple platforms
docker buildx build --platform linux/amd64,linux/arm64 -t service:latest .
```

### Environment Files
- `configs/environment/.env.api` - API configuration
- `configs/environment/.env.user` - User settings
- Generated onion environments:
  - `/run/lucid/onion/multi-onion.env` - Static onions
  - `/run/lucid/onion/dynamic-onions.env` - Dynamic onions

## 🔒 Security Features

### Tor Integration
- **ED25519-V3 onion addresses** (56 characters)
- **Cookie authentication** with hex encoding
- **Ephemeral onion rotation** for security
- **Wallet-optimized onions** with random high ports

### Container Security
- Non-privileged containers where possible
- Security options: `no-new-privileges`, `seccomp`
- Resource limits for Raspberry Pi optimization
- Professional logging with rotation

## 🐳 Docker Services

### Health Checks
All services include comprehensive health checks:
- MongoDB: Connection and authentication test
- Tor: SOCKS5 proxy validation  
- APIs: HTTP endpoint validation
- Tunnels: Port connectivity checks

### Resource Management
Optimized for Raspberry Pi deployment:
- Memory limits and reservations
- CPU constraints and guarantees
- Optimized cache sizes (MongoDB: 0.5GB WiredTiger cache)

## 🔧 Configuration

### Environment Variables
Core environment variables in `x-lucid-env`:
- `LUCID_ENV=dev` - Environment identifier
- `LUCID_PLANE=ops` - Plane isolation
- `TOR_SOCKS=tor-proxy:9050` - Tor SOCKS proxy
- `MONGO_URL` - Database connection string
- `ONION_*` - Multi-onion addresses

### Labels System
Professional labeling with `org.lucid` namespace:
- `org.lucid.plane=ops` - Plane identification
- `org.lucid.service=<name>` - Service identification
- `org.lucid.tor.*` - Tor-specific metadata

## 📝 Scripts Reference

### DevContainer Scripts (`scripts/devcontainer/`)
- `setup-build-factory.sh` - Build environment setup
- `build-core-support.sh` - Core service builder
- `fix_editor_env.sh` - Editor environment fixes

### Deployment Scripts (`scripts/deployment/`)
- `Setup-DevContainer.ps1` - Windows setup
- `Clean-LucidFromLists.ps1` - Cleanup utility

### Network Scripts (`02-network-security/tor/scripts/`)
- `create_ephemeral_onion.sh` - Static multi-onion creator
- `create_dynamic_onion.sh` - Dynamic onion management
- `demo_onion_usage.sh` - Demonstration script

## 🚨 Troubleshooting

### Common Issues

**Docker Network Issues:**
```bash
# Recreate the development network
docker network rm lucid-dev_lucid_net
docker network create --driver bridge --attachable \
  --subnet=172.20.0.0/16 --gateway=172.20.0.1 lucid-dev_lucid_net
```

**Service Health Checks Failing:**
```bash
# Check service logs
docker compose -f infrastructure/compose/lucid-dev.yaml logs <service-name>

# Restart unhealthy services
docker compose -f infrastructure/compose/lucid-dev.yaml restart <service-name>
```

**Onion Creation Issues:**
```bash
# Check Tor logs
docker logs tor_proxy

# Verify cookie file
docker exec tor_proxy ls -la /var/lib/tor/control_auth_cookie
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Follow the established project structure
4. Test with both AMD64 and ARM64 if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Professional Infrastructure Platform** | **Multi-Onion Security** | **Pi-Optimized**