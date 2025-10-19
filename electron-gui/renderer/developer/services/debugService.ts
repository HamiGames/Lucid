export interface DebugTool {
  id: string;
  name: string;
  description: string;
  category: string;
  icon: string;
  enabled: boolean;
}

export interface SystemInfo {
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

export interface NetworkInfo {
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

export interface DebugLog {
  id: string;
  timestamp: string;
  level: 'debug' | 'info' | 'warn' | 'error';
  source: string;
  message: string;
  data?: any;
}

export interface DebugReport {
  timestamp: string;
  system: SystemInfo;
  network: NetworkInfo;
  tools: DebugTool[];
  logs: DebugLog[];
  performance: {
    memoryUsage: number;
    cpuUsage: number;
    diskUsage: number;
    networkLatency: number;
  };
}

class DebugService {
  private debugTools: DebugTool[] = [];
  private systemInfo: SystemInfo | null = null;
  private networkInfo: NetworkInfo | null = null;
  private debugLogs: DebugLog[] = [];
  private subscribers: Array<(info: { system: SystemInfo | null; network: NetworkInfo | null; tools: DebugTool[] }) => void> = [];

  constructor() {
    this.initializeDebugTools();
  }

  private initializeDebugTools(): void {
    this.debugTools = [
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
  }

  async getSystemInfo(): Promise<SystemInfo> {
    try {
      // Load system information from the system
      const systemInfo = await this.loadSystemInfoFromSystem();
      this.systemInfo = systemInfo;
      this.notifySubscribers();
      return systemInfo;
    } catch (error) {
      console.error('Failed to load system info:', error);
      throw new Error('Failed to load system information');
    }
  }

  private async loadSystemInfoFromSystem(): Promise<SystemInfo> {
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
  }

  async getNetworkInfo(): Promise<NetworkInfo> {
    try {
      // Load network information from the system
      const networkInfo = await this.loadNetworkInfoFromSystem();
      this.networkInfo = networkInfo;
      this.notifySubscribers();
      return networkInfo;
    } catch (error) {
      console.error('Failed to load network info:', error);
      throw new Error('Failed to load network information');
    }
  }

  private async loadNetworkInfoFromSystem(): Promise<NetworkInfo> {
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
  }

  getDebugTools(): DebugTool[] {
    return [...this.debugTools];
  }

  toggleDebugTool(toolId: string): void {
    const tool = this.debugTools.find(t => t.id === toolId);
    if (tool) {
      tool.enabled = !tool.enabled;
      this.notifySubscribers();
    }
  }

  enableDebugTool(toolId: string): void {
    const tool = this.debugTools.find(t => t.id === toolId);
    if (tool) {
      tool.enabled = true;
      this.notifySubscribers();
    }
  }

  disableDebugTool(toolId: string): void {
    const tool = this.debugTools.find(t => t.id === toolId);
    if (tool) {
      tool.enabled = false;
      this.notifySubscribers();
    }
  }

  async executeDebugTool(toolId: string): Promise<any> {
    const tool = this.debugTools.find(t => t.id === toolId);
    if (!tool) {
      throw new Error('Debug tool not found');
    }

    if (!tool.enabled) {
      throw new Error('Debug tool is not enabled');
    }

    try {
      // Execute the debug tool
      return await this.executeTool(tool);
    } catch (error) {
      console.error(`Failed to execute debug tool ${toolId}:`, error);
      throw error;
    }
  }

  private async executeTool(tool: DebugTool): Promise<any> {
    // Mock tool execution - in real implementation, these would perform actual debugging
    switch (tool.id) {
      case 'memory-profiler':
        return {
          heapUsed: 1024 * 1024 * 1024, // 1GB
          heapTotal: 2 * 1024 * 1024 * 1024, // 2GB
          external: 512 * 1024 * 1024, // 512MB
          rss: 1.5 * 1024 * 1024 * 1024, // 1.5GB
          leaks: []
        };
      
      case 'network-analyzer':
        return {
          activeConnections: 12,
          totalBytesIn: 1024 * 1024 * 1024, // 1GB
          totalBytesOut: 512 * 1024 * 1024, // 512MB
          averageLatency: 45, // ms
          connections: [
            { id: 'conn1', type: 'HTTP', status: 'active', latency: 42 },
            { id: 'conn2', type: 'WebSocket', status: 'active', latency: 38 }
          ]
        };
      
      case 'tor-debugger':
        return {
          circuits: 8,
          activeCircuits: 6,
          circuitDetails: [
            { id: 'circuit1', status: 'built', length: 3, latency: 120 },
            { id: 'circuit2', status: 'building', length: 2, latency: 0 }
          ],
          torVersion: '0.4.7.13',
          bootstrapProgress: 100
        };
      
      case 'api-tracer':
        return {
          totalRequests: 1250,
          averageResponseTime: 45, // ms
          errorRate: 0.8, // %
          endpoints: [
            { path: '/api/auth/login', requests: 150, avgTime: 35, errors: 2 },
            { path: '/api/sessions', requests: 800, avgTime: 50, errors: 5 }
          ]
        };
      
      case 'blockchain-monitor':
        return {
          network: 'TRON',
          height: 12345678,
          connected: true,
          latency: 120, // ms
          lastBlock: {
            height: 12345678,
            hash: 'abc123...',
            timestamp: new Date().toISOString()
          }
        };
      
      case 'session-debugger':
        return {
          totalSessions: 42,
          activeSessions: 35,
          idleSessions: 5,
          terminatedSessions: 2,
          averageSessionDuration: 1800, // seconds
          sessionDetails: [
            { id: 'sess1', status: 'active', duration: 1200, dataSize: 1024 },
            { id: 'sess2', status: 'idle', duration: 300, dataSize: 512 }
          ]
        };
      
      default:
        throw new Error('Unknown debug tool');
    }
  }

  async generateDebugReport(): Promise<DebugReport> {
    try {
      const system = await this.getSystemInfo();
      const network = await this.getNetworkInfo();
      const enabledTools = this.debugTools.filter(tool => tool.enabled);
      
      // Get performance metrics
      const performance = {
        memoryUsage: system.memory.used / system.memory.total * 100,
        cpuUsage: system.cpu.usage,
        diskUsage: 23.4, // Mock value
        networkLatency: 45 // Mock value
      };

      const report: DebugReport = {
        timestamp: new Date().toISOString(),
        system,
        network,
        tools: enabledTools,
        logs: this.debugLogs,
        performance
      };

      return report;
    } catch (error) {
      console.error('Failed to generate debug report:', error);
      throw new Error('Failed to generate debug report');
    }
  }

  async exportDebugReport(format: 'json' | 'txt' = 'json'): Promise<Blob> {
    try {
      const report = await this.generateDebugReport();
      
      let content: string;
      let mimeType: string;

      if (format === 'json') {
        content = JSON.stringify(report, null, 2);
        mimeType = 'application/json';
      } else {
        content = this.formatReportAsText(report);
        mimeType = 'text/plain';
      }

      return new Blob([content], { type: mimeType });
    } catch (error) {
      console.error('Failed to export debug report:', error);
      throw new Error('Failed to export debug report');
    }
  }

  private formatReportAsText(report: DebugReport): string {
    return `
LUCID DEBUG REPORT
Generated: ${report.timestamp}

SYSTEM INFORMATION
==================
Version: ${report.system.version}
Build: ${report.system.build}
Environment: ${report.system.environment}
Platform: ${report.system.platform} (${report.system.arch})
Node Version: ${report.system.nodeVersion}
Electron Version: ${report.system.electronVersion}
Uptime: ${Math.floor(report.system.uptime / 1000 / 60 / 60)} hours

Memory Usage: ${(report.system.memory.used / 1024 / 1024 / 1024).toFixed(2)} GB / ${(report.system.memory.total / 1024 / 1024 / 1024).toFixed(2)} GB
CPU Usage: ${report.system.cpu.usage}% (${report.system.cpu.cores} cores)

NETWORK INFORMATION
===================
Tor: ${report.network.tor.connected ? 'Connected' : 'Disconnected'} (${report.network.tor.circuits} circuits)
API Status: ${report.network.api.status}
Blockchain: ${report.network.blockchain.connected ? 'Connected' : 'Disconnected'} (${report.network.blockchain.network})

PERFORMANCE METRICS
===================
Memory Usage: ${report.performance.memoryUsage.toFixed(1)}%
CPU Usage: ${report.performance.cpuUsage}%
Disk Usage: ${report.performance.diskUsage}%
Network Latency: ${report.performance.networkLatency}ms

ENABLED DEBUG TOOLS
===================
${report.tools.map(tool => `- ${tool.name} (${tool.category})`).join('\n')}

DEBUG LOGS
==========
${report.logs.length} log entries
${report.logs.slice(0, 10).map(log => `[${log.timestamp}] ${log.level} ${log.source}: ${log.message}`).join('\n')}
${report.logs.length > 10 ? `... and ${report.logs.length - 10} more entries` : ''}
    `.trim();
  }

  addDebugLog(log: Omit<DebugLog, 'id' | 'timestamp'>): void {
    const debugLog: DebugLog = {
      id: `log-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date().toISOString(),
      ...log
    };

    this.debugLogs.unshift(debugLog);
    
    // Keep only last 1000 logs
    if (this.debugLogs.length > 1000) {
      this.debugLogs = this.debugLogs.slice(0, 1000);
    }
  }

  getDebugLogs(): DebugLog[] {
    return [...this.debugLogs];
  }

  clearDebugLogs(): void {
    this.debugLogs = [];
  }

  subscribe(callback: (info: { system: SystemInfo | null; network: NetworkInfo | null; tools: DebugTool[] }) => void): () => void {
    this.subscribers.push(callback);
    
    return () => {
      this.subscribers = this.subscribers.filter(sub => sub !== callback);
    };
  }

  private notifySubscribers(): void {
    this.subscribers.forEach(callback => 
      callback({
        system: this.systemInfo,
        network: this.networkInfo,
        tools: this.debugTools
      })
    );
  }

  getSystemInfo(): SystemInfo | null {
    return this.systemInfo;
  }

  getNetworkInfo(): NetworkInfo | null {
    return this.networkInfo;
  }

  destroy(): void {
    this.subscribers = [];
    this.debugLogs = [];
  }
}

export const debugService = new DebugService();
