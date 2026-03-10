import React, { useState, useEffect } from 'react';
import { PoolInfoCard } from '../components/PoolInfoCard';

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

interface PoolNode {
  node_id: string;
  operator_id: string;
  status: 'active' | 'inactive' | 'maintenance';
  poot_score: number;
  uptime_percentage: number;
  last_activity: string;
  contribution_percentage: number;
}

interface PoolStats {
  total_sessions_processed: number;
  total_data_processed: number;
  average_response_time: number;
  success_rate: number;
  total_earnings: number;
  pool_share_percentage: number;
}

interface PoolLeaderboard {
  rank: number;
  node_id: string;
  operator_id: string;
  poot_score: number;
  contribution_percentage: number;
  uptime_percentage: number;
}

interface PoolPageProps {
  nodeUser: any;
  systemHealth: any;
  onRouteChange: (route: string) => void;
  onNotification: (type: 'info' | 'warning' | 'error' | 'success', message: string) => void;
}

const PoolPage: React.FC<PoolPageProps> = ({
  nodeUser,
  systemHealth,
  onRouteChange,
  onNotification
}) => {
  const [poolInfo, setPoolInfo] = useState<PoolInfo | null>(null);
  const [poolNodes, setPoolNodes] = useState<PoolNode[]>([]);
  const [poolStats, setPoolStats] = useState<PoolStats | null>(null);
  const [leaderboard, setLeaderboard] = useState<PoolLeaderboard[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'nodes' | 'leaderboard' | 'join'>('overview');
  const [availablePools, setAvailablePools] = useState<PoolInfo[]>([]);

  useEffect(() => {
    if (nodeUser?.pool_id) {
      loadPoolData();
    } else {
      loadAvailablePools();
      setActiveTab('join');
    }
  }, [nodeUser?.pool_id]);

  const loadPoolData = async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Load pool information
      const poolResponse = await fetch(`/api/node/pool/${nodeUser.pool_id}`);
      if (poolResponse.ok) {
        const poolData = await poolResponse.json();
        setPoolInfo(poolData.info);
        setPoolNodes(poolData.nodes);
        setPoolStats(poolData.stats);
        setLeaderboard(poolData.leaderboard);
      }

      onNotification('success', 'Pool data loaded successfully');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load pool data';
      setError(errorMessage);
      onNotification('error', errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const loadAvailablePools = async () => {
    try {
      const response = await fetch('/api/node/pools/available');
      if (response.ok) {
        const data = await response.json();
        setAvailablePools(data);
      }
    } catch (err) {
      console.error('Failed to load available pools:', err);
    }
  };

  const handleJoinPool = async (poolId: string) => {
    try {
      const response = await fetch(`/api/node/pool/${poolId}/join`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        onNotification('success', 'Successfully joined the pool');
        // Refresh node user data
        window.location.reload();
      } else {
        throw new Error('Failed to join pool');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to join pool';
      onNotification('error', errorMessage);
    }
  };

  const handleLeavePool = async () => {
    try {
      const response = await fetch(`/api/node/pool/${nodeUser.pool_id}/leave`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        onNotification('success', 'Successfully left the pool');
        // Refresh node user data
        window.location.reload();
      } else {
        throw new Error('Failed to leave pool');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to leave pool';
      onNotification('error', errorMessage);
    }
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const formatPercentage = (value: number): string => {
    return `${value.toFixed(2)}%`;
  };

  const getStatusColor = (status: string): string => {
    const colors: Record<string, string> = {
      active: '#27ae60',
      inactive: '#95a5a6',
      maintenance: '#f39c12',
    };
    return colors[status] || '#95a5a6';
  };

  const getRankIcon = (rank: number): string => {
    if (rank === 1) return '🥇';
    if (rank === 2) return '🥈';
    if (rank === 3) return '🥉';
    return `#${rank}`;
  };

  if (isLoading) {
    return (
      <div className="pool-page">
        <div className="node-loading">
          <div className="spinner"></div>
          <span>Loading pool data...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="pool-page">
        <div className="node-error">
          <h3>Pool Error</h3>
          <p>{error}</p>
          <button onClick={loadPoolData} className="node-action-btn">
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="pool-page">
      {/* Page Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Pool Management</h1>
          <p className="page-subtitle">
            {nodeUser?.pool_id ? 'Manage your pool participation' : 'Join a pool to increase your earnings'}
          </p>
        </div>
        <div className="page-actions">
          <button
            onClick={nodeUser?.pool_id ? loadPoolData : loadAvailablePools}
            className="node-action-btn"
            title="Refresh Data"
          >
            🔄 Refresh
          </button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="pool-tabs">
        {nodeUser?.pool_id ? (
          <>
            <button
              className={`tab-button ${activeTab === 'overview' ? 'active' : ''}`}
              onClick={() => setActiveTab('overview')}
            >
              Pool Overview
            </button>
            <button
              className={`tab-button ${activeTab === 'nodes' ? 'active' : ''}`}
              onClick={() => setActiveTab('nodes')}
            >
              Pool Nodes
            </button>
            <button
              className={`tab-button ${activeTab === 'leaderboard' ? 'active' : ''}`}
              onClick={() => setActiveTab('leaderboard')}
            >
              Leaderboard
            </button>
          </>
        ) : (
          <button
            className={`tab-button ${activeTab === 'join' ? 'active' : ''}`}
            onClick={() => setActiveTab('join')}
          >
            Join Pool
          </button>
        )}
      </div>

      {/* Tab Content */}
      <div className="tab-content">
        {activeTab === 'overview' && poolInfo && (
          <div className="pool-overview">
            {/* Pool Information Card */}
            <PoolInfoCard
              poolId={poolInfo.pool_id}
              onViewDetails={() => setActiveTab('nodes')}
            />

            {/* Pool Statistics */}
            {poolStats && (
              <div className="pool-stats">
                <h3>Pool Statistics</h3>
                <div className="stats-grid">
                  <div className="stat-item">
                    <div className="stat-label">Total Sessions</div>
                    <div className="stat-value">{poolStats.total_sessions_processed.toLocaleString()}</div>
                  </div>
                  <div className="stat-item">
                    <div className="stat-label">Data Processed</div>
                    <div className="stat-value">
                      {(poolStats.total_data_processed / 1024 / 1024 / 1024).toFixed(2)} GB
                    </div>
                  </div>
                  <div className="stat-item">
                    <div className="stat-label">Avg Response Time</div>
                    <div className="stat-value">{poolStats.average_response_time}ms</div>
                  </div>
                  <div className="stat-item">
                    <div className="stat-label">Success Rate</div>
                    <div className="stat-value">{formatPercentage(poolStats.success_rate)}</div>
                  </div>
                  <div className="stat-item">
                    <div className="stat-label">Total Earnings</div>
                    <div className="stat-value">
                      ${poolStats.total_earnings.toFixed(2)}
                    </div>
                  </div>
                  <div className="stat-item">
                    <div className="stat-label">Pool Share</div>
                    <div className="stat-value">{formatPercentage(poolStats.pool_share_percentage)}</div>
                  </div>
                </div>
              </div>
            )}

            {/* Pool Actions */}
            <div className="pool-actions">
              <button
                onClick={() => setActiveTab('nodes')}
                className="node-action-btn"
                title="View Pool Nodes"
              >
                👥 View Nodes
              </button>
              <button
                onClick={() => setActiveTab('leaderboard')}
                className="node-action-btn"
                title="View Leaderboard"
              >
                🏆 Leaderboard
              </button>
              <button
                onClick={handleLeavePool}
                className="node-action-btn danger"
                title="Leave Pool"
              >
                🚪 Leave Pool
              </button>
            </div>
          </div>
        )}

        {activeTab === 'nodes' && (
          <div className="pool-nodes">
            <h3>Pool Nodes</h3>
            <div className="nodes-table">
              <div className="table-header">
                <div className="table-cell">Node ID</div>
                <div className="table-cell">Operator</div>
                <div className="table-cell">Status</div>
                <div className="table-cell">PoOT Score</div>
                <div className="table-cell">Uptime</div>
                <div className="table-cell">Contribution</div>
                <div className="table-cell">Last Activity</div>
              </div>
              {poolNodes.length > 0 ? (
                poolNodes.map((node) => (
                  <div key={node.node_id} className="table-row">
                    <div className="table-cell">
                      <span className="node-id">
                        {node.node_id.substring(0, 8)}...
                      </span>
                    </div>
                    <div className="table-cell">{node.operator_id}</div>
                    <div className="table-cell">
                      <span
                        className="status-badge"
                        style={{ color: getStatusColor(node.status) }}
                      >
                        {node.status}
                      </span>
                    </div>
                    <div className="table-cell">
                      <span className="poot-score">{node.poot_score.toFixed(2)}</span>
                    </div>
                    <div className="table-cell">
                      {formatPercentage(node.uptime_percentage)}
                    </div>
                    <div className="table-cell">
                      {formatPercentage(node.contribution_percentage)}
                    </div>
                    <div className="table-cell">
                      {formatDate(node.last_activity)}
                    </div>
                  </div>
                ))
              ) : (
                <div className="no-data">
                  <p>No nodes found in this pool.</p>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'leaderboard' && (
          <div className="pool-leaderboard">
            <h3>Pool Leaderboard</h3>
            <div className="leaderboard-table">
              <div className="table-header">
                <div className="table-cell">Rank</div>
                <div className="table-cell">Node ID</div>
                <div className="table-cell">Operator</div>
                <div className="table-cell">PoOT Score</div>
                <div className="table-cell">Contribution</div>
                <div className="table-cell">Uptime</div>
              </div>
              {leaderboard.length > 0 ? (
                leaderboard.map((entry) => (
                  <div key={entry.node_id} className="table-row">
                    <div className="table-cell">
                      <span className="rank">
                        {getRankIcon(entry.rank)}
                      </span>
                    </div>
                    <div className="table-cell">
                      <span className="node-id">
                        {entry.node_id.substring(0, 8)}...
                      </span>
                    </div>
                    <div className="table-cell">{entry.operator_id}</div>
                    <div className="table-cell">
                      <span className="poot-score">{entry.poot_score.toFixed(2)}</span>
                    </div>
                    <div className="table-cell">
                      {formatPercentage(entry.contribution_percentage)}
                    </div>
                    <div className="table-cell">
                      {formatPercentage(entry.uptime_percentage)}
                    </div>
                  </div>
                ))
              ) : (
                <div className="no-data">
                  <p>No leaderboard data available.</p>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'join' && (
          <div className="join-pool">
            <h3>Join a Pool</h3>
            <p className="join-description">
              Joining a pool can increase your earnings by combining resources with other nodes.
              Choose a pool that matches your node's capabilities and goals.
            </p>
            
            <div className="available-pools">
              {availablePools.length > 0 ? (
                availablePools.map((pool) => (
                  <div key={pool.pool_id} className="pool-card">
                    <div className="pool-card-header">
                      <h4>{pool.name}</h4>
                      <span
                        className="pool-status"
                        style={{ color: getStatusColor(pool.status) }}
                      >
                        {pool.status}
                      </span>
                    </div>
                    <div className="pool-card-body">
                      <p className="pool-description">{pool.description}</p>
                      <div className="pool-stats">
                        <div className="pool-stat">
                          <span className="stat-label">Nodes:</span>
                          <span className="stat-value">{pool.active_nodes}/{pool.total_nodes}</span>
                        </div>
                        <div className="pool-stat">
                          <span className="stat-label">Avg PoOT Score:</span>
                          <span className="stat-value">{pool.average_poot_score.toFixed(2)}</span>
                        </div>
                        <div className="pool-stat">
                          <span className="stat-label">Performance:</span>
                          <span className="stat-value">{formatPercentage(pool.pool_performance)}</span>
                        </div>
                      </div>
                      <button
                        onClick={() => handleJoinPool(pool.pool_id)}
                        className="node-action-btn"
                        disabled={pool.status !== 'active'}
                        title="Join Pool"
                      >
                        Join Pool
                      </button>
                    </div>
                  </div>
                ))
              ) : (
                <div className="no-data">
                  <p>No available pools found.</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default PoolPage;
