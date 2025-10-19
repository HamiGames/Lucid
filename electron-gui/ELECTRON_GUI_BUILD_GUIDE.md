# Electron GUI Build Guide

## Overview

This guide provides comprehensive instructions for building the Lucid Electron GUI application, ensuring compatibility with the Docker build process and API build progression outlined in the project documentation.

## Prerequisites

### System Requirements

**Build Host**: Windows 11 console with Docker Desktop + BuildKit  
**Target Host**: Raspberry Pi 5 (192.168.0.75) via SSH (user: pickme)  
**Platform**: linux/arm64 (aarch64) for Pi deployment, win32 for development

### Required Software

1. **Node.js**: v18.x or higher
2. **npm**: v9.x or higher  
3. **Electron**: v28.x (as specified in package.json)
4. **Docker Desktop**: Latest version with BuildKit enabled
5. **Git**: For version control
6. **SSH**: For Pi deployment

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

### Runtime Dependencies

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

## Architecture Overview

### Multi-Window Architecture

The Electron GUI implements a sophisticated multi-window architecture with 4 distinct interfaces:

1. **User GUI** - End-user interface for session management
2. **Developer GUI** - Development tools and backend service management  
3. **Node GUI** - Node operator interface for network participation
4. **Admin GUI** - System administration and full-stack management

### Main Process Components

- **Tor Manager**: Manages bundled Tor binary with SOCKS5 proxy
- **Docker Manager**: Orchestrates backend services via Docker API
- **Window Manager**: Coordinates multiple BrowserWindow instances
- **IPC Handlers**: Secure communication between main and renderer processes

### Renderer Process Architecture

Each GUI type has its own renderer process with:
- React-based UI components
- Zustand state management
- Tor-proxied API communication
- Hardware wallet integration
- Real-time monitoring capabilities

## Build Process

### Phase 1: Environment Setup

#### 1.1 Clone and Setup

```bash
# Navigate to project root
cd Lucid

# Install dependencies
cd electron-gui
npm install

# Verify installation
npm run build:main
npm run build:renderer
```

#### 1.2 Environment Configuration

Create environment files based on the Docker build process:

**Development Environment** (`configs/env.development.json`):
```json
{
  "api": {
    "gateway": "http://localhost:8080",
    "auth": "http://localhost:8089",
    "admin": "http://localhost:8083",
    "blockchain": "http://localhost:8084",
    "session": "http://localhost:8087",
    "node": "http://localhost:8095"
  },
  "tor": {
    "socksPort": 9050,
    "controlPort": 9051,
    "dataDirectory": "./assets/tor"
  },
  "docker": {
    "host": "localhost",
    "port": 2375
  }
}
```

**Production Environment** (`configs/env.production.json`):
```json
{
  "api": {
    "gateway": "http://192.168.0.75:8080",
    "auth": "http://192.168.0.75:8089",
    "admin": "http://192.168.0.75:8083",
    "blockchain": "http://192.168.0.75:8084",
    "session": "http://192.168.0.75:8087",
    "node": "http://192.168.0.75:8095"
  },
  "tor": {
    "socksPort": 9050,
    "controlPort": 9051,
    "dataDirectory": "./assets/tor"
  },
  "docker": {
    "host": "192.168.0.75",
    "port": 2375,
    "ssh": {
      "host": "192.168.0.75",
      "user": "pickme",
      "port": 22
    }
  }
}
```

#### 1.3 Tor Configuration

**Tor Configuration** (`configs/tor.config.json`):
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

### Phase 2: Development Build

#### 2.1 Development Server

```bash
# Start development server
npm run dev

# Or run components separately
npm run dev:main    # Main process
npm run dev:renderer # Renderer processes
```

#### 2.2 Build Process

```bash
# Build main process
npm run build:main

# Build renderer processes  
npm run build:renderer

# Build everything
npm run build
```

#### 2.3 Testing

```bash
# Run unit tests
npm test

# Run E2E tests
npm run test:e2e

# Run specific GUI tests
npm test -- --testNamePattern="admin-gui"
npm test -- --testNamePattern="user-gui"
npm test -- --testNamePattern="developer-gui"
npm test -- --testNamePattern="node-gui"
```

### Phase 3: Production Build

#### 3.1 Multi-Platform Build

```bash
# Build for Windows
npm run package:win

# Build for Linux (Pi target)
npm run package:linux

# Build for macOS
npm run package:mac

# Build for all platforms
npm run package
```

#### 3.2 Docker Integration

**Docker Configuration** (`configs/docker.config.json`):
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
  "deployDir": "/opt/lucid/production",
  "composeFiles": [
    "docker-compose.foundation.yml",
    "docker-compose.core.yml", 
    "docker-compose.application.yml",
    "docker-compose.support.yml"
  ]
}
```

### Phase 4: Deployment

#### 4.1 Pi Deployment

```bash
# Deploy to Raspberry Pi
npm run deploy:pi

# Or manual deployment
scp -r dist/ pickme@192.168.0.75:/opt/lucid/electron-gui/
ssh pickme@192.168.0.75 "cd /opt/lucid/electron-gui && ./lucid-desktop"
```

#### 4.2 Service Integration

The Electron GUI integrates with the Docker build process phases:

**Phase 1 (Foundation)**: Connects to MongoDB, Redis, Elasticsearch, Auth Service
**Phase 2 (Core)**: Integrates with API Gateway, Service Mesh, Blockchain Core
**Phase 3 (Application)**: Manages Session Services, RDP Services, Node Management
**Phase 4 (Support)**: Connects to Admin Interface, TRON Payment Services

## API Integration

### Service Endpoints

The Electron GUI communicates with the following services based on user role:

#### User GUI Endpoints
- Session API (Port 8087)
- Auth Service (Port 8089)
- API Gateway (Port 8080)

#### Developer GUI Endpoints  
- All Phase 1-3 services
- Docker API for service management
- Real-time logs and metrics

#### Node GUI Endpoints
- Node Management (Port 8095)
- Session API (Port 8087)
- Auth Service (Port 8089)

#### Admin GUI Endpoints
- All services (Phases 1-4)
- Admin Interface (Port 8083)
- TRON Payment Services (Ports 8091-8097)

### Tor Integration

All API communication is routed through Tor SOCKS5 proxy:

```typescript
// Example API client configuration
const apiClient = new Axios({
  proxy: {
    host: '127.0.0.1',
    port: 9050,
    protocol: 'socks5'
  },
  timeout: 30000
});
```

### Hardware Wallet Integration

Support for Ledger, Trezor, and KeepKey wallets:

```typescript
// Hardware wallet connection
const connectWallet = async (type: 'ledger' | 'trezor' | 'keepkey') => {
  const wallet = await window.electronAPI.connectHardwareWallet(type);
  return wallet;
};
```

## Security Considerations

### Context Isolation

All renderer processes operate with strict context isolation:
- No `nodeIntegration` enabled
- All IPC communication via preload scripts
- Secure context bridge for API exposure

### Tor Security

- All external communication routed through Tor SOCKS5 proxy
- Dynamic circuit creation for .onion endpoints
- No plaintext .onion addresses in logs or UI
- Automatic Tor daemon management

### Hardware Wallet Security

- Secure hardware wallet integration
- TRON signature-based authentication
- Isolated payment processing
- No private key exposure

## Performance Requirements

- **App Startup**: < 5 seconds
- **Tor Bootstrap**: < 30 seconds  
- **Docker Service Startup**: < 60 seconds (admin/dev)
- **API Response Time**: < 500ms (via Tor proxy)
- **Memory Usage**: < 512MB per renderer process
- **CPU Usage**: < 10% during idle state

## Troubleshooting

### Common Issues

1. **Tor Connection Failed**
   - Check Tor binary in `assets/tor/`
   - Verify SOCKS5 proxy configuration
   - Check firewall settings

2. **Docker Connection Failed**
   - Verify Docker daemon is running
   - Check SSH connection to Pi
   - Verify Docker API port (2375)

3. **API Connection Failed**
   - Check backend services are running
   - Verify Tor proxy is working
   - Check network connectivity

4. **Hardware Wallet Not Detected**
   - Install device drivers
   - Check USB connection
   - Verify wallet is unlocked

### Debug Mode

```bash
# Enable debug logging
DEBUG=electron-gui:* npm run dev

# Check Tor status
npm run tor:status

# Check Docker status  
npm run docker:status

# Check API connectivity
npm run api:test
```

## Build Scripts

### Available Scripts

```json
{
  "scripts": {
    "dev": "concurrently \"npm run dev:main\" \"npm run dev:renderer\"",
    "dev:main": "tsc -p tsconfig.main.json && electron .",
    "dev:renderer": "webpack serve --config webpack.renderer.config.js",
    "build": "npm run build:main && npm run build:renderer",
    "build:main": "tsc -p tsconfig.main.json",
    "build:renderer": "webpack --config webpack.renderer.config.js",
    "package": "electron-builder",
    "package:win": "electron-builder --win",
    "package:linux": "electron-builder --linux", 
    "package:mac": "electron-builder --mac",
    "test": "jest",
    "test:e2e": "jest --config jest.e2e.config.js",
    "deploy:pi": "node scripts/deploy-pi.js",
    "tor:status": "node scripts/tor-status.js",
    "docker:status": "node scripts/docker-status.js",
    "api:test": "node scripts/api-test.js"
  }
}
```

## File Structure

```
electron-gui/
├── main/                          # Main process code
│   ├── index.ts                   # Electron entry point
│   ├── tor-manager.ts             # Tor daemon management
│   ├── docker-manager.ts          # Docker service management
│   ├── window-manager.ts          # Multi-window coordination
│   ├── docker-service.ts          # Docker API integration
│   └── ipc-handlers.ts            # IPC event handlers
├── renderer/                      # Renderer processes
│   ├── user/                      # User GUI
│   ├── developer/                 # Developer GUI
│   ├── node/                      # Node GUI
│   ├── admin/                     # Admin GUI
│   └── common/                    # Shared components
├── shared/                        # Shared utilities
│   ├── api-client.ts              # Tor-proxied API client
│   ├── constants.ts               # API endpoints, ports
│   ├── types.ts                   # TypeScript interfaces
│   ├── tor-types.ts              # Tor-specific types
│   ├── utils.ts                   # Utility functions
│   └── ipc-channels.ts           # IPC channel definitions
├── assets/                        # Static assets
│   ├── icons/                     # Application icons
│   ├── images/                    # Images
│   └── tor/                       # Tor binaries
├── configs/                       # Configuration files
│   ├── tor.config.json           # Tor configuration
│   ├── docker.config.json        # Docker configuration
│   ├── env.development.json       # Development environment
│   └── env.production.json        # Production environment
├── scripts/                       # Build and deployment scripts
│   ├── build.js                   # Build automation
│   ├── dev.js                     # Development startup
│   ├── deploy-pi.js               # Pi deployment
│   ├── tor-status.js              # Tor status check
│   ├── docker-status.js           # Docker status check
│   └── api-test.js                # API connectivity test
├── tests/                         # Test files
│   ├── main.spec.ts               # Main process tests
│   ├── admin-gui.spec.ts          # Admin GUI tests
│   ├── user-gui.spec.ts           # User GUI tests
│   ├── developer-gui.spec.ts      # Developer GUI tests
│   ├── node-gui.spec.ts           # Node GUI tests
│   └── e2e/                       # End-to-end tests
├── package.json                   # Dependencies and scripts
├── tsconfig.json                  # TypeScript configuration
├── tsconfig.main.json             # Main process TypeScript config
├── webpack.common.js              # Shared webpack configuration
├── webpack.main.config.js         # Main process webpack config
├── webpack.renderer.config.js     # Renderer process webpack config
├── electron-builder.yml           # Build configuration
├── jest.config.js                 # Jest configuration
├── jest.e2e.config.js             # E2E test configuration
└── ELECTRON_GUI_BUILD_GUIDE.md    # This guide
```

## Compliance with Docker Build Process

### Phase Alignment

The Electron GUI build process aligns with the Docker build process phases:

**Pre-Build Phase**: Environment setup, Tor configuration, Docker integration
**Phase 1**: Foundation services integration (MongoDB, Redis, Auth)
**Phase 2**: Core services integration (API Gateway, Blockchain)
**Phase 3**: Application services integration (Sessions, RDP, Nodes)
**Phase 4**: Support services integration (Admin, TRON payments)

### API Build Progression

The GUI development follows the API build progression:

**Steps 1-6**: Foundation services (Auth, Storage)
**Steps 7-14**: Core services (Gateway, Blockchain)
**Steps 15-28**: Application services (Sessions, RDP, Nodes)
**Steps 29-35**: Support services (Admin, TRON payments)

### Distroless Compliance

The Electron GUI integrates with distroless containers:
- No direct container management
- API communication only
- Tor proxy for all external communication
- Hardware wallet integration for authentication

## Next Steps

1. **Complete Development**: Finish implementing all GUI components
2. **Integration Testing**: Test with Docker build process phases
3. **Performance Optimization**: Optimize for Pi deployment
4. **Security Audit**: Review Tor and hardware wallet integration
5. **Production Deployment**: Deploy to Pi with full service stack

---

**Created**: 2025-01-27  
**Project**: Lucid Electron GUI Build Guide  
**Status**: Complete Build Guide ✅
