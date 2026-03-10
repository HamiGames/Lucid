import React, { useState } from 'react';

interface APIResponse {
  status: number;
  statusText: string;
  headers: Record<string, string>;
  data: any;
  duration: number;
  timestamp: string;
}

interface ResponseViewerProps {
  response: APIResponse;
  onClear?: () => void;
  onCopy?: () => void;
  className?: string;
}

export const ResponseViewer: React.FC<ResponseViewerProps> = ({
  response,
  onClear,
  onCopy,
  className = ''
}) => {
  const [activeTab, setActiveTab] = useState<'body' | 'headers' | 'raw'>('body');
  const [expanded, setExpanded] = useState(false);

  const getStatusColor = (status: number): string => {
    if (status >= 200 && status < 300) return '#10b981';
    if (status >= 300 && status < 400) return '#f59e0b';
    if (status >= 400 && status < 500) return '#ef4444';
    if (status >= 500) return '#dc2626';
    return '#6b7280';
  };

  const getStatusIcon = (status: number): string => {
    if (status >= 200 && status < 300) return '✅';
    if (status >= 300 && status < 400) return '🔄';
    if (status >= 400 && status < 500) return '❌';
    if (status >= 500) return '💥';
    return '❓';
  };

  const formatDuration = (duration: number): string => {
    if (duration < 1000) return `${duration}ms`;
    return `${(duration / 1000).toFixed(2)}s`;
  };

  const formatTimestamp = (timestamp: string): string => {
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  const formatHeaders = (headers: Record<string, string>): string => {
    return Object.entries(headers)
      .map(([key, value]) => `${key}: ${value}`)
      .join('\n');
  };

  const formatData = (data: any): string => {
    if (typeof data === 'string') {
      try {
        const parsed = JSON.parse(data);
        return JSON.stringify(parsed, null, 2);
      } catch {
        return data;
      }
    }
    return JSON.stringify(data, null, 2);
  };

  const handleCopy = () => {
    let text = '';
    
    switch (activeTab) {
      case 'body':
        text = formatData(response.data);
        break;
      case 'headers':
        text = formatHeaders(response.headers);
        break;
      case 'raw':
        text = JSON.stringify(response, null, 2);
        break;
    }

    navigator.clipboard.writeText(text).then(() => {
      onCopy?.();
    }).catch(err => {
      console.error('Failed to copy text:', err);
    });
  };

  const renderBody = () => {
    const formattedData = formatData(response.data);
    const isJson = typeof response.data === 'object' || (typeof response.data === 'string' && response.data.startsWith('{'));
    
    return (
      <div style={{ position: 'relative' }}>
        <pre style={{
          margin: 0,
          padding: '1rem',
          background: 'rgba(15, 23, 42, 0.5)',
          borderRadius: '0.25rem',
          border: '1px solid rgba(51, 65, 85, 0.3)',
          color: '#d1d5db',
          fontSize: '0.875rem',
          lineHeight: '1.5',
          overflow: 'auto',
          maxHeight: expanded ? 'none' : '300px',
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word'
        }}>
          {formattedData}
        </pre>
        
        {!expanded && formattedData.length > 1000 && (
          <button
            onClick={() => setExpanded(true)}
            style={{
              position: 'absolute',
              bottom: '0.5rem',
              right: '0.5rem',
              background: 'rgba(15, 23, 42, 0.8)',
              color: '#60a5fa',
              border: '1px solid rgba(59, 130, 246, 0.3)',
              padding: '0.25rem 0.5rem',
              borderRadius: '0.25rem',
              fontSize: '0.75rem',
              cursor: 'pointer'
            }}
          >
            Show More
          </button>
        )}
      </div>
    );
  };

  const renderHeaders = () => {
    return (
      <div>
        <div style={{ display: 'grid', gap: '0.5rem' }}>
          {Object.entries(response.headers).map(([key, value]) => (
            <div key={key} style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '0.5rem',
              background: 'rgba(15, 23, 42, 0.3)',
              borderRadius: '0.25rem',
              border: '1px solid rgba(51, 65, 85, 0.3)'
            }}>
              <span style={{ color: '#f8fafc', fontWeight: '500', fontSize: '0.875rem' }}>
                {key}
              </span>
              <span style={{ color: '#94a3b8', fontSize: '0.875rem', wordBreak: 'break-all' }}>
                {value}
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderRaw = () => {
    const rawData = JSON.stringify(response, null, 2);
    
    return (
      <div style={{ position: 'relative' }}>
        <pre style={{
          margin: 0,
          padding: '1rem',
          background: 'rgba(15, 23, 42, 0.5)',
          borderRadius: '0.25rem',
          border: '1px solid rgba(51, 65, 85, 0.3)',
          color: '#d1d5db',
          fontSize: '0.875rem',
          lineHeight: '1.5',
          overflow: 'auto',
          maxHeight: expanded ? 'none' : '300px',
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word'
        }}>
          {rawData}
        </pre>
        
        {!expanded && rawData.length > 1000 && (
          <button
            onClick={() => setExpanded(true)}
            style={{
              position: 'absolute',
              bottom: '0.5rem',
              right: '0.5rem',
              background: 'rgba(15, 23, 42, 0.8)',
              color: '#60a5fa',
              border: '1px solid rgba(59, 130, 246, 0.3)',
              padding: '0.25rem 0.5rem',
              borderRadius: '0.25rem',
              fontSize: '0.75rem',
              cursor: 'pointer'
            }}
          >
            Show More
          </button>
        )}
      </div>
    );
  };

  return (
    <div className={`response-viewer ${className}`} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {/* Response Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '1rem',
        background: 'rgba(30, 41, 59, 0.5)',
        borderRadius: '0.5rem',
        border: '1px solid rgba(51, 65, 85, 0.3)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '1.25rem' }}>{getStatusIcon(response.status)}</span>
            <span style={{ 
              color: getStatusColor(response.status),
              fontSize: '1.25rem',
              fontWeight: '600'
            }}>
              {response.status}
            </span>
            <span style={{ color: '#94a3b8', fontSize: '0.875rem' }}>
              {response.statusText}
            </span>
          </div>
          
          <div style={{ display: 'flex', gap: '1rem', fontSize: '0.75rem', color: '#94a3b8' }}>
            <span>Duration: {formatDuration(response.duration)}</span>
            <span>Time: {formatTimestamp(response.timestamp)}</span>
          </div>
        </div>
        
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            onClick={handleCopy}
            style={{
              background: 'transparent',
              border: '1px solid rgba(59, 130, 246, 0.3)',
              color: '#60a5fa',
              padding: '0.25rem 0.5rem',
              borderRadius: '0.25rem',
              fontSize: '0.75rem',
              cursor: 'pointer'
            }}
          >
            Copy
          </button>
          {onClear && (
            <button
              onClick={onClear}
              style={{
                background: 'transparent',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                color: '#ef4444',
                padding: '0.25rem 0.5rem',
                borderRadius: '0.25rem',
                fontSize: '0.75rem',
                cursor: 'pointer'
            }}
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '0.5rem', borderBottom: '1px solid rgba(51, 65, 85, 0.3)' }}>
        {[
          { id: 'body', label: 'Response Body', count: Object.keys(response.data || {}).length },
          { id: 'headers', label: 'Headers', count: Object.keys(response.headers || {}).length },
          { id: 'raw', label: 'Raw Response', count: 1 }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as 'body' | 'headers' | 'raw')}
            style={{
              padding: '0.5rem 1rem',
              background: activeTab === tab.id ? 'rgba(59, 130, 246, 0.2)' : 'transparent',
              border: 'none',
              borderBottom: activeTab === tab.id ? '2px solid #3b82f6' : '2px solid transparent',
              color: activeTab === tab.id ? '#60a5fa' : '#94a3b8',
              fontSize: '0.875rem',
              cursor: 'pointer',
              transition: 'all 0.2s ease'
            }}
          >
            {tab.label} {tab.count > 0 && `(${tab.count})`}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div style={{ minHeight: '200px' }}>
        {activeTab === 'body' && renderBody()}
        {activeTab === 'headers' && renderHeaders()}
        {activeTab === 'raw' && renderRaw()}
      </div>

      {/* Response Info */}
      <div style={{
        padding: '0.75rem',
        background: 'rgba(30, 41, 59, 0.3)',
        borderRadius: '0.5rem',
        border: '1px solid rgba(51, 65, 85, 0.3)',
        fontSize: '0.75rem',
        color: '#94a3b8'
      }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '1rem' }}>
          <div>
            <div style={{ color: '#d1d5db', marginBottom: '0.25rem' }}>Status</div>
            <div style={{ color: getStatusColor(response.status) }}>
              {response.status} {response.statusText}
            </div>
          </div>
          <div>
            <div style={{ color: '#d1d5db', marginBottom: '0.25rem' }}>Duration</div>
            <div>{formatDuration(response.duration)}</div>
          </div>
          <div>
            <div style={{ color: '#d1d5db', marginBottom: '0.25rem' }}>Size</div>
            <div>{JSON.stringify(response.data).length} bytes</div>
          </div>
          <div>
            <div style={{ color: '#d1d5db', marginBottom: '0.25rem' }}>Timestamp</div>
            <div>{formatTimestamp(response.timestamp)}</div>
          </div>
        </div>
      </div>
    </div>
  );
};
