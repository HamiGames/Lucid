# API Integration Mapping Guide

## Overview

This document provides comprehensive mapping between the Electron GUI components and the Lucid API backend systems, ensuring proper integration with all service clusters defined in the API architecture.

## API Cluster Integration Matrix

### 1. API Gateway Cluster Integration

#### Admin GUI Integration
```typescript
// Admin GUI API endpoints
const ADMIN_API_ENDPOINTS = {
  // System Management
  SYSTEM_STATUS: '/api/v1/admin/system/status',
  SYSTEM_METRICS: '/api/v1/admin/system/metrics',
  SYSTEM_HEALTH: '/api/v1/admin/system/health',
  
  // User Management
  USERS_LIST: '/api/v1/admin/users',
  USER_CREATE: '/api/v1/admin/users',
  USER_UPDATE: '/api/v1/admin/users/{id}',
  USER_DELETE: '/api/v1/admin/users/{id}',
  USER_SUSPEND: '/api/v1/admin/users/{id}/suspend',
  USER_ACTIVATE: '/api/v1/admin/users/{id}/activate',
  
  // Session Management
  SESSIONS_LIST: '/api/v1/admin/sessions',
  SESSION_DETAILS: '/api/v1/admin/sessions/{id}',
  SESSION_TERMINATE: '/api/v1/admin/sessions/{id}/terminate',
  SESSION_ANCHOR: '/api/v1/admin/sessions/{id}/anchor',
  SESSION_EXPORT: '/api/v1/admin/sessions/{id}/export',
  
  // Node Management
  NODES_LIST: '/api/v1/admin/nodes',
  NODE_DETAILS: '/api/v1/admin/nodes/{id}',
  NODE_MAINTENANCE: '/api/v1/admin/nodes/{id}/maintenance',
  NODE_HEALTH: '/api/v1/admin/nodes/{id}/health',
  
  // Blockchain Management
  BLOCKCHAIN_STATUS: '/api/v1/admin/blockchain/status',
  BLOCKCHAIN_ANCHORING: '/api/v1/admin/blockchain/anchoring',
  BLOCKS_RECENT: '/api/v1/admin/blockchain/blocks/recent',
  BLOCKS_STATISTICS: '/api/v1/admin/blockchain/blocks/statistics',
  
  // Audit and Logs
  AUDIT_LOGS: '/api/v1/admin/audit/logs',
  AUDIT_EXPORT: '/api/v1/admin/audit/export',
  AUDIT_STATISTICS: '/api/v1/admin/audit/statistics',
  
  // Configuration
  CONFIG_GET: '/api/v1/admin/config',
  CONFIG_UPDATE: '/api/v1/admin/config',
  CONFIG_BACKUP: '/api/v1/admin/config/backup',
  CONFIG_RESTORE: '/api/v1/admin/config/restore'
};
```

#### User GUI Integration
```typescript
// User GUI API endpoints
const USER_API_ENDPOINTS = {
  // Session Management
  SESSIONS_MY: '/api/v1/user/sessions',
  SESSION_CREATE: '/api/v1/user/sessions',
  SESSION_DETAILS: '/api/v1/user/sessions/{id}',
  SESSION_UPDATE: '/api/v1/user/sessions/{id}',
  SESSION_DELETE: '/api/v1/user/sessions/{id}',
  SESSION_HISTORY: '/api/v1/user/sessions/history',
  
  // Wallet Integration
  WALLET_BALANCE: '/api/v1/user/wallet/balance',
  WALLET_TRANSACTIONS: '/api/v1/user/wallet/transactions',
  WALLET_SEND: '/api/v1/user/wallet/send',
  WALLET_RECEIVE: '/api/v1/user/wallet/receive',
  
  // Profile Management
  PROFILE_GET: '/api/v1/user/profile',
  PROFILE_UPDATE: '/api/v1/user/profile',
  PROFILE_SETTINGS: '/api/v1/user/settings',
  
  // Payment History
  PAYMENTS_HISTORY: '/api/v1/user/payments/history',
  PAYMENT_DETAILS: '/api/v1/user/payments/{id}'
};
```

#### Developer GUI Integration
```typescript
// Developer GUI API endpoints
const DEVELOPER_API_ENDPOINTS = {
  // API Explorer
  API_DOCS: '/api/v1/developer/docs',
  API_ENDPOINTS: '/api/v1/developer/endpoints',
  API_SCHEMA: '/api/v1/developer/schema',
  
  // Logs and Monitoring
  LOGS_SYSTEM: '/api/v1/developer/logs/system',
  LOGS_APPLICATION: '/api/v1/developer/logs/application',
  LOGS_ERRORS: '/api/v1/developer/logs/errors',
  
  // Metrics and Performance
  METRICS_SYSTEM: '/api/v1/developer/metrics/system',
  METRICS_APPLICATION: '/api/v1/developer/metrics/application',
  METRICS_PERFORMANCE: '/api/v1/developer/metrics/performance',
  
  // Testing Tools
  API_TEST: '/api/v1/developer/test',
  API_VALIDATE: '/api/v1/developer/validate',
  API_DEBUG: '/api/v1/developer/debug'
};
```

#### Node Operator GUI Integration
```typescript
// Node Operator GUI API endpoints
const NODE_API_ENDPOINTS = {
  // Node Status
  NODE_STATUS: '/api/v1/node/status',
  NODE_HEALTH: '/api/v1/node/health',
  NODE_METRICS: '/api/v1/node/metrics',
  
  // Resource Monitoring
  RESOURCES_CPU: '/api/v1/node/resources/cpu',
  RESOURCES_MEMORY: '/api/v1/node/resources/memory',
  RESOURCES_DISK: '/api/v1/node/resources/disk',
  RESOURCES_NETWORK: '/api/v1/node/resources/network',
  
  // Earnings and Payouts
  EARNINGS_CURRENT: '/api/v1/node/earnings/current',
  EARNINGS_HISTORY: '/api/v1/node/earnings/history',
  PAYOUTS_PENDING: '/api/v1/node/payouts/pending',
  PAYOUTS_HISTORY: '/api/v1/node/payouts/history',
  
  // Pool Management
  POOL_STATUS: '/api/v1/node/pool/status',
  POOL_JOIN: '/api/v1/node/pool/join',
  POOL_LEAVE: '/api/v1/node/pool/leave',
  POOL_STATISTICS: '/api/v1/node/pool/statistics',
  
  // Configuration
  CONFIG_GET: '/api/v1/node/config',
  CONFIG_UPDATE: '/api/v1/node/config',
  CONFIG_VALIDATE: '/api/v1/node/config/validate',
  
  // Maintenance
  MAINTENANCE_MODE: '/api/v1/node/maintenance/mode',
  MAINTENANCE_TOOLS: '/api/v1/node/maintenance/tools',
  MAINTENANCE_LOGS: '/api/v1/node/maintenance/logs'
};
```

### 2. Blockchain Core Cluster Integration

#### Blockchain Operations
```typescript
// Blockchain Core API endpoints
const BLOCKCHAIN_API_ENDPOINTS = {
  // Blockchain Status
  BLOCKCHAIN_STATUS: '/api/v1/blockchain/status',
  BLOCKCHAIN_HEIGHT: '/api/v1/blockchain/height',
  BLOCKCHAIN_HASH: '/api/v1/blockchain/hash',
  
  // Block Operations
  BLOCK_GET: '/api/v1/blockchain/blocks/{hash}',
  BLOCK_LATEST: '/api/v1/blockchain/blocks/latest',
  BLOCK_RECENT: '/api/v1/blockchain/blocks/recent',
  BLOCK_VALIDATE: '/api/v1/blockchain/blocks/{hash}/validate',
  
  // Transaction Operations
  TRANSACTION_GET: '/api/v1/blockchain/transactions/{id}',
  TRANSACTION_CREATE: '/api/v1/blockchain/transactions',
  TRANSACTION_VALIDATE: '/api/v1/blockchain/transactions/{id}/validate',
  TRANSACTION_BROADCAST: '/api/v1/blockchain/transactions/{id}/broadcast',
  
  // Consensus Operations
  CONSENSUS_STATUS: '/api/v1/blockchain/consensus/status',
  CONSENSUS_PARTICIPANTS: '/api/v1/blockchain/consensus/participants',
  CONSENSUS_VOTE: '/api/v1/blockchain/consensus/vote',
  
  // Session Anchoring
  ANCHORING_QUEUE: '/api/v1/blockchain/anchoring/queue',
  ANCHORING_STATUS: '/api/v1/blockchain/anchoring/status',
  ANCHORING_SUBMIT: '/api/v1/blockchain/anchoring/submit',
  ANCHORING_CONFIRM: '/api/v1/blockchain/anchoring/confirm'
};
```

### 3. Session Management Cluster Integration

#### Session Operations
```typescript
// Session Management API endpoints
const SESSION_API_ENDPOINTS = {
  // Session CRUD
  SESSION_CREATE: '/api/v1/sessions',
  SESSION_GET: '/api/v1/sessions/{id}',
  SESSION_UPDATE: '/api/v1/sessions/{id}',
  SESSION_DELETE: '/api/v1/sessions/{id}',
  SESSION_LIST: '/api/v1/sessions',
  
  // Session Operations
  SESSION_START: '/api/v1/sessions/{id}/start',
  SESSION_STOP: '/api/v1/sessions/{id}/stop',
  SESSION_PAUSE: '/api/v1/sessions/{id}/pause',
  SESSION_RESUME: '/api/v1/sessions/{id}/resume',
  
  // Session Data
  SESSION_DATA_UPLOAD: '/api/v1/sessions/{id}/data/upload',
  SESSION_DATA_DOWNLOAD: '/api/v1/sessions/{id}/data/download',
  SESSION_DATA_LIST: '/api/v1/sessions/{id}/data',
  SESSION_DATA_DELETE: '/api/v1/sessions/{id}/data/{dataId}',
  
  // Session Recording
  SESSION_RECORD_START: '/api/v1/sessions/{id}/record/start',
  SESSION_RECORD_STOP: '/api/v1/sessions/{id}/record/stop',
  SESSION_RECORD_STATUS: '/api/v1/sessions/{id}/record/status',
  SESSION_RECORD_DOWNLOAD: '/api/v1/sessions/{id}/record/download',
  
  // Session Processing
  SESSION_PROCESS: '/api/v1/sessions/{id}/process',
  SESSION_PROCESS_STATUS: '/api/v1/sessions/{id}/process/status',
  SESSION_PROCESS_RESULT: '/api/v1/sessions/{id}/process/result'
};
```

### 4. RDP Services Cluster Integration

#### RDP Operations
```typescript
// RDP Services API endpoints
const RDP_API_ENDPOINTS = {
  // RDP Server Management
  RDP_SERVER_CREATE: '/api/v1/rdp/servers',
  RDP_SERVER_GET: '/api/v1/rdp/servers/{id}',
  RDP_SERVER_UPDATE: '/api/v1/rdp/servers/{id}',
  RDP_SERVER_DELETE: '/api/v1/rdp/servers/{id}',
  RDP_SERVER_LIST: '/api/v1/rdp/servers',
  
  // RDP Connection Management
  RDP_CONNECT: '/api/v1/rdp/connect',
  RDP_DISCONNECT: '/api/v1/rdp/disconnect',
  RDP_STATUS: '/api/v1/rdp/status',
  RDP_SESSIONS: '/api/v1/rdp/sessions',
  
  // RDP Monitoring
  RDP_MONITOR_STATUS: '/api/v1/rdp/monitor/status',
  RDP_MONITOR_METRICS: '/api/v1/rdp/monitor/metrics',
  RDP_MONITOR_LOGS: '/api/v1/rdp/monitor/logs',
  RDP_MONITOR_ALERTS: '/api/v1/rdp/monitor/alerts',
  
  // RDP Controller
  RDP_CONTROLLER_START: '/api/v1/rdp/controller/start',
  RDP_CONTROLLER_STOP: '/api/v1/rdp/controller/stop',
  RDP_CONTROLLER_STATUS: '/api/v1/rdp/controller/status',
  RDP_CONTROLLER_CONFIG: '/api/v1/rdp/controller/config'
};
```

### 5. TRON Payment Cluster Integration

#### TRON Payment Operations
```typescript
// TRON Payment API endpoints
const TRON_API_ENDPOINTS = {
  // Wallet Management
  WALLET_CREATE: '/api/v1/tron/wallet/create',
  WALLET_IMPORT: '/api/v1/tron/wallet/import',
  WALLET_BALANCE: '/api/v1/tron/wallet/balance',
  WALLET_ADDRESS: '/api/v1/tron/wallet/address',
  
  // Transaction Operations
  TRANSACTION_SEND: '/api/v1/tron/transaction/send',
  TRANSACTION_GET: '/api/v1/tron/transaction/{id}',
  TRANSACTION_HISTORY: '/api/v1/tron/transaction/history',
  TRANSACTION_STATUS: '/api/v1/tron/transaction/{id}/status',
  
  // USDT-TRC20 Operations
  USDT_BALANCE: '/api/v1/tron/usdt/balance',
  USDT_SEND: '/api/v1/tron/usdt/send',
  USDT_RECEIVE: '/api/v1/tron/usdt/receive',
  USDT_HISTORY: '/api/v1/tron/usdt/history',
  
  // Payout Operations
  PAYOUT_CREATE: '/api/v1/tron/payout/create',
  PAYOUT_GET: '/api/v1/tron/payout/{id}',
  PAYOUT_LIST: '/api/v1/tron/payout/list',
  PAYOUT_STATUS: '/api/v1/tron/payout/{id}/status',
  
  // Staking Operations
  STAKING_INFO: '/api/v1/tron/staking/info',
  STAKING_STAKE: '/api/v1/tron/staking/stake',
  STAKING_UNSTAKE: '/api/v1/tron/staking/unstake',
  STAKING_REWARDS: '/api/v1/tron/staking/rewards'
};
```

## API Client Implementation

### 1. Base API Client (`shared/api-client.ts`)

```typescript
interface ApiClientConfig {
  baseUrl: string;
  timeout: number;
  retries: number;
  torProxy: string;
}

class ApiClient {
  private config: ApiClientConfig;
  private torAgent: Agent;
  
  constructor(config: ApiClientConfig) {
    this.config = config;
    this.torAgent = new Agent({
      socksHost: '127.0.0.1',
      socksPort: 9050
    });
  }
  
  async request<T>(
    method: string,
    endpoint: string,
    data?: any,
    headers?: Record<string, string>
  ): Promise<ApiResponse<T>> {
    // Implementation with Tor proxy
  }
  
  async get<T>(endpoint: string, headers?: Record<string, string>): Promise<ApiResponse<T>>;
  async post<T>(endpoint: string, data: any, headers?: Record<string, string>): Promise<ApiResponse<T>>;
  async put<T>(endpoint: string, data: any, headers?: Record<string, string>): Promise<ApiResponse<T>>;
  async delete<T>(endpoint: string, headers?: Record<string, string>): Promise<ApiResponse<T>>;
}
```

### 2. Admin API Client (`renderer/admin/services/adminApi.ts`)

```typescript
class AdminApiClient extends ApiClient {
  // System Management
  async getSystemStatus(): Promise<SystemStatus>;
  async getSystemMetrics(): Promise<SystemMetrics>;
  async getSystemHealth(): Promise<SystemHealth>;
  
  // User Management
  async getUsers(params?: UserListParams): Promise<UserListResponse>;
  async createUser(userData: CreateUserRequest): Promise<User>;
  async updateUser(id: string, userData: UpdateUserRequest): Promise<User>;
  async deleteUser(id: string): Promise<void>;
  async suspendUser(id: string): Promise<void>;
  async activateUser(id: string): Promise<void>;
  
  // Session Management
  async getSessions(params?: SessionListParams): Promise<SessionListResponse>;
  async getSessionDetails(id: string): Promise<SessionDetails>;
  async terminateSession(id: string): Promise<void>;
  async anchorSession(id: string): Promise<AnchorResult>;
  async exportSession(id: string): Promise<ExportResult>;
  
  // Node Management
  async getNodes(): Promise<NodeListResponse>;
  async getNodeDetails(id: string): Promise<NodeDetails>;
  async setNodeMaintenance(id: string, maintenance: boolean): Promise<void>;
  async getNodeHealth(id: string): Promise<NodeHealth>;
  
  // Blockchain Management
  async getBlockchainStatus(): Promise<BlockchainStatus>;
  async getAnchoringQueue(): Promise<AnchoringQueue>;
  async getRecentBlocks(): Promise<BlockListResponse>;
  async getBlockchainStatistics(): Promise<BlockchainStatistics>;
  
  // Audit and Logs
  async getAuditLogs(params?: AuditLogParams): Promise<AuditLogResponse>;
  async exportAuditLogs(params?: AuditExportParams): Promise<ExportResult>;
  async getAuditStatistics(): Promise<AuditStatistics>;
  
  // Configuration
  async getConfig(): Promise<SystemConfig>;
  async updateConfig(config: SystemConfig): Promise<void>;
  async backupConfig(): Promise<BackupResult>;
  async restoreConfig(backupData: BackupData): Promise<void>;
}
```

### 3. User API Client (`renderer/user/services/sessionService.ts`)

```typescript
class UserSessionService extends ApiClient {
  // Session Management
  async getMySessions(): Promise<SessionListResponse>;
  async createSession(sessionData: CreateSessionRequest): Promise<Session>;
  async getSessionDetails(id: string): Promise<SessionDetails>;
  async updateSession(id: string, sessionData: UpdateSessionRequest): Promise<Session>;
  async deleteSession(id: string): Promise<void>;
  async getSessionHistory(): Promise<SessionHistoryResponse>;
  
  // Session Operations
  async startSession(id: string): Promise<void>;
  async stopSession(id: string): Promise<void>;
  async pauseSession(id: string): Promise<void>;
  async resumeSession(id: string): Promise<void>;
  
  // Session Data
  async uploadSessionData(id: string, data: SessionData): Promise<UploadResult>;
  async downloadSessionData(id: string, dataId: string): Promise<DownloadResult>;
  async getSessionDataList(id: string): Promise<SessionDataListResponse>;
  async deleteSessionData(id: string, dataId: string): Promise<void>;
}
```

### 4. Developer API Client (`renderer/developer/services/apiService.ts`)

```typescript
class DeveloperApiService extends ApiClient {
  // API Documentation
  async getApiDocs(): Promise<ApiDocumentation>;
  async getApiEndpoints(): Promise<ApiEndpointList>;
  async getApiSchema(): Promise<ApiSchema>;
  
  // Logs and Monitoring
  async getSystemLogs(params?: LogParams): Promise<LogResponse>;
  async getApplicationLogs(params?: LogParams): Promise<LogResponse>;
  async getErrorLogs(params?: LogParams): Promise<LogResponse>;
  
  // Metrics and Performance
  async getSystemMetrics(): Promise<SystemMetrics>;
  async getApplicationMetrics(): Promise<ApplicationMetrics>;
  async getPerformanceMetrics(): Promise<PerformanceMetrics>;
  
  // Testing Tools
  async testApiEndpoint(endpoint: string, method: string, data?: any): Promise<TestResult>;
  async validateApiRequest(request: ApiRequest): Promise<ValidationResult>;
  async debugApiCall(call: ApiCall): Promise<DebugResult>;
}
```

### 5. Node API Client (`renderer/node/services/nodeService.ts`)

```typescript
class NodeApiService extends ApiClient {
  // Node Status
  async getNodeStatus(): Promise<NodeStatus>;
  async getNodeHealth(): Promise<NodeHealth>;
  async getNodeMetrics(): Promise<NodeMetrics>;
  
  // Resource Monitoring
  async getCpuResources(): Promise<CpuResources>;
  async getMemoryResources(): Promise<MemoryResources>;
  async getDiskResources(): Promise<DiskResources>;
  async getNetworkResources(): Promise<NetworkResources>;
  
  // Earnings and Payouts
  async getCurrentEarnings(): Promise<CurrentEarnings>;
  async getEarningsHistory(): Promise<EarningsHistory>;
  async getPendingPayouts(): Promise<PendingPayouts>;
  async getPayoutsHistory(): Promise<PayoutsHistory>;
  
  // Pool Management
  async getPoolStatus(): Promise<PoolStatus>;
  async joinPool(poolId: string): Promise<void>;
  async leavePool(): Promise<void>;
  async getPoolStatistics(): Promise<PoolStatistics>;
  
  // Configuration
  async getNodeConfig(): Promise<NodeConfig>;
  async updateNodeConfig(config: NodeConfig): Promise<void>;
  async validateNodeConfig(config: NodeConfig): Promise<ValidationResult>;
  
  // Maintenance
  async setMaintenanceMode(enabled: boolean): Promise<void>;
  async getMaintenanceTools(): Promise<MaintenanceTools>;
  async getMaintenanceLogs(): Promise<MaintenanceLogs>;
}
```

## WebSocket Integration

### 1. Real-time Updates

```typescript
// WebSocket connection for real-time updates
class WebSocketService {
  private ws: WebSocket | null = null;
  private reconnectInterval: number = 5000;
  private maxReconnectAttempts: number = 5;
  private reconnectAttempts: number = 0;
  
  connect(url: string): void {
    this.ws = new WebSocket(url);
    
    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
    };
    
    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleMessage(data);
    };
    
    this.ws.onclose = () => {
      console.log('WebSocket disconnected');
      this.reconnect();
    };
    
    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }
  
  private handleMessage(data: any): void {
    switch (data.type) {
      case 'tor_status':
        this.emit('tor_status', data.payload);
        break;
      case 'session_update':
        this.emit('session_update', data.payload);
        break;
      case 'blockchain_update':
        this.emit('blockchain_update', data.payload);
        break;
      case 'node_status':
        this.emit('node_status', data.payload);
        break;
    }
  }
  
  private reconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => {
        this.connect(this.ws?.url || '');
      }, this.reconnectInterval);
    }
  }
}
```

### 2. Event Handling

```typescript
// Event handling for different GUI types
class AdminEventService extends WebSocketService {
  handleTorStatus(status: TorStatus): void {
    // Update Tor indicator in admin GUI
  }
  
  handleSessionUpdate(session: Session): void {
    // Update sessions table in admin GUI
  }
  
  handleBlockchainUpdate(block: Block): void {
    // Update blockchain status in admin GUI
  }
  
  handleNodeStatus(node: Node): void {
    // Update nodes table in admin GUI
  }
}

class UserEventService extends WebSocketService {
  handleTorStatus(status: TorStatus): void {
    // Update Tor indicator in user GUI
  }
  
  handleSessionUpdate(session: Session): void {
    // Update user's sessions in user GUI
  }
  
  handleWalletUpdate(wallet: Wallet): void {
    // Update wallet balance in user GUI
  }
}
```

## Error Handling

### 1. Standard Error Responses

```typescript
interface ApiError {
  code: string;
  message: string;
  details?: Record<string, any>;
  request_id: string;
  timestamp: string;
  service: string;
  version: string;
}

class ApiErrorHandler {
  static handleError(error: ApiError): void {
    switch (error.code) {
      case 'LUCID_ERR_1XXX':
        // Validation errors
        this.handleValidationError(error);
        break;
      case 'LUCID_ERR_2XXX':
        // Authentication/Authorization errors
        this.handleAuthError(error);
        break;
      case 'LUCID_ERR_3XXX':
        // Rate limiting errors
        this.handleRateLimitError(error);
        break;
      case 'LUCID_ERR_4XXX':
        // Business logic errors
        this.handleBusinessError(error);
        break;
      case 'LUCID_ERR_5XXX':
        // System errors
        this.handleSystemError(error);
        break;
    }
  }
  
  private static handleValidationError(error: ApiError): void {
    // Show validation error message
  }
  
  private static handleAuthError(error: ApiError): void {
    // Redirect to login or show auth error
  }
  
  private static handleRateLimitError(error: ApiError): void {
    // Show rate limit message with retry time
  }
  
  private static handleBusinessError(error: ApiError): void {
    // Show business logic error message
  }
  
  private static handleSystemError(error: ApiError): void {
    // Show system error message and contact support
  }
}
```

### 2. Retry Logic

```typescript
class ApiRetryHandler {
  private maxRetries: number = 3;
  private retryDelay: number = 1000;
  
  async withRetry<T>(
    operation: () => Promise<T>,
    retryCondition?: (error: any) => boolean
  ): Promise<T> {
    let lastError: any;
    
    for (let attempt = 1; attempt <= this.maxRetries; attempt++) {
      try {
        return await operation();
      } catch (error) {
        lastError = error;
        
        if (retryCondition && !retryCondition(error)) {
          throw error;
        }
        
        if (attempt < this.maxRetries) {
          await this.delay(this.retryDelay * attempt);
        }
      }
    }
    
    throw lastError;
  }
  
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}
```

## Rate Limiting

### 1. Client-side Rate Limiting

```typescript
class RateLimiter {
  private requests: Map<string, number[]> = new Map();
  private limits: Map<string, RateLimit> = new Map();
  
  constructor() {
    this.setupLimits();
  }
  
  private setupLimits(): void {
    this.limits.set('public', { requests: 100, window: 60000 }); // 100/min
    this.limits.set('authenticated', { requests: 1000, window: 60000 }); // 1000/min
    this.limits.set('admin', { requests: 10000, window: 60000 }); // 10000/min
  }
  
  canMakeRequest(endpoint: string, userType: string): boolean {
    const limit = this.limits.get(userType);
    if (!limit) return true;
    
    const now = Date.now();
    const windowStart = now - limit.window;
    
    const requests = this.requests.get(endpoint) || [];
    const recentRequests = requests.filter(time => time > windowStart);
    
    return recentRequests.length < limit.requests;
  }
  
  recordRequest(endpoint: string): void {
    const now = Date.now();
    const requests = this.requests.get(endpoint) || [];
    requests.push(now);
    this.requests.set(endpoint, requests);
  }
}
```

## Authentication Integration

### 1. JWT Token Management

```typescript
class AuthService {
  private accessToken: string | null = null;
  private refreshToken: string | null = null;
  private tokenExpiry: number | null = null;
  
  async login(credentials: LoginCredentials): Promise<AuthResult> {
    const response = await this.apiClient.post('/api/v1/auth/login', credentials);
    
    if (response.success) {
      this.accessToken = response.data.access_token;
      this.refreshToken = response.data.refresh_token;
      this.tokenExpiry = response.data.expires_at;
      
      // Store tokens securely
      await this.storeTokens();
    }
    
    return response;
  }
  
  async refreshAccessToken(): Promise<boolean> {
    if (!this.refreshToken) return false;
    
    try {
      const response = await this.apiClient.post('/api/v1/auth/refresh', {
        refresh_token: this.refreshToken
      });
      
      if (response.success) {
        this.accessToken = response.data.access_token;
        this.tokenExpiry = response.data.expires_at;
        await this.storeTokens();
        return true;
      }
    } catch (error) {
      console.error('Token refresh failed:', error);
    }
    
    return false;
  }
  
  async logout(): Promise<void> {
    if (this.accessToken) {
      try {
        await this.apiClient.post('/api/v1/auth/logout', {
          access_token: this.accessToken
        });
      } catch (error) {
        console.error('Logout failed:', error);
      }
    }
    
    this.clearTokens();
  }
  
  isAuthenticated(): boolean {
    return this.accessToken !== null && 
           this.tokenExpiry !== null && 
           Date.now() < this.tokenExpiry;
  }
  
  getAuthHeaders(): Record<string, string> {
    return this.accessToken ? {
      'Authorization': `Bearer ${this.accessToken}`
    } : {};
  }
}
```

### 2. Hardware Wallet Integration

```typescript
class HardwareWalletService {
  async connectWallet(): Promise<WalletConnection> {
    // Connect to hardware wallet
    const wallet = await this.detectWallet();
    return wallet.connect();
  }
  
  async signTransaction(transaction: Transaction): Promise<SignedTransaction> {
    const wallet = await this.getConnectedWallet();
    return wallet.signTransaction(transaction);
  }
  
  async getPublicKey(): Promise<string> {
    const wallet = await this.getConnectedWallet();
    return wallet.getPublicKey();
  }
  
  async getAddress(): Promise<string> {
    const wallet = await this.getConnectedWallet();
    return wallet.getAddress();
  }
}
```

## Data Models

### 1. Common Data Types

```typescript
// Common data types used across all GUIs
interface User {
  id: string;
  username: string;
  email: string;
  role: 'user' | 'node_operator' | 'admin' | 'super_admin';
  status: 'active' | 'suspended' | 'inactive';
  created_at: string;
  updated_at: string;
}

interface Session {
  id: string;
  user_id: string;
  title: string;
  description?: string;
  status: 'active' | 'paused' | 'stopped' | 'completed';
  created_at: string;
  updated_at: string;
  started_at?: string;
  ended_at?: string;
}

interface Node {
  id: string;
  name: string;
  status: 'online' | 'offline' | 'maintenance';
  health: 'healthy' | 'unhealthy' | 'degraded';
  resources: NodeResources;
  earnings: NodeEarnings;
  pool?: Pool;
}

interface BlockchainStatus {
  height: number;
  hash: string;
  timestamp: string;
  difficulty: number;
  transactions_count: number;
  anchoring_queue_size: number;
}
```

### 2. GUI-specific Data Types

```typescript
// Admin GUI specific types
interface AdminDashboard {
  system_status: SystemStatus;
  metrics: SystemMetrics;
  recent_activity: ActivityItem[];
  alerts: Alert[];
}

interface SystemMetrics {
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  network_usage: number;
  active_sessions: number;
  total_users: number;
  blockchain_height: number;
}

// User GUI specific types
interface UserDashboard {
  active_sessions: Session[];
  wallet_balance: WalletBalance;
  recent_payments: Payment[];
  session_history: SessionHistory[];
}

interface WalletBalance {
  trx: number;
  usdt: number;
  total_value_usd: number;
}

// Developer GUI specific types
interface DeveloperDashboard {
  api_endpoints: ApiEndpoint[];
  system_logs: LogEntry[];
  metrics: DeveloperMetrics;
  debug_tools: DebugTool[];
}

interface ApiEndpoint {
  path: string;
  method: string;
  description: string;
  parameters: Parameter[];
  responses: Response[];
}

// Node GUI specific types
interface NodeDashboard {
  node_status: NodeStatus;
  resources: NodeResources;
  earnings: NodeEarnings;
  pool_info: PoolInfo;
  maintenance: MaintenanceInfo;
}

interface NodeEarnings {
  current_period: number;
  total_earned: number;
  pending_payouts: number;
  payout_history: Payout[];
}
```

## Testing Integration

### 1. API Mocking

```typescript
// Mock API responses for testing
class ApiMockService {
  private mockResponses: Map<string, any> = new Map();
  
  setupMocks(): void {
    // Admin API mocks
    this.mockResponses.set('GET /api/v1/admin/system/status', {
      status: 'healthy',
      services: ['api-gateway', 'blockchain-core', 'session-management'],
      uptime: 3600
    });
    
    // User API mocks
    this.mockResponses.set('GET /api/v1/user/sessions', {
      sessions: [
        { id: '1', title: 'Test Session', status: 'active' }
      ]
    });
    
    // Developer API mocks
    this.mockResponses.set('GET /api/v1/developer/endpoints', {
      endpoints: [
        { path: '/api/v1/sessions', method: 'GET', description: 'List sessions' }
      ]
    });
    
    // Node API mocks
    this.mockResponses.set('GET /api/v1/node/status', {
      status: 'online',
      health: 'healthy',
      resources: { cpu: 45, memory: 60, disk: 30 }
    });
  }
  
  getMockResponse(endpoint: string, method: string): any {
    const key = `${method} ${endpoint}`;
    return this.mockResponses.get(key);
  }
}
```

### 2. Integration Testing

```typescript
// Integration tests for API communication
describe('API Integration', () => {
  let apiClient: ApiClient;
  let mockService: ApiMockService;
  
  beforeEach(() => {
    apiClient = new ApiClient({
      baseUrl: 'http://localhost:8080',
      timeout: 5000,
      retries: 3,
      torProxy: 'socks5://127.0.0.1:9050'
    });
    
    mockService = new ApiMockService();
    mockService.setupMocks();
  });
  
  test('should connect to API through Tor proxy', async () => {
    const response = await apiClient.get('/api/v1/health');
    expect(response.success).toBe(true);
  });
  
  test('should handle authentication', async () => {
    const authService = new AuthService(apiClient);
    const result = await authService.login({
      username: 'test',
      password: 'test'
    });
    
    expect(result.success).toBe(true);
    expect(authService.isAuthenticated()).toBe(true);
  });
  
  test('should handle rate limiting', async () => {
    const rateLimiter = new RateLimiter();
    
    // Make multiple requests quickly
    for (let i = 0; i < 10; i++) {
      const canMake = rateLimiter.canMakeRequest('/api/v1/sessions', 'authenticated');
      expect(canMake).toBe(true);
      rateLimiter.recordRequest('/api/v1/sessions');
    }
  });
});
```

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-01-10  
**Next Review**: 2025-02-10
