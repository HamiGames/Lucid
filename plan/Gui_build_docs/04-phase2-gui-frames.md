# Phase 2: GUI Frame Development

## Overview

Phase 2 focuses on developing the four specialized GUI frames in parallel, reusing existing components where possible and creating new components for Electron-specific functionality.

## 2.1 User GUI Frame

### Directory Structure
```
renderer/user/
├── index.html                     # Entry point
├── App.tsx                        # Main React app component
├── components/                     # Reused from apps/gui-user/src/components/
│   ├── ConnectionSettings.tsx
│   ├── SessionManager.tsx
│   ├── ProofsViewer.tsx
│   ├── QRCodeScanner.tsx
│   └── WalletConnect.tsx
├── hooks/                         # Electron-specific hooks
│   ├── useElectronAPI.ts
│   ├── useSessions.ts
│   ├── useChunks.ts
│   └── useProofs.ts
├── pages/                         # Page components
│   ├── Dashboard.tsx
│   ├── Sessions.tsx
│   ├── Upload.tsx
│   └── Settings.tsx
├── services/                      # API services
│   ├── session-api.ts
│   ├── chunk-api.ts
│   └── proof-api.ts
└── styles/
    ├── main.css
    └── components.css
```

### Key Features

#### Session Management
- **Create Session**: New session creation with privacy settings
- **Session List**: View all user sessions with status
- **Session Details**: Detailed view of session progress
- **Session History**: Historical session data

#### Chunk Operations
- **Upload Chunks**: Drag-and-drop file upload
- **Chunk Progress**: Real-time upload progress
- **Chunk Verification**: Hash verification for uploaded chunks
- **Download Chunks**: Retrieve previously uploaded chunks

#### Proof Verification
- **Merkle Proofs**: Visual Merkle tree representation
- **Blockchain Anchoring**: Monitor anchoring progress
- **Proof Validation**: Verify session proofs
- **Audit Trail**: Complete proof audit trail

#### TRON Integration
- **Wallet Connection**: Hardware wallet integration
- **Payment Processing**: TRON payment for services
- **Balance Display**: Real-time wallet balance
- **Transaction History**: Payment transaction history

### Implementation

#### Main App Component
**File**: `renderer/user/App.tsx`

```typescript
import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { useElectronAPI } from './hooks/useElectronAPI';
import Dashboard from './pages/Dashboard';
import Sessions from './pages/Sessions';
import Upload from './pages/Upload';
import Settings from './pages/Settings';
import './styles/main.css';

export default function App() {
  const [isConnected, setIsConnected] = useState(false);
  const [torStatus, setTorStatus] = useState<'connected' | 'disconnected'>('disconnected');
  const electronAPI = useElectronAPI();

  useEffect(() => {
    const checkConnection = async () => {
      try {
        const status = await electronAPI.tor.getStatus();
        setTorStatus(status.connected ? 'connected' : 'disconnected');
        setIsConnected(status.connected);
      } catch (error) {
        console.error('Failed to check connection:', error);
      }
    };

    checkConnection();
    const interval = setInterval(checkConnection, 5000);
    return () => clearInterval(interval);
  }, [electronAPI]);

  return (
    <Router>
      <div className="app">
        <header className="app-header">
          <h1>Lucid User Interface</h1>
          <div className="connection-status">
            <div className={`status-indicator ${torStatus}`} />
            <span>Tor: {torStatus}</span>
          </div>
        </header>
        
        <nav className="app-nav">
          <a href="/dashboard">Dashboard</a>
          <a href="/sessions">Sessions</a>
          <a href="/upload">Upload</a>
          <a href="/settings">Settings</a>
        </nav>

        <main className="app-main">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/sessions" element={<Sessions />} />
            <Route path="/upload" element={<Upload />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}
```

#### Electron API Hook
**File**: `renderer/user/hooks/useElectronAPI.ts`

```typescript
import { useEffect, useState } from 'react';

export function useElectronAPI() {
  const [api, setApi] = useState<any>(null);

  useEffect(() => {
    // Access exposed API from preload script
    setApi((window as any).electronAPI);
  }, []);

  return {
    // Session operations
    sessions: {
      create: (data: any) => api?.sessions.create(data),
      list: (userId: string) => api?.sessions.list(userId),
      get: (sessionId: string) => api?.sessions.get(sessionId),
      update: (sessionId: string, data: any) => api?.sessions.update(sessionId, data),
      delete: (sessionId: string) => api?.sessions.delete(sessionId),
    },
    
    // Chunk operations
    chunks: {
      upload: (sessionId: string, chunk: any) => api?.chunks.upload(sessionId, chunk),
      download: (chunkId: string) => api?.chunks.download(chunkId),
      list: (sessionId: string) => api?.chunks.list(sessionId),
    },
    
    // Proof verification
    proofs: {
      verify: (sessionId: string) => api?.proofs.verify(sessionId),
      getMerkleProof: (chunkId: string) => api?.proofs.getMerkleProof(chunkId),
      getAuditTrail: (sessionId: string) => api?.proofs.getAuditTrail(sessionId),
    },
    
    // Wallet integration
    wallet: {
      connect: () => api?.wallet.connect(),
      getBalance: () => api?.wallet.getBalance(),
      getAddress: () => api?.wallet.getAddress(),
      signTransaction: (tx: any) => api?.wallet.signTransaction(tx),
    },
    
    // Tor status
    tor: {
      getStatus: () => api?.tor.getStatus(),
      getCircuits: () => api?.tor.getCircuits(),
    },
    
    // Event listeners
    on: (channel: string, callback: (...args: any[]) => void) => {
      api?.on(channel, callback);
    },
  };
}
```

#### Session Management Hook
**File**: `renderer/user/hooks/useSessions.ts`

```typescript
import { useState, useEffect, useCallback } from 'react';
import { useElectronAPI } from './useElectronAPI';

export function useSessions() {
  const [sessions, setSessions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const electronAPI = useElectronAPI();

  const fetchSessions = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const userId = localStorage.getItem('lucid_user_id');
      if (userId) {
        const userSessions = await electronAPI.sessions.list(userId);
        setSessions(userSessions);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch sessions');
    } finally {
      setLoading(false);
    }
  }, [electronAPI]);

  const createSession = useCallback(async (sessionData: any) => {
    try {
      const newSession = await electronAPI.sessions.create(sessionData);
      setSessions(prev => [newSession, ...prev]);
      return newSession;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create session');
      throw err;
    }
  }, [electronAPI]);

  const updateSession = useCallback(async (sessionId: string, data: any) => {
    try {
      const updatedSession = await electronAPI.sessions.update(sessionId, data);
      setSessions(prev => prev.map(s => s.session_id === sessionId ? updatedSession : s));
      return updatedSession;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update session');
      throw err;
    }
  }, [electronAPI]);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  return {
    sessions,
    loading,
    error,
    createSession,
    updateSession,
    refetch: fetchSessions,
  };
}
```

## 2.2 Developer GUI Frame

### Directory Structure
```
renderer/developer/
├── index.html
├── App.tsx
├── components/                    # New components for development tools
│   ├── ServiceManager.tsx
│   ├── APITester.tsx
│   ├── BlockchainExplorer.tsx
│   ├── LogViewer.tsx
│   ├── MetricsDashboard.tsx
│   └── DockerControls.tsx
├── hooks/
│   ├── useElectronAPI.ts
│   ├── useDockerManager.ts
│   ├── useAPITester.ts
│   └── useLogViewer.ts
├── pages/
│   ├── Dashboard.tsx
│   ├── Services.tsx
│   ├── APITesting.tsx
│   ├── Blockchain.tsx
│   └── Logs.tsx
└── services/
    ├── docker-api.ts
    ├── blockchain-api.ts
    └── metrics-api.ts
```

### Key Features

#### Backend Service Management
- **Service Controls**: Start/stop Docker services
- **Service Status**: Real-time service health monitoring
- **Resource Usage**: CPU, memory, disk usage tracking
- **Service Logs**: Real-time log streaming

#### API Testing Interface
- **Endpoint Testing**: Postman-like interface for API testing
- **Request Builder**: Visual request construction
- **Response Viewer**: Formatted response display
- **Test Collections**: Save and organize API tests

#### Blockchain Explorer
- **Block Viewer**: Browse blockchain blocks
- **Transaction Explorer**: Search and view transactions
- **Session Anchors**: Monitor session anchoring
- **Consensus Monitoring**: View consensus votes

#### Development Tools
- **Log Viewer**: Real-time log streaming from containers
- **Performance Metrics**: System performance monitoring
- **Debug Tools**: Session pipeline debugging
- **Configuration**: Service configuration management

### Implementation

#### Service Manager Component
**File**: `renderer/developer/components/ServiceManager.tsx`

```typescript
import React, { useState, useEffect } from 'react';
import { useDockerManager } from '../hooks/useDockerManager';

export function ServiceManager() {
  const [services, setServices] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dockerManager = useDockerManager();

  const startStack = async () => {
    try {
      setLoading(true);
      setError(null);
      await dockerManager.startStack('developer');
      await fetchServices();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start stack');
    } finally {
      setLoading(false);
    }
  };

  const stopStack = async () => {
    try {
      setLoading(true);
      setError(null);
      await dockerManager.stopStack();
      setServices([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to stop stack');
    } finally {
      setLoading(false);
    }
  };

  const fetchServices = async () => {
    try {
      const serviceList = await dockerManager.getServices();
      setServices(serviceList);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch services');
    }
  };

  useEffect(() => {
    fetchServices();
    const interval = setInterval(fetchServices, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="service-manager">
      <div className="service-controls">
        <button 
          onClick={startStack} 
          disabled={loading}
          className="btn btn-primary"
        >
          Start Developer Stack
        </button>
        <button 
          onClick={stopStack} 
          disabled={loading}
          className="btn btn-danger"
        >
          Stop All Services
        </button>
      </div>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      <div className="services-list">
        <h3>Running Services</h3>
        {services.map(service => (
          <div key={service.name} className="service-item">
            <div className="service-info">
              <span className="service-name">{service.name}</span>
              <span className={`service-status ${service.status}`}>
                {service.status}
              </span>
            </div>
            <div className="service-metrics">
              <span>CPU: {service.cpu}%</span>
              <span>Memory: {service.memory}%</span>
              <span>Uptime: {service.uptime}s</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

#### Docker Manager Hook
**File**: `renderer/developer/hooks/useDockerManager.ts`

```typescript
import { useState, useEffect } from 'react';
import { useElectronAPI } from './useElectronAPI';

export function useDockerManager() {
  const [services, setServices] = useState<any[]>([]);
  const [systemHealth, setSystemHealth] = useState<any>(null);
  const electronAPI = useElectronAPI();

  const startStack = async (level: 'developer' | 'admin') => {
    return electronAPI.docker.startStack(level);
  };

  const stopStack = async () => {
    return electronAPI.docker.stopStack();
  };

  const getServices = async () => {
    return electronAPI.docker.getServices();
  };

  const getServiceStatus = async (serviceName: string) => {
    return electronAPI.docker.getServiceStatus(serviceName);
  };

  const getSystemHealth = async () => {
    return electronAPI.docker.getSystemHealth();
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [servicesData, healthData] = await Promise.all([
          getServices(),
          getSystemHealth()
        ]);
        setServices(servicesData);
        setSystemHealth(healthData);
      } catch (error) {
        console.error('Failed to fetch Docker data:', error);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  return {
    services,
    systemHealth,
    startStack,
    stopStack,
    getServices,
    getServiceStatus,
    getSystemHealth,
  };
}
```

## 2.3 Node GUI Frame

### Directory Structure
```
renderer/node/
├── index.html
├── App.tsx
├── components/                    # Reused from apps/gui-node/
│   ├── NodeRegistration.tsx
│   ├── PoolManager.tsx
│   ├── ResourceMonitor.tsx
│   ├── PoOTDashboard.tsx
│   └── PayoutHistory.tsx
├── hooks/
│   ├── useElectronAPI.ts
│   ├── useNodeAPI.ts
│   ├── usePoolManager.ts
│   └── useResourceMonitor.ts
├── pages/
│   ├── Dashboard.tsx
│   ├── Registration.tsx
│   ├── Pools.tsx
│   ├── Resources.tsx
│   └── Earnings.tsx
└── services/
    ├── node-api.ts
    ├── pool-api.ts
    └── payout-api.ts
```

### Key Features

#### Node Registration
- **Registration Wizard**: Step-by-step node setup
- **Hardware Validation**: System requirements check
- **Network Configuration**: Network settings
- **Authentication**: Node authentication setup

#### Pool Management
- **Pool Selection**: Browse available pools
- **Pool Requirements**: View pool requirements
- **Join/Leave Pools**: Pool membership management
- **Pool Status**: Real-time pool status

#### Resource Monitoring
- **System Metrics**: CPU, memory, disk usage
- **Network Monitoring**: Bandwidth usage
- **Performance Tracking**: System performance metrics
- **Resource Alerts**: Resource usage alerts

#### PoOT Tracking
- **Observation Time**: Track observation hours
- **Score Calculation**: PoOT score calculation
- **Score History**: Historical score data
- **Score Requirements**: Pool score requirements

#### Earnings Management
- **Payout History**: Historical payout data
- **Earnings Tracking**: Real-time earnings
- **Payment Requests**: Request payouts
- **Transaction History**: Payment transactions

### Implementation

#### Node Registration Component
**File**: `renderer/node/components/NodeRegistration.tsx`

```typescript
import React, { useState } from 'react';
import { useNodeAPI } from '../hooks/useNodeAPI';

export function NodeRegistration() {
  const [formData, setFormData] = useState({
    operatorName: '',
    email: '',
    tronAddress: '',
    hardwareSpecs: {
      cpu: '',
      memory: '',
      disk: '',
      network: ''
    }
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const nodeAPI = useNodeAPI();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      setError(null);
      await nodeAPI.registerNode(formData);
      // Redirect to dashboard or show success message
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (field: string, value: string) => {
    if (field.includes('.')) {
      const [parent, child] = field.split('.');
      setFormData(prev => ({
        ...prev,
        [parent]: {
          ...prev[parent as keyof typeof prev],
          [child]: value
        }
      }));
    } else {
      setFormData(prev => ({
        ...prev,
        [field]: value
      }));
    }
  };

  return (
    <div className="node-registration">
      <h2>Node Registration</h2>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Operator Name</label>
          <input
            type="text"
            value={formData.operatorName}
            onChange={(e) => handleChange('operatorName', e.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label>Email</label>
          <input
            type="email"
            value={formData.email}
            onChange={(e) => handleChange('email', e.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label>TRON Address</label>
          <input
            type="text"
            value={formData.tronAddress}
            onChange={(e) => handleChange('tronAddress', e.target.value)}
            required
          />
        </div>

        <div className="hardware-specs">
          <h3>Hardware Specifications</h3>
          <div className="form-group">
            <label>CPU</label>
            <input
              type="text"
              value={formData.hardwareSpecs.cpu}
              onChange={(e) => handleChange('hardwareSpecs.cpu', e.target.value)}
              placeholder="e.g., Intel i7-8700K"
            />
          </div>
          <div className="form-group">
            <label>Memory</label>
            <input
              type="text"
              value={formData.hardwareSpecs.memory}
              onChange={(e) => handleChange('hardwareSpecs.memory', e.target.value)}
              placeholder="e.g., 16GB DDR4"
            />
          </div>
          <div className="form-group">
            <label>Disk</label>
            <input
              type="text"
              value={formData.hardwareSpecs.disk}
              onChange={(e) => handleChange('hardwareSpecs.disk', e.target.value)}
              placeholder="e.g., 1TB SSD"
            />
          </div>
          <div className="form-group">
            <label>Network</label>
            <input
              type="text"
              value={formData.hardwareSpecs.network}
              onChange={(e) => handleChange('hardwareSpecs.network', e.target.value)}
              placeholder="e.g., 100Mbps"
            />
          </div>
        </div>

        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        <button type="submit" disabled={loading} className="btn btn-primary">
          {loading ? 'Registering...' : 'Register Node'}
        </button>
      </form>
    </div>
  );
}
```

## 2.4 Admin GUI Frame

### Directory Structure
```
renderer/admin/
├── index.html
├── App.tsx
├── components/                    # Converted from admin/ui/templates/
│   ├── SystemDashboard.tsx        # Converted from dashboard.html
│   ├── UserManagement.tsx        # Converted from users.html
│   ├── SessionMonitoring.tsx     # Converted from sessions.html
│   ├── NodeAdministration.tsx    # Converted from nodes.html
│   ├── BlockchainMetrics.tsx     # Converted from blockchain.html
│   ├── PaymentManagement.tsx
│   ├── EmergencyControls.tsx
│   └── AuditLogViewer.tsx
├── hooks/
│   ├── useElectronAPI.ts
│   ├── useSystemManagement.ts
│   ├── useUserManagement.ts
│   └── useAuditLogs.ts
├── pages/
│   ├── Dashboard.tsx
│   ├── Users.tsx
│   ├── Sessions.tsx
│   ├── Nodes.tsx
│   ├── Blockchain.tsx
│   ├── Payments.tsx
│   └── Security.tsx
└── services/
    ├── admin-api.ts
    ├── user-api.ts
    └── audit-api.ts
```

### Key Features

#### System Administration
- **Full Stack Management**: Start/stop all service phases
- **System Health**: Comprehensive system monitoring
- **Service Orchestration**: Docker service management
- **Resource Allocation**: System resource management

#### User Management
- **User Accounts**: User account management
- **Role-Based Access**: RBAC implementation
- **Authentication**: User authentication management
- **Permissions**: Permission management

#### Session Monitoring
- **Session Lifecycle**: Monitor all sessions
- **Session Analytics**: Session statistics and metrics
- **Session Debugging**: Session troubleshooting
- **Session History**: Historical session data

#### Node Administration
- **Node Pool Management**: Pool administration
- **Node Monitoring**: Node health and performance
- **Node Registration**: Node approval process
- **Node Maintenance**: Node maintenance operations

#### Emergency Controls
- **System Lockdown**: Emergency system lockdown
- **Service Shutdown**: Emergency service shutdown
- **Security Alerts**: Security incident response
- **Recovery Procedures**: System recovery operations

### Implementation

#### System Dashboard Component
**File**: `renderer/admin/components/SystemDashboard.tsx`

```typescript
import React, { useState, useEffect } from 'react';
import { useSystemManagement } from '../hooks/useSystemManagement';

export function SystemDashboard() {
  const [systemHealth, setSystemHealth] = useState<any>(null);
  const [services, setServices] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const systemManagement = useSystemManagement();

  useEffect(() => {
    const fetchSystemData = async () => {
      try {
        setLoading(true);
        const [health, serviceList] = await Promise.all([
          systemManagement.getSystemHealth(),
          systemManagement.getServices()
        ]);
        setSystemHealth(health);
        setServices(serviceList);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch system data');
      } finally {
        setLoading(false);
      }
    };

    fetchSystemData();
    const interval = setInterval(fetchSystemData, 10000);
    return () => clearInterval(interval);
  }, [systemManagement]);

  const startFullStack = async () => {
    try {
      await systemManagement.startFullStack();
      // Refresh data
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start full stack');
    }
  };

  const emergencyShutdown = async () => {
    try {
      await systemManagement.emergencyShutdown();
      // Handle shutdown
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Emergency shutdown failed');
    }
  };

  if (loading) {
    return <div className="loading">Loading system data...</div>;
  }

  return (
    <div className="system-dashboard">
      <div className="dashboard-header">
        <h1>System Administration Dashboard</h1>
        <div className="system-controls">
          <button onClick={startFullStack} className="btn btn-primary">
            Start Full Stack
          </button>
          <button onClick={emergencyShutdown} className="btn btn-danger">
            Emergency Shutdown
          </button>
        </div>
      </div>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      <div className="system-overview">
        <div className="health-status">
          <h3>System Health</h3>
          <div className={`status-indicator ${systemHealth?.overall}`}>
            {systemHealth?.overall}
          </div>
          <div className="health-details">
            <span>Tor: {systemHealth?.tor_status}</span>
            <span>Docker: {systemHealth?.docker_status}</span>
          </div>
        </div>

        <div className="services-overview">
          <h3>Services Status</h3>
          <div className="services-grid">
            {services.map(service => (
              <div key={service.name} className="service-card">
                <div className="service-name">{service.name}</div>
                <div className={`service-status ${service.status}`}>
                  {service.status}
                </div>
                <div className="service-metrics">
                  <span>CPU: {service.cpu}%</span>
                  <span>Memory: {service.memory}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
```

## Implementation Checklist

### Phase 2 Completion Criteria

#### User GUI
- [ ] Session management components implemented
- [ ] Chunk upload/download functionality
- [ ] Proof verification interface
- [ ] TRON wallet integration
- [ ] Connection status monitoring

#### Developer GUI
- [ ] Service management interface
- [ ] API testing tools
- [ ] Blockchain explorer
- [ ] Log viewer implementation
- [ ] Performance metrics dashboard

#### Node GUI
- [ ] Node registration wizard
- [ ] Pool management interface
- [ ] Resource monitoring
- [ ] PoOT score tracking
- [ ] Payout history display

#### Admin GUI
- [ ] System dashboard conversion
- [ ] User management interface
- [ ] Session monitoring tools
- [ ] Node administration
- [ ] Emergency controls

### Testing Requirements

- [ ] All four GUIs launch successfully
- [ ] Component reuse from existing GUIs works
- [ ] Electron-specific hooks function correctly
- [ ] API integration works through Tor proxy
- [ ] Real-time updates function properly
- [ ] Error handling works in all GUIs

### Security Verification

- [ ] All renderers use context isolation
- [ ] No nodeIntegration in any renderer
- [ ] IPC communication secure
- [ ] API calls routed through Tor
- [ ] No sensitive data in renderer processes
