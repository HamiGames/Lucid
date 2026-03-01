import React, { useState, useEffect, useCallback } from 'react';

interface User {
  id: string;
  email: string;
  tron_address: string;
  role: string;
  status: string;
  created_at: string;
  last_login: string;
  session_count: number;
}

interface SessionHistory {
  id: string;
  name: string;
  status: 'completed' | 'failed' | 'anchored';
  start_time: string;
  end_time: string;
  duration: number;
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

interface HistoryPageProps {
  user: User | null;
  onRouteChange: (routeId: string) => void;
  onNotification: (notification: any) => void;
  apiCall: (endpoint: string, method: string, data?: any) => Promise<any>;
}

export const HistoryPage: React.FC<HistoryPageProps> = ({
  user,
  onRouteChange,
  onNotification,
  apiCall
}) => {
  const [sessions, setSessions] = useState<SessionHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'completed' | 'failed' | 'anchored'>('all');
  const [sortBy, setSortBy] = useState<'created_at' | 'start_time' | 'end_time' | 'data_size'>('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(10);
  const [selectedSession, setSelectedSession] = useState<SessionHistory | null>(null);

  // Load session history
  const loadHistory = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams({
        page: currentPage.toString(),
        limit: itemsPerPage.toString(),
        sort_by: sortBy,
        sort_order: sortOrder,
        ...(filter !== 'all' && { status: filter }),
        ...(searchQuery && { search: searchQuery })
      });

      const response = await apiCall(`/sessions/history?${params}`, 'GET');
      
      if (response.success) {
        setSessions(response.sessions || []);
      } else {
        throw new Error(response.message || 'Failed to load session history');
      }
    } catch (err) {
      console.error('Failed to load session history:', err);
      setError(err instanceof Error ? err.message : 'Failed to load session history');
      onNotification({
        type: 'error',
        title: 'Error',
        message: 'Failed to load session history'
      });
    } finally {
      setLoading(false);
    }
  }, [currentPage, itemsPerPage, sortBy, sortOrder, filter, searchQuery, apiCall, onNotification]);

  // Export session data
  const handleExportSession = useCallback(async (sessionId: string) => {
    try {
      const response = await apiCall(`/sessions/${sessionId}/export`, 'GET');
      
      if (response.success) {
        // Create download link
        const blob = new Blob([response.data], { type: 'application/json' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `session-${sessionId}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);

        onNotification({
          type: 'success',
          title: 'Export Successful',
          message: 'Session data exported successfully'
        });
      } else {
        throw new Error(response.message || 'Failed to export session');
      }
    } catch (err) {
      console.error('Failed to export session:', err);
      onNotification({
        type: 'error',
        title: 'Export Failed',
        message: 'Failed to export session data'
      });
    }
  }, [apiCall, onNotification]);

  // View session details
  const handleViewDetails = useCallback((session: SessionHistory) => {
    setSelectedSession(session);
  }, []);

  // Close session details modal
  const handleCloseDetails = useCallback(() => {
    setSelectedSession(null);
  }, []);

  // Get filtered sessions
  const getFilteredSessions = useCallback(() => {
    return sessions.sort((a, b) => {
      let aValue: any = a[sortBy];
      let bValue: any = b[sortBy];

      if (sortBy === 'created_at' || sortBy === 'start_time' || sortBy === 'end_time') {
        aValue = new Date(aValue).getTime();
        bValue = new Date(bValue).getTime();
      }

      if (sortOrder === 'asc') {
        return aValue > bValue ? 1 : -1;
      } else {
        return aValue < bValue ? 1 : -1;
      }
    });
  }, [sessions, sortBy, sortOrder]);

  // Load history on mount and when dependencies change
  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  // Format file size
  const formatFileSize = (bytes: number): string => {
    const sizes = ['B', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 B';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
  };

  // Format duration
  const formatDuration = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;

    if (hours > 0) {
      return `${hours}h ${minutes}m ${secs}s`;
    } else if (minutes > 0) {
      return `${minutes}m ${secs}s`;
    } else {
      return `${secs}s`;
    }
  };

  // Format date
  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString();
  };

  const filteredSessions = getFilteredSessions();
  const totalPages = Math.ceil(sessions.length / itemsPerPage);

  if (loading) {
    return (
      <div className="user-content">
        <div className="user-page-header">
          <h1 className="user-page-title">Session History</h1>
          <p className="user-page-subtitle">View your completed session history</p>
        </div>
        <div className="user-loading">
          <div className="user-loading-spinner"></div>
          Loading session history...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="user-content">
        <div className="user-page-header">
          <h1 className="user-page-title">Session History</h1>
          <p className="user-page-subtitle">View your completed session history</p>
        </div>
        <div className="user-card">
          <div className="user-card-body">
            <div className="user-empty-state">
              <div className="user-empty-state-title">Error Loading History</div>
              <p className="user-empty-state-description">{error}</p>
              <button className="user-btn user-btn-primary" onClick={loadHistory}>
                Retry
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="user-content">
      <div className="user-page-header">
        <h1 className="user-page-title">Session History</h1>
        <p className="user-page-subtitle">View your completed session history</p>
      </div>

      {/* Filters and Search */}
      <div className="user-card">
        <div className="user-card-body">
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap' }}>
            {/* Search */}
            <div style={{ flex: '1', minWidth: '200px' }}>
              <input
                type="text"
                className="user-form-input"
                placeholder="Search sessions..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>

            {/* Filter */}
            <div>
              <select 
                className="user-form-input user-form-select"
                value={filter}
                onChange={(e) => setFilter(e.target.value as any)}
                style={{ width: 'auto', minWidth: '120px' }}
              >
                <option value="all">All Sessions</option>
                <option value="completed">Completed</option>
                <option value="failed">Failed</option>
                <option value="anchored">Anchored</option>
              </select>
            </div>

            {/* Sort */}
            <div>
              <select 
                className="user-form-input user-form-select"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                style={{ width: 'auto', minWidth: '120px' }}
              >
                <option value="created_at">Created Date</option>
                <option value="start_time">Start Time</option>
                <option value="end_time">End Time</option>
                <option value="data_size">Data Size</option>
              </select>
            </div>

            {/* Order */}
            <div>
              <select 
                className="user-form-input user-form-select"
                value={sortOrder}
                onChange={(e) => setSortOrder(e.target.value as any)}
                style={{ width: 'auto', minWidth: '100px' }}
              >
                <option value="desc">Newest First</option>
                <option value="asc">Oldest First</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Sessions Table */}
      {filteredSessions.length === 0 ? (
        <div className="user-card">
          <div className="user-card-body">
            <div className="user-empty-state">
              <div className="user-empty-state-title">No History Found</div>
              <p className="user-empty-state-description">
                {searchQuery 
                  ? `No sessions found matching "${searchQuery}".`
                  : "You haven't completed any sessions yet."
                }
              </p>
              {!searchQuery && (
                <button className="user-btn user-btn-primary" onClick={() => onRouteChange('create-session')}>
                  Create Your First Session
                </button>
              )}
            </div>
          </div>
        </div>
      ) : (
        <>
          <div className="user-table-container">
            <table className="user-table">
              <thead>
                <tr>
                  <th>Session Name</th>
                  <th>Status</th>
                  <th>Start Time</th>
                  <th>End Time</th>
                  <th>Duration</th>
                  <th>Data Size</th>
                  <th>Chunks</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredSessions.map(session => (
                  <tr key={session.id}>
                    <td>
                      <div>
                        <div style={{ fontWeight: '500' }}>{session.name}</div>
                        {session.blockchain_anchor && (
                          <div className="user-status user-status-active" style={{ fontSize: '0.75rem', marginTop: '0.25rem' }}>
                            <span className="user-status-dot"></span>
                            Anchored
                          </div>
                        )}
                      </div>
                    </td>
                    <td>
                      <span className={`user-status user-status-${session.status === 'completed' ? 'active' : session.status === 'failed' ? 'error' : 'active'}`}>
                        <span className="user-status-dot"></span>
                        {session.status}
                      </span>
                    </td>
                    <td>{formatDate(session.start_time)}</td>
                    <td>{formatDate(session.end_time)}</td>
                    <td>{formatDuration(session.duration)}</td>
                    <td>{formatFileSize(session.data_size)}</td>
                    <td>{session.chunks_count}</td>
                    <td>
                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button
                          className="user-btn user-btn-sm user-btn-secondary"
                          onClick={() => handleViewDetails(session)}
                        >
                          View
                        </button>
                        <button
                          className="user-btn user-btn-sm user-btn-primary"
                          onClick={() => handleExportSession(session.id)}
                        >
                          Export
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="user-card">
              <div className="user-card-body">
                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '1rem' }}>
                  <button
                    className="user-btn user-btn-secondary"
                    onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                    disabled={currentPage === 1}
                  >
                    Previous
                  </button>
                  <span>
                    Page {currentPage} of {totalPages}
                  </span>
                  <button
                    className="user-btn user-btn-secondary"
                    onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                    disabled={currentPage === totalPages}
                  >
                    Next
                  </button>
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {/* Session Details Modal */}
      {selectedSession && (
        <div className="user-modal-overlay" onClick={handleCloseDetails}>
          <div className="user-modal" onClick={(e) => e.stopPropagation()}>
            <div className="user-modal-header">
              <h3 className="user-modal-title">Session Details</h3>
              <button className="user-modal-close" onClick={handleCloseDetails}>
                ×
              </button>
            </div>
            <div className="user-modal-body">
              <div style={{ display: 'grid', gap: '1rem' }}>
                <div>
                  <strong>Name:</strong> {selectedSession.name}
                </div>
                <div>
                  <strong>Status:</strong> 
                  <span className={`user-status user-status-${selectedSession.status === 'completed' ? 'active' : selectedSession.status === 'failed' ? 'error' : 'active'}`} style={{ marginLeft: '0.5rem' }}>
                    <span className="user-status-dot"></span>
                    {selectedSession.status}
                  </span>
                </div>
                <div>
                  <strong>Start Time:</strong> {formatDate(selectedSession.start_time)}
                </div>
                <div>
                  <strong>End Time:</strong> {formatDate(selectedSession.end_time)}
                </div>
                <div>
                  <strong>Duration:</strong> {formatDuration(selectedSession.duration)}
                </div>
                <div>
                  <strong>Data Size:</strong> {formatFileSize(selectedSession.data_size)}
                </div>
                <div>
                  <strong>Chunks:</strong> {selectedSession.chunks_count}
                </div>
                <div>
                  <strong>Node ID:</strong> {selectedSession.node_id}
                </div>
                {selectedSession.merkle_root && (
                  <div>
                    <strong>Merkle Root:</strong> 
                    <div style={{ fontFamily: 'monospace', fontSize: '0.875rem', marginTop: '0.25rem', wordBreak: 'break-all' }}>
                      {selectedSession.merkle_root}
                    </div>
                  </div>
                )}
                {selectedSession.blockchain_anchor && (
                  <div>
                    <strong>Blockchain Anchor:</strong>
                    <div style={{ marginTop: '0.5rem', padding: '1rem', backgroundColor: 'var(--user-bg-secondary)', borderRadius: 'var(--user-radius-md)' }}>
                      <div><strong>Block Height:</strong> {selectedSession.blockchain_anchor.block_height}</div>
                      <div><strong>Transaction Hash:</strong> 
                        <div style={{ fontFamily: 'monospace', fontSize: '0.875rem', marginTop: '0.25rem', wordBreak: 'break-all' }}>
                          {selectedSession.blockchain_anchor.transaction_hash}
                        </div>
                      </div>
                      <div><strong>Timestamp:</strong> {formatDate(selectedSession.blockchain_anchor.timestamp)}</div>
                    </div>
                  </div>
                )}
              </div>
            </div>
            <div className="user-modal-footer">
              <button
                className="user-btn user-btn-primary"
                onClick={() => handleExportSession(selectedSession.id)}
              >
                Export Session
              </button>
              <button className="user-btn user-btn-secondary" onClick={handleCloseDetails}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
