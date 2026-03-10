import React, { useState, useEffect } from 'react';
import { NodeStatusCard } from '../components/NodeStatusCard';
import { ResourceChart } from '../components/ResourceChart';
import { EarningsCard } from '../components/EarningsCard';
import { PoolInfoCard } from '../components/PoolInfoCard';
import { PoOTScoreCard } from '../components/PoOTScoreCard';

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

interface NodeMetrics {
  sessions_processed: number;
  data_processed: number;
  average_response_time: number;
  error_rate: number;
  network_latency: number;
}

interface RecentActivity {
  id: string;
  type: 'session' | 'maintenance' | 'earnings' | 'system';
  description: string;
  timestamp: string;
  status: 'success' | 'warning' | 'error';
}

interface NodeDashboardPageProps {
  nodeUser: NodeUser | null;
  systemHealth: SystemHealth | null;
  onRouteChange: (route: string) => void;
  onNotification: (type: 'info' | 'warning' | 'error' | 'success', message: string) => void;
}

const NodeDashboardPage: React.FC<NodeDashboardPageProps> = ({
  nodeUser,
  systemHealth,
  onRouteChange,
  onNotification
}) => {
  const [metrics, setMetrics] = useState<NodeMetrics | null>(null);
  const [recentActivity, setRecentActivity] = useState<RecentActivity[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Load node metrics
      const metricsResponse = await fetch('/api/node/metrics');
      if (metricsResponse.ok) {
        const metricsData = await metricsResponse.json();
        setMetrics(metricsData);
      }

      // Load recent activity
      const activityResponse = await fetch('/api/node/activity');
      if (activityResponse.ok) {
        const activityData = await activityResponse.json();
        setRecentActivity(activityData);
      }

      onNotification('success', 'Dashboard data loaded successfully');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load dashboard data';
      setError(errorMessage);
      onNotification('error', errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRefresh = () => {
    loadDashboardData();
  };

  const handleNodeAction = async (action: string) => {
    try {
      let endpoint = '';
      let successMessage = '';

      switch (action) {
        case 'restart':
          endpoint = '/api/node/restart';
          successMessage = 'Node restart initiated';
          break;
        case 'maintenance':
          endpoint = '/api/node/maintenance';
          successMessage = 'Maintenance mode activated';
          break;
        case 'update':
          endpoint = '/api/node/update';
          successMessage = 'Node update initiated';
          break;
        default:
          throw new Error('Unknown action');
      }

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        onNotification('success', successMessage);
        // Refresh data after action
        setTimeout(loadDashboardData, 1000);
      } else {
        throw new Error('Action failed');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Action failed';
      onNotification('error', errorMessage);
    }
  };

  if (isLoading) {
    return (
      <div className="node-dashboard">
        <div className="node-loading">
          <div className="spinner"></div>
          <span>Loading dashboard...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="node-dashboard">
        <div className="node-error">
          <h3>Dashboard Error</h3>
          <p>{error}</p>
          <button onClick={handleRefresh} className="node-action-btn">
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="node-dashboard">
      {/* Dashboard Header */}
      <div className="dashboard-header">
        <div>
          <h1 className="dashboard-title">Node Dashboard</h1>
          <p className="dashboard-subtitle">
            Welcome back, {nodeUser?.operator_id || 'Node Operator'}
          </p>
        </div>
        <div className="dashboard-actions">
          <button
            onClick={handleRefresh}
            className="node-action-btn"
            title="Refresh Data"
          >
            🔄 Refresh
          </button>
        </div>
      </div>

      {/* Node Status Overview */}
      <div className="node-status-grid">
        <NodeStatusCard
          nodeUser={nodeUser}
          systemHealth={systemHealth}
          onAction={handleNodeAction}
        />
        
        <PoOTScoreCard
          pootScore={nodeUser?.poot_score || 0}
          uptime={nodeUser?.uptime_percentage || 0}
          lastActivity={nodeUser?.last_activity || ''}
        />
      </div>

      {/* Key Metrics */}
      <div className="node-metrics">
        <div className="metric-item">
          <div className="metric-value">{metrics?.sessions_processed || 0}</div>
          <div className="metric-label">Sessions Processed</div>
        </div>
        <div className="metric-item">
          <div className="metric-value">
            {metrics?.data_processed ? (metrics.data_processed / 1024 / 1024 / 1024).toFixed(2) + ' GB' : '0 GB'}
          </div>
          <div className="metric-label">Data Processed</div>
        </div>
        <div className="metric-item">
          <div className="metric-value">{metrics?.average_response_time || 0}ms</div>
          <div className="metric-label">Avg Response Time</div>
        </div>
        <div className="metric-item">
          <div className="metric-value">
            {metrics?.error_rate ? (metrics.error_rate * 100).toFixed(2) + '%' : '0%'}
          </div>
          <div className="metric-label">Error Rate</div>
        </div>
      </div>

      {/* Resource and Earnings Overview */}
      <div className="dashboard-grid">
        <div className="dashboard-section">
          <ResourceChart
            systemHealth={systemHealth}
            onViewDetails={() => onRouteChange('resources')}
          />
        </div>
        <div className="dashboard-section">
          <EarningsCard
            totalEarnings={nodeUser?.total_earnings || 0}
            onViewDetails={() => onRouteChange('earnings')}
          />
        </div>
      </div>

      {/* Pool Information */}
      {nodeUser?.pool_id && (
        <div className="dashboard-section">
          <PoolInfoCard
            poolId={nodeUser.pool_id}
            onViewDetails={() => onRouteChange('pool')}
          />
        </div>
      )}

      {/* Recent Activity */}
      <div className="recent-activity">
        <h3>Recent Activity</h3>
        <div className="activity-list">
          {recentActivity.length > 0 ? (
            recentActivity.map((activity) => (
              <div key={activity.id} className="activity-item">
                <div className="activity-icon">
                  {activity.type === 'session' && '📊'}
                  {activity.type === 'maintenance' && '🔧'}
                  {activity.type === 'earnings' && '💰'}
                  {activity.type === 'system' && '⚙️'}
                </div>
                <div className="activity-content">
                  <div className="activity-description">{activity.description}</div>
                  <div className="activity-timestamp">
                    {new Date(activity.timestamp).toLocaleString()}
                  </div>
                </div>
                <div className={`activity-status ${activity.status}`}>
                  {activity.status}
                </div>
              </div>
            ))
          ) : (
            <div className="no-activity">
              <p>No recent activity to display</p>
            </div>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="node-actions">
        <button
          onClick={() => handleNodeAction('restart')}
          className="node-action-btn warning"
          title="Restart Node"
        >
          🔄 Restart Node
        </button>
        <button
          onClick={() => handleNodeAction('maintenance')}
          className="node-action-btn"
          title="Enter Maintenance Mode"
        >
          🔧 Maintenance Mode
        </button>
        <button
          onClick={() => handleNodeAction('update')}
          className="node-action-btn"
          title="Check for Updates"
        >
          📦 Check Updates
        </button>
        <button
          onClick={() => onRouteChange('configuration')}
          className="node-action-btn"
          title="Node Configuration"
        >
          ⚙️ Configuration
        </button>
      </div>
    </div>
  );
};

export default NodeDashboardPage;
