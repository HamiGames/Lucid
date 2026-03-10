import React, { useState, useEffect, useRef } from 'react';
import { LogViewer } from '../components/LogViewer';

interface LogEntry {
  id: string;
  timestamp: string;
  level: 'debug' | 'info' | 'warn' | 'error' | 'fatal';
  source: string;
  message: string;
  data?: any;
  stack?: string;
}

interface LogFilters {
  level: string;
  source: string;
  search: string;
  timeRange: {
    start: string;
    end: string;
  };
}

const LogsPage: React.FC = () => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [filteredLogs, setFilteredLogs] = useState<LogEntry[]>([]);
  const [filters, setFilters] = useState<LogFilters>({
    level: 'all',
    source: 'all',
    search: '',
    timeRange: {
      start: '',
      end: ''
    }
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLive, setIsLive] = useState(true);
  const [autoScroll, setAutoScroll] = useState(true);
  const [logCount, setLogCount] = useState(0);
  const logContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadLogs();
    if (isLive) {
      const interval = setInterval(loadNewLogs, 2000);
      return () => clearInterval(interval);
    }
  }, [isLive]);

  useEffect(() => {
    applyFilters();
  }, [logs, filters]);

  useEffect(() => {
    if (autoScroll && logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [filteredLogs, autoScroll]);

  const loadLogs = async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Load logs from the system
      const logEntries = await loadLogsFromSystem();
      setLogs(logEntries);
      setLogCount(logEntries.length);
    } catch (error) {
      console.error('Failed to load logs:', error);
      setError('Failed to load logs');
    } finally {
      setIsLoading(false);
    }
  };

  const loadNewLogs = async () => {
    try {
      // Load only new logs since last update
      const newLogs = await loadNewLogsFromSystem();
      if (newLogs.length > 0) {
        setLogs(prev => [...prev, ...newLogs]);
        setLogCount(prev => prev + newLogs.length);
      }
    } catch (error) {
      console.error('Failed to load new logs:', error);
    }
  };

  const loadLogsFromSystem = async (): Promise<LogEntry[]> => {
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
      }
    ];

    return mockLogs;
  };

  const loadNewLogsFromSystem = async (): Promise<LogEntry[]> => {
    // Mock new log entries
    const newLogs: LogEntry[] = [
      {
        id: `${Date.now()}`,
        timestamp: new Date().toISOString(),
        level: 'info',
        source: 'system',
        message: 'System heartbeat',
        data: { uptime: Date.now() }
      }
    ];

    return newLogs;
  };

  const applyFilters = () => {
    let filtered = [...logs];

    // Filter by level
    if (filters.level !== 'all') {
      filtered = filtered.filter(log => log.level === filters.level);
    }

    // Filter by source
    if (filters.source !== 'all') {
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
    if (filters.timeRange.start) {
      const startTime = new Date(filters.timeRange.start).getTime();
      filtered = filtered.filter(log => new Date(log.timestamp).getTime() >= startTime);
    }

    if (filters.timeRange.end) {
      const endTime = new Date(filters.timeRange.end).getTime();
      filtered = filtered.filter(log => new Date(log.timestamp).getTime() <= endTime);
    }

    setFilteredLogs(filtered);
  };

  const handleFilterChange = (key: keyof LogFilters, value: any) => {
    setFilters(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const handleClearLogs = () => {
    setLogs([]);
    setFilteredLogs([]);
    setLogCount(0);
  };

  const handleExportLogs = async () => {
    try {
      const logData = JSON.stringify(filteredLogs, null, 2);
      const blob = new Blob([logData], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `logs-${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to export logs:', error);
      setError('Failed to export logs');
    }
  };

  const getLogLevels = () => {
    const levels = Array.from(new Set(logs.map(log => log.level)));
    return ['all', ...levels];
  };

  const getLogSources = () => {
    const sources = Array.from(new Set(logs.map(log => log.source)));
    return ['all', ...sources];
  };

  return (
    <div className="developer-content">
      <div className="developer-card">
        <div className="developer-card-header">
          <div>
            <h2 className="developer-card-title">System Logs</h2>
            <p className="developer-card-subtitle">
              Real-time system logs and debugging information
            </p>
          </div>
          <div className="developer-card-actions">
            <button 
              className="developer-btn developer-btn-secondary"
              onClick={loadLogs}
              disabled={isLoading}
            >
              Refresh
            </button>
            <button 
              className="developer-btn developer-btn-secondary"
              onClick={handleExportLogs}
              disabled={filteredLogs.length === 0}
            >
              Export
            </button>
            <button 
              className="developer-btn developer-btn-danger"
              onClick={handleClearLogs}
            >
              Clear
            </button>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem', marginBottom: '2rem' }}>
          <div className="developer-form-group">
            <label className="developer-form-label">Log Level</label>
            <select
              className="developer-form-input"
              value={filters.level}
              onChange={(e) => handleFilterChange('level', e.target.value)}
            >
              {getLogLevels().map(level => (
                <option key={level} value={level}>
                  {level === 'all' ? 'All Levels' : level.toUpperCase()}
                </option>
              ))}
            </select>
          </div>

          <div className="developer-form-group">
            <label className="developer-form-label">Source</label>
            <select
              className="developer-form-input"
              value={filters.source}
              onChange={(e) => handleFilterChange('source', e.target.value)}
            >
              {getLogSources().map(source => (
                <option key={source} value={source}>
                  {source === 'all' ? 'All Sources' : source}
                </option>
              ))}
            </select>
          </div>

          <div className="developer-form-group">
            <label className="developer-form-label">Search</label>
            <input
              type="text"
              className="developer-form-input"
              placeholder="Search logs..."
              value={filters.search}
              onChange={(e) => handleFilterChange('search', e.target.value)}
            />
          </div>
        </div>

        <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem', alignItems: 'center' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#d1d5db' }}>
            <input
              type="checkbox"
              checked={isLive}
              onChange={(e) => setIsLive(e.target.checked)}
            />
            Live Updates
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#d1d5db' }}>
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
            />
            Auto Scroll
          </label>
          <span style={{ color: '#94a3b8', fontSize: '0.875rem' }}>
            {filteredLogs.length} of {logCount} logs
          </span>
        </div>

        {isLoading && (
          <div className="developer-loading">
            <div className="developer-loading-spinner"></div>
            <p>Loading logs...</p>
          </div>
        )}

        {error && (
          <div className="developer-error">
            <div className="developer-error-icon">⚠️</div>
            <div className="developer-error-title">Error</div>
            <div className="developer-error-message">{error}</div>
            <button 
              className="developer-btn developer-btn-primary"
              onClick={loadLogs}
            >
              Retry
            </button>
          </div>
        )}

        {!isLoading && !error && (
          <div ref={logContainerRef} style={{ maxHeight: '500px', overflowY: 'auto' }}>
            <LogViewer
              logs={filteredLogs}
              onLogClick={(log) => console.log('Log clicked:', log)}
            />
          </div>
        )}
      </div>
    </div>
  );
};

export { LogsPage };
