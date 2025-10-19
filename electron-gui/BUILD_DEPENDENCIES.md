# Electron GUI Build Dependencies

## Overview

This document outlines all dependencies required for the Electron GUI build process, ensuring compatibility with the Docker build process and API build progression.

## System Dependencies

### Required Software

| Software | Version | Purpose | Platform |
|----------|---------|---------|----------|
| Node.js | v18.x+ | Runtime environment | Windows 11, Linux ARM64 |
| npm | v9.x+ | Package manager | Windows 11, Linux ARM64 |
| Electron | v28.1.0 | Desktop framework | Windows 11, Linux ARM64 |
| Docker Desktop | Latest | Container orchestration | Windows 11 |
| Git | Latest | Version control | Windows 11, Linux ARM64 |
| SSH | Latest | Pi deployment | Windows 11 |

### Build Tools

| Tool | Version | Purpose |
|------|---------|---------|
| TypeScript | ^5.3.3 | Type checking and compilation |
| Webpack | ^5.89.0 | Module bundling |
| Electron Builder | ^24.9.1 | Application packaging |
| Jest | ^29.7.0 | Testing framework |
| ESLint | ^8.55.0 | Code linting |

## Package Dependencies

### Main Dependencies

```json
{
  "dependencies": {
    "axios": "^1.6.2",
    "dockerode": "^4.0.2", 
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "socks-proxy-agent": "^8.0.2",
    "tor-control": "^0.1.1",
    "zustand": "^4.4.7"
  }
}
```

### Development Dependencies

```json
{
  "devDependencies": {
    "@types/node": "^20.10.0",
    "@types/react": "^18.2.45",
    "@types/react-dom": "^18.2.18",
    "@typescript-eslint/eslint-plugin": "^6.14.0",
    "@typescript-eslint/parser": "^6.14.0",
    "concurrently": "^8.2.2",
    "electron": "^28.1.0",
    "electron-builder": "^24.9.1",
    "eslint": "^8.55.0",
    "jest": "^29.7.0",
    "spectron": "^19.0.0",
    "ts-loader": "^9.5.1",
    "typescript": "^5.3.3",
    "webpack": "^5.89.0",
    "webpack-cli": "^5.1.4",
    "webpack-dev-server": "^4.15.1"
  }
}
```

## Docker Build Process Dependencies

### Phase 1: Foundation Services

| Service | Port | Purpose | GUI Integration |
|---------|------|---------|-----------------|
| MongoDB | 27017 | Database | All GUIs (via API) |
| Redis | 6379 | Cache/Session | All GUIs (via API) |
| Elasticsearch | 9200 | Search | Admin/Developer GUIs |
| Auth Service | 8089 | Authentication | All GUIs |

### Phase 2: Core Services

| Service | Port | Purpose | GUI Integration |
|---------|------|---------|-----------------|
| API Gateway | 8080 | Routing | All GUIs |
| Service Mesh | 8086 | Discovery | Admin/Developer GUIs |
| Blockchain Engine | 8084 | Consensus | Admin/Developer GUIs |
| Session Anchoring | 8085 | Blockchain anchoring | Admin/Developer GUIs |
| Block Manager | 8086 | Block validation | Admin/Developer GUIs |
| Data Chain | 8087 | Data storage | All GUIs |

### Phase 3: Application Services

| Service | Port | Purpose | GUI Integration |
|---------|------|---------|-----------------|
| Session Pipeline | 8081 | Session processing | User/Admin GUIs |
| Session Recorder | 8082 | Recording | User/Admin GUIs |
| Session Controller | 8082 | Session control | User/Admin GUIs |
| Session Storage | 8087 | Session data | All GUIs |
| Session API | 8087 | Session management | All GUIs |
| RDP Server Manager | 8081 | RDP management | Admin GUI |
| XRDP Integration | 3389 | RDP protocol | Admin GUI |
| Resource Monitor | 8090 | Resource tracking | Node/Admin GUIs |
| Node Management | 8095 | Node operations | Node/Admin GUIs |

### Phase 4: Support Services

| Service | Port | Purpose | GUI Integration |
|---------|------|---------|-----------------|
| Admin Interface | 8083 | Administration | Admin GUI |
| TRON Client | 8091 | TRON integration | Admin GUI |
| Payout Router | 8092 | Payment routing | Admin GUI |
| Wallet Manager | 8093 | Wallet management | Admin GUI |
| USDT Manager | 8094 | USDT operations | Admin GUI |
| TRX Staking | 8096 | Staking operations | Admin GUI |
| Payment Gateway | 8097 | Payment processing | Admin GUI |

## API Build Progression Dependencies

### Steps 1-6: Foundation Services

**Required for GUI Development:**
- Auth Service (Step 6) - JWT authentication
- MongoDB (Step 1) - User data storage
- Redis (Step 2) - Session management
- Elasticsearch (Step 3) - Search functionality

**GUI Integration Points:**
- User authentication flow
- Session management
- Hardware wallet integration
- TRON signature verification

### Steps 7-14: Core Services

**Required for GUI Development:**
- API Gateway (Step 8) - Request routing
- Service Mesh (Step 9) - Service discovery
- Blockchain Engine (Step 10) - Consensus mechanism
- Session Anchoring (Step 11) - Blockchain anchoring

**GUI Integration Points:**
- API routing and load balancing
- Service health monitoring
- Blockchain status display
- Transaction monitoring

### Steps 15-28: Application Services

**Required for GUI Development:**
- Session Management Pipeline (Step 15) - Session processing
- RDP Services (Step 19) - Remote desktop
- Node Management (Step 23) - Node operations
- Admin Backend APIs (Step 23) - Administration

**GUI Integration Points:**
- Session creation and management
- RDP connection handling
- Node registration and monitoring
- Administrative functions

### Steps 29-35: Support Services

**Required for GUI Development:**
- TRON Payment APIs (Step 26) - Payment processing
- TRON Containers (Step 27) - Payment services
- Multi-platform builds (Step 35) - Cross-platform support

**GUI Integration Points:**
- Payment processing
- Wallet management
- Cross-platform deployment
- Pi-specific optimizations

## Tor Integration Dependencies

### Tor Binary Requirements

| Platform | Binary | Size | Purpose |
|----------|--------|------|---------|
| Windows | tor.exe | ~15MB | Windows Tor daemon |
| Linux ARM64 | tor | ~12MB | Pi Tor daemon |
| macOS | tor | ~12MB | macOS Tor daemon |

### Tor Configuration

```json
{
  "socksPort": 9050,
  "controlPort": 9051,
  "dataDirectory": "./assets/tor",
  "logLevel": "notice",
  "exitNodes": [],
  "strictNodes": false,
  "allowSingleHopExits": false,
  "bootstrapTimeout": 300,
  "circuitBuildTimeout": 60
}
```

### Tor Dependencies

- **socks-proxy-agent**: SOCKS5 proxy integration
- **tor-control**: Tor daemon control
- **axios**: HTTP client with proxy support

## Hardware Wallet Dependencies

### Supported Wallets

| Wallet | Library | Purpose |
|--------|---------|---------|
| Ledger | @ledgerhq/hw-app-tron | TRON operations |
| Trezor | @trezor/connect | TRON operations |
| KeepKey | @keepkey/hdwallet | TRON operations |

### Hardware Wallet Integration

- USB device detection
- TRON signature verification
- Secure key management
- Payment processing

## Docker Integration Dependencies

### Docker API Requirements

- **dockerode**: Docker API client
- **SSH**: Remote Docker access
- **Docker Compose**: Service orchestration

### Docker Configuration

```json
{
  "host": "192.168.0.75",
  "port": 2375,
  "ssh": {
    "host": "192.168.0.75",
    "user": "pickme",
    "port": 22,
    "keyPath": "~/.ssh/id_rsa"
  },
  "deployDir": "/opt/lucid/production"
}
```

## Build Environment Dependencies

### Windows 11 Development

```bash
# Required environment variables
NODE_ENV=development
ELECTRON_ENV=development
TOR_ENABLED=true
DOCKER_HOST=tcp://192.168.0.75:2375
```

### Raspberry Pi 5 Deployment

```bash
# Required environment variables
NODE_ENV=production
ELECTRON_ENV=production
TOR_ENABLED=true
DOCKER_HOST=tcp://localhost:2375
```

## Network Dependencies

### Required Ports

| Port | Service | Purpose |
|------|---------|---------|
| 9050 | Tor SOCKS5 | Proxy communication |
| 9051 | Tor Control | Tor daemon control |
| 2375 | Docker API | Container management |
| 22 | SSH | Pi deployment |
| 8080-8097 | Lucid Services | API communication |

### Network Configuration

- **Tor SOCKS5 Proxy**: All external communication
- **Docker API**: Service orchestration
- **SSH**: Remote deployment
- **API Endpoints**: Service communication

## Security Dependencies

### Security Requirements

- **Context Isolation**: Secure renderer processes
- **Tor Integration**: Anonymous communication
- **Hardware Wallet**: Secure key management
- **TRON Blockchain**: Payment processing

### Security Dependencies

- **socks-proxy-agent**: Secure proxy communication
- **tor-control**: Tor daemon security
- **Hardware wallet libraries**: Secure key management
- **TRON libraries**: Blockchain security

## Performance Dependencies

### Performance Requirements

- **App Startup**: < 5 seconds
- **Tor Bootstrap**: < 30 seconds
- **Docker Service Startup**: < 60 seconds
- **API Response Time**: < 500ms
- **Memory Usage**: < 512MB per process
- **CPU Usage**: < 10% idle

### Performance Dependencies

- **Webpack**: Module bundling optimization
- **Electron Builder**: Application packaging
- **Jest**: Testing performance
- **TypeScript**: Compilation optimization

## Testing Dependencies

### Testing Framework

- **Jest**: Unit testing
- **Spectron**: E2E testing
- **React Testing Library**: Component testing
- **Electron Testing**: Main process testing

### Testing Requirements

- **Unit Tests**: All components
- **E2E Tests**: Full user workflows
- **Integration Tests**: API communication
- **Performance Tests**: Load testing

## Deployment Dependencies

### Deployment Targets

| Platform | Architecture | Purpose |
|----------|--------------|---------|
| Windows | x64 | Development |
| Linux ARM64 | aarch64 | Pi deployment |
| macOS | x64/ARM64 | Development |

### Deployment Requirements

- **Electron Builder**: Multi-platform packaging
- **Docker**: Container deployment
- **SSH**: Remote deployment
- **Tor**: Secure communication

## Compliance Dependencies

### Docker Build Process Compliance

- **Distroless Containers**: Security compliance
- **Multi-stage Builds**: Optimization compliance
- **Service Orchestration**: Docker Compose compliance
- **Network Isolation**: Security compliance

### API Build Progression Compliance

- **Phase 1**: Foundation services integration
- **Phase 2**: Core services integration
- **Phase 3**: Application services integration
- **Phase 4**: Support services integration

## Troubleshooting Dependencies

### Common Issues

| Issue | Dependency | Solution |
|-------|-------------|----------|
| Tor Connection Failed | tor-control | Check Tor binary |
| Docker Connection Failed | dockerode | Check Docker daemon |
| API Connection Failed | axios | Check Tor proxy |
| Hardware Wallet Not Detected | Hardware libraries | Check USB connection |

### Debug Dependencies

- **Debug logging**: Development debugging
- **Tor status**: Tor daemon monitoring
- **Docker status**: Container monitoring
- **API testing**: Connectivity testing

---

**Created**: 2025-01-27  
**Project**: Lucid Electron GUI Dependencies  
**Status**: Complete Dependencies Guide ✅
