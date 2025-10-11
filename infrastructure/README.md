# LUCID Infrastructure Directory Structure

## Overview

This directory contains all infrastructure-related files for the Lucid RDP project, properly organized to separate infrastructure concerns from application code.

## Directory Structure

```javascript

infrastructure/
├── docker/                          # All Dockerfiles organized by service type
│   ├── sessions/                    # Session-related services
│   │   ├── Dockerfile.keystroke-monitor.distroless
│   │   ├── Dockerfile.window-focus-monitor.distroless
│   │   ├── Dockerfile.resource-monitor.distroless
│   │   ├── Dockerfile.session-recorder
│   │   ├── Dockerfile.orchestrator
│   │   ├── Dockerfile.chunker
│   │   ├── Dockerfile.merkle-builder
│   │   └── Dockerfile.encryptor
│   ├── rdp/                         # RDP-related services
│   │   ├── Dockerfile.rdp-host.distroless
│   │   ├── Dockerfile.clipboard-handler.distroless
│   │   ├── Dockerfile.file-transfer-handler.distroless
│   │   ├── Dockerfile.wayland-integration.distroless
│   │   ├── Dockerfile.server-manager
│   │   ├── Dockerfile.server-manager.simple
│   │   └── Dockerfile.xrdp-integration
│   ├── wallet/                      # Wallet services
│   ├── blockchain/                 # Blockchain services
│   ├── admin/                      # Admin UI services
│   ├── node/                       # Node services
│   ├── common/                     # Common services
│   ├── payment-systems/           # Payment system services
│   └── tools/                      # Tool services
├── compose/                        # Docker Compose files
└── README.md                       # This file

```dockerfile

## Benefits of This Structure

### 1. **Separation of Concerns**

- **Application Code**: Remains in `sessions/`, `RDP/`, `wallet/`, etc.

- **Infrastructure Code**: Centralized in `infrastructure/`

- **Clear Boundaries**: Easy to distinguish between code and infrastructure

### 2. **Improved Maintainability**

- **Logical Grouping**: Dockerfiles grouped by service type

- **Easier Navigation**: Developers know exactly where to find infrastructure files

- **Version Control**: Infrastructure changes are isolated from application changes

### 3. **Better CI/CD**

- **Build Context**: All Dockerfiles use project root as build context

- **Consistent Paths**: COPY commands reference correct source paths

- **Parallel Builds**: Different service types can be built independently

### 4. **Team Collaboration**

- **Role Separation**: Developers focus on code, DevOps on infrastructure

- **Clear Ownership**: Infrastructure team owns `infrastructure/` directory

- **Reduced Conflicts**: Less chance of merge conflicts between code and infrastructure

## Dockerfile Organization

### Sessions Services

All session-related Dockerfiles are in `infrastructure/docker/sessions/`:

- **Keystroke Monitor**: Cross-platform keystroke capture

- **Window Focus Monitor**: Window focus tracking

- **Resource Monitor**: System resource monitoring

- **Session Recorder**: Session recording and metadata

- **Orchestrator**: Session orchestration

- **Chunker**: Data chunking for sessions

- **Merkle Builder**: Merkle tree construction

- **Encryptor**: Session data encryption

### RDP Services

All RDP-related Dockerfiles are in `infrastructure/docker/rdp/`:

- **RDP Host**: Main RDP hosting service

- **Clipboard Handler**: Clipboard transfer management

- **File Transfer Handler**: File transfer management

- **Wayland Integration**: Wayland display server integration

- **Server Manager**: RDP server management

- **XRDP Integration**: XRDP server integration

## Build Context and COPY Commands

All Dockerfiles use the project root as build context and reference source paths correctly:

```dockerfile

# Build context is project root

# COPY commands reference correct paths

COPY sessions/recorder/ /app/sessions/recorder/
COPY RDP/recorder/ /app/RDP/recorder/
COPY wallet/walletd/ /app/wallet/walletd/

```

## Rebuild Process

After reorganization, all distroless images can be rebuilt using:

```powershell

# Rebuild all distroless images

.\scripts\rebuild-all-distroless.ps1

# Or rebuild specific service types

docker buildx build --platform linux/amd64,linux/arm64 --file infrastructure/docker/sessions/Dockerfile.keystroke-monitor.distroless --tag pickme/lucid:keystroke-monitor .

```

## Migration Benefits

### Before Reorganization

```

sessions/recorder/
├── audit_trail.py
├── keystroke_monitor.py
├── Dockerfile.keystroke-monitor.distroless  # ❌ Mixed with code
└── Dockerfile.session-recorder              # ❌ Mixed with code

```

### After Reorganization

```

sessions/recorder/                           # ✅ Clean code directory
├── audit_trail.py
├── keystroke_monitor.py
└── window_focus_monitor.py

infrastructure/docker/sessions/              # ✅ Clean infrastructure directory
├── Dockerfile.keystroke-monitor.distroless
└── Dockerfile.session-recorder

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

### 3. **Version Control**

- Commit infrastructure changes separately from code changes

- Use clear commit messages for infrastructure updates

- Tag releases with infrastructure version information

### 4. **Documentation**

- Keep this README updated with new services

- Document any special build requirements

- Maintain service dependency information

## Next Steps

1. **Update Build Scripts**: Modify existing build scripts to use new paths

1. **Update CI/CD**: Update pipeline configurations for new structure

1. **Test Builds**: Verify all services build correctly with new structure

1. **Update Documentation**: Update any documentation referencing old paths

## Support

For questions about the infrastructure reorganization:

- Check this README for common issues

- Review the reorganization script: `scripts/reorganize-infrastructure.ps1`

- Use the rebuild script: `scripts/rebuild-all-distroless.ps1`

This reorganization provides a solid foundation for scalable infrastructure management while maintaining clean separation between application code and infrastructure concerns.
