# Phase 3: Coordination & Syntax Guide

## Overview

Phase 3 establishes coordination patterns, shared interfaces, and development standards across all four GUI frames to ensure consistency and maintainability.

## 3.1 Shared TypeScript Interfaces

### Core Type Definitions

**File**: `shared/types.ts`

```typescript
// User types (from API Gateway - Cluster 01)
export interface User {
  user_id: string;
  email: string;
  tron_address: string;
  hardware_wallet?: HardwareWallet;
  role: 'user' | 'node_operator' | 'admin' | 'super_admin';
  created_at: string;
  updated_at: string;
}

export interface HardwareWallet {
  type: 'ledger' | 'trezor' | 'keepkey';
  address: string;
  public_key: string;
  connected: boolean;
  last_connected: string;
}

// Session types (from Session Management - Cluster 03)
export interface Session {
  session_id: string;
  user_id: string;
  status: 'active' | 'completed' | 'failed' | 'anchored';
  chunks: Chunk[];
  merkle_root?: string;
  blockchain_anchor?: BlockchainAnchor;
  privacy_level: 'public' | 'private' | 'confidential';
  created_at: string;
  updated_at: string;
  expires_at?: string;
}

export interface Chunk {
  chunk_id: string;
  session_id: string;
  sequence: number;
  hash: string;
  size: number;
  encrypted: boolean;
  compressed: boolean;
  created_at: string;
  uploaded_at?: string;
}

export interface BlockchainAnchor {
  transaction_hash: string;
  block_height: number;
  block_hash: string;
  timestamp: string;
  confirmation_count: number;
}

// Node types (from Node Management - Cluster 05)
export interface Node {
  node_id: string;
  operator_id: string;
  status: 'registered' | 'active' | 'inactive' | 'suspended';
  pool_id?: string;
  poot_score: number;
  resources: NodeResources;
  created_at: string;
  updated_at: string;
  last_seen: string;
}

export interface NodeResources {
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  network_bandwidth: number;
  uptime: number;
}

export interface Pool {
  pool_id: string;
  name: string;
  description: string;
  min_poot_score: number;
  max_nodes: number;
  current_nodes: number;
  status: 'active' | 'inactive' | 'full';
  created_at: string;
  updated_at: string;
}

// Blockchain types (from Blockchain Core - Cluster 02)
export interface Block {
  block_id: string;
  height: number;
  previous_hash: string;
  merkle_root: string;
  transactions: Transaction[];
  timestamp: string;
  consensus_votes?: ConsensusVote[];
  difficulty: number;
  nonce: number;
}

export interface Transaction {
  transaction_id: string;
  type: 'session_anchor' | 'payout' | 'governance';
  data: any;
  timestamp: string;
  block_height: number;
  fee: number;
  status: 'pending' | 'confirmed' | 'failed';
}

export interface ConsensusVote {
  node_id: string;
  vote: 'approve' | 'reject';
  timestamp: string;
  signature: string;
}

// Admin types
export interface ServiceStatus {
  name: string;
  status: 'starting' | 'healthy' | 'unhealthy' | 'stopped';
  uptime: number;
  cpu: number;
  memory: number;
  port: number;
  last_restart: string;
  error_count: number;
}

export interface SystemHealth {
  overall: 'healthy' | 'degraded' | 'critical';
  services: ServiceStatus[];
  tor_status: 'connected' | 'disconnected';
  docker_status: 'running' | 'stopped';
  last_updated: string;
}

// TRON Payment types (from TRON Payment - Cluster 07)
export interface Payout {
  payout_id: string;
  node_id: string;
  amount_usdt: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  transaction_hash?: string;
  created_at: string;
  completed_at?: string;
  fee: number;
}

// API Response types
export interface APIResponse<T> {
  success: boolean;
  data: T;
  error?: string;
  code?: string;
  timestamp: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  limit: number;
  has_more: boolean;
  next_page?: number;
  prev_page?: number;
}

// Error types
export interface LucidError {
  code: string;
  message: string;
  details?: any;
  timestamp: string;
  request_id?: string;
}

// Configuration types
export interface AppConfig {
  api_endpoints: {
    gateway: string;
    blockchain: string;
    auth: string;
    sessions: string;
    nodes: string;
    admin: string;
    tron_payment: string;
  };
  tor_config: {
    socks_port: number;
    control_port: number;
    data_dir: string;
  };
  gui_config: {
    theme: 'light' | 'dark';
    language: string;
    auto_update: boolean;
    notifications: boolean;
  };
}

// Event types for IPC communication
export interface IPCEvent {
  channel: string;
  data: any;
  timestamp: string;
  source: 'main' | 'renderer';
}

// File upload types
export interface FileUpload {
  file_id: string;
  file_name: string;
  file_size: number;
  file_type: string;
  chunk_count: number;
  uploaded_chunks: number;
  progress: number;
  status: 'uploading' | 'completed' | 'failed';
  created_at: string;
  completed_at?: string;
}

// Notification types
export interface Notification {
  id: string;
  type: 'info' | 'warning' | 'error' | 'success';
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
  actions?: NotificationAction[];
}

export interface NotificationAction {
  label: string;
  action: string;
  data?: any;
}
```

## 3.2 API Hooks Convention

### Standardized API Hooks

**File**: `shared/hooks/useAPI.ts`

```typescript
import { useState, useEffect, useCallback } from 'react';

export interface APIState<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
  lastUpdated: string | null;
}

export function useAPI<T>(
  apiCall: () => Promise<T>,
  dependencies: any[] = [],
  options: {
    immediate?: boolean;
    retryCount?: number;
    retryDelay?: number;
    onSuccess?: (data: T) => void;
    onError?: (error: Error) => void;
  } = {}
) {
  const [state, setState] = useState<APIState<T>>({
    data: null,
    loading: false,
    error: null,
    lastUpdated: null
  });

  const {
    immediate = true,
    retryCount = 0,
    retryDelay = 1000,
    onSuccess,
    onError
  } = options;

  const fetchData = useCallback(async (retryAttempt = 0) => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      const result = await apiCall();
      setState({
        data: result,
        loading: false,
        error: null,
        lastUpdated: new Date().toISOString()
      });
      onSuccess?.(result);
    } catch (err) {
      const error = err as Error;
      setState(prev => ({
        ...prev,
        loading: false,
        error,
        lastUpdated: new Date().toISOString()
      }));
      
      onError?.(error);
      
      // Retry logic
      if (retryAttempt < retryCount) {
        setTimeout(() => {
          fetchData(retryAttempt + 1);
        }, retryDelay);
      }
    }
  }, dependencies);

  const refetch = useCallback(() => {
    fetchData(0);
  }, [fetchData]);

  const reset = useCallback(() => {
    setState({
      data: null,
      loading: false,
      error: null,
      lastUpdated: null
    });
  }, []);

  useEffect(() => {
    if (immediate) {
      fetchData(0);
    }
  }, [fetchData, immediate]);

  return {
    ...state,
    refetch,
    reset
  };
}

// Specialized hooks for common patterns
export function useMutation<T, P>(
  mutationFn: (params: P) => Promise<T>,
  options: {
    onSuccess?: (data: T) => void;
    onError?: (error: Error) => void;
  } = {}
) {
  const [state, setState] = useState<APIState<T>>({
    data: null,
    loading: false,
    error: null,
    lastUpdated: null
  });

  const mutate = useCallback(async (params: P) => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      const result = await mutationFn(params);
      setState({
        data: result,
        loading: false,
        error: null,
        lastUpdated: new Date().toISOString()
      });
      options.onSuccess?.(result);
      return result;
    } catch (err) {
      const error = err as Error;
      setState(prev => ({
        ...prev,
        loading: false,
        error,
        lastUpdated: new Date().toISOString()
      }));
      options.onError?.(error);
      throw error;
    }
  }, [mutationFn, options]);

  return {
    ...state,
    mutate
  };
}

export function usePaginatedAPI<T>(
  apiCall: (page: number, limit: number) => Promise<PaginatedResponse<T>>,
  initialPage = 1,
  initialLimit = 10
) {
  const [page, setPage] = useState(initialPage);
  const [limit, setLimit] = useState(initialLimit);
  const [allData, setAllData] = useState<T[]>([]);
  
  const { data, loading, error, refetch } = useAPI(
    () => apiCall(page, limit),
    [page, limit]
  );

  useEffect(() => {
    if (data) {
      if (page === 1) {
        setAllData(data.data);
      } else {
        setAllData(prev => [...prev, ...data.data]);
      }
    }
  }, [data, page]);

  const loadMore = useCallback(() => {
    if (data?.has_more) {
      setPage(prev => prev + 1);
    }
  }, [data]);

  const reset = useCallback(() => {
    setPage(1);
    setAllData([]);
    refetch();
  }, [refetch]);

  return {
    data: allData,
    loading,
    error,
    hasMore: data?.has_more || false,
    loadMore,
    reset,
    currentPage: page,
    totalPages: data ? Math.ceil(data.total / limit) : 0
  };
}
```

### GUI-Specific API Hooks

#### User GUI Hooks
**File**: `renderer/user/hooks/useSessions.ts`

```typescript
import { useAPI, useMutation } from '@/hooks/useAPI';
import { useElectronAPI } from './useElectronAPI';
import { Session, Chunk } from '@/types';

export function useUserSessions(userId: string) {
  const electronAPI = useElectronAPI();
  
  return useAPI(
    () => electronAPI.sessions.list(userId),
    [userId],
    { immediate: !!userId }
  );
}

export function useCreateSession() {
  const electronAPI = useElectronAPI();
  
  return useMutation(
    (sessionData: Partial<Session>) => electronAPI.sessions.create(sessionData),
    {
      onSuccess: (session) => {
        console.log('Session created:', session.session_id);
      }
    }
  );
}

export function useSessionChunks(sessionId: string) {
  const electronAPI = useElectronAPI();
  
  return useAPI(
    () => electronAPI.chunks.list(sessionId),
    [sessionId],
    { immediate: !!sessionId }
  );
}

export function useUploadChunk() {
  const electronAPI = useElectronAPI();
  
  return useMutation(
    ({ sessionId, chunk }: { sessionId: string; chunk: Chunk }) => 
      electronAPI.chunks.upload(sessionId, chunk),
    {
      onSuccess: (result) => {
        console.log('Chunk uploaded:', result.chunk_id);
      }
    }
  );
}
```

#### Developer GUI Hooks
**File**: `renderer/developer/hooks/useDockerManager.ts`

```typescript
import { useAPI, useMutation } from '@/hooks/useAPI';
import { useElectronAPI } from './useElectronAPI';
import { ServiceStatus, SystemHealth } from '@/types';

export function useDockerServices() {
  const electronAPI = useElectronAPI();
  
  return useAPI(
    () => electronAPI.docker.getServices(),
    [],
    { immediate: true }
  );
}

export function useSystemHealth() {
  const electronAPI = useElectronAPI();
  
  return useAPI(
    () => electronAPI.docker.getSystemHealth(),
    [],
    { immediate: true }
  );
}

export function useStartStack() {
  const electronAPI = useElectronAPI();
  
  return useMutation(
    (level: 'developer' | 'admin') => electronAPI.docker.startStack(level),
    {
      onSuccess: () => {
        console.log('Stack started successfully');
      }
    }
  );
}

export function useStopStack() {
  const electronAPI = useElectronAPI();
  
  return useMutation(
    () => electronAPI.docker.stopStack(),
    {
      onSuccess: () => {
        console.log('Stack stopped successfully');
      }
    }
  );
}
```

#### Node GUI Hooks
**File**: `renderer/node/hooks/useNodeAPI.ts`

```typescript
import { useAPI, useMutation } from '@/hooks/useAPI';
import { useElectronAPI } from './useElectronAPI';
import { Node, Pool, Payout } from '@/types';

export function useNodeStatus(nodeId: string) {
  const electronAPI = useElectronAPI();
  
  return useAPI(
    () => electronAPI.nodes.getStatus(nodeId),
    [nodeId],
    { immediate: !!nodeId }
  );
}

export function useNodePools() {
  const electronAPI = useElectronAPI();
  
  return useAPI(
    () => electronAPI.nodes.getPools(),
    [],
    { immediate: true }
  );
}

export function useJoinPool() {
  const electronAPI = useElectronAPI();
  
  return useMutation(
    ({ nodeId, poolId }: { nodeId: string; poolId: string }) =>
      electronAPI.nodes.joinPool(nodeId, poolId),
    {
      onSuccess: () => {
        console.log('Successfully joined pool');
      }
    }
  );
}

export function usePayoutHistory(nodeId: string) {
  const electronAPI = useElectronAPI();
  
  return useAPI(
    () => electronAPI.payouts.getHistory(nodeId),
    [nodeId],
    { immediate: !!nodeId }
  );
}
```

#### Admin GUI Hooks
**File**: `renderer/admin/hooks/useSystemManagement.ts`

```typescript
import { useAPI, useMutation } from '@/hooks/useAPI';
import { useElectronAPI } from './useElectronAPI';
import { User, SystemHealth, ServiceStatus } from '@/types';

export function useSystemHealth() {
  const electronAPI = useElectronAPI();
  
  return useAPI(
    () => electronAPI.system.getHealth(),
    [],
    { immediate: true }
  );
}

export function useUserManagement() {
  const electronAPI = useElectronAPI();
  
  return useAPI(
    () => electronAPI.admin.getUsers(),
    [],
    { immediate: true }
  );
}

export function useStartFullStack() {
  const electronAPI = useElectronAPI();
  
  return useMutation(
    () => electronAPI.system.startFullStack(),
    {
      onSuccess: () => {
        console.log('Full stack started');
      }
    }
  );
}

export function useEmergencyShutdown() {
  const electronAPI = useElectronAPI();
  
  return useMutation(
    () => electronAPI.system.emergencyShutdown(),
    {
      onSuccess: () => {
        console.log('Emergency shutdown initiated');
      }
    }
  );
}
```

## 3.3 Naming Conventions (Syntax Guide)

### File Naming Standards

**File**: `docs/SYNTAX_GUIDE.md`

```markdown
# Electron GUI Syntax and Naming Guide

## File Naming Conventions

### React Components
- **Format**: PascalCase with descriptive names
- **Examples**: `SessionManager.tsx`, `ProofsViewer.tsx`, `NodeRegistration.tsx`
- **Pattern**: `[Feature][Type].tsx` (e.g., `SessionManager`, `UserDashboard`)

### Utility Files
- **Format**: camelCase with descriptive names
- **Examples**: `api-client.ts`, `tor-manager.ts`, `window-manager.ts`
- **Pattern**: `[feature]-[type].ts` (e.g., `api-client`, `docker-manager`)

### Hooks
- **Format**: camelCase with `use` prefix
- **Examples**: `useElectronAPI.ts`, `useSessions.ts`, `useDockerManager.ts`
- **Pattern**: `use[Feature].ts` (e.g., `useSessions`, `useNodeAPI`)

### Styles
- **Format**: kebab-case
- **Examples**: `session-manager.css`, `user-dashboard.css`
- **Pattern**: `[feature]-[type].css`

### Configuration Files
- **Format**: kebab-case with descriptive names
- **Examples**: `electron-builder.json`, `webpack.config.js`
- **Pattern**: `[tool]-[type].[ext]`

## Component Structure Standards

### React Component Template
```typescript
// 1. Imports (grouped: React, third-party, local)
import React, { useState, useEffect, useCallback } from 'react';
import { Button, Card, Alert } from '@/components/ui';
import { useAPI } from '@/hooks/useAPI';
import { Session, Chunk } from '@/types';

// 2. Type definitions
interface ComponentProps {
  userId: string;
  onSuccess?: (data: any) => void;
  onError?: (error: Error) => void;
}

interface ComponentState {
  loading: boolean;
  error: string | null;
  data: any | null;
}

// 3. Component definition
export function ComponentName({ 
  userId, 
  onSuccess, 
  onError 
}: ComponentProps) {
  // 4. State declarations
  const [state, setState] = useState<ComponentState>({
    loading: false,
    error: null,
    data: null
  });
  
  // 5. Custom hooks
  const { data, loading, error } = useAPI(
    () => fetchData(userId),
    [userId]
  );
  
  // 6. Effect hooks
  useEffect(() => {
    if (data) {
      onSuccess?.(data);
    }
  }, [data, onSuccess]);
  
  useEffect(() => {
    if (error) {
      onError?.(error);
    }
  }, [error, onError]);
  
  // 7. Event handlers
  const handleClick = useCallback(() => {
    // Handle click logic
  }, []);
  
  const handleSubmit = useCallback((formData: any) => {
    // Handle submit logic
  }, []);
  
  // 8. Render helpers
  const renderContent = () => {
    if (loading) return <div>Loading...</div>;
    if (error) return <div>Error: {error}</div>;
    return <div>Content</div>;
  };
  
  // 9. Return JSX
  return (
    <div className="component-name">
      <header className="component-header">
        <h2>Component Title</h2>
      </header>
      
      <main className="component-main">
        {renderContent()}
      </main>
      
      <footer className="component-footer">
        <Button onClick={handleClick}>
          Action Button
        </Button>
      </footer>
    </div>
  );
}
```

## API Call Patterns

### Standard API Hook Usage
```typescript
// ✅ CORRECT - Use shared useAPI hook
const { data, loading, error, refetch } = useAPI(
  () => api.getUserProfile(userId),
  [userId],
  { 
    immediate: !!userId,
    retryCount: 3,
    onSuccess: (data) => console.log('Success:', data)
  }
);

// ❌ INCORRECT - Direct API calls
const [data, setData] = useState(null);
useEffect(() => {
  fetch('/api/users/' + userId)
    .then(res => res.json())
    .then(setData);
}, [userId]);
```

### Mutation Hook Usage
```typescript
// ✅ CORRECT - Use useMutation hook
const createSession = useMutation(
  (sessionData) => api.sessions.create(sessionData),
  {
    onSuccess: (session) => {
      console.log('Session created:', session.id);
      // Update local state or refetch data
    },
    onError: (error) => {
      console.error('Failed to create session:', error);
    }
  }
);

// Usage
const handleCreateSession = async (data) => {
  try {
    await createSession.mutate(data);
  } catch (error) {
    // Error handled by onError callback
  }
};
```

## Error Handling Standards

### Lucid Error Code Handling
```typescript
try {
  await api.createSession(data);
} catch (error) {
  if (error.code === 'LUCID_ERR_2001') {
    // Authentication failed
    showError('Please log in again');
  } else if (error.code === 'LUCID_ERR_3001') {
    // Rate limit exceeded
    showError('Too many requests, please wait');
  } else if (error.code === 'LUCID_ERR_4001') {
    // Session not found
    showError('Session not found');
  } else {
    // Generic error
    showError('An unexpected error occurred');
  }
}
```

### Error Boundary Implementation
```typescript
import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div className="error-boundary">
          <h2>Something went wrong</h2>
          <p>{this.state.error?.message}</p>
        </div>
      );
    }

    return this.props.children;
  }
}
```

## IPC Communication Patterns

### Preload Script Pattern
```typescript
// main/preload-user.js
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  // Session operations
  sessions: {
    create: (data) => ipcRenderer.invoke('sessions:create', data),
    list: (userId) => ipcRenderer.invoke('sessions:list', userId),
    get: (sessionId) => ipcRenderer.invoke('sessions:get', sessionId),
    update: (sessionId, data) => ipcRenderer.invoke('sessions:update', sessionId, data),
    delete: (sessionId) => ipcRenderer.invoke('sessions:delete', sessionId),
  },
  
  // Chunk operations
  chunks: {
    upload: (sessionId, chunk) => ipcRenderer.invoke('chunks:upload', sessionId, chunk),
    download: (chunkId) => ipcRenderer.invoke('chunks:download', chunkId),
    list: (sessionId) => ipcRenderer.invoke('chunks:list', sessionId),
  },
  
  // Event listeners
  on: (channel, callback) => {
    const validChannels = [
      'session-updated',
      'chunk-uploaded',
      'proof-verified',
      'tor-status-changed'
    ];
    if (validChannels.includes(channel)) {
      ipcRenderer.on(channel, (event, ...args) => callback(...args));
    }
  },
  
  // Remove listeners
  removeAllListeners: (channel) => {
    ipcRenderer.removeAllListeners(channel);
  }
});
```

### Renderer Hook Pattern
```typescript
// renderer/user/hooks/useElectronAPI.ts
export function useElectronAPI() {
  const [api, setApi] = useState<any>(null);

  useEffect(() => {
    setApi((window as any).electronAPI);
  }, []);

  return {
    sessions: {
      create: (data) => api?.sessions.create(data),
      list: (userId) => api?.sessions.list(userId),
      // ... other methods
    },
    
    // Event subscription
    subscribe: (channel, callback) => {
      api?.on(channel, callback);
    },
    
    // Cleanup
    unsubscribe: (channel) => {
      api?.removeAllListeners(channel);
    }
  };
}
```

## Service Naming Conventions

### API Endpoint Naming
- **API Gateway**: `api-gateway` (Port 8080)
- **Blockchain Core**: `lucid-blocks` (Port 8084)
- **Authentication**: `auth-service` (Port 8089)
- **Session Management**: `session-api` (Port 8087)
- **Node Management**: `node-management` (Port 8095)
- **Admin Interface**: `admin-interface` (Port 8083)
- **TRON Payment**: `tron-payment-service` (Port 8085)

### Docker Service Naming
- **Format**: `lucid-[service]-[environment]`
- **Examples**: `lucid-gateway-prod`, `lucid-blocks-dev`
- **Pattern**: Consistent with API endpoint names

### Environment Variables
- **Format**: `LUCID_[SERVICE]_[SETTING]`
- **Examples**: `LUCID_GATEWAY_PORT`, `LUCID_TOR_SOCKS_PORT`
- **Pattern**: Uppercase with underscores

## Code Quality Standards

### TypeScript Configuration
```json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "strictFunctionTypes": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedIndexedAccess": true
  }
}
```

### ESLint Configuration
```json
{
  "extends": [
    "@typescript-eslint/recommended",
    "react-hooks/recommended"
  ],
  "rules": {
    "@typescript-eslint/no-unused-vars": "error",
    "@typescript-eslint/explicit-function-return-type": "warn",
    "react-hooks/rules-of-hooks": "error",
    "react-hooks/exhaustive-deps": "warn"
  }
}
```

### Prettier Configuration
```json
{
  "semi": true,
  "trailingComma": "es5",
  "singleQuote": true,
  "printWidth": 80,
  "tabWidth": 2,
  "useTabs": false
}
```
```

## 3.4 API Endpoint Mapping Document

### Comprehensive Endpoint Mapping

**File**: `docs/API_ENDPOINTS.md`

```markdown
# API Endpoint Mapping

## User GUI Endpoints

### Session Management (Cluster 03)
- **Create Session**: `POST /api/v1/sessions`
  - Hook: `useCreateSession()`
  - File: `renderer/user/hooks/useSessions.ts`
  - Parameters: `{ user_id, privacy_level, expires_at }`
  
- **List Sessions**: `GET /api/v1/sessions?user_id={userId}`
  - Hook: `useUserSessions(userId)`
  - File: `renderer/user/hooks/useSessions.ts`
  - Returns: `Session[]`
  
- **Get Session**: `GET /api/v1/sessions/{sessionId}`
  - Hook: `useSession(sessionId)`
  - File: `renderer/user/hooks/useSessions.ts`
  - Returns: `Session`

- **Update Session**: `PUT /api/v1/sessions/{sessionId}`
  - Hook: `useUpdateSession()`
  - File: `renderer/user/hooks/useSessions.ts`
  - Parameters: `{ status, privacy_level }`

### Chunk Management (Cluster 03)
- **Upload Chunk**: `POST /api/v1/sessions/{sessionId}/chunks`
  - Hook: `useUploadChunk()`
  - File: `renderer/user/hooks/useChunks.ts`
  - Parameters: `{ chunk_data, sequence, hash }`
  
- **Download Chunk**: `GET /api/v1/chunks/{chunkId}`
  - Hook: `useDownloadChunk(chunkId)`
  - File: `renderer/user/hooks/useChunks.ts`
  - Returns: `Chunk`

- **List Chunks**: `GET /api/v1/sessions/{sessionId}/chunks`
  - Hook: `useSessionChunks(sessionId)`
  - File: `renderer/user/hooks/useChunks.ts`
  - Returns: `Chunk[]`

### Proof Verification (Cluster 02)
- **Verify Session Anchor**: `POST /api/v1/anchoring/verify`
  - Hook: `useVerifyAnchor(sessionId)`
  - File: `renderer/user/hooks/useProofs.ts`
  - Returns: `{ verified: boolean, proof: MerkleProof }`

- **Get Merkle Proof**: `GET /api/v1/chunks/{chunkId}/proof`
  - Hook: `useMerkleProof(chunkId)`
  - File: `renderer/user/hooks/useProofs.ts`
  - Returns: `MerkleProof`

### User Profile (Cluster 01)
- **Get User Profile**: `GET /api/v1/users/{userId}`
  - Hook: `useUserProfile(userId)`
  - File: `renderer/user/hooks/useUser.ts`
  - Returns: `User`

- **Update Profile**: `PUT /api/v1/users/{userId}`
  - Hook: `useUpdateProfile()`
  - File: `renderer/user/hooks/useUser.ts`
  - Parameters: `{ email, tron_address }`

## Developer GUI Endpoints

### Docker Management (Local IPC)
- **Start Service Stack**: IPC `docker:start-stack`
  - Hook: `useStartStack()`
  - File: `renderer/developer/hooks/useDockerManager.ts`
  - Parameters: `{ level: 'developer' | 'admin' }`

- **Stop Service Stack**: IPC `docker:stop-stack`
  - Hook: `useStopStack()`
  - File: `renderer/developer/hooks/useDockerManager.ts`

- **Get Service Status**: IPC `docker:service-status`
  - Hook: `useDockerServices()`
  - File: `renderer/developer/hooks/useDockerManager.ts`
  - Returns: `ServiceStatus[]`

### Blockchain Explorer (Cluster 02)
- **Get Block by Height**: `GET /api/v1/blocks/{height}`
  - Hook: `useBlock(height)`
  - File: `renderer/developer/hooks/useBlockchain.ts`
  - Returns: `Block`

- **Get Latest Blocks**: `GET /api/v1/blocks?limit={limit}`
  - Hook: `useLatestBlocks(limit)`
  - File: `renderer/developer/hooks/useBlockchain.ts`
  - Returns: `Block[]`

- **Get Transaction**: `GET /api/v1/transactions/{txId}`
  - Hook: `useTransaction(txId)`
  - File: `renderer/developer/hooks/useBlockchain.ts`
  - Returns: `Transaction`

### API Testing
- **Test Endpoint**: `POST /api/v1/test/endpoint`
  - Hook: `useAPITester()`
  - File: `renderer/developer/hooks/useAPITester.ts`
  - Parameters: `{ method, url, headers, body }`

### Log Viewer
- **Get Service Logs**: IPC `logs:get-logs`
  - Hook: `useServiceLogs(serviceName)`
  - File: `renderer/developer/hooks/useLogViewer.ts`
  - Returns: `LogEntry[]`

## Node GUI Endpoints

### Node Management (Cluster 05)
- **Register Node**: `POST /api/v1/nodes/register`
  - Hook: `useRegisterNode()`
  - File: `renderer/node/hooks/useNodeAPI.ts`
  - Parameters: `{ operator_id, hardware_specs, tron_address }`

- **Get Node Status**: `GET /api/v1/nodes/{nodeId}/status`
  - Hook: `useNodeStatus(nodeId)`
  - File: `renderer/node/hooks/useNodeAPI.ts`
  - Returns: `Node`

- **Update Node**: `PUT /api/v1/nodes/{nodeId}`
  - Hook: `useUpdateNode()`
  - File: `renderer/node/hooks/useNodeAPI.ts`
  - Parameters: `{ status, resources }`

### Pool Management (Cluster 05)
- **List Pools**: `GET /api/v1/pools`
  - Hook: `useNodePools()`
  - File: `renderer/node/hooks/usePoolManager.ts`
  - Returns: `Pool[]`

- **Join Pool**: `POST /api/v1/nodes/{nodeId}/pool`
  - Hook: `useJoinPool()`
  - File: `renderer/node/hooks/usePoolManager.ts`
  - Parameters: `{ poolId }`

- **Leave Pool**: `DELETE /api/v1/nodes/{nodeId}/pool`
  - Hook: `useLeavePool()`
  - File: `renderer/node/hooks/usePoolManager.ts`

### PoOT Tracking (Cluster 05)
- **Get PoOT Score**: `GET /api/v1/nodes/{nodeId}/poot`
  - Hook: `usePootScore(nodeId)`
  - File: `renderer/node/hooks/usePoot.ts`
  - Returns: `{ score: number, history: PootEntry[] }`

- **Get Observation Time**: `GET /api/v1/nodes/{nodeId}/observation`
  - Hook: `useObservationTime(nodeId)`
  - File: `renderer/node/hooks/usePoot.ts`
  - Returns: `{ total_hours: number, sessions: ObservationSession[] }`

### Resource Monitoring
- **Get Resource Usage**: `GET /api/v1/nodes/{nodeId}/resources`
  - Hook: `useResourceUsage(nodeId)`
  - File: `renderer/node/hooks/useResourceMonitor.ts`
  - Returns: `NodeResources`

### Payout Management (Cluster 07)
- **Get Payout History**: `GET /api/v1/payouts?node_id={nodeId}`
  - Hook: `usePayoutHistory(nodeId)`
  - File: `renderer/node/hooks/usePayouts.ts`
  - Returns: `Payout[]`

- **Request Payout**: `POST /api/v1/payouts`
  - Hook: `useRequestPayout()`
  - File: `renderer/node/hooks/usePayouts.ts`
  - Parameters: `{ node_id, amount }`

## Admin GUI Endpoints

### System Management (Cluster 06)
- **Get System Health**: `GET /api/v1/admin/system/health`
  - Hook: `useSystemHealth()`
  - File: `renderer/admin/hooks/useSystemManagement.ts`
  - Returns: `SystemHealth`

- **Start Full Stack**: IPC `system:start-full-stack`
  - Hook: `useStartFullStack()`
  - File: `renderer/admin/hooks/useSystemManagement.ts`

- **Emergency Shutdown**: IPC `system:emergency-shutdown`
  - Hook: `useEmergencyShutdown()`
  - File: `renderer/admin/hooks/useSystemManagement.ts`

### User Management (Cluster 01)
- **List Users**: `GET /api/v1/admin/users`
  - Hook: `useUserManagement()`
  - File: `renderer/admin/hooks/useUserManagement.ts`
  - Returns: `User[]`

- **Update User Role**: `PUT /api/v1/admin/users/{userId}/role`
  - Hook: `useUpdateUserRole()`
  - File: `renderer/admin/hooks/useUserManagement.ts`
  - Parameters: `{ role: 'user' | 'node_operator' | 'admin' | 'super_admin' }`

- **Suspend User**: `POST /api/v1/admin/users/{userId}/suspend`
  - Hook: `useSuspendUser()`
  - File: `renderer/admin/hooks/useUserManagement.ts`

### Session Monitoring (Cluster 03)
- **List All Sessions**: `GET /api/v1/admin/sessions`
  - Hook: `useAllSessions()`
  - File: `renderer/admin/hooks/useSessionMonitoring.ts`
  - Returns: `Session[]`

- **Get Session Analytics**: `GET /api/v1/admin/sessions/analytics`
  - Hook: `useSessionAnalytics()`
  - File: `renderer/admin/hooks/useSessionMonitoring.ts`
  - Returns: `{ total_sessions, active_sessions, completed_sessions }`

### Node Administration (Cluster 05)
- **List All Nodes**: `GET /api/v1/admin/nodes`
  - Hook: `useAllNodes()`
  - File: `renderer/admin/hooks/useNodeAdministration.ts`
  - Returns: `Node[]`

- **Approve Node**: `POST /api/v1/admin/nodes/{nodeId}/approve`
  - Hook: `useApproveNode()`
  - File: `renderer/admin/hooks/useNodeAdministration.ts`

- **Suspend Node**: `POST /api/v1/admin/nodes/{nodeId}/suspend`
  - Hook: `useSuspendNode()`
  - File: `renderer/admin/hooks/useNodeAdministration.ts`

### TRON Payment Management (Cluster 07)
- **List All Payouts**: `GET /api/v1/admin/payouts`
  - Hook: `useAllPayouts()`
  - File: `renderer/admin/hooks/usePaymentManagement.ts`
  - Returns: `Payout[]`

- **Process Payout**: `POST /api/v1/admin/payouts/{payoutId}/process`
  - Hook: `useProcessPayout()`
  - File: `renderer/admin/hooks/usePaymentManagement.ts`

- **Get Payment Analytics**: `GET /api/v1/admin/payments/analytics`
  - Hook: `usePaymentAnalytics()`
  - File: `renderer/admin/hooks/usePaymentManagement.ts`
  - Returns: `{ total_payouts, total_amount, pending_payouts }`

### Audit Logs
- **Get Audit Logs**: `GET /api/v1/admin/audit-logs`
  - Hook: `useAuditLogs()`
  - File: `renderer/admin/hooks/useAuditLogs.ts`
  - Returns: `AuditLogEntry[]`

- **Get Security Events**: `GET /api/v1/admin/security-events`
  - Hook: `useSecurityEvents()`
  - File: `renderer/admin/hooks/useAuditLogs.ts`
  - Returns: `SecurityEvent[]`
```

## Implementation Checklist

### Phase 3 Completion Criteria

- [ ] Shared TypeScript interfaces defined
- [ ] Standardized API hooks implemented
- [ ] Naming conventions documented
- [ ] API endpoint mapping completed
- [ ] Error handling patterns established
- [ ] IPC communication patterns documented
- [ ] Code quality standards defined

### Testing Requirements

- [ ] All shared interfaces compile correctly
- [ ] API hooks work across all GUIs
- [ ] Naming conventions followed consistently
- [ ] Error handling works in all scenarios
- [ ] IPC communication secure and functional

### Documentation Requirements

- [ ] Syntax guide comprehensive and clear
- [ ] API endpoint mapping complete
- [ ] Code examples provided
- [ ] Best practices documented
- [ ] Troubleshooting guide included
