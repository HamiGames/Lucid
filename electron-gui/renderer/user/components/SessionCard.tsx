import React from 'react';

interface Session {
  id: string;
  status: 'active' | 'completed' | 'failed' | 'anchored';
  start_time: string;
  end_time?: string;
  duration?: number;
  data_size: number;
  chunks_count: number;
  node_id: string;
  merkle_root?: string;
  blockchain_anchor?: {
    block_height: number;
    transaction_hash: string;
    timestamp: string;
  };
  created_at: string;
  updated_at: string;
}

interface SessionCardProps {
  session: Session;
  selected: boolean;
  onSelect: (selected: boolean) => void;
  formatFileSize: (bytes: number) => string;
  formatDuration: (seconds: number) => string;
}

export const SessionCard: React.FC<SessionCardProps> = ({
  session,
  selected,
  onSelect,
  formatFileSize,
  formatDuration
}) => {
  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'active':
        return 'var(--user-success)';
      case 'completed':
        return 'var(--user-info)';
      case 'failed':
        return 'var(--user-error)';
      case 'anchored':
        return 'var(--user-primary)';
      default:
        return 'var(--user-secondary)';
    }
  };

  const getStatusIcon = (status: string): string => {
    switch (status) {
      case 'active':
        return '🟢';
      case 'completed':
        return '✅';
      case 'failed':
        return '❌';
      case 'anchored':
        return '🔗';
      default:
        return '⚪';
    }
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString();
  };

  const getProgressPercentage = (): number => {
    if (session.status === 'completed' || session.status === 'anchored') {
      return 100;
    } else if (session.status === 'failed') {
      return 0;
    } else {
      // For active sessions, calculate based on time elapsed vs expected duration
      const startTime = new Date(session.start_time).getTime();
      const now = new Date().getTime();
      const elapsed = (now - startTime) / 1000; // seconds
      const expectedDuration = session.duration || 300; // default 5 minutes
      return Math.min((elapsed / expectedDuration) * 100, 95); // cap at 95% for active
    }
  };

  return (
    <div 
      className="user-card"
      style={{
        border: selected ? '2px solid var(--user-primary)' : '1px solid var(--user-border-primary)',
        cursor: 'pointer',
        transition: 'all var(--user-transition-fast)'
      }}
      onClick={() => onSelect(!selected)}
    >
      <div className="user-card-header">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <input
              type="checkbox"
              checked={selected}
              onChange={(e) => {
                e.stopPropagation();
                onSelect(e.target.checked);
              }}
              style={{ margin: 0 }}
            />
            <span style={{ fontSize: '1.25rem' }}>{getStatusIcon(session.status)}</span>
            <span style={{ 
              color: getStatusColor(session.status),
              fontWeight: '600',
              textTransform: 'capitalize'
            }}>
              {session.status}
            </span>
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--user-text-secondary)' }}>
            ID: {session.id.substring(0, 8)}...
          </div>
        </div>
      </div>

      <div className="user-card-body">
        <div style={{ display: 'grid', gap: '1rem' }}>
          {/* Session Info */}
          <div>
            <div style={{ fontSize: '0.875rem', color: 'var(--user-text-secondary)', marginBottom: '0.25rem' }}>
              Session Details
            </div>
            <div style={{ display: 'grid', gap: '0.5rem', fontSize: '0.875rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Started:</span>
                <span>{formatDate(session.start_time)}</span>
              </div>
              {session.end_time && (
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>Ended:</span>
                  <span>{formatDate(session.end_time)}</span>
                </div>
              )}
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Duration:</span>
                <span>{session.duration ? formatDuration(session.duration) : 'N/A'}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Data Size:</span>
                <span>{formatFileSize(session.data_size)}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Chunks:</span>
                <span>{session.chunks_count}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Node:</span>
                <span style={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                  {session.node_id.substring(0, 12)}...
                </span>
              </div>
            </div>
          </div>

          {/* Progress Bar */}
          {session.status === 'active' && (
            <div>
              <div style={{ 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center',
                marginBottom: '0.5rem'
              }}>
                <span style={{ fontSize: '0.875rem', color: 'var(--user-text-secondary)' }}>
                  Progress
                </span>
                <span style={{ fontSize: '0.875rem', fontWeight: '500' }}>
                  {Math.round(getProgressPercentage())}%
                </span>
              </div>
              <div style={{
                width: '100%',
                height: '8px',
                backgroundColor: 'var(--user-bg-tertiary)',
                borderRadius: '4px',
                overflow: 'hidden'
              }}>
                <div style={{
                  width: `${getProgressPercentage()}%`,
                  height: '100%',
                  backgroundColor: getStatusColor(session.status),
                  transition: 'width 0.3s ease',
                  borderRadius: '4px'
                }} />
              </div>
            </div>
          )}

          {/* Blockchain Anchor Info */}
          {session.blockchain_anchor && (
            <div style={{
              padding: '1rem',
              backgroundColor: 'var(--user-bg-secondary)',
              borderRadius: 'var(--user-radius-md)',
              border: '1px solid var(--user-primary)'
            }}>
              <div style={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: '0.5rem',
                marginBottom: '0.5rem'
              }}>
                <span style={{ fontSize: '1rem' }}>🔗</span>
                <span style={{ fontWeight: '600', fontSize: '0.875rem' }}>
                  Blockchain Anchored
                </span>
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--user-text-secondary)' }}>
                <div>Block: {session.blockchain_anchor.block_height}</div>
                <div style={{ 
                  fontFamily: 'monospace', 
                  wordBreak: 'break-all',
                  marginTop: '0.25rem'
                }}>
                  TX: {session.blockchain_anchor.transaction_hash.substring(0, 16)}...
                </div>
                <div style={{ marginTop: '0.25rem' }}>
                  {formatDate(session.blockchain_anchor.timestamp)}
                </div>
              </div>
            </div>
          )}

          {/* Merkle Root */}
          {session.merkle_root && (
            <div>
              <div style={{ fontSize: '0.875rem', color: 'var(--user-text-secondary)', marginBottom: '0.25rem' }}>
                Merkle Root
              </div>
              <div style={{
                fontFamily: 'monospace',
                fontSize: '0.75rem',
                backgroundColor: 'var(--user-bg-secondary)',
                padding: '0.5rem',
                borderRadius: 'var(--user-radius-sm)',
                wordBreak: 'break-all',
                color: 'var(--user-text-secondary)'
              }}>
                {session.merkle_root}
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="user-card-footer">
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          fontSize: '0.75rem',
          color: 'var(--user-text-tertiary)'
        }}>
          <span>
            Created: {formatDate(session.created_at)}
          </span>
          <span>
            Updated: {formatDate(session.updated_at)}
          </span>
        </div>
      </div>
    </div>
  );
};
