export interface LogEntry {
  id: string;
  timestamp: string;
  level: 'debug' | 'info' | 'warn' | 'error' | 'fatal';
  source: string;
  message: string;
  data?: any;
  stack?: string;
}

export interface LogFilters {
  level?: string;
  source?: string;
  search?: string;
  timeRange?: {
    start: string;
    end: string;
  };
  limit?: number;
  offset?: number;
}

export interface LogStatistics {
  totalLogs: number;
  logsByLevel: Record<string, number>;
  logsBySource: Record<string, number>;
  logsByHour: Array<{
    hour: string;
    count: number;
  }>;
  errorRate: number;
  topSources: Array<{
    source: string;
    count: number;
  }>;
}

export interface LogExportOptions {
  format: 'json' | 'csv' | 'txt';
  filters: LogFilters;
  includeData: boolean;
  includeStack: boolean;
}

class LogService {
  private logs: LogEntry[] = [];
  private subscribers: Array<(logs: LogEntry[]) => void> = [];
  private isLive: boolean = false;
  private liveInterval: NodeJS.Timeout | null = null;
  private lastLogId: number = 0;

  constructor() {
    this.startLiveUpdates();
  }

  async getLogs(filters: LogFilters = {}): Promise<LogEntry[]> {
    try {
      // Load logs from the system
      const allLogs = await this.loadLogsFromSystem();
      this.logs = allLogs;
      
      // Apply filters
      let filteredLogs = this.applyFilters(allLogs, filters);
      
      // Apply pagination
      if (filters.limit) {
        const offset = filters.offset || 0;
        filteredLogs = filteredLogs.slice(offset, offset + filters.limit);
      }
      
      return filteredLogs;
    } catch (error) {
      console.error('Failed to load logs:', error);
      throw new Error('Failed to load logs');
    }
  }

  private async loadLogsFromSystem(): Promise<LogEntry[]> {
    // Mock log entries - in real implementation, these would come from the log service
    const mockLogs: LogEntry[] = [
      {
        id: '1',
        timestamp: new Date(Date.now() - 1000).toISOString(),
        level: 'info',
        source: 'api-gateway',
        message: 'API request received',
        data: { method: 'GET', path: '/api/health' }
      },
      {
        id: '2',
        timestamp: new Date(Date.now() - 2000).toISOString(),
        level: 'debug',
        source: 'tor-manager',
        message: 'Tor circuit established',
        data: { circuitId: 'abc123' }
      },
      {
        id: '3',
        timestamp: new Date(Date.now() - 3000).toISOString(),
        level: 'warn',
        source: 'session-manager',
        message: 'Session timeout warning',
        data: { sessionId: 'sess123', timeoutIn: 300 }
      },
      {
        id: '4',
        timestamp: new Date(Date.now() - 4000).toISOString(),
        level: 'error',
        source: 'blockchain-service',
        message: 'Failed to anchor session',
        data: { sessionId: 'sess456', error: 'Network timeout' },
        stack: 'Error: Network timeout\n    at BlockchainService.anchorSession'
      },
      {
        id: '5',
        timestamp: new Date(Date.now() - 5000).toISOString(),
        level: 'info',
        source: 'user-service',
        message: 'User login successful',
        data: { userId: 'user123', ip: '192.168.1.1' }
      },
      {
        id: '6',
        timestamp: new Date(Date.now() - 6000).toISOString(),
        level: 'debug',
        source: 'node-manager',
        message: 'Node health check completed',
        data: { nodeId: 'node456', status: 'healthy' }
      },
      {
        id: '7',
        timestamp: new Date(Date.now() - 7000).toISOString(),
        level: 'warn',
        source: 'api-gateway',
        message: 'Rate limit exceeded',
        data: { ip: '192.168.1.100', endpoint: '/api/sessions' }
      },
      {
        id: '8',
        timestamp: new Date(Date.now() - 8000).toISOString(),
        level: 'error',
        source: 'database',
        message: 'Connection timeout',
        data: { query: 'SELECT * FROM sessions', duration: 5000 },
        stack: 'Error: Connection timeout\n    at Database.query'
      }
    ];

    return mockLogs;
  }

  private applyFilters(logs: LogEntry[], filters: LogFilters): LogEntry[] {
    let filtered = [...logs];

    // Filter by level
    if (filters.level && filters.level !== 'all') {
      filtered = filtered.filter(log => log.level === filters.level);
    }

    // Filter by source
    if (filters.source && filters.source !== 'all') {
      filtered = filtered.filter(log => log.source === filters.source);
    }

    // Filter by search query
    if (filters.search) {
      const query = filters.search.toLowerCase();
      filtered = filtered.filter(log => 
        log.message.toLowerCase().includes(query) ||
        log.source.toLowerCase().includes(query) ||
        (log.data && JSON.stringify(log.data).toLowerCase().includes(query))
      );
    }

    // Filter by time range
    if (filters.timeRange) {
      if (filters.timeRange.start) {
        const startTime = new Date(filters.timeRange.start).getTime();
        filtered = filtered.filter(log => new Date(log.timestamp).getTime() >= startTime);
      }
      if (filters.timeRange.end) {
        const endTime = new Date(filters.timeRange.end).getTime();
        filtered = filtered.filter(log => new Date(log.timestamp).getTime() <= endTime);
      }
    }

    // Sort by timestamp (newest first)
    filtered.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

    return filtered;
  }

  async getLogStatistics(filters: LogFilters = {}): Promise<LogStatistics> {
    const logs = await this.getLogs(filters);
    
    const logsByLevel: Record<string, number> = {};
    const logsBySource: Record<string, number> = {};
    const logsByHour: Array<{ hour: string; count: number }> = [];
    let errorCount = 0;

    // Initialize hour buckets
    const hourBuckets: Record<string, number> = {};
    for (let i = 0; i < 24; i++) {
      hourBuckets[i.toString().padStart(2, '0')] = 0;
    }

    logs.forEach(log => {
      // Count by level
      logsByLevel[log.level] = (logsByLevel[log.level] || 0) + 1;
      
      // Count by source
      logsBySource[log.source] = (logsBySource[log.source] || 0) + 1;
      
      // Count errors
      if (log.level === 'error' || log.level === 'fatal') {
        errorCount++;
      }
      
      // Count by hour
      const hour = new Date(log.timestamp).getHours().toString().padStart(2, '0');
      hourBuckets[hour]++;
    });

    // Convert hour buckets to array
    Object.entries(hourBuckets).forEach(([hour, count]) => {
      logsByHour.push({ hour, count });
    });

    // Get top sources
    const topSources = Object.entries(logsBySource)
      .map(([source, count]) => ({ source, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 5);

    return {
      totalLogs: logs.length,
      logsByLevel,
      logsBySource,
      logsByHour,
      errorRate: logs.length > 0 ? (errorCount / logs.length) * 100 : 0,
      topSources
    };
  }

  async exportLogs(options: LogExportOptions): Promise<Blob> {
    const logs = await this.getLogs(options.filters);
    
    let content: string;
    
    switch (options.format) {
      case 'json':
        content = JSON.stringify(logs, null, 2);
        break;
      case 'csv':
        content = this.exportToCSV(logs, options);
        break;
      case 'txt':
        content = this.exportToTXT(logs, options);
        break;
      default:
        throw new Error('Unsupported export format');
    }

    return new Blob([content], { type: 'text/plain' });
  }

  private exportToCSV(logs: LogEntry[], options: LogExportOptions): string {
    const headers = ['timestamp', 'level', 'source', 'message'];
    if (options.includeData) headers.push('data');
    if (options.includeStack) headers.push('stack');
    
    const rows = logs.map(log => {
      const row = [
        log.timestamp,
        log.level,
        log.source,
        log.message
      ];
      
      if (options.includeData) {
        row.push(log.data ? JSON.stringify(log.data) : '');
      }
      
      if (options.includeStack) {
        row.push(log.stack || '');
      }
      
      return row.map(field => `"${field.replace(/"/g, '""')}"`).join(',');
    });
    
    return [headers.join(','), ...rows].join('\n');
  }

  private exportToTXT(logs: LogEntry[], options: LogExportOptions): string {
    return logs.map(log => {
      let line = `[${log.timestamp}] ${log.level.toUpperCase()} ${log.source}: ${log.message}`;
      
      if (options.includeData && log.data) {
        line += `\nData: ${JSON.stringify(log.data, null, 2)}`;
      }
      
      if (options.includeStack && log.stack) {
        line += `\nStack: ${log.stack}`;
      }
      
      return line;
    }).join('\n\n');
  }

  startLiveUpdates(): void {
    if (this.isLive) return;
    
    this.isLive = true;
    this.liveInterval = setInterval(async () => {
      try {
        const newLogs = await this.loadNewLogs();
        if (newLogs.length > 0) {
          this.logs = [...newLogs, ...this.logs];
          this.notifySubscribers();
        }
      } catch (error) {
        console.error('Failed to load new logs:', error);
      }
    }, 2000); // Update every 2 seconds
  }

  stopLiveUpdates(): void {
    if (this.liveInterval) {
      clearInterval(this.liveInterval);
      this.liveInterval = null;
    }
    this.isLive = false;
  }

  private async loadNewLogs(): Promise<LogEntry[]> {
    // Mock new log entries
    const newLogs: LogEntry[] = [
      {
        id: `${++this.lastLogId}`,
        timestamp: new Date().toISOString(),
        level: 'info',
        source: 'system',
        message: 'System heartbeat',
        data: { uptime: Date.now() }
      }
    ];

    return newLogs;
  }

  subscribe(callback: (logs: LogEntry[]) => void): () => void {
    this.subscribers.push(callback);
    
    return () => {
      this.subscribers = this.subscribers.filter(sub => sub !== callback);
    };
  }

  private notifySubscribers(): void {
    this.subscribers.forEach(callback => callback(this.logs));
  }

  clearLogs(): void {
    this.logs = [];
    this.notifySubscribers();
  }

  getLogSources(): string[] {
    const sources = new Set(this.logs.map(log => log.source));
    return Array.from(sources);
  }

  getLogLevels(): string[] {
    const levels = new Set(this.logs.map(log => log.level));
    return Array.from(levels);
  }

  isLiveUpdatesEnabled(): boolean {
    return this.isLive;
  }

  destroy(): void {
    this.stopLiveUpdates();
    this.subscribers = [];
  }
}

export const logService = new LogService();
