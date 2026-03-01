import React, { useState, useMemo } from 'react';

interface Session {
  id: string;
  user: string;
  status: 'active' | 'idle' | 'terminated';
  node: string;
  startTime: string;
  duration: string;
  bandwidth: string;
  lastActivity: string;
}

interface SessionsTableProps {
  sessions: Session[];
  loading?: boolean;
  onSessionSelect?: (session: Session) => void;
  onBulkAction?: (action: string, sessionIds: string[]) => void;
  onRefresh?: () => void;
  className?: string;
}

export const SessionsTable: React.FC<SessionsTableProps> = ({
  sessions,
  loading = false,
  onSessionSelect,
  onBulkAction,
  onRefresh,
  className = ''
}) => {
  const [selectedSessions, setSelectedSessions] = useState<string[]>([]);
  const [sortField, setSortField] = useState<keyof Session>('startTime');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [filterStatus, setFilterStatus] = useState<string>('');
  const [filterUser, setFilterUser] = useState<string>('');
  const [filterNode, setFilterNode] = useState<string>('');

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedSessions(sessions.map(session => session.id));
    } else {
      setSelectedSessions([]);
    }
  };

  const handleSelectSession = (sessionId: string, checked: boolean) => {
    if (checked) {
      setSelectedSessions(prev => [...prev, sessionId]);
    } else {
      setSelectedSessions(prev => prev.filter(id => id !== sessionId));
    }
  };

  const handleSort = (field: keyof Session) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const filteredAndSortedSessions = useMemo(() => {
    let filtered = sessions.filter(session => {
      if (filterStatus && session.status !== filterStatus) return false;
      if (filterUser && !session.user.toLowerCase().includes(filterUser.toLowerCase())) return false;
      if (filterNode && !session.node.toLowerCase().includes(filterNode.toLowerCase())) return false;
      return true;
    });

    return filtered.sort((a, b) => {
      const aValue = a[sortField];
      const bValue = b[sortField];
      
      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return sortDirection === 'asc' 
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue);
      }
      
      return sortDirection === 'asc' 
        ? (aValue < bValue ? -1 : 1)
        : (aValue > bValue ? -1 : 1);
    });
  }, [sessions, filterStatus, filterUser, filterNode, sortField, sortDirection]);

  const getStatusClass = (status: string) => {
    switch (status) {
      case 'active':
        return 'status-active';
      case 'idle':
        return 'status-idle';
      case 'terminated':
        return 'status-terminated';
      default:
        return '';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return '🟢';
      case 'idle':
        return '🟡';
      case 'terminated':
        return '🔴';
      default:
        return '⚪';
    }
  };

  const handleBulkAction = (action: string) => {
    if (onBulkAction && selectedSessions.length > 0) {
      onBulkAction(action, selectedSessions);
      setSelectedSessions([]);
    }
  };

  if (loading) {
    return (
      <div className={`sessions-table loading ${className}`}>
        <div className="loading-spinner"></div>
        <div className="loading-text">Loading sessions...</div>
      </div>
    );
  }

  return (
    <div className={`sessions-table ${className}`}>
      <div className="table-header">
        <div className="table-title">
          <h3>Active Sessions</h3>
          <span className="session-count">{filteredAndSortedSessions.length} sessions</span>
        </div>
        <div className="table-actions">
          {selectedSessions.length > 0 && (
            <div className="bulk-actions">
              <button 
                className="btn danger"
                onClick={() => handleBulkAction('terminate')}
              >
                Terminate Selected ({selectedSessions.length})
              </button>
              <button 
                className="btn secondary"
                onClick={() => handleBulkAction('anchor')}
              >
                Anchor to Blockchain
              </button>
            </div>
          )}
          <button className="btn secondary" onClick={onRefresh}>
            🔄 Refresh
          </button>
        </div>
      </div>

      <div className="table-filters">
        <div className="filter-group">
          <label>Status:</label>
          <select 
            value={filterStatus} 
            onChange={(e) => setFilterStatus(e.target.value)}
          >
            <option value="">All</option>
            <option value="active">Active</option>
            <option value="idle">Idle</option>
            <option value="terminated">Terminated</option>
          </select>
        </div>
        <div className="filter-group">
          <label>User:</label>
          <input 
            type="text"
            placeholder="Filter by user..."
            value={filterUser}
            onChange={(e) => setFilterUser(e.target.value)}
          />
        </div>
        <div className="filter-group">
          <label>Node:</label>
          <input 
            type="text"
            placeholder="Filter by node..."
            value={filterNode}
            onChange={(e) => setFilterNode(e.target.value)}
          />
        </div>
      </div>

      <div className="table-container">
        <table className="sessions-table-content">
          <thead>
            <tr>
              <th className="checkbox-col">
                <input 
                  type="checkbox"
                  checked={selectedSessions.length === sessions.length && sessions.length > 0}
                  onChange={(e) => handleSelectAll(e.target.checked)}
                />
              </th>
              <th 
                className="sortable"
                onClick={() => handleSort('id')}
              >
                Session ID {sortField === 'id' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th 
                className="sortable"
                onClick={() => handleSort('user')}
              >
                User {sortField === 'user' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th 
                className="sortable"
                onClick={() => handleSort('status')}
              >
                Status {sortField === 'status' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th 
                className="sortable"
                onClick={() => handleSort('node')}
              >
                Node {sortField === 'node' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th 
                className="sortable"
                onClick={() => handleSort('startTime')}
              >
                Start Time {sortField === 'startTime' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th 
                className="sortable"
                onClick={() => handleSort('duration')}
              >
                Duration {sortField === 'duration' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th 
                className="sortable"
                onClick={() => handleSort('bandwidth')}
              >
                Bandwidth {sortField === 'bandwidth' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredAndSortedSessions.map((session) => (
              <tr key={session.id} className="session-row">
                <td className="checkbox-col">
                  <input 
                    type="checkbox"
                    checked={selectedSessions.includes(session.id)}
                    onChange={(e) => handleSelectSession(session.id, e.target.checked)}
                  />
                </td>
                <td className="session-id">
                  <button 
                    className="session-link"
                    onClick={() => onSessionSelect?.(session)}
                  >
                    {session.id}
                  </button>
                </td>
                <td className="user-cell">{session.user}</td>
                <td className="status-cell">
                  <span className={`status-badge ${getStatusClass(session.status)}`}>
                    {getStatusIcon(session.status)} {session.status}
                  </span>
                </td>
                <td className="node-cell">{session.node}</td>
                <td className="start-time">{session.startTime}</td>
                <td className="duration">{session.duration}</td>
                <td className="bandwidth">{session.bandwidth}</td>
                <td className="actions-cell">
                  <div className="action-buttons">
                    <button 
                      className="btn-icon"
                      onClick={() => onSessionSelect?.(session)}
                      title="View Details"
                    >
                      👁️
                    </button>
                    <button 
                      className="btn-icon danger"
                      onClick={() => handleBulkAction('terminate', [session.id])}
                      title="Terminate Session"
                    >
                      🛑
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {filteredAndSortedSessions.length === 0 && (
        <div className="empty-state">
          <div className="empty-icon">📊</div>
          <div className="empty-text">No sessions found</div>
          <div className="empty-subtext">
            {sessions.length === 0 
              ? 'No sessions are currently active'
              : 'Try adjusting your filters'
            }
          </div>
        </div>
      )}
    </div>
  );
};

export default SessionsTable;
