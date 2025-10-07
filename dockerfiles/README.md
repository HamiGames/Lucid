# LUCID Centralized Dockerfiles Directory

## Overview

This directory contains all Dockerfiles for the Lucid RDP project, centralized for better organization and maintainability. All Dockerfiles reference modules from their actual locations in the codebase.

## Directory Structure

```
dockerfiles/
├── sessions/                    # Session-related services
│   ├── Dockerfile.keystroke-monitor.distroless
│   ├── Dockerfile.window-focus-monitor.distroless
│   ├── Dockerfile.resource-monitor.distroless
│   ├── Dockerfile.session-recorder
│   ├── Dockerfile.orchestrator
│   ├── Dockerfile.chunker
│   ├── Dockerfile.merkle-builder
│   └── Dockerfile.encryptor
├── rdp/                        # RDP-related services
│   ├── Dockerfile.rdp-host.distroless
│   ├── Dockerfile.clipboard-handler.distroless
│   ├── Dockerfile.file-transfer-handler.distroless
│   ├── Dockerfile.wayland-integration.distroless
│   ├── Dockerfile.server-manager
│   ├── Dockerfile.server-manager.simple
│   └── Dockerfile.xrdp-integration
├── wallet/                     # Wallet services
│   ├── Dockerfile.software-vault.distroless
│   ├── Dockerfile.role-manager.distroless
│   └── Dockerfile.key-rotation.distroless
├── blockchain/                 # Blockchain services
│   ├── Dockerfile.api
│   ├── Dockerfile.api.distroless
│   ├── Dockerfile.chain-client
│   ├── Dockerfile.contract-deployment
│   ├── Dockerfile.contract-deployment.simple
│   ├── Dockerfile.lucid-anchors-client.distroless
│   └── Dockerfile.on-system-chain-client.distroless
├── admin/                      # Admin UI services
│   ├── Dockerfile.admin-ui
│   └── Dockerfile.admin-ui.distroless
├── node/                       # Node services
│   ├── Dockerfile.dht-node
│   ├── Dockerfile.leader-selection.distroless
│   └── Dockerfile.task-proofs.distroless
├── common/                     # Common services
│   ├── Dockerfile.server-tools
│   ├── Dockerfile.server-tools.distroless
│   ├── Dockerfile.lucid-governor.distroless
│   └── Dockerfile.timelock.distroless
├── payment-systems/           # Payment system services
│   ├── Dockerfile.tron-client
│   ├── Dockerfile.payout-router-v0.distroless
│   └── Dockerfile.usdt-trc20.distroless
└── tools/                      # Tool services (future)
```

## Key Benefits

### 1. **Centralized Management**
- All Dockerfiles in one location
- Easy to find and maintain
- Clear separation from application code

### 2. **Clean Application Directories**
- Application code directories contain only Python modules
- No Dockerfiles mixed with source code
- Clear separation of concerns

### 3. **Consistent Build Context**
- All Dockerfiles use project root as build context
- COPY commands reference modules from their actual locations
- Consistent build process across all services

### 4. **Better Organization**
- Dockerfiles grouped by service type
- Easy to understand service relationships
- Scalable structure for future services

## Build Context and COPY Commands

All Dockerfiles use the project root as build context and reference source paths correctly:

```dockerfile
# Build context is project root
# COPY commands reference correct paths
COPY sessions/recorder/ /app/sessions/recorder/
COPY RDP/recorder/ /app/RDP/recorder/
COPY wallet/walletd/ /app/wallet/walletd/
COPY blockchain/chain-client/ /app/blockchain/chain-client/
```

## Service Categories

### **Sessions Services** (`dockerfiles/sessions/`)
- **Keystroke Monitor**: Cross-platform keystroke capture
- **Window Focus Monitor**: Window focus tracking
- **Resource Monitor**: System resource monitoring
- **Session Recorder**: Session recording and metadata
- **Orchestrator**: Session orchestration
- **Chunker**: Data chunking for sessions
- **Merkle Builder**: Merkle tree construction
- **Encryptor**: Session data encryption

### **RDP Services** (`dockerfiles/rdp/`)
- **RDP Host**: Main RDP hosting service
- **Clipboard Handler**: Clipboard transfer management
- **File Transfer Handler**: File transfer management
- **Wayland Integration**: Wayland display server integration
- **Server Manager**: RDP server management
- **XRDP Integration**: XRDP server integration

### **Wallet Services** (`dockerfiles/wallet/`)
- **Software Vault**: Passphrase-protected vault
- **Role Manager**: Role-based access control
- **Key Rotation**: Key rotation system

### **Blockchain Services** (`dockerfiles/blockchain/`)
- **API**: Blockchain API service
- **Chain Client**: On-system chain client
- **Contract Deployment**: Smart contract deployment
- **Lucid Anchors Client**: LucidAnchors contract client
- **On-System Chain Client**: On-System Chain client

### **Admin Services** (`dockerfiles/admin/`)
- **Admin UI**: Web-based administration interface

### **Node Services** (`dockerfiles/node/`)
- **DHT Node**: Distributed hash table node
- **Leader Selection**: Consensus leader selection
- **Task Proofs**: Task proof collection

### **Common Services** (`dockerfiles/common/`)
- **Server Tools**: Common server utilities
- **Lucid Governor**: Governance system
- **Timelock**: Timelock implementation

### **Payment Systems** (`dockerfiles/payment-systems/`)
- **TRON Client**: TRON blockchain client
- **Payout Router V0**: No-KYC payout router
- **USDT TRC20**: USDT-TRC20 integration

## Build Process

### **Individual Service Build**
```bash
# Build a specific service
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --file dockerfiles/sessions/Dockerfile.keystroke-monitor.distroless \
  --tag pickme/lucid:keystroke-monitor \
  .
```

### **All Services Build**
```bash
# Build all services (use the rebuild script)
.\scripts\rebuild-all-distroless.ps1
```

## Best Practices

### 1. **Dockerfile Naming**
- Use descriptive names: `Dockerfile.service-name.distroless`
- Include service type in directory structure
- Maintain consistent naming conventions

### 2. **Build Context**
- Always use project root as build context
- Reference source paths from project root
- Keep COPY commands consistent across all Dockerfiles

### 3. **Service Organization**
- Group related services in same directory
- Use logical service categories
- Maintain clear service boundaries

### 4. **Documentation**
- Keep this README updated with new services
- Document any special build requirements
- Maintain service dependency information

## Migration Benefits

### **Before Centralization (Problems)**
```
sessions/recorder/
├── audit_trail.py
├── keystroke_monitor.py
├── Dockerfile.keystroke-monitor.distroless  # ❌ Mixed with code
└── Dockerfile.session-recorder              # ❌ Mixed with code

wallet/walletd/
├── software_vault.py
├── role_manager.py
├── Dockerfile.software-vault.distroless     # ❌ Mixed with code
└── Dockerfile.role-manager.distroless       # ❌ Mixed with code
```

### **After Centralization (Solutions)**
```
sessions/recorder/                           # ✅ Clean code directory
├── audit_trail.py
├── keystroke_monitor.py
└── window_focus_monitor.py

wallet/walletd/                              # ✅ Clean code directory
├── software_vault.py
├── role_manager.py
└── key_rotation.py

dockerfiles/                                 # ✅ Centralized Dockerfiles
├── sessions/
│   ├── Dockerfile.keystroke-monitor.distroless
│   └── Dockerfile.session-recorder
└── wallet/
    ├── Dockerfile.software-vault.distroless
    └── Dockerfile.role-manager.distroless
```

## Future Additions

When adding new services:

1. **Create the service module** in the appropriate application directory
2. **Create the Dockerfile** in the appropriate `dockerfiles/` subdirectory
3. **Update this README** with the new service information
4. **Update build scripts** to include the new service

## Support

For questions about the centralized Docker structure:
- Check this README for common issues
- Review the centralization script: `scripts/centralize-dockerfiles.ps1`
- Use the rebuild script: `scripts/rebuild-all-distroless.ps1`

This centralized structure provides a clean, maintainable, and scalable approach to Docker container management for the Lucid RDP project! 🚀
