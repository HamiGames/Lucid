import React, { useState, useEffect, useRef } from 'react';

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

interface ResourceChartProps {
  systemHealth: ResourceData | null;
  onViewDetails?: () => void;
  showDetails?: boolean;
  className?: string;
}

const ResourceChart: React.FC<ResourceChartProps> = ({
  systemHealth,
  onViewDetails,
  showDetails = false,
  className = ''
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [chartType, setChartType] = useState<'gauge' | 'bar' | 'line'>('gauge');
  const [selectedResource, setSelectedResource] = useState<'cpu' | 'memory' | 'disk' | 'network'>('cpu');
  const [animationFrame, setAnimationFrame] = useState(0);

  useEffect(() => {
    if (canvasRef.current && systemHealth) {
      drawChart();
    }
  }, [systemHealth, chartType, selectedResource, animationFrame]);

  const drawChart = () => {
    const canvas = canvasRef.current;
    if (!canvas || !systemHealth) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const { width, height } = canvas;
    ctx.clearRect(0, 0, width, height);

    switch (chartType) {
      case 'gauge':
        drawGaugeChart(ctx, width, height);
        break;
      case 'bar':
        drawBarChart(ctx, width, height);
        break;
      case 'line':
        drawLineChart(ctx, width, height);
        break;
    }
  };

  const drawGaugeChart = (ctx: CanvasRenderingContext2D, width: number, height: number) => {
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = Math.min(width, height) * 0.3;
    
    // Draw background circle
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI);
    ctx.strokeStyle = '#ecf0f1';
    ctx.lineWidth = 20;
    ctx.stroke();

    // Get current value and color
    const { value, color } = getResourceValue(selectedResource);
    const angle = (value / 100) * 2 * Math.PI;

    // Draw progress arc
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, -Math.PI / 2, -Math.PI / 2 + angle);
    ctx.strokeStyle = color;
    ctx.lineWidth = 20;
    ctx.stroke();

    // Draw center text
    ctx.fillStyle = '#2c3e50';
    ctx.font = 'bold 24px Inter';
    ctx.textAlign = 'center';
    ctx.fillText(`${value.toFixed(1)}%`, centerX, centerY + 8);

    // Draw resource label
    ctx.font = '14px Inter';
    ctx.fillStyle = '#7f8c8d';
    ctx.fillText(selectedResource.toUpperCase(), centerX, centerY + 30);
  };

  const drawBarChart = (ctx: CanvasRenderingContext2D, width: number, height: number) => {
    const resources = ['cpu', 'memory', 'disk', 'network'];
    const barWidth = width / resources.length - 20;
    const maxHeight = height * 0.8;

    resources.forEach((resource, index) => {
      const { value, color } = getResourceValue(resource as any);
      const barHeight = (value / 100) * maxHeight;
      const x = index * (barWidth + 20) + 10;
      const y = height - barHeight - 40;

      // Draw bar
      ctx.fillStyle = color;
      ctx.fillRect(x, y, barWidth, barHeight);

      // Draw value text
      ctx.fillStyle = '#2c3e50';
      ctx.font = '12px Inter';
      ctx.textAlign = 'center';
      ctx.fillText(`${value.toFixed(1)}%`, x + barWidth / 2, y - 5);

      // Draw resource label
      ctx.fillText(resource.toUpperCase(), x + barWidth / 2, height - 20);
    });
  };

  const drawLineChart = (ctx: CanvasRenderingContext2D, width: number, height: number) => {
    // Simulate historical data for line chart
    const dataPoints = 20;
    const { value } = getResourceValue(selectedResource);
    const points: number[] = [];

    // Generate mock historical data
    for (let i = 0; i < dataPoints; i++) {
      const baseValue = value;
      const variation = (Math.random() - 0.5) * 20;
      points.push(Math.max(0, Math.min(100, baseValue + variation)));
    }

    const stepX = width / (dataPoints - 1);
    const maxHeight = height * 0.8;

    // Draw line
    ctx.beginPath();
    ctx.strokeStyle = '#3498db';
    ctx.lineWidth = 3;

    points.forEach((point, index) => {
      const x = index * stepX;
      const y = height - 40 - (point / 100) * maxHeight;

      if (index === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    });

    ctx.stroke();

    // Draw data points
    points.forEach((point, index) => {
      const x = index * stepX;
      const y = height - 40 - (point / 100) * maxHeight;

      ctx.beginPath();
      ctx.arc(x, y, 4, 0, 2 * Math.PI);
      ctx.fillStyle = '#3498db';
      ctx.fill();
    });

    // Draw current value
    ctx.fillStyle = '#2c3e50';
    ctx.font = 'bold 16px Inter';
    ctx.textAlign = 'center';
    ctx.fillText(`Current: ${value.toFixed(1)}%`, width / 2, 30);
  };

  const getResourceValue = (resource: 'cpu' | 'memory' | 'disk' | 'network') => {
    if (!systemHealth) return { value: 0, color: '#95a5a6' };

    let value: number;
    let color: string;

    switch (resource) {
      case 'cpu':
        value = systemHealth.cpu.usage;
        color = getResourceColor(value);
        break;
      case 'memory':
        value = (systemHealth.memory.used / systemHealth.memory.total) * 100;
        color = getResourceColor(value);
        break;
      case 'disk':
        value = (systemHealth.disk.used / systemHealth.disk.total) * 100;
        color = getResourceColor(value);
        break;
      case 'network':
        value = Math.min(100, systemHealth.network.bandwidth / 1000); // Assuming 1000 Mbps max
        color = getResourceColor(value);
        break;
      default:
        value = 0;
        color = '#95a5a6';
    }

    return { value, color };
  };

  const getResourceColor = (value: number): string => {
    if (value < 50) return '#27ae60'; // Green
    if (value < 80) return '#f39c12'; // Orange
    return '#e74c3c'; // Red
  };

  const formatResourceValue = (resource: 'cpu' | 'memory' | 'disk' | 'network'): string => {
    if (!systemHealth) return 'N/A';

    switch (resource) {
      case 'cpu':
        return `${systemHealth.cpu.usage.toFixed(1)}%`;
      case 'memory':
        return `${((systemHealth.memory.used / systemHealth.memory.total) * 100).toFixed(1)}%`;
      case 'disk':
        return `${((systemHealth.disk.used / systemHealth.disk.total) * 100).toFixed(1)}%`;
      case 'network':
        return `${(systemHealth.network.bandwidth / 1024 / 1024).toFixed(1)} MB/s`;
      default:
        return 'N/A';
    }
  };

  const formatResourceDetails = (resource: 'cpu' | 'memory' | 'disk' | 'network'): string => {
    if (!systemHealth) return 'No data available';

    switch (resource) {
      case 'cpu':
        return `${systemHealth.cpu.cores} cores, ${systemHealth.cpu.temperature}°C`;
      case 'memory':
        return `${(systemHealth.memory.used / 1024 / 1024 / 1024).toFixed(1)}GB / ${(systemHealth.memory.total / 1024 / 1024 / 1024).toFixed(1)}GB`;
      case 'disk':
        return `${(systemHealth.disk.used / 1024 / 1024 / 1024).toFixed(1)}GB / ${(systemHealth.disk.total / 1024 / 1024 / 1024).toFixed(1)}GB`;
      case 'network':
        return `${systemHealth.network.latency}ms latency, ${systemHealth.network.packets_sent} packets sent`;
      default:
        return 'No data available';
    }
  };

  return (
    <div className={`resource-chart ${className}`}>
      <div className="chart-header">
        <h3 className="chart-title">Resource Monitoring</h3>
        <div className="chart-controls">
          <select
            value={chartType}
            onChange={(e) => setChartType(e.target.value as any)}
            className="chart-type-select"
          >
            <option value="gauge">Gauge</option>
            <option value="bar">Bar Chart</option>
            <option value="line">Line Chart</option>
          </select>
        </div>
      </div>

      <div className="chart-content">
        {/* Resource Selector */}
        <div className="resource-selector">
          {(['cpu', 'memory', 'disk', 'network'] as const).map((resource) => (
            <button
              key={resource}
              className={`resource-btn ${selectedResource === resource ? 'active' : ''}`}
              onClick={() => setSelectedResource(resource)}
            >
              {resource.toUpperCase()}
            </button>
          ))}
        </div>

        {/* Chart Canvas */}
        <div className="chart-container">
          <canvas
            ref={canvasRef}
            width={400}
            height={300}
            className="chart-canvas"
          />
        </div>

        {/* Resource Information */}
        <div className="resource-info">
          <div className="resource-value">
            {formatResourceValue(selectedResource)}
          </div>
          <div className="resource-details">
            {formatResourceDetails(selectedResource)}
          </div>
        </div>

        {/* Detailed Information */}
        {showDetails && systemHealth && (
          <div className="resource-details-section">
            <h4>Detailed Information</h4>
            <div className="details-grid">
              {selectedResource === 'cpu' && (
                <>
                  <div className="detail-item">
                    <span className="detail-label">Cores:</span>
                    <span className="detail-value">{systemHealth.cpu.cores}</span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Temperature:</span>
                    <span className="detail-value">{systemHealth.cpu.temperature}°C</span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Load Average:</span>
                    <span className="detail-value">
                      {systemHealth.cpu.load_average.map((load, index) => (
                        <span key={index}>{load.toFixed(2)}{index < 2 ? ', ' : ''}</span>
                      ))}
                    </span>
                  </div>
                </>
              )}

              {selectedResource === 'memory' && (
                <>
                  <div className="detail-item">
                    <span className="detail-label">Used:</span>
                    <span className="detail-value">
                      {(systemHealth.memory.used / 1024 / 1024 / 1024).toFixed(1)} GB
                    </span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Free:</span>
                    <span className="detail-value">
                      {(systemHealth.memory.free / 1024 / 1024 / 1024).toFixed(1)} GB
                    </span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Cached:</span>
                    <span className="detail-value">
                      {(systemHealth.memory.cached / 1024 / 1024 / 1024).toFixed(1)} GB
                    </span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Swap Used:</span>
                    <span className="detail-value">
                      {(systemHealth.memory.swap_used / 1024 / 1024 / 1024).toFixed(1)} GB
                    </span>
                  </div>
                </>
              )}

              {selectedResource === 'disk' && (
                <>
                  <div className="detail-item">
                    <span className="detail-label">Used:</span>
                    <span className="detail-value">
                      {(systemHealth.disk.used / 1024 / 1024 / 1024).toFixed(1)} GB
                    </span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Free:</span>
                    <span className="detail-value">
                      {(systemHealth.disk.free / 1024 / 1024 / 1024).toFixed(1)} GB
                    </span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Read Speed:</span>
                    <span className="detail-value">
                      {(systemHealth.disk.read_speed / 1024 / 1024).toFixed(1)} MB/s
                    </span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Write Speed:</span>
                    <span className="detail-value">
                      {(systemHealth.disk.write_speed / 1024 / 1024).toFixed(1)} MB/s
                    </span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">I/O Wait:</span>
                    <span className="detail-value">{systemHealth.disk.io_wait.toFixed(1)}%</span>
                  </div>
                </>
              )}

              {selectedResource === 'network' && (
                <>
                  <div className="detail-item">
                    <span className="detail-label">Bandwidth:</span>
                    <span className="detail-value">
                      {(systemHealth.network.bandwidth / 1024 / 1024).toFixed(1)} MB/s
                    </span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Latency:</span>
                    <span className="detail-value">{systemHealth.network.latency} ms</span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Packets Sent:</span>
                    <span className="detail-value">{systemHealth.network.packets_sent.toLocaleString()}</span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Packets Received:</span>
                    <span className="detail-value">{systemHealth.network.packets_received.toLocaleString()}</span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Bytes Sent:</span>
                    <span className="detail-value">
                      {(systemHealth.network.bytes_sent / 1024 / 1024 / 1024).toFixed(1)} GB
                    </span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Bytes Received:</span>
                    <span className="detail-value">
                      {(systemHealth.network.bytes_received / 1024 / 1024 / 1024).toFixed(1)} GB
                    </span>
                  </div>
                </>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Action Button */}
      {onViewDetails && (
        <div className="chart-actions">
          <button
            onClick={onViewDetails}
            className="node-action-btn"
            title="View Detailed Resource Information"
          >
            📊 View Details
          </button>
        </div>
      )}
    </div>
  );
};

export { ResourceChart };
