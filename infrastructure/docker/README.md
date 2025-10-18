# Docker Infrastructure Organization

This directory contains all Dockerfiles organized by functional component areas.

## Directory Structure

### `/admin/`

- **Dockerfile.admin-ui** - Admin UI container

- **Dockerfile.admin-ui.distroless** - Distroless admin UI container

### `/blockchain/`

- **Dockerfile** - Base blockchain container

- **Dockerfile.chain-client** - Blockchain chain client

- **Dockerfile.contract-deployment** - Contract deployment container

- **Dockerfile.contract-deployment.simple** - Simplified contract deployment

- **Dockerfile.distroless** - Distroless blockchain container

- **Dockerfile.lucid-anchors-client.distroless** - Lucid anchors client

- **Dockerfile.on-system-chain-client.distroless** - On-system chain client

### `/common/`

- **Dockerfile** - Base common container

- **Dockerfile.beta** - Beta build container

- **Dockerfile.common** - Common utilities container

- **Dockerfile.common.distroless** - Distroless common container

- **Dockerfile.distroless** - Distroless base container

- **Dockerfile.lucid-governor.distroless** - Lucid governance container

- **Dockerfile.timelock.distroless** - Timelock container

### `/databases/`

- *(Empty - for future database-related containers)*

### `/gui/`

- *(Empty - for future GUI containers)*

### `/node/`

- **Dockerfile.dht-node** - DHT node container

- **Dockerfile.leader-selection.distroless** - Leader selection container

- **Dockerfile.task-proofs.distroless** - Task proofs container

### `/payment-systems/`

- **Dockerfile.payout-router-v0.distroless** - Payout router V0

- **Dockerfile.tron-client** - TRON client container

- **Dockerfile.usdt-trc20.distroless** - USDT TRC20 container

### `/rdp/`

- **Dockerfile.clipboard-handler.distroless** - Clipboard handler

- **Dockerfile.file-transfer-handler.distroless** - File transfer handler

- **Dockerfile.keystroke-monitor.distroless** - Keystroke monitor

- **Dockerfile.rdp-host.distroless** - RDP host container

- **Dockerfile.resource-monitor.distroless** - Resource monitor

- **Dockerfile.server-manager** - Server manager container

- **Dockerfile.server-manager.simple** - Simplified server manager

- **Dockerfile.wayland-integration.distroless** - Wayland integration

- **Dockerfile.window-focus-monitor.distroless** - Window focus monitor

- **Dockerfile.xrdp-integration** - XRDP integration

### `/sessions/`

- **Dockerfile.chunker** - Session chunker container

- **Dockerfile.clipboard-handler.distroless** - Session clipboard handler

- **Dockerfile.encryptor** - Session encryptor container

- **Dockerfile.merkle_builder** - Merkle tree builder

- **Dockerfile.orchestrator** - Session orchestrator

- **Dockerfile.session-recorder** - Session recorder container

### `/tools/`

- *(Empty - for future tool containers)*

### `/users/`

- *(Empty - for future user-related containers)*

### `/vm/`

- *(Empty - for future VM containers)*

### `/wallet/`

- **Dockerfile.key-rotation.distroless** - Key rotation container

- **Dockerfile.role-manager.distroless** - Role manager container

- **Dockerfile.software-vault.distroless** - Software vault container

## Organization Principles

1. **Functional Grouping**: Dockerfiles are organized by the functional area they serve

1. **Distroless Variants**: Security-hardened distroless containers are clearly marked

1. **Naming Convention**: Descriptive names that indicate purpose and variant

1. **Scalability**: Empty directories are prepared for future components

## Build Commands

Each subdirectory can be built independently:

```bash

# Example: Build admin containers

cd admin/
docker build -f Dockerfile.admin-ui -t lucid-admin-ui .
docker build -f Dockerfile.admin-ui.distroless -t lucid-admin-ui-distroless .

```

## Migration Notes

- Previously scattered Dockerfiles in the root directory have been reorganized

- Duplicate files were consolidated to their appropriate subdirectories

- All references should be updated to use the new paths
