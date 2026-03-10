# Electron GUI Docker Integration Guide

## Overview

This guide provides comprehensive instructions for integrating the Electron GUI with the Docker build process and API build progression, ensuring seamless communication with all Lucid backend services.

## Docker Build Process Integration

### Phase Alignment

The Electron GUI integrates with the Docker build process phases as follows:

#### Pre-Build Phase
- **Environment Configuration**: Tor and Docker settings
- **Base Image Preparation**: Distroless container compatibility
- **Network Setup**: lucid-pi-network configuration

#### Phase 1: Foundation Services
- **MongoDB Integration**: User data and session storage
- **Redis Integration**: Session management and caching
- **Elasticsearch Integration**: Search functionality
- **Auth Service Integration**: JWT authentication and hardware wallet support

#### Phase 2: Core Services
- **API Gateway Integration**: Request routing and load balancing
- **Service Mesh Integration**: Service discovery and health monitoring
- **Blockchain Integration**: Consensus monitoring and transaction tracking
- **Session Anchoring Integration**: Blockchain anchoring operations

#### Phase 3: Application Services
- **Session Management Integration**: Session creation and management
- **RDP Services Integration**: Remote desktop operations
- **Node Management Integration**: Node registration and monitoring
- **Resource Monitoring Integration**: System resource tracking

#### Phase 4: Support Services
- **Admin Interface Integration**: System administration
- **TRON Payment Integration**: Payment processing and wallet management
- **Emergency Controls Integration**: System lockdown and shutdown

## API Build Progression Integration

### Steps 1-6: Foundation Services

#### Step 1: MongoDB Container
```typescript
// MongoDB connection configuration
const mongoConfig = {
  host: '192.168.0.75',
  port: 27017,
  database: 'lucid_auth',
  username: process.env.MONGODB_USERNAME,
  password: process.env.MONGODB_PASSWORD
};
```

#### Step 2: Redis Container
```typescript
// Redis connection configuration
const redisConfig = {
  host: '192.168.0.75',
  port: 6379,
  database: 1,
  password: process.env.REDIS_PASSWORD
};
```

#### Step 6: Auth Service Container
```typescript
// Auth service integration
const authService = {
  baseURL: 'http://192.168.0.75:8089',
  endpoints: {
    login: '/auth/login',
    logout: '/auth/logout',
    verify: '/auth/verify',
    refresh: '/auth/refresh'
  }
};
```

### Steps 7-14: Core Services

#### Step 8: API Gateway Container
```typescript
// API Gateway integration
const apiGateway = {
  baseURL: 'http://192.168.0.75:8080',
  endpoints: {
    health: '/health',
    services: '/services',
    routes: '/routes'
  }
};
```

#### Step 10: Blockchain Engine Container
```typescript
// Blockchain integration
const blockchainEngine = {
  baseURL: 'http://192.168.0.75:8084',
  endpoints: {
    status: '/blockchain/status',
    blocks: '/blockchain/blocks',
    transactions: '/blockchain/transactions'
  }
};
```

### Steps 15-28: Application Services

#### Step 15: Session Management Pipeline
```typescript
// Session management integration
const sessionPipeline = {
  baseURL: 'http://192.168.0.75:8081',
  endpoints: {
    create: '/sessions/create',
    status: '/sessions/status',
    chunks: '/sessions/chunks'
  }
};
```

#### Step 19: RDP Services
```typescript
// RDP services integration
const rdpServices = {
  baseURL: 'http://192.168.0.75:8081',
  endpoints: {
    connect: '/rdp/connect',
    disconnect: '/rdp/disconnect',
    status: '/rdp/status'
  }
};
```

#### Step 23: Node Management
```typescript
// Node management integration
const nodeManagement = {
  baseURL: 'http://192.168.0.75:8095',
  endpoints: {
    register: '/nodes/register',
    status: '/nodes/status',
    earnings: '/nodes/earnings'
  }
};
```

### Steps 29-35: Support Services

#### Step 26: TRON Payment APIs
```typescript
// TRON payment integration
const tronPayment = {
  baseURL: 'http://192.168.0.75:8091',
  endpoints: {
    balance: '/tron/balance',
    transfer: '/tron/transfer',
    staking: '/tron/staking'
  }
};
```

## Service Communication Architecture

### Tor Integration

All API communication is routed through Tor SOCKS5 proxy:

```typescript
// Tor proxy configuration
const torConfig = {
  socksPort: 9050,
  controlPort: 9051,
  proxy: {
    host: '127.0.0.1',
    port: 9050,
    protocol: 'socks5'
  }
};

// API client with Tor proxy
const apiClient = axios.create({
  proxy: torConfig.proxy,
  timeout: 30000,
  headers: {
    'User-Agent': 'Lucid-Electron-GUI/1.0.0'
  }
});
```

### Docker Service Management

```typescript
// Docker service management
class DockerServiceManager {
  private docker: Docker;
  private sshConfig: SSHConfig;

  constructor() {
    this.docker = new Docker({
      host: '192.168.0.75',
      port: 2375,
      ssh: {
        host: '192.168.0.75',
        user: 'pickme',
        port: 22
      }
    });
  }

  async startService(serviceName: string): Promise<boolean> {
    try {
      const container = this.docker.getContainer(serviceName);
      await container.start();
      return true;
    } catch (error) {
      console.error(`Failed to start ${serviceName}:`, error);
      return false;
    }
  }

  async stopService(serviceName: string): Promise<boolean> {
    try {
      const container = this.docker.getContainer(serviceName);
      await container.stop();
      return true;
    } catch (error) {
      console.error(`Failed to stop ${serviceName}:`, error);
      return false;
    }
  }

  async getServiceStatus(serviceName: string): Promise<string> {
    try {
      const container = this.docker.getContainer(serviceName);
      const info = await container.inspect();
      return info.State.Status;
    } catch (error) {
      console.error(`Failed to get status for ${serviceName}:`, error);
      return 'unknown';
    }
  }
}
```

## GUI-Specific Service Integration

### User GUI Integration

```typescript
// User GUI service integration
class UserGUIServices {
  private apiClient: AxiosInstance;
  private authService: AuthService;
  private sessionService: SessionService;

  constructor() {
    this.apiClient = createTorClient();
    this.authService = new AuthService(this.apiClient);
    this.sessionService = new SessionService(this.apiClient);
  }

  async createSession(sessionData: SessionData): Promise<Session> {
    return await this.sessionService.create(sessionData);
  }

  async getSessionStatus(sessionId: string): Promise<SessionStatus> {
    return await this.sessionService.getStatus(sessionId);
  }

  async uploadChunk(sessionId: string, chunk: Chunk): Promise<boolean> {
    return await this.sessionService.uploadChunk(sessionId, chunk);
  }
}
```

### Developer GUI Integration

```typescript
// Developer GUI service integration
class DeveloperGUIServices {
  private dockerManager: DockerServiceManager;
  private apiClient: AxiosInstance;
  private logService: LogService;
  private metricsService: MetricsService;

  constructor() {
    this.dockerManager = new DockerServiceManager();
    this.apiClient = createTorClient();
    this.logService = new LogService(this.apiClient);
    this.metricsService = new MetricsService(this.apiClient);
  }

  async startBackendServices(): Promise<boolean> {
    const services = ['mongodb', 'redis', 'auth-service', 'api-gateway'];
    for (const service of services) {
      await this.dockerManager.startService(service);
    }
    return true;
  }

  async getServiceLogs(serviceName: string): Promise<string[]> {
    return await this.logService.getLogs(serviceName);
  }

  async getServiceMetrics(serviceName: string): Promise<Metrics> {
    return await this.metricsService.getMetrics(serviceName);
  }
}
```

### Node GUI Integration

```typescript
// Node GUI service integration
class NodeGUIServices {
  private apiClient: AxiosInstance;
  private nodeService: NodeService;
  private earningsService: EarningsService;
  private resourceService: ResourceService;

  constructor() {
    this.apiClient = createTorClient();
    this.nodeService = new NodeService(this.apiClient);
    this.earningsService = new EarningsService(this.apiClient);
    this.resourceService = new ResourceService(this.apiClient);
  }

  async registerNode(nodeData: NodeData): Promise<Node> {
    return await this.nodeService.register(nodeData);
  }

  async getNodeEarnings(nodeId: string): Promise<Earnings> {
    return await this.earningsService.getEarnings(nodeId);
  }

  async getResourceUsage(): Promise<ResourceUsage> {
    return await this.resourceService.getUsage();
  }
}
```

### Admin GUI Integration

```typescript
// Admin GUI service integration
class AdminGUIServices {
  private apiClient: AxiosInstance;
  private adminService: AdminService;
  private userService: UserService;
  private sessionService: SessionService;
  private nodeService: NodeService;
  private tronService: TronService;

  constructor() {
    this.apiClient = createTorClient();
    this.adminService = new AdminService(this.apiClient);
    this.userService = new UserService(this.apiClient);
    this.sessionService = new SessionService(this.apiClient);
    this.nodeService = new NodeService(this.apiClient);
    this.tronService = new TronService(this.apiClient);
  }

  async getSystemHealth(): Promise<SystemHealth> {
    return await this.adminService.getSystemHealth();
  }

  async getAllUsers(): Promise<User[]> {
    return await this.userService.getAll();
  }

  async getAllSessions(): Promise<Session[]> {
    return await this.sessionService.getAll();
  }

  async getAllNodes(): Promise<Node[]> {
    return await this.nodeService.getAll();
  }

  async getTronBalance(): Promise<TronBalance> {
    return await this.tronService.getBalance();
  }
}
```

## Docker Compose Integration

### Service Discovery

```typescript
// Service discovery configuration
const serviceDiscovery = {
  consul: {
    host: '192.168.0.75',
    port: 8500,
    services: [
      'lucid-mongodb',
      'lucid-redis',
      'lucid-auth-service',
      'lucid-api-gateway',
      'lucid-blockchain-engine',
      'lucid-session-pipeline',
      'lucid-node-management',
      'lucid-admin-interface'
    ]
  }
};
```

### Health Monitoring

```typescript
// Health monitoring configuration
const healthMonitoring = {
  endpoints: {
    mongodb: 'http://192.168.0.75:27017/health',
    redis: 'http://192.168.0.75:6379/health',
    auth: 'http://192.168.0.75:8089/health',
    gateway: 'http://192.168.0.75:8080/health',
    blockchain: 'http://192.168.0.75:8084/health',
    session: 'http://192.168.0.75:8087/health',
    node: 'http://192.168.0.75:8095/health',
    admin: 'http://192.168.0.75:8083/health'
  },
  checkInterval: 30000, // 30 seconds
  timeout: 5000 // 5 seconds
};
```

## Network Configuration

### Docker Network Integration

```typescript
// Docker network configuration
const dockerNetwork = {
  name: 'lucid-pi-network',
  subnet: '172.20.0.0/16',
  gateway: '172.20.0.1',
  services: {
    mongodb: '172.20.0.10',
    redis: '172.20.0.11',
    auth: '172.20.0.12',
    gateway: '172.20.0.13',
    blockchain: '172.20.0.14',
    session: '172.20.0.15',
    node: '172.20.0.16',
    admin: '172.20.0.17'
  }
};
```

### Tor Network Integration

```typescript
// Tor network configuration
const torNetwork = {
  socksPort: 9050,
  controlPort: 9051,
  dataDirectory: './assets/tor',
  exitNodes: [],
  strictNodes: false,
  allowSingleHopExits: false,
  bootstrapTimeout: 300,
  circuitBuildTimeout: 60
};
```

## Security Integration

### Context Isolation

```typescript
// Context isolation configuration
const contextIsolation = {
  nodeIntegration: false,
  contextIsolation: true,
  enableRemoteModule: false,
  preload: path.join(__dirname, 'preload.js'),
  webSecurity: true,
  allowRunningInsecureContent: false
};
```

### Tor Security

```typescript
// Tor security configuration
const torSecurity = {
  proxy: {
    host: '127.0.0.1',
    port: 9050,
    protocol: 'socks5'
  },
  dns: {
    servers: ['127.0.0.1:9053']
  },
  headers: {
    'User-Agent': 'Lucid-Electron-GUI/1.0.0'
  }
};
```

## Performance Integration

### Caching Strategy

```typescript
// Caching configuration
const cachingStrategy = {
  redis: {
    host: '192.168.0.75',
    port: 6379,
    database: 1,
    ttl: 3600 // 1 hour
  },
  memory: {
    maxSize: 100 * 1024 * 1024, // 100MB
    ttl: 300000 // 5 minutes
  }
};
```

### Load Balancing

```typescript
// Load balancing configuration
const loadBalancing = {
  strategy: 'round-robin',
  healthCheck: {
    interval: 30000,
    timeout: 5000,
    retries: 3
  },
  services: {
    api: ['192.168.0.75:8080'],
    auth: ['192.168.0.75:8089'],
    session: ['192.168.0.75:8087']
  }
};
```

## Monitoring Integration

### Metrics Collection

```typescript
// Metrics collection configuration
const metricsCollection = {
  endpoints: {
    system: 'http://192.168.0.75:8090/metrics/system',
    services: 'http://192.168.0.75:8090/metrics/services',
    network: 'http://192.168.0.75:8090/metrics/network'
  },
  collectionInterval: 60000, // 1 minute
  retentionPeriod: 7 * 24 * 60 * 60 * 1000 // 7 days
};
```

### Log Aggregation

```typescript
// Log aggregation configuration
const logAggregation = {
  endpoints: {
    system: 'http://192.168.0.75:9200/logs/system',
    services: 'http://192.168.0.75:9200/logs/services',
    application: 'http://192.168.0.75:9200/logs/application'
  },
  logLevel: 'info',
  retentionPeriod: 30 * 24 * 60 * 60 * 1000 // 30 days
};
```

## Deployment Integration

### Pi Deployment

```typescript
// Pi deployment configuration
const piDeployment = {
  host: '192.168.0.75',
  user: 'pickme',
  port: 22,
  deployDir: '/opt/lucid/electron-gui',
  services: {
    electron: 'lucid-desktop',
    tor: 'tor',
    docker: 'docker'
  }
};
```

### Service Orchestration

```typescript
// Service orchestration configuration
const serviceOrchestration = {
  phases: {
    foundation: [
      'lucid-mongodb',
      'lucid-redis',
      'lucid-elasticsearch',
      'lucid-auth-service'
    ],
    core: [
      'lucid-api-gateway',
      'lucid-service-mesh-controller',
      'lucid-blockchain-engine',
      'lucid-session-anchoring'
    ],
    application: [
      'lucid-session-pipeline',
      'lucid-rdp-server-manager',
      'lucid-node-management'
    ],
    support: [
      'lucid-admin-interface',
      'lucid-tron-client',
      'lucid-payment-gateway'
    ]
  }
};
```

## Testing Integration

### Integration Testing

```typescript
// Integration testing configuration
const integrationTesting = {
  services: {
    mongodb: 'mongodb://192.168.0.75:27017/lucid_test',
    redis: 'redis://192.168.0.75:6379/1',
    auth: 'http://192.168.0.75:8089',
    gateway: 'http://192.168.0.75:8080'
  },
  testData: {
    users: './tests/data/users.json',
    sessions: './tests/data/sessions.json',
    nodes: './tests/data/nodes.json'
  }
};
```

### Performance Testing

```typescript
// Performance testing configuration
const performanceTesting = {
  loadTest: {
    users: 100,
    duration: 300000, // 5 minutes
    rampUp: 60000 // 1 minute
  },
  stressTest: {
    users: 500,
    duration: 600000, // 10 minutes
    rampUp: 120000 // 2 minutes
  }
};
```

## Troubleshooting Integration

### Debug Configuration

```typescript
// Debug configuration
const debugConfig = {
  logging: {
    level: 'debug',
    file: './logs/electron-gui.log',
    maxSize: 10 * 1024 * 1024, // 10MB
    maxFiles: 5
  },
  monitoring: {
    enabled: true,
    interval: 5000,
    metrics: ['cpu', 'memory', 'network', 'disk']
  }
};
```

### Error Handling

```typescript
// Error handling configuration
const errorHandling = {
  retry: {
    maxAttempts: 3,
    delay: 1000,
    backoff: 2
  },
  fallback: {
    enabled: true,
    timeout: 5000
  },
  notification: {
    enabled: true,
    channels: ['console', 'file', 'email']
  }
};
```

---

**Created**: 2025-01-27  
**Project**: Lucid Electron GUI Docker Integration  
**Status**: Complete Integration Guide ✅
