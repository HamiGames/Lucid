# Technology Stack Documentation

## Core Dependencies

### Electron Framework
```json
{
  "electron": "^28.0.0",
  "electron-builder": "^24.6.4",
  "electron-dev": "^2.0.0"
}
```

**Purpose**: Multi-process desktop application framework
**Key Features**:
- Multi-window architecture support
- Context isolation for security
- Native OS integration
- Cross-platform compatibility (Windows, Linux, macOS)

### Frontend Framework
```json
{
  "react": "^18.2.0",
  "react-dom": "^18.2.0",
  "@types/react": "^18.2.0",
  "@types/react-dom": "^18.2.0"
}
```

**Purpose**: Component-based UI development
**Integration**: Reuses existing GUI components from `apps/gui-user/` and `apps/gui-admin/`

### State Management
```json
{
  "zustand": "^4.4.0"
}
```

**Purpose**: Lightweight state management
**Rationale**: Already used in existing GUIs, maintains consistency

### HTTP Client & Networking
```json
{
  "axios": "^1.6.0",
  "socks-proxy-agent": "^8.0.0"
}
```

**Purpose**: API communication with Tor proxy integration
**Features**:
- Automatic SOCKS5 proxy routing
- Request/response interceptors
- Error handling with Lucid error codes

## Security & Privacy Stack

### Tor Integration
```json
{
  "tor-control": "^2.0.0"
}
```

**Purpose**: Tor daemon management and circuit control
**Features**:
- Bundled Tor binary management
- Dynamic circuit creation
- SOCKS5 proxy configuration
- Onion address masking

### Hardware Wallet Support
```json
{
  "@ledgerhq/hw-app-tron": "^6.0.0",
  "@trezor/connect": "^9.0.0",
  "tronweb": "^5.0.0"
}
```

**Purpose**: Hardware wallet integration for TRON blockchain
**Supported Devices**:
- Ledger (Nano S, Nano X, Ledger Live)
- Trezor (Model T, One)
- KeepKey (via Trezor compatibility)

## Backend Integration

### Docker Management
```json
{
  "dockerode": "^4.0.0"
}
```

**Purpose**: Docker service orchestration
**Features**:
- Container lifecycle management
- Service health monitoring
- Compose file parsing
- Resource usage tracking

### Blockchain Integration
```json
{
  "web3": "^4.0.0",
  "tronweb": "^5.0.0"
}
```

**Purpose**: Blockchain interaction and smart contract calls
**Features**:
- TRON network integration
- Smart contract interaction
- Transaction monitoring
- Wallet management

## Development Tools

### TypeScript Configuration
```json
{
  "typescript": "^5.0.0",
  "@types/node": "^20.0.0",
  "ts-node": "^10.9.0"
}
```

**Configuration**: Strict mode with comprehensive type checking
**Features**:
- Path mapping for clean imports
- Strict null checks
- No implicit any
- Comprehensive interface definitions

### Build Tools
```json
{
  "webpack": "^5.88.0",
  "webpack-cli": "^5.1.0",
  "webpack-dev-server": "^4.15.0",
  "ts-loader": "^9.4.0",
  "html-webpack-plugin": "^5.5.0"
}
```

**Purpose**: Module bundling and development server
**Features**:
- Hot module replacement
- TypeScript compilation
- Asset optimization
- Development server

### Testing Framework
```json
{
  "jest": "^29.6.0",
  "@types/jest": "^29.5.0",
  "spectron": "^19.0.0",
  "electron": "^28.0.0"
}
```

**Purpose**: Unit and end-to-end testing
**Features**:
- Component testing
- E2E testing with Spectron
- Mock services
- Integration testing

## Platform-Specific Dependencies

### Windows
```json
{
  "node-gyp": "^9.4.0",
  "windows-build-tools": "^5.2.0"
}
```

**Purpose**: Native module compilation on Windows
**Features**:
- Visual Studio Build Tools integration
- Python environment setup
- Native binary compilation

### Linux (Raspberry Pi)
```json
{
  "node-gyp": "^9.4.0",
  "build-essential": "system"
}
```

**Purpose**: ARM64 compilation for Raspberry Pi
**Features**:
- Cross-compilation support
- ARM64 binary generation
- System dependency management

## API Integration Stack

### REST API Client
```typescript
// Shared API client with Tor proxy
import axios from 'axios';
import { SocksProxyAgent } from 'socks-proxy-agent';

const agent = new SocksProxyAgent('socks5://127.0.0.1:9050');
const client = axios.create({
  httpAgent: agent,
  httpsAgent: agent,
  baseURL: 'http://localhost:8080'
});
```

### WebSocket Integration
```json
{
  "ws": "^8.14.0",
  "@types/ws": "^8.5.0"
}
```

**Purpose**: Real-time communication with backend services
**Features**:
- Service status updates
- Log streaming
- Performance metrics
- Session monitoring

## Build and Packaging

### Electron Builder
```json
{
  "electron-builder": "^24.6.4"
}
```

**Configuration**:
- Windows: NSIS installer + Portable
- Linux: AppImage + DEB packages
- macOS: DMG installer
- Auto-updater integration

### Cross-Platform Builds
```json
{
  "electron-builder": "^24.6.4",
  "electron-notarize": "^1.2.0"
}
```

**Features**:
- Multi-platform packaging
- Code signing
- Notarization (macOS)
- Auto-updater support

## Development Environment

### Development Server
```json
{
  "concurrently": "^8.2.0",
  "nodemon": "^3.0.0",
  "webpack-dev-server": "^4.15.0"
}
```

**Purpose**: Hot reload and development workflow
**Features**:
- Concurrent main/renderer development
- Hot module replacement
- TypeScript compilation
- Asset serving

### Code Quality
```json
{
  "eslint": "^8.45.0",
  "prettier": "^3.0.0",
  "husky": "^8.0.0",
  "lint-staged": "^14.0.0"
}
```

**Purpose**: Code quality and consistency
**Features**:
- ESLint configuration
- Prettier formatting
- Pre-commit hooks
- Staged file linting

## Performance Optimization

### Bundle Optimization
```json
{
  "webpack-bundle-analyzer": "^4.9.0",
  "compression-webpack-plugin": "^10.0.0"
}
```

**Purpose**: Bundle size optimization
**Features**:
- Bundle analysis
- Code splitting
- Asset compression
- Tree shaking

### Memory Management
```json
{
  "v8-profiler": "^6.0.0",
  "clinic.js": "^11.0.0"
}
```

**Purpose**: Performance monitoring and optimization
**Features**:
- Memory profiling
- CPU profiling
- Performance analysis
- Bottleneck identification

## Security Dependencies

### Encryption
```json
{
  "crypto-js": "^4.1.0",
  "node-forge": "^1.3.0"
}
```

**Purpose**: Client-side encryption and security
**Features**:
- AES encryption
- RSA key generation
- Hash functions
- Secure random generation

### Certificate Management
```json
{
  "node-forge": "^1.3.0",
  "pem": "^1.14.0"
}
```

**Purpose**: Certificate handling and validation
**Features**:
- Certificate parsing
- Key generation
- Signature verification
- Chain validation

## Monitoring and Logging

### Application Monitoring
```json
{
  "winston": "^3.10.0",
  "electron-log": "^4.4.0"
}
```

**Purpose**: Logging and monitoring
**Features**:
- Structured logging
- Log rotation
- Performance metrics
- Error tracking

### Health Monitoring
```json
{
  "node-health-check": "^1.0.0"
}
```

**Purpose**: Service health monitoring
**Features**:
- Health check endpoints
- Service status monitoring
- Dependency checking
- Performance metrics
