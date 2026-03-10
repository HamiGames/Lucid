import React, { useState, useEffect, useRef } from 'react';

interface LogEntry {
  id: string;
  timestamp: string;
  level: 'debug' | 'info' | 'warn' | 'error' | 'fatal';
  source: string;
  message: string;
  data?: any;
  stack?: string;
}

interface LogViewerProps {
  logs: LogEntry[];
  onLogClick?: (log: LogEntry) => void;
  onLogSelect?: (log: LogEntry) => void;
  selectedLogId?: string;
  maxHeight?: number;
  showTimestamp?: boolean;
  showSource?: boolean;
  showData?: boolean;
  className?: string;
}

export const LogViewer: React.FC<LogViewerProps> = ({
  logs,
  onLogClick,
  onLogSelect,
  selectedLogId,
  maxHeight = 400,
  showTimestamp = true,
  showSource = true,
  showData = false,
  className = ''
}) => {
  const [expandedLogs, setExpandedLogs] = useState<Set<string>>(new Set());
  const [filteredLogs, setFilteredLogs] = useState<LogEntry[]>(logs);
  const [searchQuery, setSearchQuery] = useState('');
  const [levelFilter, setLevelFilter] = useState<string>('all');
  const logContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setFilteredLogs(logs);
  }, [logs]);

  useEffect(() => {
    applyFilters();
  }, [logs, searchQuery, levelFilter]);

  const applyFilters = () => {
    let filtered = [...logs];

    // Filter by search query
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(log => 
        log.message.toLowerCase().includes(query) ||
        log.source.toLowerCase().includes(query) ||
        (log.data && JSON.stringify(log.data).toLowerCase().includes(query))
      );
    }

    // Filter by level
    if (levelFilter !== 'all') {
      filtered = filtered.filter(log => log.level === levelFilter);
    }

    setFilteredLogs(filtered);
  };

  const handleLogClick = (log: LogEntry) => {
    onLogClick?.(log);
  };

  const handleLogSelect = (log: LogEntry) => {
    onLogSelect?.(log);
  };

  const handleLogExpand = (logId: string) => {
    setExpandedLogs(prev => {
      const newSet = new Set(prev);
      if (newSet.has(logId)) {
        newSet.delete(logId);
      } else {
        newSet.add(logId);
      }
      return newSet;
    });
  };

  const getLevelColor = (level: string): string => {
    switch (level) {
      case 'debug': return '#6b7280';
      case 'info': return '#3b82f6';
      case 'warn': return '#f59e0b';
      case 'error': return '#ef4444';
      case 'fatal': return '#dc2626';
      default: return '#6b7280';
    }
  };

  const getLevelIcon = (level: string): string => {
    switch (level) {
      case 'debug': return '🔍';
      case 'info': return 'ℹ️';
      case 'warn': return '⚠️';
      case 'error': return '❌';
      case 'fatal': return '💀';
      default: return '❓';
    }
  };

  const formatTimestamp = (timestamp: string): string => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString();
  };

  const formatDate = (timestamp: string): string => {
    const date = new Date(timestamp);
    return date.toLocaleDateString();
  };

  const getLogLevels = (): string[] => {
    const levels = Array.from(new Set(logs.map(log => log.level)));
    return ['all', ...levels];
  };

  const isLogExpanded = (logId: string): boolean => {
    return expandedLogs.has(logId);
  };

  const isLogSelected = (logId: string): boolean => {
    return selectedLogId === logId;
  };

  return (
    <div className={`log-viewer ${className}`} style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Filters */}
      <div style={{ 
        display: 'flex', 
        gap: '1rem', 
        marginBottom: '1rem', 
        padding: '1rem',
        background: 'rgba(30, 41, 59, 0.5)',
        borderRadius: '0.5rem',
        border: '1px solid rgba(51, 65, 85, 0.3)'
      }}>
        <div style={{ flex: 1 }}>
          <input
            type="text"
            placeholder="Search logs..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: '100%',
              padding: '0.5rem',
              border: '1px solid rgba(51, 65, 85, 0.3)',
              borderRadius: '0.25rem',
              background: 'rgba(15, 23, 42, 0.5)',
              color: '#f8fafc',
              fontSize: '0.875rem'
            }}
          />
        </div>
        <div>
          <select
            value={levelFilter}
            onChange={(e) => setLevelFilter(e.target.value)}
            style={{
              padding: '0.5rem',
              border: '1px solid rgba(51, 65, 85, 0.3)',
              borderRadius: '0.25rem',
              background: 'rgba(15, 23, 42, 0.5)',
              color: '#f8fafc',
              fontSize: '0.875rem'
            }}
          >
            {getLogLevels().map(level => (
              <option key={level} value={level}>
                {level === 'all' ? 'All Levels' : level.toUpperCase()}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Logs Container */}
      <div
        ref={logContainerRef}
        style={{
          maxHeight: `${maxHeight}px`,
          overflowY: 'auto',
          background: 'rgba(15, 23, 42, 0.3)',
          borderRadius: '0.5rem',
          border: '1px solid rgba(51, 65, 85, 0.3)'
        }}
      >
        {filteredLogs.length === 0 ? (
          <div style={{ 
            padding: '2rem', 
            textAlign: 'center', 
            color: '#94a3b8' 
          }}>
            No logs found
          </div>
        ) : (
          filteredLogs.map(log => (
            <div
              key={log.id}
              style={{
                padding: '0.75rem',
                borderBottom: '1px solid rgba(51, 65, 85, 0.2)',
                cursor: 'pointer',
                background: isLogSelected(log.id) ? 'rgba(59, 130, 246, 0.1)' : 'transparent',
                borderLeft: `3px solid ${getLevelColor(log.level)}`,
                transition: 'background-color 0.2s ease'
              }}
              onClick={() => {
                handleLogClick(log);
                handleLogSelect(log);
              }}
              onDoubleClick={() => handleLogExpand(log.id)}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
                <div style={{ 
                  fontSize: '1rem', 
                  marginTop: '0.125rem',
                  flexShrink: 0
                }}>
                  {getLevelIcon(log.level)}
                </div>
                
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                    <span style={{ 
                      color: getLevelColor(log.level),
                      fontSize: '0.75rem',
                      fontWeight: '600',
                      textTransform: 'uppercase'
                    }}>
                      {log.level}
                    </span>
                    {showSource && (
                      <span style={{ 
                        color: '#64748b',
                        fontSize: '0.75rem',
                        background: 'rgba(51, 65, 85, 0.3)',
                        padding: '0.125rem 0.375rem',
                        borderRadius: '0.25rem'
                      }}>
                        {log.source}
                      </span>
                    )}
                    {showTimestamp && (
                      <span style={{ 
                        color: '#94a3b8',
                        fontSize: '0.75rem'
                      }}>
                        {formatTimestamp(log.timestamp)}
                      </span>
                    )}
                  </div>
                  
                  <div style={{ 
                    color: '#f8fafc',
                    fontSize: '0.875rem',
                    lineHeight: '1.4',
                    wordBreak: 'break-word'
                  }}>
                    {log.message}
                  </div>

                  {log.data && showData && (
                    <div style={{ 
                      marginTop: '0.5rem',
                      padding: '0.5rem',
                      background: 'rgba(30, 41, 59, 0.5)',
                      borderRadius: '0.25rem',
                      border: '1px solid rgba(51, 65, 85, 0.3)'
                    }}>
                      <pre style={{ 
                        margin: 0,
                        fontSize: '0.75rem',
                        color: '#d1d5db',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word'
                      }}>
                        {JSON.stringify(log.data, null, 2)}
                      </pre>
                    </div>
                  )}

                  {log.stack && isLogExpanded(log.id) && (
                    <div style={{ 
                      marginTop: '0.5rem',
                      padding: '0.5rem',
                      background: 'rgba(239, 68, 68, 0.1)',
                      borderRadius: '0.25rem',
                      border: '1px solid rgba(239, 68, 68, 0.3)'
                    }}>
                      <pre style={{ 
                        margin: 0,
                        fontSize: '0.75rem',
                        color: '#fca5a5',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word'
                      }}>
                        {log.stack}
                      </pre>
                    </div>
                  )}

                  {(log.data || log.stack) && (
                    <button
                      style={{
                        marginTop: '0.5rem',
                        background: 'transparent',
                        border: 'none',
                        color: '#60a5fa',
                        fontSize: '0.75rem',
                        cursor: 'pointer',
                        textDecoration: 'underline'
                      }}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleLogExpand(log.id);
                      }}
                    >
                      {isLogExpanded(log.id) ? 'Show Less' : 'Show More'}
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Log Count */}
      <div style={{ 
        padding: '0.5rem 1rem',
        background: 'rgba(30, 41, 59, 0.5)',
        borderTop: '1px solid rgba(51, 65, 85, 0.3)',
        fontSize: '0.75rem',
        color: '#94a3b8',
        textAlign: 'center'
      }}>
        Showing {filteredLogs.length} of {logs.length} logs
      </div>
    </div>
  );
};
