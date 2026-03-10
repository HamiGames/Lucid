import React, { useState, useEffect } from 'react';
import { MetricChart } from '../components/MetricChart';

interface MetricData {
  id: string;
  name: string;
  value: number;
  unit: string;
  trend: 'up' | 'down' | 'stable';
  change: number;
  timestamp: string;
}

interface ChartData {
  id: string;
  title: string;
  type: 'line' | 'bar' | 'area' | 'pie';
  data: Array<{
    timestamp: string;
    value: number;
    label?: string;
  }>;
  color: string;
  description: string;
}

interface MetricsFilters {
  timeRange: '1h' | '6h' | '24h' | '7d' | '30d';
  category: string;
  refreshInterval: number;
}

const MetricsPage: React.FC = () => {
  const [metrics, setMetrics] = useState<MetricData[]>([]);
  const [charts, setCharts] = useState<ChartData[]>([]);
  const [filters, setFilters] = useState<MetricsFilters>({
    timeRange: '24h',
    category: 'all',
    refreshInterval: 30
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLive, setIsLive] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  useEffect(() => {
    loadMetrics();
    if (isLive) {
      const interval = setInterval(loadMetrics, filters.refreshInterval * 1000);
      return () => clearInterval(interval);
    }
  }, [isLive, filters.refreshInterval]);

  const loadMetrics = async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Load metrics from the system
      const [metricsData, chartsData] = await Promise.all([
        loadMetricsFromSystem(),
        loadChartsFromSystem()
      ]);

      setMetrics(metricsData);
      setCharts(chartsData);
      setLastUpdated(new Date());
    } catch (error) {
      console.error('Failed to load metrics:', error);
      setError('Failed to load metrics');
    } finally {
      setIsLoading(false);
    }
  };

  const loadMetricsFromSystem = async (): Promise<MetricData[]> => {
    // Mock metrics data - in real implementation, these would come from the metrics service
    const mockMetrics: MetricData[] = [
      {
        id: 'cpu-usage',
        name: 'CPU Usage',
        value: 45.2,
        unit: '%',
        trend: 'up',
        change: 2.1,
        timestamp: new Date().toISOString()
      },
      {
        id: 'memory-usage',
        name: 'Memory Usage',
        value: 68.7,
        unit: '%',
        trend: 'stable',
        change: 0.3,
        timestamp: new Date().toISOString()
      },
      {
        id: 'disk-usage',
        name: 'Disk Usage',
        value: 23.4,
        unit: '%',
        trend: 'down',
        change: -1.2,
        timestamp: new Date().toISOString()
      },
      {
        id: 'network-throughput',
        name: 'Network Throughput',
        value: 125.6,
        unit: 'Mbps',
        trend: 'up',
        change: 5.8,
        timestamp: new Date().toISOString()
      },
      {
        id: 'active-sessions',
        name: 'Active Sessions',
        value: 42,
        unit: 'sessions',
        trend: 'up',
        change: 3,
        timestamp: new Date().toISOString()
      },
      {
        id: 'tor-circuits',
        name: 'Tor Circuits',
        value: 8,
        unit: 'circuits',
        trend: 'stable',
        change: 0,
        timestamp: new Date().toISOString()
      }
    ];

    return mockMetrics;
  };

  const loadChartsFromSystem = async (): Promise<ChartData[]> => {
    // Mock charts data
    const now = Date.now();
    const generateDataPoints = (hours: number, interval: number = 5) => {
      const points = [];
      for (let i = hours * 12; i >= 0; i -= interval) {
        points.push({
          timestamp: new Date(now - i * 5 * 60 * 1000).toISOString(),
          value: Math.random() * 100,
          label: new Date(now - i * 5 * 60 * 1000).toLocaleTimeString()
        });
      }
      return points;
    };

    const mockCharts: ChartData[] = [
      {
        id: 'cpu-trend',
        title: 'CPU Usage Trend',
        type: 'line',
        data: generateDataPoints(24),
        color: '#3b82f6',
        description: 'CPU usage over time'
      },
      {
        id: 'memory-trend',
        title: 'Memory Usage Trend',
        type: 'area',
        data: generateDataPoints(24),
        color: '#10b981',
        description: 'Memory usage over time'
      },
      {
        id: 'network-io',
        title: 'Network I/O',
        type: 'bar',
        data: generateDataPoints(24),
        color: '#f59e0b',
        description: 'Network input/output over time'
      },
      {
        id: 'session-distribution',
        title: 'Session Distribution',
        type: 'pie',
        data: [
          { timestamp: new Date().toISOString(), value: 60, label: 'Active' },
          { timestamp: new Date().toISOString(), value: 25, label: 'Idle' },
          { timestamp: new Date().toISOString(), value: 15, label: 'Terminated' }
        ],
        color: '#8b5cf6',
        description: 'Distribution of session states'
      }
    ];

    return mockCharts;
  };

  const handleFilterChange = (key: keyof MetricsFilters, value: any) => {
    setFilters(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const handleExportMetrics = async () => {
    try {
      const metricsData = {
        metrics,
        charts,
        timestamp: new Date().toISOString(),
        filters
      };
      
      const dataStr = JSON.stringify(metricsData, null, 2);
      const blob = new Blob([dataStr], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `metrics-${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to export metrics:', error);
      setError('Failed to export metrics');
    }
  };

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'up': return '📈';
      case 'down': return '📉';
      case 'stable': return '➡️';
      default: return '➡️';
    }
  };

  const getTrendColor = (trend: string) => {
    switch (trend) {
      case 'up': return '#10b981';
      case 'down': return '#ef4444';
      case 'stable': return '#6b7280';
      default: return '#6b7280';
    }
  };

  return (
    <div className="developer-content">
      <div className="developer-card">
        <div className="developer-card-header">
          <div>
            <h2 className="developer-card-title">System Metrics</h2>
            <p className="developer-card-subtitle">
              Real-time system performance metrics and monitoring
            </p>
          </div>
          <div className="developer-card-actions">
            <button 
              className="developer-btn developer-btn-secondary"
              onClick={loadMetrics}
              disabled={isLoading}
            >
              Refresh
            </button>
            <button 
              className="developer-btn developer-btn-secondary"
              onClick={handleExportMetrics}
            >
              Export
            </button>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem', marginBottom: '2rem' }}>
          <div className="developer-form-group">
            <label className="developer-form-label">Time Range</label>
            <select
              className="developer-form-input"
              value={filters.timeRange}
              onChange={(e) => handleFilterChange('timeRange', e.target.value)}
            >
              <option value="1h">Last Hour</option>
              <option value="6h">Last 6 Hours</option>
              <option value="24h">Last 24 Hours</option>
              <option value="7d">Last 7 Days</option>
              <option value="30d">Last 30 Days</option>
            </select>
          </div>

          <div className="developer-form-group">
            <label className="developer-form-label">Category</label>
            <select
              className="developer-form-input"
              value={filters.category}
              onChange={(e) => handleFilterChange('category', e.target.value)}
            >
              <option value="all">All Categories</option>
              <option value="system">System</option>
              <option value="network">Network</option>
              <option value="sessions">Sessions</option>
              <option value="tor">Tor</option>
            </select>
          </div>

          <div className="developer-form-group">
            <label className="developer-form-label">Refresh Interval (seconds)</label>
            <select
              className="developer-form-input"
              value={filters.refreshInterval}
              onChange={(e) => handleFilterChange('refreshInterval', parseInt(e.target.value))}
            >
              <option value="10">10 seconds</option>
              <option value="30">30 seconds</option>
              <option value="60">1 minute</option>
              <option value="300">5 minutes</option>
            </select>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem', alignItems: 'center' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#d1d5db' }}>
            <input
              type="checkbox"
              checked={isLive}
              onChange={(e) => setIsLive(e.target.checked)}
            />
            Live Updates
          </label>
          {lastUpdated && (
            <span style={{ color: '#94a3b8', fontSize: '0.875rem' }}>
              Last updated: {lastUpdated.toLocaleTimeString()}
            </span>
          )}
        </div>

        {isLoading && (
          <div className="developer-loading">
            <div className="developer-loading-spinner"></div>
            <p>Loading metrics...</p>
          </div>
        )}

        {error && (
          <div className="developer-error">
            <div className="developer-error-icon">⚠️</div>
            <div className="developer-error-title">Error</div>
            <div className="developer-error-message">{error}</div>
            <button 
              className="developer-btn developer-btn-primary"
              onClick={loadMetrics}
            >
              Retry
            </button>
          </div>
        )}

        {!isLoading && !error && (
          <>
            {/* Metrics Cards */}
            <div style={{ marginBottom: '2rem' }}>
              <h3 style={{ marginBottom: '1rem', color: '#f8fafc' }}>Current Metrics</h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
                {metrics.map(metric => (
                  <div key={metric.id} className="developer-card" style={{ padding: '1rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                      <span style={{ fontSize: '0.875rem', color: '#94a3b8' }}>{metric.name}</span>
                      <span style={{ fontSize: '0.75rem', color: getTrendColor(metric.trend) }}>
                        {getTrendIcon(metric.trend)} {metric.change > 0 ? '+' : ''}{metric.change}{metric.unit}
                      </span>
                    </div>
                    <div style={{ fontSize: '1.5rem', fontWeight: '600', color: '#f8fafc' }}>
                      {metric.value}{metric.unit}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Charts */}
            <div>
              <h3 style={{ marginBottom: '1rem', color: '#f8fafc' }}>Performance Charts</h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '1.5rem' }}>
                {charts.map(chart => (
                  <div key={chart.id} className="developer-card">
                    <div className="developer-card-header">
                      <div>
                        <h4 className="developer-card-title">{chart.title}</h4>
                        <p className="developer-card-subtitle">{chart.description}</p>
                      </div>
                    </div>
                    <MetricChart
                      data={chart.data}
                      type={chart.type}
                      color={chart.color}
                      height={200}
                    />
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export { MetricsPage };
