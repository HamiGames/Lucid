import React, { useState, useEffect } from 'react';

// Types
interface NodeUser {
  node_id: string;
  operator_id: string;
  pool_id?: string;
  status: 'active' | 'inactive' | 'maintenance' | 'suspended';
  hardware_info: {
    cpu_cores: number;
    memory_gb: number;
    disk_gb: number;
    network_speed_mbps: number;
  };
  location: {
    country: string;
    region: string;
    timezone: string;
  };
  poot_score: number;
  total_earnings: number;
  uptime_percentage: number;
  created_at: string;
  last_activity: string;
}

interface SystemHealth {
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  network_bandwidth: number;
  temperature: number;
  uptime: number;
  last_health_check: string;
}

interface NodeStatusCardProps {
  nodeUser: NodeUser | null;
  systemHealth: SystemHealth | null;
  onAction: (action: string) => void;
  className?: string;
}

const NodeStatusCard: React.FC<NodeStatusCardProps> = ({
  nodeUser,
  systemHealth,
  onAction,
  className = ''
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  useEffect(() => {
    const interval = setInterval(() => {
      setLastUpdate(new Date());
    }, 30000); // Update every 30 seconds

    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string): string => {
    const colors: Record<string, string> = {
      active: '#27ae60',
      inactive: '#95a5a6',
      maintenance: '#f39c12',
      suspended: '#e74c3c',
    };
    return colors[status] || '#95a5a6';
  };

  const getStatusIcon = (status: string): string => {
    const icons: Record<string, string> = {
      active: '🟢',
      inactive: '⚫',
      maintenance: '🟡',
      suspended: '🔴',
    };
    return icons[status] || '⚪';
  };

  const formatUptime = (seconds: number): string => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);

    if (days > 0) {
      return `${days}d ${hours}h ${minutes}m`;
    } else if (hours > 0) {
      return `${hours}h ${minutes}m`;
    } else {
      return `${minutes}m`;
    }
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatBytes = (bytes: number): string => {
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let size = bytes;
    let unitIndex = 0;

    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }

    return `${size.toFixed(1)} ${units[unitIndex]}`;
  };

  const getResourceStatus = (usage: number): 'good' | 'warning' | 'critical' => {
    if (usage < 70) return 'good';
    if (usage < 90) return 'warning';
    return 'critical';
  };

  if (!nodeUser) {
    return (
      <div className={`node-status-card ${className}`}>
        <div className="status-card-header">
          <h3 className="status-card-title">Node Status</h3>
          <div className="status-indicator status-inactive"></div>
        </div>
        <div className="status-card-body">
          <div className="no-data">
            <p>No node information available</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`node-status-card ${className}`}>
      <div className="status-card-header">
        <h3 className="status-card-title">Node Status</h3>
        <div className="status-info">
          <span className="status-icon">{getStatusIcon(nodeUser.status)}</span>
          <span
            className="status-text"
            style={{ color: getStatusColor(nodeUser.status) }}
          >
            {nodeUser.status.toUpperCase()}
          </span>
        </div>
      </div>

      <div className="status-card-body">
        {/* Basic Node Information */}
        <div className="node-info-section">
          <div className="info-item">
            <span className="info-label">Node ID:</span>
            <span className="info-value">{nodeUser.node_id.substring(0, 12)}...</span>
          </div>
          <div className="info-item">
            <span className="info-label">Operator:</span>
            <span className="info-value">{nodeUser.operator_id}</span>
          </div>
          {nodeUser.pool_id && (
            <div className="info-item">
              <span className="info-label">Pool:</span>
              <span className="info-value">{nodeUser.pool_id.substring(0, 8)}...</span>
            </div>
          )}
          <div className="info-item">
            <span className="info-label">Location:</span>
            <span className="info-value">{nodeUser.location.country}, {nodeUser.location.region}</span>
          </div>
        </div>

        {/* System Health Overview */}
        {systemHealth && (
          <div className="health-section">
            <h4 className="section-title">System Health</h4>
            <div className="health-grid">
              <div className="health-item">
                <div className="health-label">CPU</div>
                <div className={`health-value ${getResourceStatus(systemHealth.cpu_usage)}`}>
                  {systemHealth.cpu_usage.toFixed(1)}%
                </div>
                <div className="health-bar">
                  <div
                    className="health-fill cpu"
                    style={{ width: `${systemHealth.cpu_usage}%` }}
                  ></div>
                </div>
              </div>
              <div className="health-item">
                <div className="health-label">Memory</div>
                <div className={`health-value ${getResourceStatus(systemHealth.memory_usage)}`}>
                  {systemHealth.memory_usage.toFixed(1)}%
                </div>
                <div className="health-bar">
                  <div
                    className="health-fill memory"
                    style={{ width: `${systemHealth.memory_usage}%` }}
                  ></div>
                </div>
              </div>
              <div className="health-item">
                <div className="health-label">Disk</div>
                <div className={`health-value ${getResourceStatus(systemHealth.disk_usage)}`}>
                  {systemHealth.disk_usage.toFixed(1)}%
                </div>
                <div className="health-bar">
                  <div
                    className="health-fill disk"
                    style={{ width: `${systemHealth.disk_usage}%` }}
                  ></div>
                </div>
              </div>
              <div className="health-item">
                <div className="health-label">Temperature</div>
                <div className={`health-value ${
                  systemHealth.temperature > 80 ? 'critical' : 
                  systemHealth.temperature > 70 ? 'warning' : 'good'
                }`}>
                  {systemHealth.temperature}°C
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Hardware Information */}
        <div className="hardware-section">
          <h4 className="section-title">Hardware</h4>
          <div className="hardware-grid">
            <div className="hardware-item">
              <div className="hardware-label">CPU Cores</div>
              <div className="hardware-value">{nodeUser.hardware_info.cpu_cores}</div>
            </div>
            <div className="hardware-item">
              <div className="hardware-label">Memory</div>
              <div className="hardware-value">{nodeUser.hardware_info.memory_gb} GB</div>
            </div>
            <div className="hardware-item">
              <div className="hardware-label">Disk</div>
              <div className="hardware-value">{nodeUser.hardware_info.disk_gb} GB</div>
            </div>
            <div className="hardware-item">
              <div className="hardware-label">Network</div>
              <div className="hardware-value">{nodeUser.hardware_info.network_speed_mbps} Mbps</div>
            </div>
          </div>
        </div>

        {/* Performance Metrics */}
        <div className="performance-section">
          <h4 className="section-title">Performance</h4>
          <div className="performance-grid">
            <div className="performance-item">
              <div className="performance-label">Uptime</div>
              <div className="performance-value">
                {nodeUser.uptime_percentage.toFixed(1)}%
              </div>
            </div>
            <div className="performance-item">
              <div className="performance-label">PoOT Score</div>
              <div className="performance-value">
                {nodeUser.poot_score.toFixed(2)}
              </div>
            </div>
            <div className="performance-item">
              <div className="performance-label">Total Earnings</div>
              <div className="performance-value">
                ${nodeUser.total_earnings.toFixed(2)}
              </div>
            </div>
            <div className="performance-item">
              <div className="performance-label">Last Activity</div>
              <div className="performance-value">
                {formatDate(nodeUser.last_activity)}
              </div>
            </div>
          </div>
        </div>

        {/* Expandable Details */}
        <div className="details-section">
          <button
            className="expand-button"
            onClick={() => setIsExpanded(!isExpanded)}
          >
            <span>{isExpanded ? '▼' : '▶'}</span>
            {isExpanded ? 'Hide Details' : 'Show Details'}
          </button>

          {isExpanded && (
            <div className="expanded-details">
              <div className="detail-grid">
                <div className="detail-item">
                  <span className="detail-label">Created:</span>
                  <span className="detail-value">{formatDate(nodeUser.created_at)}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Timezone:</span>
                  <span className="detail-value">{nodeUser.location.timezone}</span>
                </div>
                {systemHealth && (
                  <>
                    <div className="detail-item">
                      <span className="detail-label">System Uptime:</span>
                      <span className="detail-value">{formatUptime(systemHealth.uptime)}</span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">Network Bandwidth:</span>
                      <span className="detail-value">
                        {formatBytes(systemHealth.network_bandwidth)}/s
                      </span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">Last Health Check:</span>
                      <span className="detail-value">{formatDate(systemHealth.last_health_check)}</span>
                    </div>
                  </>
                )}
                <div className="detail-item">
                  <span className="detail-label">Last Update:</span>
                  <span className="detail-value">{lastUpdate.toLocaleTimeString()}</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Quick Actions */}
        <div className="quick-actions">
          <button
            onClick={() => onAction('restart')}
            className="action-btn restart"
            title="Restart Node"
          >
            🔄 Restart
          </button>
          <button
            onClick={() => onAction('maintenance')}
            className="action-btn maintenance"
            title="Enter Maintenance Mode"
          >
            🔧 Maintenance
          </button>
          <button
            onClick={() => onAction('update')}
            className="action-btn update"
            title="Check for Updates"
          >
            📦 Update
          </button>
        </div>
      </div>
    </div>
  );
};

export { NodeStatusCard };
