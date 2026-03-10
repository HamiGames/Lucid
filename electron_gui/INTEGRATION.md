# Electron GUI Integration with Docker Backend

## Architecture

- **Electron GUI**: Runs on Windows 11/Desktop (any OS)
- **Backend Services**: Run on Raspberry Pi 5 (192.168.0.75)
- **Tor**: Bundled with Electron GUI (no container)
- **Docker Management**: SSH-based via GUI

## Startup Sequence

1. **Deploy Docker Services on Pi** (follow docker-build-process-plan.md)
   - Phase 1: Foundation services
   - Phase 2: Core services
   - Phase 3: Application services
   - Phase 4: Support services

2. **Launch Electron GUI on Desktop**
   ```bash
   cd electron-gui
   npm install
   npm run build
   npm start
   ```

3. **GUI Auto-Initialization**
   - Tor Manager starts bundled Tor daemon
   - Docker Service connects to Pi via SSH
   - API clients configure Tor proxy
   - GUI connects to backend services

## Service Integration by Phase

### Phase 1 - Foundation Services
GUI can connect to:
- Auth Service (8089) - User authentication
- MongoDB (27017) - Data storage
- Redis (6379) - Session caching
- Elasticsearch (9200) - Search functionality

### Phase 2 - Core Services
GUI can connect to:
- API Gateway (8080) - Primary API endpoint
- Blockchain Engine (8084) - Blockchain operations
- Session Anchoring (8085) - Blockchain anchoring
- Service Mesh Controller (8086) - Service discovery
- Block Manager (8086) - Block validation
- Data Chain (8087) - Data storage

### Phase 3 - Application Services
GUI can connect to:
- Session API (8087) - Session management
- RDP Server Manager (8081) - Remote desktop
- Session Controller (8082) - Session control
- Resource Monitor (8090) - System monitoring
- Node Management (8095) - Node operations

### Phase 4 - Support Services
GUI can connect to:
- Admin Interface (8083) - Administration
- TRON Client (8091) - TRON blockchain
- Payout Router (8092) - Payment routing
- Wallet Manager (8093) - Wallet operations
- USDT Manager (8094) - USDT handling
- TRX Staking (8096) - Staking operations
- Payment Gateway (8097) - Payment processing

## Network Communication

All API requests flow:
Desktop GUI → Tor SOCKS5 Proxy (9050) → Pi Services (192.168.0.75)

## Docker Management

Admin/Developer GUIs can:
- View all container status
- Start/stop individual services
- Deploy entire phases via docker-compose
- View logs and metrics
- Monitor health checks

## Service Discovery

The Electron GUI uses the following service discovery pattern:

```typescript
// Service endpoints by phase
const serviceEndpoints = {
  foundation: [
    'http://192.168.0.75:8089', // Auth Service
    'mongodb://192.168.0.75:27017', // MongoDB
    'redis://192.168.0.75:6379', // Redis
    'http://192.168.0.75:9200' // Elasticsearch
  ],
  core: [
    'http://192.168.0.75:8080', // API Gateway
    'http://192.168.0.75:8084', // Blockchain Engine
    'http://192.168.0.75:8085', // Session Anchoring
    'http://192.168.0.75:8086', // Service Mesh
    'http://192.168.0.75:8087' // Data Chain
  ],
  application: [
    'http://192.168.0.75:8087', // Session API
    'http://192.168.0.75:8081', // RDP Server
    'http://192.168.0.75:8082', // Session Controller
    'http://192.168.0.75:8090', // Resource Monitor
    'http://192.168.0.75:8095' // Node Management
  ],
  support: [
    'http://192.168.0.75:8083', // Admin Interface
    'http://192.168.0.75:8091', // TRON Client
    'http://192.168.0.75:8092', // Payout Router
    'http://192.168.0.75:8093', // Wallet Manager
    'http://192.168.0.75:8094', // USDT Manager
    'http://192.168.0.75:8096', // TRX Staking
    'http://192.168.0.75:8097' // Payment Gateway
  ]
};
```

## Configuration Files

The integration uses the following configuration files:

- `configs/env.production.json` - API endpoints and service URLs
- `configs/docker.config.json` - Docker service configuration
- `shared/constants.ts` - Service endpoints and constants
- `main/connection-validator.ts` - Phase-based connection validation

## Testing Strategy

After each Docker phase deployment:

1. **Phase 1 Complete**: Test Auth, Storage connectivity from GUI
2. **Phase 2 Complete**: Test Gateway, Blockchain from GUI
3. **Phase 3 Complete**: Test Session, Node management from GUI
4. **Phase 4 Complete**: Test full Admin, Payment features from GUI

## Troubleshooting

### Connection Issues
- Verify Pi services are running: `ssh pickme@192.168.0.75 "docker ps"`
- Check Tor proxy status in GUI
- Validate SSH key authentication to Pi
- Confirm network connectivity to 192.168.0.75

### Service Discovery Issues
- Verify service endpoints in configuration files
- Check Docker container health status
- Validate API Gateway routing
- Test individual service endpoints

### Performance Issues
- Monitor Tor circuit performance
- Check Pi resource utilization
- Validate network latency
- Review service health metrics

## Security Considerations

- All API communication routed through Tor SOCKS5 proxy
- SSH key-based authentication for Pi access
- No plaintext credentials in configuration files
- Hardware wallet integration for authentication
- Context isolation in Electron renderer processes

## Deployment Checklist

- [ ] Pi Docker services deployed and healthy
- [ ] SSH key configured for Pi access
- [ ] Tor binary bundled with Electron GUI
- [ ] Configuration files updated with correct endpoints
- [ ] Network connectivity verified
- [ ] Service discovery tested
- [ ] Phase-based validation implemented
- [ ] Error handling configured
- [ ] Logging and monitoring enabled
