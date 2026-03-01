import React, { useState, useEffect } from 'react';

// Types
interface PoolInfo {
  pool_id: string;
  name: string;
  description: string;
  operator_id: string;
  total_nodes: number;
  active_nodes: number;
  total_poot_score: number;
  average_poot_score: number;
  pool_performance: number;
  created_at: string;
  status: 'active' | 'inactive' | 'maintenance';
}

interface PoolStats {
  total_sessions_processed: number;
  total_data_processed: number;
  average_response_time: number;
  success_rate: number;
  total_earnings: number;
  pool_share_percentage: number;
}

interface PoolInfoCardProps {
  poolId: string;
  onViewDetails?: () => void;
  className?: string;
}

const PoolInfoCard: React.FC<PoolInfoCardProps> = ({
  poolId,
  onViewDetails,
  className = ''
}) => {
  const [poolInfo, setPoolInfo] = useState<PoolInfo | null>(null);
  const [poolStats, setPoolStats] = useState<PoolStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (poolId) {
      loadPoolInfo();
    }
  }, [poolId]);

  const loadPoolInfo = async () => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await fetch(`/api/node/pool/${poolId}`);
      if (response.ok) {
        const data = await response.json();
        setPoolInfo(data.info);
        setPoolStats(data.stats);
      } else {
        throw new Error('Failed to load pool information');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load pool information');
    } finally {
      setIsLoading(false);
    }
  };

  const getStatusColor = (status: string): string => {
    const colors: Record<string, string> = {
      active: '#27ae60',
      inactive: '#95a5a6',
      maintenance: '#f39c12',
    };
    return colors[status] || '#95a5a6';
  };

  const getStatusIcon = (status: string): string => {
    const icons: Record<string, string> = {
      active: '🟢',
      inactive: '⚫',
      maintenance: '🟡',
    };
    return icons[status] || '⚪';
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
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

  const formatNumber = (num: number): string => {
    if (num >= 1000000) {
      return `${(num / 1000000).toFixed(1)}M`;
    } else if (num >= 1000) {
      return `${(num / 1000).toFixed(1)}K`;
    }
    return num.toString();
  };

  const getPerformanceColor = (performance: number): string => {
    if (performance >= 80) return '#27ae60';
    if (performance >= 60) return '#f39c12';
    return '#e74c3c';
  };

  const getNodeHealthPercentage = (): number => {
    if (!poolInfo) return 0;
    return (poolInfo.active_nodes / poolInfo.total_nodes) * 100;
  };

  if (isLoading) {
    return (
      <div className={`pool-info-card ${className}`}>
        <div className="card-header">
          <h3 className="card-title">Pool Information</h3>
        </div>
        <div className="card-body">
          <div className="loading-state">
            <div className="spinner"></div>
            <span>Loading pool information...</span>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`pool-info-card ${className}`}>
        <div className="card-header">
          <h3 className="card-title">Pool Information</h3>
        </div>
        <div className="card-body">
          <div className="error-state">
            <span className="error-icon">❌</span>
            <span className="error-message">{error}</span>
            <button onClick={loadPoolInfo} className="retry-btn">
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!poolInfo) {
    return (
      <div className={`pool-info-card ${className}`}>
        <div className="card-header">
          <h3 className="card-title">Pool Information</h3>
        </div>
        <div className="card-body">
          <div className="no-data">
            <p>No pool information available</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`pool-info-card ${className}`}>
      <div className="card-header">
        <h3 className="card-title">Pool Information</h3>
        <div className="pool-status">
          <span className="status-icon">{getStatusIcon(poolInfo.status)}</span>
          <span
            className="status-text"
            style={{ color: getStatusColor(poolInfo.status) }}
          >
            {poolInfo.status.toUpperCase()}
          </span>
        </div>
      </div>

      <div className="card-body">
        {/* Pool Basic Information */}
        <div className="pool-basic-info">
          <div className="pool-name">{poolInfo.name}</div>
          <div className="pool-description">{poolInfo.description}</div>
          <div className="pool-operator">
            <span className="operator-label">Operator:</span>
            <span className="operator-value">{poolInfo.operator_id}</span>
          </div>
          <div className="pool-created">
            <span className="created-label">Created:</span>
            <span className="created-value">{formatDate(poolInfo.created_at)}</span>
          </div>
        </div>

        {/* Pool Statistics */}
        <div className="pool-statistics">
          <div className="stats-grid">
            <div className="stat-item">
              <div className="stat-icon">👥</div>
              <div className="stat-content">
                <div className="stat-label">Total Nodes</div>
                <div className="stat-value">{poolInfo.total_nodes}</div>
              </div>
            </div>
            <div className="stat-item">
              <div className="stat-icon">🟢</div>
              <div className="stat-content">
                <div className="stat-label">Active Nodes</div>
                <div className="stat-value">{poolInfo.active_nodes}</div>
              </div>
            </div>
            <div className="stat-item">
              <div className="stat-icon">📊</div>
              <div className="stat-content">
                <div className="stat-label">Total PoOT Score</div>
                <div className="stat-value">{formatNumber(poolInfo.total_poot_score)}</div>
              </div>
            </div>
            <div className="stat-item">
              <div className="stat-icon">⚡</div>
              <div className="stat-content">
                <div className="stat-label">Avg PoOT Score</div>
                <div className="stat-value">{poolInfo.average_poot_score.toFixed(2)}</div>
              </div>
            </div>
          </div>
        </div>

        {/* Pool Performance */}
        <div className="pool-performance">
          <div className="performance-header">
            <span className="performance-label">Pool Performance</span>
            <span
              className="performance-value"
              style={{ color: getPerformanceColor(poolInfo.pool_performance) }}
            >
              {poolInfo.pool_performance.toFixed(1)}%
            </span>
          </div>
          <div className="performance-bar">
            <div
              className="performance-fill"
              style={{
                width: `${poolInfo.pool_performance}%`,
                backgroundColor: getPerformanceColor(poolInfo.pool_performance),
              }}
            ></div>
          </div>
        </div>

        {/* Node Health */}
        <div className="node-health">
          <div className="health-header">
            <span className="health-label">Node Health</span>
            <span className="health-value">
              {getNodeHealthPercentage().toFixed(1)}%
            </span>
          </div>
          <div className="health-bar">
            <div
              className="health-fill"
              style={{
                width: `${getNodeHealthPercentage()}%`,
                backgroundColor: getNodeHealthPercentage() >= 80 ? '#27ae60' : 
                                getNodeHealthPercentage() >= 60 ? '#f39c12' : '#e74c3c',
              }}
            ></div>
          </div>
          <div className="health-details">
            <span className="health-text">
              {poolInfo.active_nodes} of {poolInfo.total_nodes} nodes active
            </span>
          </div>
        </div>

        {/* Pool Activity Stats */}
        {poolStats && (
          <div className="pool-activity">
            <h4 className="activity-title">Pool Activity</h4>
            <div className="activity-grid">
              <div className="activity-item">
                <div className="activity-label">Sessions Processed</div>
                <div className="activity-value">{formatNumber(poolStats.total_sessions_processed)}</div>
              </div>
              <div className="activity-item">
                <div className="activity-label">Data Processed</div>
                <div className="activity-value">{formatBytes(poolStats.total_data_processed)}</div>
              </div>
              <div className="activity-item">
                <div className="activity-label">Avg Response Time</div>
                <div className="activity-value">{poolStats.average_response_time}ms</div>
              </div>
              <div className="activity-item">
                <div className="activity-label">Success Rate</div>
                <div className="activity-value">{poolStats.success_rate.toFixed(1)}%</div>
              </div>
              <div className="activity-item">
                <div className="activity-label">Total Earnings</div>
                <div className="activity-value">${poolStats.total_earnings.toFixed(2)}</div>
              </div>
              <div className="activity-item">
                <div className="activity-label">Pool Share</div>
                <div className="activity-value">{poolStats.pool_share_percentage.toFixed(1)}%</div>
              </div>
            </div>
          </div>
        )}

        {/* Pool Benefits */}
        <div className="pool-benefits">
          <h4 className="benefits-title">Pool Benefits</h4>
          <div className="benefits-list">
            <div className="benefit-item">
              <span className="benefit-icon">🤝</span>
              <span className="benefit-text">Shared resources and increased reliability</span>
            </div>
            <div className="benefit-item">
              <span className="benefit-icon">📈</span>
              <span className="benefit-text">Higher earnings through collective performance</span>
            </div>
            <div className="benefit-item">
              <span className="benefit-icon">🛡️</span>
              <span className="benefit-text">Reduced risk through distributed load</span>
            </div>
            <div className="benefit-item">
              <span className="benefit-icon">⚡</span>
              <span className="benefit-text">Improved response times and efficiency</span>
            </div>
          </div>
        </div>

        {/* Action Button */}
        {onViewDetails && (
          <div className="card-actions">
            <button
              onClick={onViewDetails}
              className="node-action-btn"
              title="View Detailed Pool Information"
            >
              👥 View Pool Details
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export { PoolInfoCard };
