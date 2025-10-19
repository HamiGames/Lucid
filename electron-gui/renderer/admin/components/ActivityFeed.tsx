import React, { useState, useMemo } from 'react';

interface ActivityItem {
  id: string;
  type: 'session' | 'user' | 'node' | 'blockchain' | 'system';
  action: string;
  description: string;
  timestamp: string;
  userId?: string;
  sessionId?: string;
  nodeId?: string;
  severity: 'info' | 'warning' | 'error' | 'success';
  metadata?: Record<string, any>;
}

interface ActivityFeedProps {
  activities: ActivityItem[];
  loading?: boolean;
  onActivitySelect?: (activity: ActivityItem) => void;
  onFilterChange?: (filter: string) => void;
  onRefresh?: () => void;
  maxItems?: number;
  className?: string;
}

export const ActivityFeed: React.FC<ActivityFeedProps> = ({
  activities,
  loading = false,
  onActivitySelect,
  onFilterChange,
  onRefresh,
  maxItems = 50,
  className = ''
}) => {
  const [filter, setFilter] = useState<string>('');
  const [sortOrder, setSortOrder] = useState<'newest' | 'oldest'>('newest');

  const filteredAndSortedActivities = useMemo(() => {
    let filtered = activities.filter(activity => {
      if (filter && !activity.type.includes(filter) && 
          !activity.action.toLowerCase().includes(filter.toLowerCase()) &&
          !activity.description.toLowerCase().includes(filter.toLowerCase())) return false;
      return true;
    });

    const sorted = filtered.sort((a, b) => {
      const aTime = new Date(a.timestamp).getTime();
      const bTime = new Date(b.timestamp).getTime();
      return sortOrder === 'newest' ? bTime - aTime : aTime - bTime;
    });

    return sorted.slice(0, maxItems);
  }, [activities, filter, sortOrder, maxItems]);

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'session':
        return '🖥️';
      case 'user':
        return '👤';
      case 'node':
        return '🖥️';
      case 'blockchain':
        return '⛓️';
      case 'system':
        return '⚙️';
      default:
        return '📋';
    }
  };

  const getSeverityClass = (severity: string) => {
    switch (severity) {
      case 'success':
        return 'severity-success';
      case 'info':
        return 'severity-info';
      case 'warning':
        return 'severity-warning';
      case 'error':
        return 'severity-error';
      default:
        return '';
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'success':
        return '✅';
      case 'info':
        return 'ℹ️';
      case 'warning':
        return '⚠️';
      case 'error':
        return '❌';
      default:
        return '📋';
    }
  };

  const getTimeAgo = (timestamp: string) => {
    const now = new Date();
    const activityTime = new Date(timestamp);
    const diffMs = now.getTime() - activityTime.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffDays > 0) return `${diffDays}d ago`;
    if (diffHours > 0) return `${diffHours}h ago`;
    if (diffMins > 0) return `${diffMins}m ago`;
    return 'Just now';
  };

  const handleFilterChange = (newFilter: string) => {
    setFilter(newFilter);
    onFilterChange?.(newFilter);
  };

  if (loading) {
    return (
      <div className={`activity-feed loading ${className}`}>
        <div className="loading-spinner"></div>
        <div className="loading-text">Loading activity...</div>
      </div>
    );
  }

  return (
    <div className={`activity-feed ${className}`}>
      <div className="feed-header">
        <div className="feed-title">
          <h3>Recent Activity</h3>
          <span className="activity-count">{filteredAndSortedActivities.length} activities</span>
        </div>
        <div className="feed-controls">
          <select 
            value={sortOrder}
            onChange={(e) => setSortOrder(e.target.value as 'newest' | 'oldest')}
            className="sort-select"
          >
            <option value="newest">Newest First</option>
            <option value="oldest">Oldest First</option>
          </select>
          <button className="btn secondary" onClick={onRefresh}>
            🔄
          </button>
        </div>
      </div>

      <div className="feed-filters">
        <div className="filter-group">
          <label>Filter:</label>
          <select 
            value={filter}
            onChange={(e) => handleFilterChange(e.target.value)}
          >
            <option value="">All Activities</option>
            <option value="session">Sessions</option>
            <option value="user">Users</option>
            <option value="node">Nodes</option>
            <option value="blockchain">Blockchain</option>
            <option value="system">System</option>
          </select>
        </div>
        <div className="filter-group">
          <input 
            type="text"
            placeholder="Search activities..."
            value={filter}
            onChange={(e) => handleFilterChange(e.target.value)}
          />
        </div>
      </div>

      <div className="activity-list">
        {filteredAndSortedActivities.map((activity) => (
          <div 
            key={activity.id} 
            className={`activity-item ${getSeverityClass(activity.severity)}`}
            onClick={() => onActivitySelect?.(activity)}
          >
            <div className="activity-icon">
              {getTypeIcon(activity.type)}
            </div>
            <div className="activity-content">
              <div className="activity-header">
                <span className="activity-type">{activity.type}</span>
                <span className="activity-time">{getTimeAgo(activity.timestamp)}</span>
              </div>
              <div className="activity-action">
                <span className={`severity-icon ${getSeverityClass(activity.severity)}`}>
                  {getSeverityIcon(activity.severity)}
                </span>
                <span className="action-text">{activity.action}</span>
              </div>
              <div className="activity-description">{activity.description}</div>
              <div className="activity-metadata">
                {activity.userId && (
                  <span className="metadata-item">User: {activity.userId}</span>
                )}
                {activity.sessionId && (
                  <span className="metadata-item">Session: {activity.sessionId}</span>
                )}
                {activity.nodeId && (
                  <span className="metadata-item">Node: {activity.nodeId}</span>
                )}
              </div>
            </div>
            <div className="activity-timestamp">
              {new Date(activity.timestamp).toLocaleTimeString()}
            </div>
          </div>
        ))}
      </div>

      {filteredAndSortedActivities.length === 0 && (
        <div className="empty-state">
          <div className="empty-icon">📋</div>
          <div className="empty-text">No activities found</div>
          <div className="empty-subtext">
            {activities.length === 0 
              ? 'No recent activity'
              : 'Try adjusting your filters'
            }
          </div>
        </div>
      )}

      {activities.length > maxItems && (
        <div className="feed-footer">
          <button className="btn secondary">
            Load More ({activities.length - maxItems} remaining)
          </button>
        </div>
      )}
    </div>
  );
};

export default ActivityFeed;
