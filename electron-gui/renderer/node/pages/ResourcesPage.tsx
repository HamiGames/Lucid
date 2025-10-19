import React, { useState, useEffect } from 'react';
import { ResourceChart } from '../components/ResourceChart';

// Types
interface ResourceData {
  cpu: {
    usage: number;
    cores: number;
    temperature: number;
    load_average: number[];
  };
  memory: {
    total: number;
    used: number;
    free: number;
    cached: number;
    swap_total: number;
    swap_used: number;
  };
  disk: {
    total: number;
    used: number;
    free: number;
    read_speed: number;
    write_speed: number;
    io_wait: number;
  };
  network: {
    bandwidth: number;
    latency: number;
    packets_sent: number;
    packets_received: number;
    bytes_sent: number;
    bytes_received: number;
  };
}

interface ResourceMetrics {
  timestamp: string;
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  network_bandwidth: number;
  temperature: number;
}

interface ResourcesPageProps {
  nodeUser: any;
  systemHealth: any;
  onRouteChange: (route: string) => void;
  onNotification: (type: 'info' | 'warning' | 'error' | 'success', message: string) => void;
}

const ResourcesPage: React.FC<ResourcesPageProps> = ({
  nodeUser,
  systemHealth,
  onRouteChange,
  onNotification
}) => {
  const [resourceData, setResourceData] = useState<ResourceData | null>(null);
  const [metricsHistory, setMetricsHistory] = useState<ResourceMetrics[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshInterval, setRefreshInterval] = useState<number | null>(null);
  const [timeRange, setTimeRange] = useState<'1h' | '6h' | '24h' | '7d'>('1h');

  useEffect(() => {
    loadResourceData();
    startAutoRefresh();

    return () => {
      if (refreshInterval) {
        clearInterval(refreshInterval);
      }
    };
  }, []);

  const loadResourceData = async () => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await fetch(`/api/node/resources?timeRange=${timeRange}`);
      if (response.ok) {
        const data = await response.json();
        setResourceData(data.current);
        setMetricsHistory(data.history);
        onNotification('success', 'Resource data updated');
      } else {
        throw new Error('Failed to load resource data');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load resource data';
      setError(errorMessage);
      onNotification('error', errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const startAutoRefresh = () => {
    const interval = setInterval(loadResourceData, 30000); // Refresh every 30 seconds
    setRefreshInterval(interval);
  };

  const stopAutoRefresh = () => {
    if (refreshInterval) {
      clearInterval(refreshInterval);
      setRefreshInterval(null);
    }
  };

  const handleTimeRangeChange = (newTimeRange: '1h' | '6h' | '24h' | '7d') => {
    setTimeRange(newTimeRange);
    loadResourceData();
  };

  const formatBytes = (bytes: number): string => {
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let size = bytes;
    let unitIndex = 0;

    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }

    return `${size.toFixed(2)} ${units[unitIndex]}`;
  };

  const formatPercentage = (value: number): string => {
    return `${value.toFixed(1)}%`;
  };

  const getResourceStatus = (usage: number): 'good' | 'warning' | 'critical' => {
    if (usage < 70) return 'good';
    if (usage < 90) return 'warning';
    return 'critical';
  };

  if (isLoading && !resourceData) {
    return (
      <div className="resources-page">
        <div className="node-loading">
          <div className="spinner"></div>
          <span>Loading resource data...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="resources-page">
        <div className="node-error">
          <h3>Resource Monitoring Error</h3>
          <p>{error}</p>
          <button onClick={loadResourceData} className="node-action-btn">
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="resources-page">
      {/* Page Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Resource Monitoring</h1>
          <p className="page-subtitle">Real-time monitoring of node resources</p>
        </div>
        <div className="page-actions">
          <select
            value={timeRange}
            onChange={(e) => handleTimeRangeChange(e.target.value as any)}
            className="time-range-select"
          >
            <option value="1h">Last Hour</option>
            <option value="6h">Last 6 Hours</option>
            <option value="24h">Last 24 Hours</option>
            <option value="7d">Last 7 Days</option>
          </select>
          <button
            onClick={refreshInterval ? stopAutoRefresh : startAutoRefresh}
            className={`node-action-btn ${refreshInterval ? 'warning' : ''}`}
            title={refreshInterval ? 'Stop Auto Refresh' : 'Start Auto Refresh'}
          >
            {refreshInterval ? '⏸️ Stop' : '▶️ Start'} Auto Refresh
          </button>
          <button
            onClick={loadResourceData}
            className="node-action-btn"
            title="Refresh Now"
          >
            🔄 Refresh
          </button>
        </div>
      </div>

      {/* Real-time Resource Charts */}
      <div className="resource-charts">
        <ResourceChart
          systemHealth={resourceData}
          onViewDetails={() => {}}
          showDetails={true}
        />
      </div>

      {/* Detailed Resource Information */}
      {resourceData && (
        <div className="resource-details">
          {/* CPU Information */}
          <div className="resource-section">
            <h3>CPU Information</h3>
            <div className="resource-grid">
              <div className="resource-item">
                <div className="resource-label">Usage</div>
                <div className={`resource-value ${getResourceStatus(resourceData.cpu.usage)}`}>
                  {formatPercentage(resourceData.cpu.usage)}
                </div>
                <div className="resource-bar">
                  <div
                    className="resource-fill resource-cpu"
                    style={{ width: `${resourceData.cpu.usage}%` }}
                  ></div>
                </div>
              </div>
              <div className="resource-item">
                <div className="resource-label">Cores</div>
                <div className="resource-value">{resourceData.cpu.cores}</div>
              </div>
              <div className="resource-item">
                <div className="resource-label">Temperature</div>
                <div className={`resource-value ${
                  resourceData.cpu.temperature > 80 ? 'critical' : 
                  resourceData.cpu.temperature > 70 ? 'warning' : 'good'
                }`}>
                  {resourceData.cpu.temperature}°C
                </div>
              </div>
              <div className="resource-item">
                <div className="resource-label">Load Average</div>
                <div className="resource-value">
                  {resourceData.cpu.load_average.map((load, index) => (
                    <span key={index}>{load.toFixed(2)}{index < 2 ? ', ' : ''}</span>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Memory Information */}
          <div className="resource-section">
            <h3>Memory Information</h3>
            <div className="resource-grid">
              <div className="resource-item">
                <div className="resource-label">Total Memory</div>
                <div className="resource-value">{formatBytes(resourceData.memory.total)}</div>
              </div>
              <div className="resource-item">
                <div className="resource-label">Used Memory</div>
                <div className="resource-value">{formatBytes(resourceData.memory.used)}</div>
                <div className="resource-bar">
                  <div
                    className="resource-fill resource-memory"
                    style={{ width: `${(resourceData.memory.used / resourceData.memory.total) * 100}%` }}
                  ></div>
                </div>
              </div>
              <div className="resource-item">
                <div className="resource-label">Free Memory</div>
                <div className="resource-value">{formatBytes(resourceData.memory.free)}</div>
              </div>
              <div className="resource-item">
                <div className="resource-label">Cached</div>
                <div className="resource-value">{formatBytes(resourceData.memory.cached)}</div>
              </div>
              <div className="resource-item">
                <div className="resource-label">Swap Used</div>
                <div className="resource-value">
                  {formatBytes(resourceData.memory.swap_used)} / {formatBytes(resourceData.memory.swap_total)}
                </div>
              </div>
            </div>
          </div>

          {/* Disk Information */}
          <div className="resource-section">
            <h3>Disk Information</h3>
            <div className="resource-grid">
              <div className="resource-item">
                <div className="resource-label">Total Space</div>
                <div className="resource-value">{formatBytes(resourceData.disk.total)}</div>
              </div>
              <div className="resource-item">
                <div className="resource-label">Used Space</div>
                <div className="resource-value">{formatBytes(resourceData.disk.used)}</div>
                <div className="resource-bar">
                  <div
                    className="resource-fill resource-disk"
                    style={{ width: `${(resourceData.disk.used / resourceData.disk.total) * 100}%` }}
                  ></div>
                </div>
              </div>
              <div className="resource-item">
                <div className="resource-label">Free Space</div>
                <div className="resource-value">{formatBytes(resourceData.disk.free)}</div>
              </div>
              <div className="resource-item">
                <div className="resource-label">Read Speed</div>
                <div className="resource-value">{formatBytes(resourceData.disk.read_speed)}/s</div>
              </div>
              <div className="resource-item">
                <div className="resource-label">Write Speed</div>
                <div className="resource-value">{formatBytes(resourceData.disk.write_speed)}/s</div>
              </div>
              <div className="resource-item">
                <div className="resource-label">I/O Wait</div>
                <div className="resource-value">{formatPercentage(resourceData.disk.io_wait)}</div>
              </div>
            </div>
          </div>

          {/* Network Information */}
          <div className="resource-section">
            <h3>Network Information</h3>
            <div className="resource-grid">
              <div className="resource-item">
                <div className="resource-label">Bandwidth Usage</div>
                <div className="resource-value">{formatBytes(resourceData.network.bandwidth)}/s</div>
              </div>
              <div className="resource-item">
                <div className="resource-label">Latency</div>
                <div className="resource-value">{resourceData.network.latency}ms</div>
              </div>
              <div className="resource-item">
                <div className="resource-label">Packets Sent</div>
                <div className="resource-value">{resourceData.network.packets_sent.toLocaleString()}</div>
              </div>
              <div className="resource-item">
                <div className="resource-label">Packets Received</div>
                <div className="resource-value">{resourceData.network.packets_received.toLocaleString()}</div>
              </div>
              <div className="resource-item">
                <div className="resource-label">Bytes Sent</div>
                <div className="resource-value">{formatBytes(resourceData.network.bytes_sent)}</div>
              </div>
              <div className="resource-item">
                <div className="resource-label">Bytes Received</div>
                <div className="resource-value">{formatBytes(resourceData.network.bytes_received)}</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Resource Alerts */}
      <div className="resource-alerts">
        <h3>Resource Alerts</h3>
        <div className="alerts-list">
          {resourceData && (
            <>
              {resourceData.cpu.usage > 90 && (
                <div className="alert-item critical">
                  <span className="alert-icon">⚠️</span>
                  <span className="alert-message">High CPU usage: {formatPercentage(resourceData.cpu.usage)}</span>
                </div>
              )}
              {(resourceData.memory.used / resourceData.memory.total) > 0.9 && (
                <div className="alert-item critical">
                  <span className="alert-icon">⚠️</span>
                  <span className="alert-message">High memory usage: {formatPercentage((resourceData.memory.used / resourceData.memory.total) * 100)}</span>
                </div>
              )}
              {(resourceData.disk.used / resourceData.disk.total) > 0.9 && (
                <div className="alert-item critical">
                  <span className="alert-icon">⚠️</span>
                  <span className="alert-message">Low disk space: {formatPercentage((resourceData.disk.used / resourceData.disk.total) * 100)} used</span>
                </div>
              )}
              {resourceData.cpu.temperature > 80 && (
                <div className="alert-item warning">
                  <span className="alert-icon">🌡️</span>
                  <span className="alert-message">High CPU temperature: {resourceData.cpu.temperature}°C</span>
                </div>
              )}
              {resourceData.network.latency > 100 && (
                <div className="alert-item warning">
                  <span className="alert-icon">📡</span>
                  <span className="alert-message">High network latency: {resourceData.network.latency}ms</span>
                </div>
              )}
            </>
          )}
          {resourceData && (
            resourceData.cpu.usage <= 90 &&
            (resourceData.memory.used / resourceData.memory.total) <= 0.9 &&
            (resourceData.disk.used / resourceData.disk.total) <= 0.9 &&
            resourceData.cpu.temperature <= 80 &&
            resourceData.network.latency <= 100
          ) && (
            <div className="alert-item success">
              <span className="alert-icon">✅</span>
              <span className="alert-message">All resources are operating within normal parameters</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ResourcesPage;
