import React from 'react';

interface SessionControlsProps {
  selectedCount: number;
  totalSessions: number;
  activeSessions: number;
  onCreateSession: () => void;
  onViewHistory: () => void;
  onTerminateSelected: () => void;
  onAnchorSelected: () => void;
}

export const SessionControls: React.FC<SessionControlsProps> = ({
  selectedCount,
  totalSessions,
  activeSessions,
  onCreateSession,
  onViewHistory,
  onTerminateSelected,
  onAnchorSelected
}) => {
  return (
    <div className="user-card">
      <div className="user-card-body">
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
          gap: '1rem',
          alignItems: 'center'
        }}>
          {/* Session Statistics */}
          <div style={{ display: 'grid', gap: '0.5rem' }}>
            <div style={{ fontSize: '0.875rem', color: 'var(--user-text-secondary)' }}>
              Session Statistics
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ 
                  fontSize: '1.5rem', 
                  fontWeight: '700', 
                  color: 'var(--user-primary)',
                  marginBottom: '0.25rem'
                }}>
                  {totalSessions}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--user-text-secondary)' }}>
                  Total
                </div>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ 
                  fontSize: '1.5rem', 
                  fontWeight: '700', 
                  color: 'var(--user-success)',
                  marginBottom: '0.25rem'
                }}>
                  {activeSessions}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--user-text-secondary)' }}>
                  Active
                </div>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ 
                  fontSize: '1.5rem', 
                  fontWeight: '700', 
                  color: selectedCount > 0 ? 'var(--user-warning)' : 'var(--user-text-tertiary)',
                  marginBottom: '0.25rem'
                }}>
                  {selectedCount}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--user-text-secondary)' }}>
                  Selected
                </div>
              </div>
            </div>
          </div>

          {/* Primary Actions */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <button
              className="user-btn user-btn-primary"
              onClick={onCreateSession}
              style={{ width: '100%' }}
            >
              <span style={{ marginRight: '0.5rem' }}>➕</span>
              Create New Session
            </button>
            <button
              className="user-btn user-btn-secondary"
              onClick={onViewHistory}
              style={{ width: '100%' }}
            >
              <span style={{ marginRight: '0.5rem' }}>📜</span>
              View History
            </button>
          </div>

          {/* Bulk Actions */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <div style={{ fontSize: '0.875rem', color: 'var(--user-text-secondary)', marginBottom: '0.25rem' }}>
              Bulk Actions
            </div>
            <button
              className="user-btn user-btn-warning"
              onClick={onTerminateSelected}
              disabled={selectedCount === 0}
              style={{ width: '100%' }}
            >
              <span style={{ marginRight: '0.5rem' }}>⏹️</span>
              Terminate Selected
            </button>
            <button
              className="user-btn user-btn-success"
              onClick={onAnchorSelected}
              disabled={selectedCount === 0}
              style={{ width: '100%' }}
            >
              <span style={{ marginRight: '0.5rem' }}>🔗</span>
              Anchor Selected
            </button>
          </div>
        </div>

        {/* Selection Info */}
        {selectedCount > 0 && (
          <div style={{
            marginTop: '1rem',
            padding: '1rem',
            backgroundColor: 'var(--user-bg-secondary)',
            borderRadius: 'var(--user-radius-md)',
            border: '1px solid var(--user-warning)'
          }}>
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '0.5rem',
              marginBottom: '0.5rem'
            }}>
              <span style={{ fontSize: '1.25rem' }}>⚠️</span>
              <span style={{ fontWeight: '500', color: 'var(--user-warning)' }}>
                {selectedCount} session{selectedCount !== 1 ? 's' : ''} selected
              </span>
            </div>
            <div style={{ fontSize: '0.875rem', color: 'var(--user-text-secondary)' }}>
              You can perform bulk actions on the selected sessions using the buttons above.
            </div>
          </div>
        )}

        {/* Quick Tips */}
        <div style={{
          marginTop: '1rem',
          padding: '1rem',
          backgroundColor: 'var(--user-bg-tertiary)',
          borderRadius: 'var(--user-radius-md)',
          fontSize: '0.875rem',
          color: 'var(--user-text-secondary)'
        }}>
          <div style={{ fontWeight: '500', marginBottom: '0.5rem', color: 'var(--user-text-primary)' }}>
            💡 Quick Tips
          </div>
          <ul style={{ margin: 0, paddingLeft: '1.5rem' }}>
            <li>Click on session cards to select them for bulk operations</li>
            <li>Use filters and sorting to find specific sessions</li>
            <li>Active sessions can be terminated or anchored to the blockchain</li>
            <li>Completed sessions can be exported or viewed in detail</li>
          </ul>
        </div>
      </div>
    </div>
  );
};
