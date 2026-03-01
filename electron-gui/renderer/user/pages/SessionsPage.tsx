import React, { useState, useEffect, useCallback } from 'react';
import { SessionCard } from '../components/SessionCard';
import { SessionControls } from '../components/SessionControls';

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

interface SessionsPageProps {
  user: User | null;
  onRouteChange: (routeId: string) => void;
  onNotification: (notification: any) => void;
  apiCall: (endpoint: string, method: string, data?: any) => Promise<any>;
}

export const SessionsPage: React.FC<SessionsPageProps> = ({
  user,
  onRouteChange,
  onNotification,
  apiCall
}) => {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSessions, setSelectedSessions] = useState<string[]>([]);
  const [filter, setFilter] = useState<'all' | 'active' | 'completed' | 'failed' | 'anchored'>('all');
  const [sortBy, setSortBy] = useState<'created_at' | 'start_time' | 'data_size'>('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  // Load user sessions
  const loadSessions = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiCall('/sessions', 'GET');
      
      if (response.success) {
        setSessions(response.sessions || []);
      } else {
        throw new Error(response.message || 'Failed to load sessions');
      }
    } catch (err) {
      console.error('Failed to load sessions:', err);
      setError(err instanceof Error ? err.message : 'Failed to load sessions');
      onNotification({
        type: 'error',
        title: 'Error',
        message: 'Failed to load sessions'
      });
    } finally {
      setLoading(false);
    }
  }, [apiCall, onNotification]);

  // Create new session
  const handleCreateSession = useCallback(() => {
    onRouteChange('create-session');
  }, [onRouteChange]);

  // View session history
  const handleViewHistory = useCallback(() => {
    onRouteChange('history');
  }, [onRouteChange]);

  // Select session
  const handleSelectSession = useCallback((sessionId: string, selected: boolean) => {
    setSelectedSessions(prev => {
      if (selected) {
        return [...prev, sessionId];
      } else {
        return prev.filter(id => id !== sessionId);
      }
    });
  }, []);

  // Select all sessions
  const handleSelectAll = useCallback(() => {
    const filteredSessions = getFilteredSessions();
    if (selectedSessions.length === filteredSessions.length) {
      setSelectedSessions([]);
    } else {
      setSelectedSessions(filteredSessions.map(s => s.id));
    }
  }, [selectedSessions]);

  // Terminate selected sessions
  const handleTerminateSessions = useCallback(async () => {
    if (selectedSessions.length === 0) return;

    try {
      const response = await apiCall('/sessions/terminate', 'POST', {
        session_ids: selectedSessions
      });

      if (response.success) {
        onNotification({
          type: 'success',
          title: 'Sessions Terminated',
          message: `${selectedSessions.length} session(s) terminated successfully`
        });
        setSelectedSessions([]);
        loadSessions();
      } else {
        throw new Error(response.message || 'Failed to terminate sessions');
      }
    } catch (err) {
      console.error('Failed to terminate sessions:', err);
      onNotification({
        type: 'error',
        title: 'Error',
        message: 'Failed to terminate sessions'
      });
    }
  }, [selectedSessions, apiCall, onNotification, loadSessions]);

  // Anchor selected sessions
  const handleAnchorSessions = useCallback(async () => {
    if (selectedSessions.length === 0) return;

    try {
      const response = await apiCall('/sessions/anchor', 'POST', {
        session_ids: selectedSessions
      });

      if (response.success) {
        onNotification({
          type: 'success',
          title: 'Sessions Anchored',
          message: `${selectedSessions.length} session(s) anchored to blockchain`
        });
        setSelectedSessions([]);
        loadSessions();
      } else {
        throw new Error(response.message || 'Failed to anchor sessions');
      }
    } catch (err) {
      console.error('Failed to anchor sessions:', err);
      onNotification({
        type: 'error',
        title: 'Error',
        message: 'Failed to anchor sessions'
      });
    }
  }, [selectedSessions, apiCall, onNotification, loadSessions]);

  // Get filtered sessions
  const getFilteredSessions = useCallback(() => {
    let filtered = sessions;

    if (filter !== 'all') {
      filtered = filtered.filter(session => session.status === filter);
    }

    return filtered.sort((a, b) => {
      let aValue: any = a[sortBy];
      let bValue: any = b[sortBy];

      if (sortBy === 'created_at' || sortBy === 'start_time') {
        aValue = new Date(aValue).getTime();
        bValue = new Date(bValue).getTime();
      }

      if (sortOrder === 'asc') {
        return aValue > bValue ? 1 : -1;
      } else {
        return aValue < bValue ? 1 : -1;
      }
    });
  }, [sessions, filter, sortBy, sortOrder]);

  // Load sessions on mount
  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

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

  const filteredSessions = getFilteredSessions();

  if (loading) {
    return (
      <div className="user-content">
        <div className="user-page-header">
          <h1 className="user-page-title">My Sessions</h1>
          <p className="user-page-subtitle">Manage your active and completed sessions</p>
        </div>
        <div className="user-loading">
          <div className="user-loading-spinner"></div>
          Loading sessions...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="user-content">
        <div className="user-page-header">
          <h1 className="user-page-title">My Sessions</h1>
          <p className="user-page-subtitle">Manage your active and completed sessions</p>
        </div>
        <div className="user-card">
          <div className="user-card-body">
            <div className="user-empty-state">
              <div className="user-empty-state-title">Error Loading Sessions</div>
              <p className="user-empty-state-description">{error}</p>
              <button className="user-btn user-btn-primary" onClick={loadSessions}>
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
        <h1 className="user-page-title">My Sessions</h1>
        <p className="user-page-subtitle">Manage your active and completed sessions</p>
      </div>

      {/* Session Controls */}
      <SessionControls
        selectedCount={selectedSessions.length}
        totalSessions={sessions.length}
        activeSessions={sessions.filter(s => s.status === 'active').length}
        onCreateSession={handleCreateSession}
        onViewHistory={handleViewHistory}
        onTerminateSelected={handleTerminateSessions}
        onAnchorSelected={handleAnchorSessions}
      />

      {/* Filters and Sorting */}
      <div className="user-card">
        <div className="user-card-body">
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', marginBottom: '1rem' }}>
            <div>
              <label className="user-form-label">Filter:</label>
              <select 
                className="user-form-input user-form-select"
                value={filter}
                onChange={(e) => setFilter(e.target.value as any)}
                style={{ width: 'auto', minWidth: '120px' }}
              >
                <option value="all">All Sessions</option>
                <option value="active">Active</option>
                <option value="completed">Completed</option>
                <option value="failed">Failed</option>
                <option value="anchored">Anchored</option>
              </select>
            </div>
            <div>
              <label className="user-form-label">Sort by:</label>
              <select 
                className="user-form-input user-form-select"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                style={{ width: 'auto', minWidth: '120px' }}
              >
                <option value="created_at">Created Date</option>
                <option value="start_time">Start Time</option>
                <option value="data_size">Data Size</option>
              </select>
            </div>
            <div>
              <label className="user-form-label">Order:</label>
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

      {/* Sessions List */}
      {filteredSessions.length === 0 ? (
        <div className="user-card">
          <div className="user-card-body">
            <div className="user-empty-state">
              <div className="user-empty-state-title">No Sessions Found</div>
              <p className="user-empty-state-description">
                {filter === 'all' 
                  ? "You haven't created any sessions yet."
                  : `No ${filter} sessions found.`
                }
              </p>
              <button className="user-btn user-btn-primary" onClick={handleCreateSession}>
                Create Your First Session
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="user-sessions-grid" style={{ display: 'grid', gap: '1rem', gridTemplateColumns: 'repeat(auto-fill, minmax(400px, 1fr))' }}>
          {filteredSessions.map(session => (
            <SessionCard
              key={session.id}
              session={session}
              selected={selectedSessions.includes(session.id)}
              onSelect={(selected) => handleSelectSession(session.id, selected)}
              formatFileSize={formatFileSize}
              formatDuration={formatDuration}
            />
          ))}
        </div>
      )}

      {/* Select All Checkbox */}
      {filteredSessions.length > 0 && (
        <div className="user-card">
          <div className="user-card-body">
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <input
                type="checkbox"
                checked={selectedSessions.length === filteredSessions.length && filteredSessions.length > 0}
                onChange={handleSelectAll}
              />
              Select All Sessions ({filteredSessions.length})
            </label>
          </div>
        </div>
      )}
    </div>
  );
};
