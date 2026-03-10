# Lucid Electron GUI

## Overview

The Lucid Electron GUI is a sophisticated multi-window desktop application that provides four distinct interfaces for different user roles in the Lucid ecosystem. Built with Electron, React, and TypeScript, it integrates seamlessly with the Lucid Docker build process and API backend services.

## Features

### Multi-Window Architecture
- **User GUI**: End-user interface for session management
- **Developer GUI**: Development tools and backend service management
- **Node GUI**: Node operator interface for network participation
- **Admin GUI**: System administration and full-stack management

### Core Capabilities
- **Tor Integration**: Secure, anonymous communication via bundled Tor binary
- **Docker Integration**: Service orchestration and management
- **Hardware Wallet Support**: Ledger, Trezor, and KeepKey integration
- **TRON Blockchain**: Payment processing and authentication
- **Real-time Monitoring**: System health and service status tracking

## Quick Start

### Prerequisites

- Node.js v18.x or higher
- npm v9.x or higher
- Docker Desktop (for development)
- SSH access to Raspberry Pi (for deployment)

### Installation

```bash
# Clone the repository
git clone https://github.com/HamiGames/Lucid.git
cd Lucid/electron-gui

# Install dependencies
npm install

# Start development environment
npm run dev
```

### Development

```bash
# Start development server
npm run dev

# Build application
npm run build

# Run tests
npm test

# Package for distribution
npm run package
```

## Architecture

### Main Process
- **Tor Manager**: Manages bundled Tor binary with SOCKS5 proxy
- **Docker Manager**: Orchestrates backend services via Docker API
- **Window Manager**: Coordinates multiple BrowserWindow instances
- **IPC Handlers**: Secure communication between main and renderer processes

### Renderer Processes
Each GUI type has its own renderer process with:
- React-based UI components
- Zustand state management
- Tor-proxied API communication
- Hardware wallet integration
- Real-time monitoring capabilities

## Service Integration

### Phase 1: Foundation Services
- MongoDB (Port 27017) - Database operations
- Redis (Port 6379) - Session management and caching
- Elasticsearch (Port 9200) - Search functionality
- Auth Service (Port 8089) - Authentication and authorization

### Phase 2: Core Services
- API Gateway (Port 8080) - Request routing and load balancing
- Service Mesh (Port 8086) - Service discovery and health monitoring
- Blockchain Engine (Port 8084) - Consensus monitoring and transaction tracking
- Session Anchoring (Port 8085) - Blockchain anchoring operations

### Phase 3: Application Services
- Session Pipeline (Port 8081) - Session processing and management
- RDP Services (Port 3389) - Remote desktop operations
- Node Management (Port 8095) - Node registration and monitoring
- Resource Monitor (Port 8090) - System resource tracking

### Phase 4: Support Services
- Admin Interface (Port 8083) - System administration
- TRON Payment Services (Ports 8091-8097) - Payment processing and wallet management
- Emergency Controls - System lockdown and shutdown capabilities

## Configuration

### Environment Configuration

**Development** (`configs/env.development.json`):
```json
{
  "api": {
    "gateway": "http://localhost:8080",
    "auth": "http://localhost:8089",
    "admin": "http://localhost:8083"
  },
  "tor": {
    "socksPort": 9050,
    "controlPort": 9051
  }
}
```

**Production** (`configs/env.production.json`):
```json
{
  "api": {
    "gateway": "http://192.168.0.75:8080",
    "auth": "http://192.168.0.75:8089",
    "admin": "http://192.168.0.75:8083"
  },
  "tor": {
    "socksPort": 9050,
    "controlPort": 9051
  }
}
```

### Tor Configuration

```json
{
  "socksPort": 9050,
  "controlPort": 9051,
  "dataDirectory": "./assets/tor",
  "logLevel": "notice",
  "bootstrapTimeout": 300,
  "circuitBuildTimeout": 60
}
```

### Docker Configuration

```json
{
  "host": "192.168.0.75",
  "port": 2375,
  "ssh": {
    "host": "192.168.0.75",
    "user": "pickme",
    "port": 22
  }
}
```

## Security

### Context Isolation
- No `nodeIntegration` enabled in renderer processes
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

## Performance

### Requirements
- **App Startup**: < 5 seconds
- **Tor Bootstrap**: < 30 seconds
- **Docker Service Startup**: < 60 seconds (admin/dev)
- **API Response Time**: < 500ms (via Tor proxy)
- **Memory Usage**: < 512MB per renderer process
- **CPU Usage**: < 10% during idle state

## Deployment

### Development Deployment

```bash
# Start development environment
npm run dev

# Check service status
npm run status:all
```

### Production Deployment

```bash
# Build application
npm run build

# Package for distribution
npm run package:linux

# Deploy to Pi
npm run deploy:pi
```

### Docker Integration

```bash
# Build Docker image
docker build -t lucid-electron-gui .

# Run with Docker Compose
docker-compose up -d
```

## Testing

### Unit Tests

```bash
# Run all tests
npm test

# Run specific test
npm test -- --testNamePattern="admin-gui"

# Run with coverage
npm run test:coverage
```

### E2E Tests

```bash
# Run E2E tests
npm run test:e2e

# Run specific E2E test
npm run test:e2e -- --testNamePattern="user-workflow"
```

### Integration Tests

```bash
# Test API connectivity
npm run status:api

# Test Tor connectivity
npm run status:tor

# Test Docker connectivity
npm run status:docker
```

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
npm run status:tor

# Check Docker status
npm run status:docker

# Check API connectivity
npm run status:api
```

## Documentation

- [Build Guide](ELECTRON_GUI_BUILD_GUIDE.md) - Comprehensive build instructions
- [Dependencies](BUILD_DEPENDENCIES.md) - All required dependencies
- [Docker Integration](DOCKER_INTEGRATION_GUIDE.md) - Docker service integration
- [Build Scripts](BUILD_SCRIPTS.md) - Build and deployment scripts

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For support and questions:
- Create an issue on GitHub
- Check the documentation
- Review the troubleshooting guide

---

**Created**: 2025-01-27  
**Project**: Lucid Electron GUI  
**Status**: Complete Documentation ✅
