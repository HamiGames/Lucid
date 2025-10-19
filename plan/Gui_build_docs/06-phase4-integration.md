# Phase 4: Integration & Testing

## Overview

Phase 4 focuses on integrating all components, implementing comprehensive testing, and preparing for deployment. This phase ensures the Electron GUI system is production-ready.

## 4.1 Preload Scripts (Security Bridge)

### Preload Script Implementation

Preload scripts serve as the security bridge between the main process and renderer processes, ensuring secure IPC communication.

#### User GUI Preload Script
**File**: `main/preload-user.js`

```javascript
const { contextBridge, ipcRenderer } = require('electron');

// Define valid channels for security
const validChannels = [
  'sessions:create',
  'sessions:list',
  'sessions:get',
  'sessions:update',
  'sessions:delete',
  'chunks:upload',
  'chunks:download',
  'chunks:list',
  'proofs:verify',
  'proofs:merkle',
  'proofs:audit-trail',
  'wallet:connect',
  'wallet:balance',
  'wallet:address',
  'wallet:sign',
  'tor:status',
  'tor:circuits',
  'session-updated',
  'chunk-uploaded',
  'proof-verified',
  'tor-status-changed'
];

// Expose secure API to renderer
contextBridge.exposeInMainWorld('electronAPI', {
  // Session operations
  sessions: {
    create: (data) => {
      if (typeof data !== 'object' || data === null) {
        throw new Error('Invalid session data');
      }
      return ipcRenderer.invoke('sessions:create', data);
    },
    
    list: (userId) => {
      if (typeof userId !== 'string' || !userId.trim()) {
        throw new Error('Invalid user ID');
      }
      return ipcRenderer.invoke('sessions:list', userId);
    },
    
    get: (sessionId) => {
      if (typeof sessionId !== 'string' || !sessionId.trim()) {
        throw new Error('Invalid session ID');
      }
      return ipcRenderer.invoke('sessions:get', sessionId);
    },
    
    update: (sessionId, data) => {
      if (typeof sessionId !== 'string' || !sessionId.trim()) {
        throw new Error('Invalid session ID');
      }
      if (typeof data !== 'object' || data === null) {
        throw new Error('Invalid update data');
      }
      return ipcRenderer.invoke('sessions:update', sessionId, data);
    },
    
    delete: (sessionId) => {
      if (typeof sessionId !== 'string' || !sessionId.trim()) {
        throw new Error('Invalid session ID');
      }
      return ipcRenderer.invoke('sessions:delete', sessionId);
    }
  },
  
  // Chunk operations
  chunks: {
    upload: (sessionId, chunk) => {
      if (typeof sessionId !== 'string' || !sessionId.trim()) {
        throw new Error('Invalid session ID');
      }
      if (typeof chunk !== 'object' || chunk === null) {
        throw new Error('Invalid chunk data');
      }
      return ipcRenderer.invoke('chunks:upload', sessionId, chunk);
    },
    
    download: (chunkId) => {
      if (typeof chunkId !== 'string' || !chunkId.trim()) {
        throw new Error('Invalid chunk ID');
      }
      return ipcRenderer.invoke('chunks:download', chunkId);
    },
    
    list: (sessionId) => {
      if (typeof sessionId !== 'string' || !sessionId.trim()) {
        throw new Error('Invalid session ID');
      }
      return ipcRenderer.invoke('chunks:list', sessionId);
    }
  },
  
  // Proof verification
  proofs: {
    verify: (sessionId) => {
      if (typeof sessionId !== 'string' || !sessionId.trim()) {
        throw new Error('Invalid session ID');
      }
      return ipcRenderer.invoke('proofs:verify', sessionId);
    },
    
    getMerkleProof: (chunkId) => {
      if (typeof chunkId !== 'string' || !chunkId.trim()) {
        throw new Error('Invalid chunk ID');
      }
      return ipcRenderer.invoke('proofs:merkle', chunkId);
    },
    
    getAuditTrail: (sessionId) => {
      if (typeof sessionId !== 'string' || !sessionId.trim()) {
        throw new Error('Invalid session ID');
      }
      return ipcRenderer.invoke('proofs:audit-trail', sessionId);
    }
  },
  
  // Wallet integration
  wallet: {
    connect: () => ipcRenderer.invoke('wallet:connect'),
    getBalance: () => ipcRenderer.invoke('wallet:balance'),
    getAddress: () => ipcRenderer.invoke('wallet:address'),
    signTransaction: (tx) => {
      if (typeof tx !== 'object' || tx === null) {
        throw new Error('Invalid transaction data');
      }
      return ipcRenderer.invoke('wallet:sign', tx);
    }
  },
  
  // Tor status
  tor: {
    getStatus: () => ipcRenderer.invoke('tor:status'),
    getCircuits: () => ipcRenderer.invoke('tor:circuits')
  },
  
  // Event listeners
  on: (channel, callback) => {
    if (!validChannels.includes(channel)) {
      throw new Error(`Invalid channel: ${channel}`);
    }
    if (typeof callback !== 'function') {
      throw new Error('Callback must be a function');
    }
    ipcRenderer.on(channel, (event, ...args) => callback(...args));
  },
  
  // Remove listeners
  removeAllListeners: (channel) => {
    if (!validChannels.includes(channel)) {
      throw new Error(`Invalid channel: ${channel}`);
    }
    ipcRenderer.removeAllListeners(channel);
  }
});
```

#### Developer GUI Preload Script
**File**: `main/preload-developer.js`

```javascript
const { contextBridge, ipcRenderer } = require('electron');

const validChannels = [
  'docker:start-stack',
  'docker:stop-stack',
  'docker:service-status',
  'docker:get-services',
  'docker:get-health',
  'api:test-endpoint',
  'logs:get-logs',
  'logs:stream-logs',
  'blockchain:get-block',
  'blockchain:get-transaction',
  'blockchain:get-latest',
  'metrics:get-metrics',
  'service-started',
  'service-stopped',
  'service-health-changed',
  'log-entry'
];

contextBridge.exposeInMainWorld('electronAPI', {
  // Docker management
  docker: {
    startStack: (level) => {
      if (!['developer', 'admin'].includes(level)) {
        throw new Error('Invalid stack level');
      }
      return ipcRenderer.invoke('docker:start-stack', level);
    },
    
    stopStack: () => ipcRenderer.invoke('docker:stop-stack'),
    
    getServices: () => ipcRenderer.invoke('docker:get-services'),
    
    getServiceStatus: (serviceName) => {
      if (typeof serviceName !== 'string' || !serviceName.trim()) {
        throw new Error('Invalid service name');
      }
      return ipcRenderer.invoke('docker:service-status', serviceName);
    },
    
    getSystemHealth: () => ipcRenderer.invoke('docker:get-health')
  },
  
  // API testing
  api: {
    testEndpoint: (config) => {
      if (typeof config !== 'object' || config === null) {
        throw new Error('Invalid API test configuration');
      }
      return ipcRenderer.invoke('api:test-endpoint', config);
    }
  },
  
  // Log viewer
  logs: {
    getLogs: (serviceName) => {
      if (typeof serviceName !== 'string' || !serviceName.trim()) {
        throw new Error('Invalid service name');
      }
      return ipcRenderer.invoke('logs:get-logs', serviceName);
    },
    
    streamLogs: (serviceName, callback) => {
      if (typeof serviceName !== 'string' || !serviceName.trim()) {
        throw new Error('Invalid service name');
      }
      if (typeof callback !== 'function') {
        throw new Error('Callback must be a function');
      }
      ipcRenderer.on('log-entry', (event, data) => {
        if (data.serviceName === serviceName) {
          callback(data);
        }
      });
    }
  },
  
  // Blockchain explorer
  blockchain: {
    getBlock: (height) => {
      if (typeof height !== 'number' || height < 0) {
        throw new Error('Invalid block height');
      }
      return ipcRenderer.invoke('blockchain:get-block', height);
    },
    
    getTransaction: (txId) => {
      if (typeof txId !== 'string' || !txId.trim()) {
        throw new Error('Invalid transaction ID');
      }
      return ipcRenderer.invoke('blockchain:get-transaction', txId);
    },
    
    getLatestBlocks: (limit) => {
      if (typeof limit !== 'number' || limit < 1 || limit > 100) {
        throw new Error('Invalid limit');
      }
      return ipcRenderer.invoke('blockchain:get-latest', limit);
    }
  },
  
  // Metrics
  metrics: {
    getMetrics: (serviceName) => {
      if (typeof serviceName !== 'string' || !serviceName.trim()) {
        throw new Error('Invalid service name');
      }
      return ipcRenderer.invoke('metrics:get-metrics', serviceName);
    }
  },
  
  // Event listeners
  on: (channel, callback) => {
    if (!validChannels.includes(channel)) {
      throw new Error(`Invalid channel: ${channel}`);
    }
    if (typeof callback !== 'function') {
      throw new Error('Callback must be a function');
    }
    ipcRenderer.on(channel, (event, ...args) => callback(...args));
  },
  
  removeAllListeners: (channel) => {
    if (!validChannels.includes(channel)) {
      throw new Error(`Invalid channel: ${channel}`);
    }
    ipcRenderer.removeAllListeners(channel);
  }
});
```

#### Node GUI Preload Script
**File**: `main/preload-node.js`

```javascript
const { contextBridge, ipcRenderer } = require('electron');

const validChannels = [
  'nodes:register',
  'nodes:get-status',
  'nodes:update',
  'pools:list',
  'pools:join',
  'pools:leave',
  'poot:get-score',
  'poot:get-history',
  'resources:get-usage',
  'payouts:get-history',
  'payouts:request',
  'node-status-changed',
  'poot-score-updated',
  'payout-received'
];

contextBridge.exposeInMainWorld('electronAPI', {
  // Node management
  nodes: {
    register: (nodeData) => {
      if (typeof nodeData !== 'object' || nodeData === null) {
        throw new Error('Invalid node data');
      }
      return ipcRenderer.invoke('nodes:register', nodeData);
    },
    
    getStatus: (nodeId) => {
      if (typeof nodeId !== 'string' || !nodeId.trim()) {
        throw new Error('Invalid node ID');
      }
      return ipcRenderer.invoke('nodes:get-status', nodeId);
    },
    
    update: (nodeId, data) => {
      if (typeof nodeId !== 'string' || !nodeId.trim()) {
        throw new Error('Invalid node ID');
      }
      if (typeof data !== 'object' || data === null) {
        throw new Error('Invalid update data');
      }
      return ipcRenderer.invoke('nodes:update', nodeId, data);
    }
  },
  
  // Pool management
  pools: {
    list: () => ipcRenderer.invoke('pools:list'),
    
    join: (nodeId, poolId) => {
      if (typeof nodeId !== 'string' || !nodeId.trim()) {
        throw new Error('Invalid node ID');
      }
      if (typeof poolId !== 'string' || !poolId.trim()) {
        throw new Error('Invalid pool ID');
      }
      return ipcRenderer.invoke('pools:join', nodeId, poolId);
    },
    
    leave: (nodeId) => {
      if (typeof nodeId !== 'string' || !nodeId.trim()) {
        throw new Error('Invalid node ID');
      }
      return ipcRenderer.invoke('pools:leave', nodeId);
    }
  },
  
  // PoOT tracking
  poot: {
    getScore: (nodeId) => {
      if (typeof nodeId !== 'string' || !nodeId.trim()) {
        throw new Error('Invalid node ID');
      }
      return ipcRenderer.invoke('poot:get-score', nodeId);
    },
    
    getHistory: (nodeId) => {
      if (typeof nodeId !== 'string' || !nodeId.trim()) {
        throw new Error('Invalid node ID');
      }
      return ipcRenderer.invoke('poot:get-history', nodeId);
    }
  },
  
  // Resource monitoring
  resources: {
    getUsage: (nodeId) => {
      if (typeof nodeId !== 'string' || !nodeId.trim()) {
        throw new Error('Invalid node ID');
      }
      return ipcRenderer.invoke('resources:get-usage', nodeId);
    }
  },
  
  // Payout management
  payouts: {
    getHistory: (nodeId) => {
      if (typeof nodeId !== 'string' || !nodeId.trim()) {
        throw new Error('Invalid node ID');
      }
      return ipcRenderer.invoke('payouts:get-history', nodeId);
    },
    
    request: (nodeId, amount) => {
      if (typeof nodeId !== 'string' || !nodeId.trim()) {
        throw new Error('Invalid node ID');
      }
      if (typeof amount !== 'number' || amount <= 0) {
        throw new Error('Invalid payout amount');
      }
      return ipcRenderer.invoke('payouts:request', nodeId, amount);
    }
  },
  
  // Event listeners
  on: (channel, callback) => {
    if (!validChannels.includes(channel)) {
      throw new Error(`Invalid channel: ${channel}`);
    }
    if (typeof callback !== 'function') {
      throw new Error('Callback must be a function');
    }
    ipcRenderer.on(channel, (event, ...args) => callback(...args));
  },
  
  removeAllListeners: (channel) => {
    if (!validChannels.includes(channel)) {
      throw new Error(`Invalid channel: ${channel}`);
    }
    ipcRenderer.removeAllListeners(channel);
  }
});
```

#### Admin GUI Preload Script
**File**: `main/preload-admin.js`

```javascript
const { contextBridge, ipcRenderer } = require('electron');

const validChannels = [
  'system:get-health',
  'system:start-full-stack',
  'system:emergency-shutdown',
  'users:list',
  'users:update-role',
  'users:suspend',
  'sessions:list-all',
  'sessions:get-analytics',
  'nodes:list-all',
  'nodes:approve',
  'nodes:suspend',
  'payouts:list-all',
  'payouts:process',
  'audit:get-logs',
  'audit:get-security-events',
  'system-health-changed',
  'user-role-changed',
  'node-status-changed',
  'payout-processed',
  'security-alert'
];

contextBridge.exposeInMainWorld('electronAPI', {
  // System management
  system: {
    getHealth: () => ipcRenderer.invoke('system:get-health'),
    startFullStack: () => ipcRenderer.invoke('system:start-full-stack'),
    emergencyShutdown: () => ipcRenderer.invoke('system:emergency-shutdown')
  },
  
  // User management
  users: {
    list: () => ipcRenderer.invoke('users:list'),
    updateRole: (userId, role) => {
      if (typeof userId !== 'string' || !userId.trim()) {
        throw new Error('Invalid user ID');
      }
      if (!['user', 'node_operator', 'admin', 'super_admin'].includes(role)) {
        throw new Error('Invalid role');
      }
      return ipcRenderer.invoke('users:update-role', userId, role);
    },
    suspend: (userId) => {
      if (typeof userId !== 'string' || !userId.trim()) {
        throw new Error('Invalid user ID');
      }
      return ipcRenderer.invoke('users:suspend', userId);
    }
  },
  
  // Session monitoring
  sessions: {
    listAll: () => ipcRenderer.invoke('sessions:list-all'),
    getAnalytics: () => ipcRenderer.invoke('sessions:get-analytics')
  },
  
  // Node administration
  nodes: {
    listAll: () => ipcRenderer.invoke('nodes:list-all'),
    approve: (nodeId) => {
      if (typeof nodeId !== 'string' || !nodeId.trim()) {
        throw new Error('Invalid node ID');
      }
      return ipcRenderer.invoke('nodes:approve', nodeId);
    },
    suspend: (nodeId) => {
      if (typeof nodeId !== 'string' || !nodeId.trim()) {
        throw new Error('Invalid node ID');
      }
      return ipcRenderer.invoke('nodes:suspend', nodeId);
    }
  },
  
  // Payout management
  payouts: {
    listAll: () => ipcRenderer.invoke('payouts:list-all'),
    process: (payoutId) => {
      if (typeof payoutId !== 'string' || !payoutId.trim()) {
        throw new Error('Invalid payout ID');
      }
      return ipcRenderer.invoke('payouts:process', payoutId);
    }
  },
  
  // Audit logs
  audit: {
    getLogs: () => ipcRenderer.invoke('audit:get-logs'),
    getSecurityEvents: () => ipcRenderer.invoke('audit:get-security-events')
  },
  
  // Event listeners
  on: (channel, callback) => {
    if (!validChannels.includes(channel)) {
      throw new Error(`Invalid channel: ${channel}`);
    }
    if (typeof callback !== 'function') {
      throw new Error('Callback must be a function');
    }
    ipcRenderer.on(channel, (event, ...args) => callback(...args));
  },
  
  removeAllListeners: (channel) => {
    if (!validChannels.includes(channel)) {
      throw new Error(`Invalid channel: ${channel}`);
    }
    ipcRenderer.removeAllListeners(channel);
  }
});
```

## 4.2 IPC Handlers (Main Process)

### Comprehensive IPC Handler Implementation

**File**: `main/ipc-handlers.ts`

```typescript
import { ipcMain } from 'electron';
import { LucidAPIClient } from '../shared/api-client';
import { TorManager } from './tor-manager';
import { DockerManager } from './docker-manager';
import { WindowManager } from './window-manager';

export function registerIPCHandlers(
  torManager: TorManager,
  dockerManager: DockerManager,
  windowManager: WindowManager
) {
  const apiClient = new LucidAPIClient('http://localhost:8080');
  
  // Session handlers
  ipcMain.handle('sessions:create', async (event, data) => {
    try {
      const session = await apiClient.createSession(data);
      return { success: true, data: session };
    } catch (error) {
      return { success: false, error: error.message, code: error.code };
    }
  });
  
  ipcMain.handle('sessions:list', async (event, userId) => {
    try {
      const sessions = await apiClient.getUserSessions(userId);
      return { success: true, data: sessions };
    } catch (error) {
      return { success: false, error: error.message, code: error.code };
    }
  });
  
  ipcMain.handle('sessions:get', async (event, sessionId) => {
    try {
      const session = await apiClient.getSession(sessionId);
      return { success: true, data: session };
    } catch (error) {
      return { success: false, error: error.message, code: error.code };
    }
  });
  
  ipcMain.handle('sessions:update', async (event, sessionId, data) => {
    try {
      const session = await apiClient.updateSession(sessionId, data);
      return { success: true, data: session };
    } catch (error) {
      return { success: false, error: error.message, code: error.code };
    }
  });
  
  ipcMain.handle('sessions:delete', async (event, sessionId) => {
    try {
      await apiClient.deleteSession(sessionId);
      return { success: true };
    } catch (error) {
      return { success: false, error: error.message, code: error.code };
    }
  });
  
  // Chunk handlers
  ipcMain.handle('chunks:upload', async (event, sessionId, chunk) => {
    try {
      const result = await apiClient.uploadChunk(sessionId, chunk);
      return { success: true, data: result };
    } catch (error) {
      return { success: false, error: error.message, code: error.code };
    }
  });
  
  ipcMain.handle('chunks:download', async (event, chunkId) => {
    try {
      const chunk = await apiClient.downloadChunk(chunkId);
      return { success: true, data: chunk };
    } catch (error) {
      return { success: false, error: error.message, code: error.code };
    }
  });
  
  ipcMain.handle('chunks:list', async (event, sessionId) => {
    try {
      const chunks = await apiClient.getSessionChunks(sessionId);
      return { success: true, data: chunks };
    } catch (error) {
      return { success: false, error: error.message, code: error.code };
    }
  });
  
  // Proof handlers
  ipcMain.handle('proofs:verify', async (event, sessionId) => {
    try {
      const proof = await apiClient.verifySessionProof(sessionId);
      return { success: true, data: proof };
    } catch (error) {
      return { success: false, error: error.message, code: error.code };
    }
  });
  
  ipcMain.handle('proofs:merkle', async (event, chunkId) => {
    try {
      const proof = await apiClient.getMerkleProof(chunkId);
      return { success: true, data: proof };
    } catch (error) {
      return { success: false, error: error.message, code: error.code };
    }
  });
  
  ipcMain.handle('proofs:audit-trail', async (event, sessionId) => {
    try {
      const auditTrail = await apiClient.getAuditTrail(sessionId);
      return { success: true, data: auditTrail };
    } catch (error) {
      return { success: false, error: error.message, code: error.code };
    }
  });
  
  // Wallet handlers
  ipcMain.handle('wallet:connect', async (event) => {
    try {
      // Implement hardware wallet connection
      const wallet = await connectHardwareWallet();
      return { success: true, data: wallet };
    } catch (error) {
      return { success: false, error: error.message };
    }
  });
  
  ipcMain.handle('wallet:balance', async (event) => {
    try {
      const balance = await getWalletBalance();
      return { success: true, data: balance };
    } catch (error) {
      return { success: false, error: error.message };
    }
  });
  
  ipcMain.handle('wallet:address', async (event) => {
    try {
      const address = await getWalletAddress();
      return { success: true, data: address };
    } catch (error) {
      return { success: false, error: error.message };
    }
  });
  
  ipcMain.handle('wallet:sign', async (event, tx) => {
    try {
      const signature = await signTransaction(tx);
      return { success: true, data: signature };
    } catch (error) {
      return { success: false, error: error.message };
    }
  });
  
  // Tor handlers
  ipcMain.handle('tor:status', async (event) => {
    try {
      const status = await torManager.getStatus();
      return { success: true, data: status };
    } catch (error) {
      return { success: false, error: error.message };
    }
  });
  
  ipcMain.handle('tor:circuits', async (event) => {
    try {
      const circuits = await torManager.getCircuits();
      return { success: true, data: circuits };
    } catch (error) {
      return { success: false, error: error.message };
    }
  });
  
  // Docker handlers (developer/admin only)
  ipcMain.handle('docker:start-stack', async (event, level) => {
    try {
      await dockerManager.startLucidStack(level);
      return { success: true };
    } catch (error) {
      return { success: false, error: error.message };
    }
  });
  
  ipcMain.handle('docker:stop-stack', async (event) => {
    try {
      await dockerManager.stopAllServices();
      return { success: true };
    } catch (error) {
      return { success: false, error: error.message };
    }
  });
  
  ipcMain.handle('docker:get-services', async (event) => {
    try {
      const services = await dockerManager.getAllServices();
      return { success: true, data: services };
    } catch (error) {
      return { success: false, error: error.message };
    }
  });
  
  ipcMain.handle('docker:service-status', async (event, serviceName) => {
    try {
      const status = await dockerManager.getServiceStatus(serviceName);
      return { success: true, data: status };
    } catch (error) {
      return { success: false, error: error.message };
    }
  });
  
  ipcMain.handle('docker:get-health', async (event) => {
    try {
      const health = await dockerManager.getSystemHealth();
      return { success: true, data: health };
    } catch (error) {
      return { success: false, error: error.message };
    }
  });
  
  // Node handlers
  ipcMain.handle('nodes:register', async (event, nodeData) => {
    try {
      const node = await apiClient.registerNode(nodeData);
      return { success: true, data: node };
    } catch (error) {
      return { success: false, error: error.message, code: error.code };
    }
  });
  
  ipcMain.handle('nodes:get-status', async (event, nodeId) => {
    try {
      const status = await apiClient.getNodeStatus(nodeId);
      return { success: true, data: status };
    } catch (error) {
      return { success: false, error: error.message, code: error.code };
    }
  });
  
  ipcMain.handle('nodes:update', async (event, nodeId, data) => {
    try {
      const node = await apiClient.updateNode(nodeId, data);
      return { success: true, data: node };
    } catch (error) {
      return { success: false, error: error.message, code: error.code };
    }
  });
  
  // Pool handlers
  ipcMain.handle('pools:list', async (event) => {
    try {
      const pools = await apiClient.getPools();
      return { success: true, data: pools };
    } catch (error) {
      return { success: false, error: error.message, code: error.code };
    }
  });
  
  ipcMain.handle('pools:join', async (event, nodeId, poolId) => {
    try {
      const result = await apiClient.joinPool(nodeId, poolId);
      return { success: true, data: result };
    } catch (error) {
      return { success: false, error: error.message, code: error.code };
    }
  });
  
  ipcMain.handle('pools:leave', async (event, nodeId) => {
    try {
      const result = await apiClient.leavePool(nodeId);
      return { success: true, data: result };
    } catch (error) {
      return { success: false, error: error.message, code: error.code };
    }
  });
  
  // PoOT handlers
  ipcMain.handle('poot:get-score', async (event, nodeId) => {
    try {
      const score = await apiClient.getPootScore(nodeId);
      return { success: true, data: score };
    } catch (error) {
      return { success: false, error: error.message, code: error.code };
    }
  });
  
  ipcMain.handle('poot:get-history', async (event, nodeId) => {
    try {
      const history = await apiClient.getPootHistory(nodeId);
      return { success: true, data: history };
    } catch (error) {
      return { success: false, error: error.message, code: error.code };
    }
  });
  
  // Resource handlers
  ipcMain.handle('resources:get-usage', async (event, nodeId) => {
    try {
      const usage = await apiClient.getResourceUsage(nodeId);
      return { success: true, data: usage };
    } catch (error) {
      return { success: false, error: error.message, code: error.code };
    }
  });
  
  // Payout handlers
  ipcMain.handle('payouts:get-history', async (event, nodeId) => {
    try {
      const history = await apiClient.getPayoutHistory(nodeId);
      return { success: true, data: history };
    } catch (error) {
      return { success: false, error: error.message, code: error.code };
    }
  });
  
  ipcMain.handle('payouts:request', async (event, nodeId, amount) => {
    try {
      const payout = await apiClient.requestPayout(nodeId, amount);
      return { success: true, data: payout };
    } catch (error) {
      return { success: false, error: error.message, code: error.code };
    }
  });
  
  // System handlers (admin only)
  ipcMain.handle('system:get-health', async (event) => {
    try {
      const health = await dockerManager.getSystemHealth();
      return { success: true, data: health };
    } catch (error) {
      return { success: false, error: error.message };
    }
  });
  
  ipcMain.handle('system:start-full-stack', async (event) => {
    try {
      await dockerManager.startLucidStack('admin');
      return { success: true };
    } catch (error) {
      return { success: false, error: error.message };
    }
  });
  
  ipcMain.handle('system:emergency-shutdown', async (event) => {
    try {
      await dockerManager.stopAllServices();
      // Additional emergency procedures
      return { success: true };
    } catch (error) {
      return { success: false, error: error.message };
    }
  });
  
  // User management handlers (admin only)
  ipcMain.handle('users:list', async (event) => {
    try {
      const users = await apiClient.getAllUsers();
      return { success: true, data: users };
    } catch (error) {
      return { success: false, error: error.message, code: error.code };
    }
  });
  
  ipcMain.handle('users:update-role', async (event, userId, role) => {
    try {
      const user = await apiClient.updateUserRole(userId, role);
      return { success: true, data: user };
    } catch (error) {
      return { success: false, error: error.message, code: error.code };
    }
  });
  
  ipcMain.handle('users:suspend', async (event, userId) => {
    try {
      const result = await apiClient.suspendUser(userId);
      return { success: true, data: result };
    } catch (error) {
      return { success: false, error: error.message, code: error.code };
    }
  });
  
  // Session monitoring handlers (admin only)
  ipcMain.handle('sessions:list-all', async (event) => {
    try {
      const sessions = await apiClient.getAllSessions();
      return { success: true, data: sessions };
    } catch (error) {
      return { success: false, error: error.message, code: error.code };
    }
  });
  
  ipcMain.handle('sessions:get-analytics', async (event) => {
    try {
      const analytics = await apiClient.getSessionAnalytics();
      return { success: true, data: analytics };
    } catch (error) {
      return { success: false, error: error.message, code: error.code };
    }
  });
  
  // Node administration handlers (admin only)
  ipcMain.handle('nodes:list-all', async (event) => {
    try {
      const nodes = await apiClient.getAllNodes();
      return { success: true, data: nodes };
    } catch (error) {
      return { success: false, error: error.message, code: error.code };
    }
  });
  
  ipcMain.handle('nodes:approve', async (event, nodeId) => {
    try {
      const result = await apiClient.approveNode(nodeId);
      return { success: true, data: result };
    } catch (error) {
      return { success: false, error: error.message, code: error.code };
    }
  });
  
  ipcMain.handle('nodes:suspend', async (event, nodeId) => {
    try {
      const result = await apiClient.suspendNode(nodeId);
      return { success: true, data: result };
    } catch (error) {
      return { success: false, error: error.message, code: error.code };
    }
  });
  
  // Payout management handlers (admin only)
  ipcMain.handle('payouts:list-all', async (event) => {
    try {
      const payouts = await apiClient.getAllPayouts();
      return { success: true, data: payouts };
    } catch (error) {
      return { success: false, error: error.message, code: error.code };
    }
  });
  
  ipcMain.handle('payouts:process', async (event, payoutId) => {
    try {
      const result = await apiClient.processPayout(payoutId);
      return { success: true, data: result };
    } catch (error) {
      return { success: false, error: error.message, code: error.code };
    }
  });
  
  // Audit log handlers (admin only)
  ipcMain.handle('audit:get-logs', async (event) => {
    try {
      const logs = await apiClient.getAuditLogs();
      return { success: true, data: logs };
    } catch (error) {
      return { success: false, error: error.message, code: error.code };
    }
  });
  
  ipcMain.handle('audit:get-security-events', async (event) => {
    try {
      const events = await apiClient.getSecurityEvents();
      return { success: true, data: events };
    } catch (error) {
      return { success: false, error: error.message, code: error.code };
    }
  });
}

// Helper functions for hardware wallet integration
async function connectHardwareWallet() {
  // Implement hardware wallet connection logic
  // This would integrate with Ledger, Trezor, etc.
  throw new Error('Hardware wallet integration not implemented');
}

async function getWalletBalance() {
  // Implement wallet balance retrieval
  throw new Error('Wallet balance retrieval not implemented');
}

async function getWalletAddress() {
  // Implement wallet address retrieval
  throw new Error('Wallet address retrieval not implemented');
}

async function signTransaction(tx: any) {
  // Implement transaction signing
  throw new Error('Transaction signing not implemented');
}
```

## 4.3 Build Configuration

### Electron Builder Configuration

**File**: `electron-builder.json`

```json
{
  "appId": "com.lucid.electron-gui",
  "productName": "Lucid Desktop",
  "directories": {
    "output": "dist",
    "buildResources": "assets"
  },
  "files": [
    "main/**/*",
    "renderer/**/*",
    "shared/**/*",
    "assets/**/*",
    "!assets/source/**/*",
    "!**/*.map"
  ],
  "extraResources": [
    {
      "from": "assets/tor",
      "to": "tor",
      "filter": ["**/*"]
    },
    {
      "from": "assets/icons",
      "to": "icons",
      "filter": ["**/*"]
    }
  ],
  "win": {
    "target": [
      {
        "target": "nsis",
        "arch": ["x64", "arm64"]
      },
      {
        "target": "portable",
        "arch": ["x64", "arm64"]
      }
    ],
    "icon": "assets/icons/icon.ico",
    "publisherName": "Lucid Systems",
    "verifyUpdateCodeSignature": false
  },
  "linux": {
    "target": [
      {
        "target": "AppImage",
        "arch": ["x64", "arm64"]
      },
      {
        "target": "deb",
        "arch": ["x64", "arm64"]
      }
    ],
    "icon": "assets/icons/icon.png",
    "category": "Network",
    "synopsis": "Lucid Desktop GUI - Multi-window Electron application",
    "description": "Lucid Desktop GUI provides secure access to the Lucid network through multiple specialized interfaces for users, developers, node operators, and administrators."
  },
  "mac": {
    "target": [
      {
        "target": "dmg",
        "arch": ["x64", "arm64"]
      }
    ],
    "icon": "assets/icons/icon.icns",
    "category": "public.app-category.developer-tools",
    "hardenedRuntime": true,
    "gatekeeperAssess": false,
    "entitlements": "assets/entitlements.mac.plist",
    "entitlementsInherit": "assets/entitlements.mac.plist"
  },
  "nsis": {
    "oneClick": false,
    "allowToChangeInstallationDirectory": true,
    "allowElevation": true,
    "installerIcon": "assets/icons/icon.ico",
    "uninstallerIcon": "assets/icons/icon.ico",
    "installerHeaderIcon": "assets/icons/icon.ico",
    "createDesktopShortcut": true,
    "createStartMenuShortcut": true,
    "shortcutName": "Lucid Desktop"
  },
  "portable": {
    "artifactName": "${productName}-${version}-portable.${ext}"
  },
  "publish": {
    "provider": "github",
    "owner": "HamiGames",
    "repo": "Lucid"
  },
  "buildVersion": "1.0.0",
  "compression": "maximum",
  "removePackageScripts": true
}
```

### Webpack Configuration

**File**: `webpack.config.js`

```javascript
const path = require('path');
const HtmlWebpackPlugin = require('html-webpack-plugin');

module.exports = {
  mode: 'development',
  entry: {
    user: './renderer/user/index.tsx',
    developer: './renderer/developer/index.tsx',
    node: './renderer/node/index.tsx',
    admin: './renderer/admin/index.tsx'
  },
  output: {
    path: path.resolve(__dirname, 'dist/renderer'),
    filename: '[name]/[name].js',
    clean: true
  },
  resolve: {
    extensions: ['.tsx', '.ts', '.jsx', '.js'],
    alias: {
      '@': path.resolve(__dirname, 'shared'),
      '@/components': path.resolve(__dirname, 'renderer'),
      '@/hooks': path.resolve(__dirname, 'shared/hooks'),
      '@/types': path.resolve(__dirname, 'shared/types.ts')
    }
  },
  module: {
    rules: [
      {
        test: /\.tsx?$/,
        use: 'ts-loader',
        exclude: /node_modules/
      },
      {
        test: /\.css$/,
        use: ['style-loader', 'css-loader']
      },
      {
        test: /\.(png|jpg|jpeg|gif|svg)$/,
        type: 'asset/resource'
      }
    ]
  },
  plugins: [
    new HtmlWebpackPlugin({
      template: './renderer/user/index.html',
      filename: 'user/index.html',
      chunks: ['user']
    }),
    new HtmlWebpackPlugin({
      template: './renderer/developer/index.html',
      filename: 'developer/index.html',
      chunks: ['developer']
    }),
    new HtmlWebpackPlugin({
      template: './renderer/node/index.html',
      filename: 'node/index.html',
      chunks: ['node']
    }),
    new HtmlWebpackPlugin({
      template: './renderer/admin/index.html',
      filename: 'admin/index.html',
      chunks: ['admin']
    })
  ],
  devServer: {
    static: {
      directory: path.join(__dirname, 'dist/renderer')
    },
    port: 3000,
    hot: true
  }
};
```

## 4.4 Testing Strategy

### Unit Testing Configuration

**File**: `jest.config.js`

```javascript
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'jsdom',
  roots: ['<rootDir>/shared', '<rootDir>/renderer'],
  testMatch: [
    '**/__tests__/**/*.+(ts|tsx|js)',
    '**/*.(test|spec).+(ts|tsx|js)'
  ],
  transform: {
    '^.+\\.(ts|tsx)$': 'ts-jest'
  },
  moduleNameMapping: {
    '^@/(.*)$': '<rootDir>/shared/$1',
    '^@/components/(.*)$': '<rootDir>/renderer/$1',
    '^@/hooks/(.*)$': '<rootDir>/shared/hooks/$1',
    '^@/types$': '<rootDir>/shared/types.ts'
  },
  setupFilesAfterEnv: ['<rootDir>/tests/setup.ts'],
  collectCoverageFrom: [
    'shared/**/*.{ts,tsx}',
    'renderer/**/*.{ts,tsx}',
    '!**/*.d.ts',
    '!**/node_modules/**'
  ],
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80
    }
  }
};
```

### E2E Testing Configuration

**File**: `jest.e2e.config.js`

```javascript
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  roots: ['<rootDir>/tests/e2e'],
  testMatch: ['**/*.e2e.spec.ts'],
  transform: {
    '^.+\\.ts$': 'ts-jest'
  },
  setupFilesAfterEnv: ['<rootDir>/tests/e2e/setup.ts'],
  testTimeout: 30000
};
```

### Test Implementation Examples

#### User GUI Tests
**File**: `tests/user-gui.spec.ts`

```typescript
import { Application } from 'spectron';
import path from 'path';

describe('User GUI', () => {
  let app: Application;
  
  beforeEach(async () => {
    app = new Application({
      path: path.join(__dirname, '..', 'node_modules', '.bin', 'electron'),
      args: [path.join(__dirname, '..')],
      env: {
        NODE_ENV: 'test'
      }
    });
    await app.start();
  });
  
  afterEach(async () => {
    if (app && app.isRunning()) {
      await app.stop();
    }
  });
  
  it('should launch user window', async () => {
    const count = await app.client.getWindowCount();
    expect(count).toBe(1);
  });
  
  it('should create session', async () => {
    await app.client.click('#create-session-btn');
    await app.client.waitForExist('#session-id', 5000);
    const sessionId = await app.client.getText('#session-id');
    expect(sessionId).toMatch(/^[a-f0-9-]{36}$/);
  });
  
  it('should upload chunk', async () => {
    // Create session first
    await app.client.click('#create-session-btn');
    await app.client.waitForExist('#session-id', 5000);
    
    // Upload chunk
    await app.client.setValue('#file-input', 'test-file.txt');
    await app.client.click('#upload-btn');
    await app.client.waitForExist('.upload-success', 10000);
    
    const successMessage = await app.client.getText('.upload-success');
    expect(successMessage).toContain('Chunk uploaded successfully');
  });
  
  it('should verify proof', async () => {
    // Setup session with chunks
    await setupSessionWithChunks();
    
    // Verify proof
    await app.client.click('#verify-proof-btn');
    await app.client.waitForExist('.proof-verified', 10000);
    
    const proofStatus = await app.client.getText('.proof-verified');
    expect(proofStatus).toContain('Proof verified');
  });
  
  it('should connect to Tor', async () => {
    await app.client.waitForExist('.tor-status', 10000);
    const torStatus = await app.client.getText('.tor-status');
    expect(torStatus).toContain('Connected');
  });
});

async function setupSessionWithChunks() {
  // Helper function to setup test session
  await app.client.click('#create-session-btn');
  await app.client.waitForExist('#session-id', 5000);
  
  // Upload test chunks
  for (let i = 0; i < 3; i++) {
    await app.client.setValue('#file-input', `test-chunk-${i}.txt`);
    await app.client.click('#upload-btn');
    await app.client.waitForExist('.upload-success', 5000);
  }
}
```

#### Developer GUI Tests
**File**: `tests/developer-gui.spec.ts`

```typescript
import { Application } from 'spectron';
import path from 'path';

describe('Developer GUI', () => {
  let app: Application;
  
  beforeEach(async () => {
    app = new Application({
      path: path.join(__dirname, '..', 'node_modules', '.bin', 'electron'),
      args: [path.join(__dirname, '..')],
      env: {
        NODE_ENV: 'test'
      }
    });
    await app.start();
  });
  
  afterEach(async () => {
    if (app && app.isRunning()) {
      await app.stop();
    }
  });
  
  it('should start developer stack', async () => {
    await app.client.click('#start-stack-btn');
    await app.client.waitForExist('.stack-started', 30000);
    
    const status = await app.client.getText('.stack-started');
    expect(status).toContain('Developer stack started');
  });
  
  it('should show service status', async () => {
    await app.client.click('#start-stack-btn');
    await app.client.waitForExist('.service-list', 30000);
    
    const services = await app.client.elements('.service-item');
    expect(services.length).toBeGreaterThan(0);
  });
  
  it('should test API endpoint', async () => {
    // Setup API test
    await app.client.setValue('#api-url', 'http://localhost:8080/api/v1/health');
    await app.client.setValue('#api-method', 'GET');
    await app.client.click('#test-api-btn');
    
    await app.client.waitForExist('.api-response', 10000);
    const response = await app.client.getText('.api-response');
    expect(response).toContain('success');
  });
  
  it('should view blockchain blocks', async () => {
    await app.client.click('#blockchain-tab');
    await app.client.waitForExist('.block-list', 5000);
    
    const blocks = await app.client.elements('.block-item');
    expect(blocks.length).toBeGreaterThan(0);
  });
  
  it('should stream service logs', async () => {
    await app.client.click('#logs-tab');
    await app.client.waitForExist('.log-viewer', 5000);
    
    // Check for log entries
    await app.client.waitForExist('.log-entry', 10000);
    const logEntries = await app.client.elements('.log-entry');
    expect(logEntries.length).toBeGreaterThan(0);
  });
});
```

#### Node GUI Tests
**File**: `tests/node-gui.spec.ts`

```typescript
import { Application } from 'spectron';
import path from 'path';

describe('Node GUI', () => {
  let app: Application;
  
  beforeEach(async () => {
    app = new Application({
      path: path.join(__dirname, '..', 'node_modules', '.bin', 'electron'),
      args: [path.join(__dirname, '..')],
      env: {
        NODE_ENV: 'test'
      }
    });
    await app.start();
  });
  
  afterEach(async () => {
    if (app && app.isRunning()) {
      await app.stop();
    }
  });
  
  it('should register node', async () => {
    await app.client.setValue('#operator-name', 'Test Operator');
    await app.client.setValue('#email', 'test@example.com');
    await app.client.setValue('#tron-address', 'TTest123...');
    await app.client.setValue('#cpu-spec', 'Intel i7-8700K');
    await app.client.setValue('#memory-spec', '16GB DDR4');
    await app.client.setValue('#disk-spec', '1TB SSD');
    await app.client.setValue('#network-spec', '100Mbps');
    
    await app.client.click('#register-btn');
    await app.client.waitForExist('.registration-success', 10000);
    
    const successMessage = await app.client.getText('.registration-success');
    expect(successMessage).toContain('Node registered successfully');
  });
  
  it('should join pool', async () => {
    // Setup registered node
    await setupRegisteredNode();
    
    await app.client.click('#pools-tab');
    await app.client.waitForExist('.pool-list', 5000);
    
    await app.client.click('.pool-item:first-child .join-btn');
    await app.client.waitForExist('.pool-joined', 10000);
    
    const status = await app.client.getText('.pool-joined');
    expect(status).toContain('Successfully joined pool');
  });
  
  it('should monitor resources', async () => {
    await setupRegisteredNode();
    
    await app.client.click('#resources-tab');
    await app.client.waitForExist('.resource-metrics', 5000);
    
    const cpuUsage = await app.client.getText('.cpu-usage');
    const memoryUsage = await app.client.getText('.memory-usage');
    
    expect(cpuUsage).toMatch(/\d+%/);
    expect(memoryUsage).toMatch(/\d+%/);
  });
  
  it('should track PoOT score', async () => {
    await setupRegisteredNode();
    
    await app.client.click('#poot-tab');
    await app.client.waitForExist('.poot-score', 5000);
    
    const score = await app.client.getText('.poot-score');
    expect(score).toMatch(/\d+\.\d+/);
  });
  
  it('should view payout history', async () => {
    await setupRegisteredNode();
    
    await app.client.click('#earnings-tab');
    await app.client.waitForExist('.payout-list', 5000);
    
    const payouts = await app.client.elements('.payout-item');
    expect(payouts.length).toBeGreaterThanOrEqual(0);
  });
});

async function setupRegisteredNode() {
  // Helper function to setup registered node
  await app.client.setValue('#operator-name', 'Test Operator');
  await app.client.setValue('#email', 'test@example.com');
  await app.client.setValue('#tron-address', 'TTest123...');
  await app.client.setValue('#cpu-spec', 'Intel i7-8700K');
  await app.client.setValue('#memory-spec', '16GB DDR4');
  await app.client.setValue('#disk-spec', '1TB SSD');
  await app.client.setValue('#network-spec', '100Mbps');
  
  await app.client.click('#register-btn');
  await app.client.waitForExist('.registration-success', 10000);
}
```

#### Admin GUI Tests
**File**: `tests/admin-gui.spec.ts`

```typescript
import { Application } from 'spectron';
import path from 'path';

describe('Admin GUI', () => {
  let app: Application;
  
  beforeEach(async () => {
    app = new Application({
      path: path.join(__dirname, '..', 'node_modules', '.bin', 'electron'),
      args: [path.join(__dirname, '..')],
      env: {
        NODE_ENV: 'test'
      }
    });
    await app.start();
  });
  
  afterEach(async () => {
    if (app && app.isRunning()) {
      await app.stop();
    }
  });
  
  it('should start full stack', async () => {
    await app.client.click('#start-full-stack-btn');
    await app.client.waitForExist('.stack-started', 60000);
    
    const status = await app.client.getText('.stack-started');
    expect(status).toContain('Full stack started');
  });
  
  it('should show system health', async () => {
    await app.client.waitForExist('.system-health', 10000);
    
    const healthStatus = await app.client.getText('.health-status');
    expect(['healthy', 'degraded', 'critical']).toContain(healthStatus);
  });
  
  it('should manage users', async () => {
    await app.client.click('#users-tab');
    await app.client.waitForExist('.user-list', 5000);
    
    const users = await app.client.elements('.user-item');
    expect(users.length).toBeGreaterThan(0);
  });
  
  it('should monitor sessions', async () => {
    await app.client.click('#sessions-tab');
    await app.client.waitForExist('.session-list', 5000);
    
    const sessions = await app.client.elements('.session-item');
    expect(sessions.length).toBeGreaterThanOrEqual(0);
  });
  
  it('should administer nodes', async () => {
    await app.client.click('#nodes-tab');
    await app.client.waitForExist('.node-list', 5000);
    
    const nodes = await app.client.elements('.node-item');
    expect(nodes.length).toBeGreaterThanOrEqual(0);
  });
  
  it('should manage payouts', async () => {
    await app.client.click('#payments-tab');
    await app.client.waitForExist('.payout-list', 5000);
    
    const payouts = await app.client.elements('.payout-item');
    expect(payouts.length).toBeGreaterThanOrEqual(0);
  });
  
  it('should view audit logs', async () => {
    await app.client.click('#security-tab');
    await app.client.waitForExist('.audit-logs', 5000);
    
    const logs = await app.client.elements('.log-entry');
    expect(logs.length).toBeGreaterThanOrEqual(0);
  });
  
  it('should handle emergency shutdown', async () => {
    await app.client.click('#emergency-shutdown-btn');
    await app.client.waitForExist('.shutdown-confirmation', 5000);
    
    await app.client.click('#confirm-shutdown-btn');
    await app.client.waitForExist('.shutdown-initiated', 10000);
    
    const status = await app.client.getText('.shutdown-initiated');
    expect(status).toContain('Emergency shutdown initiated');
  });
});
```

## Implementation Checklist

### Phase 4 Completion Criteria

- [ ] All preload scripts implemented with security validation
- [ ] Comprehensive IPC handlers for all operations
- [ ] Build configuration for all platforms
- [ ] Unit tests for all components
- [ ] E2E tests for all GUI workflows
- [ ] Security testing completed
- [ ] Performance testing completed
- [ ] Integration testing completed

### Testing Requirements

- [ ] All four GUIs launch and function correctly
- [ ] Tor integration works properly
- [ ] Docker service management functions
- [ ] API communication through Tor proxy
- [ ] Hardware wallet integration (when available)
- [ ] Error handling works in all scenarios
- [ ] Security measures are effective

### Security Verification

- [ ] Context isolation enforced
- [ ] No nodeIntegration in renderers
- [ ] IPC communication secure
- [ ] Tor proxy enforced
- [ ] Input validation in preload scripts
- [ ] No sensitive data exposure
- [ ] Secure storage implementation
