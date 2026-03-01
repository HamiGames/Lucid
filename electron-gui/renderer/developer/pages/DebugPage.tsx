import React, { useState, useEffect } from 'react';

interface DebugTool {
  id: string;
  name: string;
  description: string;
  category: string;
  icon: string;
  enabled: boolean;
}

interface SystemInfo {
  version: string;
  build: string;
  environment: string;
  nodeVersion: string;
  electronVersion: string;
  platform: string;
  arch: string;
  uptime: number;
  memory: {
    used: number;
    total: number;
    free: number;
  };
  cpu: {
    usage: number;
    cores: number;
  };
}

interface NetworkInfo {
  tor: {
    connected: boolean;
    circuits: number;
    version: string;
  };
  api: {
    endpoints: string[];
    status: 'online' | 'offline' | 'degraded';
  };
  blockchain: {
    connected: boolean;
    network: string;
    height: number;
  };
}

interface DebugLog {
  id: string;
  timestamp: string;
  level: 'debug' | 'info' | 'warn' | 'error';
  source: string;
  message: string;
  data?: any;
}

const DebugPage: React.FC = () => {
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null);
  const [networkInfo, setNetworkInfo] = useState<NetworkInfo | null>(null);
  const [debugLogs, setDebugLogs] = useState<DebugLog[]>([]);
  const [debugTools, setDebugTools] = useState<DebugTool[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedTool, setSelectedTool] = useState<string | null>(null);

  useEffect(() => {
    loadDebugInfo();
    loadDebugTools();
  }, []);

  const loadDebugInfo = async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Load system and network information
      const [system, network] = await Promise.all([
        loadSystemInfo(),
        loadNetworkInfo()
      ]);

      setSystemInfo(system);
      setNetworkInfo(network);
    } catch (error) {
      console.error('Failed to load debug info:', error);
      setError('Failed to load debug information');
    } finally {
      setIsLoading(false);
    }
  };

  const loadSystemInfo = async (): Promise<SystemInfo> => {
    // Mock system info - in real implementation, this would come from the system
    return {
      version: '1.0.0',
      build: 'development',
      environment: 'development',
      nodeVersion: '18.17.0',
      electronVersion: '27.0.0',
      platform: 'win32',
      arch: 'x64',
      uptime: Date.now() - (24 * 60 * 60 * 1000), // 24 hours
      memory: {
        used: 1024 * 1024 * 1024, // 1GB
        total: 8 * 1024 * 1024 * 1024, // 8GB
        free: 7 * 1024 * 1024 * 1024 // 7GB
      },
      cpu: {
        usage: 45.2,
        cores: 8
      }
    };
  };

  const loadNetworkInfo = async (): Promise<NetworkInfo> => {
    // Mock network info
    return {
      tor: {
        connected: true,
        circuits: 8,
        version: '0.4.7.13'
      },
      api: {
        endpoints: ['/api/auth', '/api/sessions', '/api/nodes', '/api/blockchain'],
        status: 'online'
      },
      blockchain: {
        connected: true,
        network: 'TRON',
        height: 12345678
      }
    };
  };

  const loadDebugTools = async () => {
    // Mock debug tools
    const tools: DebugTool[] = [
      {
        id: 'memory-profiler',
        name: 'Memory Profiler',
        description: 'Analyze memory usage and detect leaks',
        category: 'Performance',
        icon: '🧠',
        enabled: false
      },
      {
        id: 'network-analyzer',
        name: 'Network Analyzer',
        description: 'Monitor network traffic and connections',
        category: 'Network',
        icon: '🌐',
        enabled: false
      },
      {
        id: 'tor-debugger',
        name: 'Tor Debugger',
        description: 'Debug Tor connections and circuits',
        category: 'Network',
        icon: '🔒',
        enabled: false
      },
      {
        id: 'api-tracer',
        name: 'API Tracer',
        description: 'Trace API calls and responses',
        category: 'API',
        icon: '🔍',
        enabled: false
      },
      {
        id: 'blockchain-monitor',
        name: 'Blockchain Monitor',
        description: 'Monitor blockchain connections and transactions',
        category: 'Blockchain',
        icon: '⛓️',
        enabled: false
      },
      {
        id: 'session-debugger',
        name: 'Session Debugger',
        description: 'Debug session creation and management',
        category: 'Sessions',
        icon: '📋',
        enabled: false
      }
    ];

    setDebugTools(tools);
  };

  const handleToolToggle = (toolId: string) => {
    setDebugTools(prev => prev.map(tool => 
      tool.id === toolId ? { ...tool, enabled: !tool.enabled } : tool
    ));
  };

  const handleToolSelect = (toolId: string) => {
    setSelectedTool(selectedTool === toolId ? null : toolId);
  };

  const handleGenerateReport = async () => {
    try {
      const report = {
        timestamp: new Date().toISOString(),
        system: systemInfo,
        network: networkInfo,
        tools: debugTools.filter(tool => tool.enabled),
        logs: debugLogs
      };

      const reportData = JSON.stringify(report, null, 2);
      const blob = new Blob([reportData], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `debug-report-${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to generate report:', error);
      setError('Failed to generate debug report');
    }
  };

  const handleClearLogs = () => {
    setDebugLogs([]);
  };

  const formatBytes = (bytes: number): string => {
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    if (bytes === 0) return '0 Bytes';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  };

  const formatUptime = (ms: number): string => {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    
    if (days > 0) return `${days}d ${hours % 24}h ${minutes % 60}m`;
    if (hours > 0) return `${hours}h ${minutes % 60}m`;
    if (minutes > 0) return `${minutes}m ${seconds % 60}s`;
    return `${seconds}s`;
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'online': return '#10b981';
      case 'offline': return '#ef4444';
      case 'degraded': return '#f59e0b';
      default: return '#6b7280';
    }
  };

  const getStatusIcon = (status: string): string => {
    switch (status) {
      case 'online': return '🟢';
      case 'offline': return '🔴';
      case 'degraded': return '🟡';
      default: return '⚪';
    }
  };

  return (
    <div className="developer-content">
      <div className="developer-card">
        <div className="developer-card-header">
          <div>
            <h2 className="developer-card-title">Debug Tools</h2>
            <p className="developer-card-subtitle">
              System debugging and diagnostic tools
            </p>
          </div>
          <div className="developer-card-actions">
            <button 
              className="developer-btn developer-btn-secondary"
              onClick={loadDebugInfo}
              disabled={isLoading}
            >
              Refresh
            </button>
            <button 
              className="developer-btn developer-btn-primary"
              onClick={handleGenerateReport}
            >
              Generate Report
            </button>
          </div>
        </div>

        {isLoading && (
          <div className="developer-loading">
            <div className="developer-loading-spinner"></div>
            <p>Loading debug information...</p>
          </div>
        )}

        {error && (
          <div className="developer-error">
            <div className="developer-error-icon">⚠️</div>
            <div className="developer-error-title">Error</div>
            <div className="developer-error-message">{error}</div>
            <button 
              className="developer-btn developer-btn-primary"
              onClick={loadDebugInfo}
            >
              Retry
            </button>
          </div>
        )}

        {!isLoading && !error && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
            <div>
              <h3 style={{ marginBottom: '1rem', color: '#f8fafc' }}>System Information</h3>
              {systemInfo && (
                <div className="developer-card">
                  <div style={{ display: 'grid', gap: '1rem' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                      <div>
                        <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.25rem' }}>Version</div>
                        <div style={{ color: '#f8fafc', fontWeight: '500' }}>{systemInfo.version}</div>
                      </div>
                      <div>
                        <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.25rem' }}>Build</div>
                        <div style={{ color: '#f8fafc', fontWeight: '500' }}>{systemInfo.build}</div>
                      </div>
                      <div>
                        <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.25rem' }}>Platform</div>
                        <div style={{ color: '#f8fafc', fontWeight: '500' }}>{systemInfo.platform}</div>
                      </div>
                      <div>
                        <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.25rem' }}>Architecture</div>
                        <div style={{ color: '#f8fafc', fontWeight: '500' }}>{systemInfo.arch}</div>
                      </div>
                    </div>
                    <div style={{ borderTop: '1px solid rgba(51, 65, 85, 0.3)', paddingTop: '1rem' }}>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                        <div>
                          <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.25rem' }}>Memory Usage</div>
                          <div style={{ color: '#f8fafc', fontWeight: '500' }}>
                            {formatBytes(systemInfo.memory.used)} / {formatBytes(systemInfo.memory.total)}
                          </div>
                          <div style={{ 
                            width: '100%', 
                            height: '4px', 
                            background: 'rgba(51, 65, 85, 0.3)', 
                            borderRadius: '2px',
                            marginTop: '0.25rem'
                          }}>
                            <div style={{
                              width: `${(systemInfo.memory.used / systemInfo.memory.total) * 100}%`,
                              height: '100%',
                              background: '#3b82f6',
                              borderRadius: '2px'
                            }}></div>
                          </div>
                        </div>
                        <div>
                          <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.25rem' }}>CPU Usage</div>
                          <div style={{ color: '#f8fafc', fontWeight: '500' }}>{systemInfo.cpu.usage.toFixed(1)}%</div>
                          <div style={{ 
                            width: '100%', 
                            height: '4px', 
                            background: 'rgba(51, 65, 85, 0.3)', 
                            borderRadius: '2px',
                            marginTop: '0.25rem'
                          }}>
                            <div style={{
                              width: `${systemInfo.cpu.usage}%`,
                              height: '100%',
                              background: '#10b981',
                              borderRadius: '2px'
                            }}></div>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div style={{ borderTop: '1px solid rgba(51, 65, 85, 0.3)', paddingTop: '1rem' }}>
                      <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.25rem' }}>Uptime</div>
                      <div style={{ color: '#f8fafc', fontWeight: '500' }}>{formatUptime(systemInfo.uptime)}</div>
                    </div>
                  </div>
                </div>
              )}

              <h3 style={{ marginBottom: '1rem', color: '#f8fafc', marginTop: '2rem' }}>Network Status</h3>
              {networkInfo && (
                <div className="developer-card">
                  <div style={{ display: 'grid', gap: '1rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ color: '#f8fafc' }}>Tor Connection</span>
                      <span style={{ color: getStatusColor(networkInfo.tor.connected ? 'online' : 'offline') }}>
                        {getStatusIcon(networkInfo.tor.connected ? 'online' : 'offline')} {networkInfo.tor.connected ? 'Connected' : 'Disconnected'}
                      </span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ color: '#f8fafc' }}>API Status</span>
                      <span style={{ color: getStatusColor(networkInfo.api.status) }}>
                        {getStatusIcon(networkInfo.api.status)} {networkInfo.api.status}
                      </span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ color: '#f8fafc' }}>Blockchain</span>
                      <span style={{ color: getStatusColor(networkInfo.blockchain.connected ? 'online' : 'offline') }}>
                        {getStatusIcon(networkInfo.blockchain.connected ? 'online' : 'offline')} {networkInfo.blockchain.connected ? 'Connected' : 'Disconnected'}
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div>
              <h3 style={{ marginBottom: '1rem', color: '#f8fafc' }}>Debug Tools</h3>
              <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
                {debugTools.map(tool => (
                  <div
                    key={tool.id}
                    className={`developer-card ${selectedTool === tool.id ? 'active' : ''}`}
                    style={{ 
                      padding: '1rem', 
                      marginBottom: '0.5rem',
                      cursor: 'pointer',
                      border: selectedTool === tool.id ? '2px solid #3b82f6' : '1px solid rgba(51, 65, 85, 0.3)'
                    }}
                    onClick={() => handleToolSelect(tool.id)}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span style={{ fontSize: '1.25rem' }}>{tool.icon}</span>
                        <h4 style={{ margin: '0', color: '#f8fafc' }}>{tool.name}</h4>
                      </div>
                      <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                        <input
                          type="checkbox"
                          checked={tool.enabled}
                          onChange={() => handleToolToggle(tool.id)}
                          onClick={(e) => e.stopPropagation()}
                        />
                        <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                          {tool.enabled ? 'Enabled' : 'Disabled'}
                        </span>
                      </label>
                    </div>
                    <p style={{ margin: '0', color: '#94a3b8', fontSize: '0.875rem' }}>
                      {tool.description}
                    </p>
                    <div style={{ marginTop: '0.5rem' }}>
                      <span style={{ 
                        fontSize: '0.75rem', 
                        color: '#64748b',
                        background: 'rgba(51, 65, 85, 0.3)',
                        padding: '0.25rem 0.5rem',
                        borderRadius: '0.25rem'
                      }}>
                        {tool.category}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export { DebugPage };
