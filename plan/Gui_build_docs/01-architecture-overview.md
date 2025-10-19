# Electron GUI Architecture Overview

## Multi-Window Architecture

The Lucid Electron GUI implements a sophisticated multi-window architecture designed for different user roles and access levels.

### Main Process Responsibilities

The main process serves as the central coordinator for the entire application:

- **Tor Daemon Management**: Spawns and manages the bundled Tor binary
- **Docker Service Orchestration**: Controls backend services based on user level
- **IPC Communication**: Facilitates secure communication between main and renderer processes
- **Window Lifecycle Management**: Creates, manages, and coordinates multiple BrowserWindow instances
- **Security Enforcement**: Ensures context isolation and secure IPC patterns

### Renderer Process Architecture

Four distinct renderer processes provide specialized interfaces:

#### 1. User GUI (`user-gui`)
- **Purpose**: End-user interface for session management and file operations
- **Access Level**: Connects to running services (no backend management)
- **Key Features**:
  - Session creation and management
  - Chunk upload/download operations
  - Proof verification and Merkle tree validation
  - TRON wallet integration for payments
  - Real-time connection status monitoring

#### 2. Developer GUI (`developer-gui`)
- **Purpose**: Development tools and backend service management
- **Access Level**: Can start/stop Phase 1-3 services (Core + Application)
- **Key Features**:
  - Backend service management (Docker orchestration)
  - API endpoint testing (Postman-like interface)
  - Blockchain explorer for transaction monitoring
  - Real-time log streaming from containers
  - Performance metrics dashboard
  - Session pipeline debugging tools

#### 3. Node GUI (`node-gui`)
- **Purpose**: Node operator interface for network participation
- **Access Level**: Connects to running services (no backend management)
- **Key Features**:
  - Node registration and authentication
  - Pool management (join/leave pools)
  - Resource monitoring (CPU, memory, disk usage)
  - PoOT (Proof of Observation Time) score tracking
  - Payout history and earnings management
  - Session observation tracking

#### 4. Admin GUI (`admin-gui`)
- **Purpose**: System administration and full-stack management
- **Access Level**: Can start/stop all services (Phases 1-4)
- **Key Features**:
  - Full backend service management
  - System-wide monitoring dashboard
  - User account management with RBAC
  - Session lifecycle monitoring
  - Node pool administration
  - TRON payment management
  - Emergency controls (lockdown, shutdown)
  - Comprehensive audit log viewer

## Technology Stack

### Core Framework
- **Electron 28.x**: Multi-process architecture with context isolation
- **Node.js**: Backend service management and Tor integration
- **TypeScript**: Type-safe development across all components

### Frontend Technologies
- **React 18**: Component-based UI development
- **Zustand**: Lightweight state management (already used in existing GUIs)
- **Axios**: HTTP client with Tor proxy integration
- **Webpack**: Module bundling and development server

### Security & Privacy
- **Tor Integration**: Bundled Tor binary with SOCKS5 proxy
- **Context Isolation**: Secure IPC communication patterns
- **Hardware Wallet Support**: Ledger, Trezor, KeepKey integration
- **TRON Blockchain**: Payment processing and authentication

### Backend Integration
- **Docker API**: Service orchestration via dockerode
- **Tor Control**: Circuit management and onion routing
- **REST APIs**: Communication with Lucid backend services
- **WebSocket**: Real-time updates and monitoring

## Security Architecture

### Context Isolation
All renderer processes operate with strict context isolation:
- No `nodeIntegration` enabled in any renderer
- All IPC communication via preload scripts
- Secure context bridge for API exposure

### Tor Integration
- All external communication routed through Tor SOCKS5 proxy
- Dynamic circuit creation for .onion endpoints
- No plaintext .onion addresses in logs or UI
- Automatic Tor daemon management

### Hardware Wallet Security
- Secure hardware wallet integration
- TRON signature-based authentication
- Isolated payment processing
- No private key exposure

## File Structure

```
electron-gui/
├── main/                          # Main process code
│   ├── index.ts                   # Electron entry point
│   ├── tor-manager.ts             # Tor daemon management
│   ├── docker-manager.ts          # Docker service management
│   ├── window-manager.ts          # Multi-window coordination
│   └── ipc-handlers.ts            # IPC event handlers
├── renderer/                      # Renderer processes
│   ├── user/                      # User GUI
│   ├── developer/                 # Developer GUI
│   ├── node/                      # Node GUI
│   └── admin/                     # Admin GUI
├── shared/                        # Shared utilities
│   ├── api-client.ts              # Tor-proxied API client
│   ├── constants.ts               # API endpoints, ports
│   └── types.ts                   # TypeScript interfaces
├── assets/                        # Tor binaries, icons
│   └── tor/
│       ├── tor.exe                # Windows Tor binary
│       └── torrc.template         # Tor configuration
├── package.json
├── tsconfig.json
└── electron-builder.json          # Build configuration
```

## Access Control Matrix

| GUI Type | Backend Management | Service Access | Admin Functions |
|----------|-------------------|----------------|-----------------|
| User | ❌ | Connect Only | ❌ |
| Developer | Phase 1-3 | Full Access | ❌ |
| Node | ❌ | Connect Only | ❌ |
| Admin | All Phases | Full Access | ✅ |

## Performance Requirements

- **App Startup**: < 5 seconds
- **Tor Bootstrap**: < 30 seconds
- **Docker Service Startup**: < 60 seconds (admin/dev)
- **API Response Time**: < 500ms (via Tor proxy)
- **Memory Usage**: < 512MB per renderer process
- **CPU Usage**: < 10% during idle state

## Compliance Requirements

- All containers use distroless base images
- Tor binary bundled and isolated
- No external dependencies for core functionality
- Hardware wallet integration tested
- TRON payment isolation verified
- Security audit compliance maintained
