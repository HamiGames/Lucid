import React, { useEffect, useRef } from 'react';

interface ChartDataPoint {
  timestamp: string;
  value: number;
  label?: string;
}

interface MetricChartProps {
  data: ChartDataPoint[];
  type: 'line' | 'bar' | 'area' | 'pie';
  color?: string;
  height?: number;
  showLegend?: boolean;
  showGrid?: boolean;
  showTooltips?: boolean;
  className?: string;
}

export const MetricChart: React.FC<MetricChartProps> = ({
  data,
  type,
  color = '#3b82f6',
  height = 200,
  showLegend = true,
  showGrid = true,
  showTooltips = true,
  className = ''
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const chartRef = useRef<any>(null);

  useEffect(() => {
    if (data.length === 0) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    // Clear previous chart
    if (chartRef.current) {
      chartRef.current.destroy();
    }

    // Create new chart
    createChart();
  }, [data, type, color, height]);

  const createChart = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas size
    canvas.width = canvas.offsetWidth * window.devicePixelRatio;
    canvas.height = height * window.devicePixelRatio;
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

    // Clear canvas
    ctx.clearRect(0, 0, canvas.offsetWidth, height);

    // Draw chart based on type
    switch (type) {
      case 'line':
        drawLineChart(ctx, canvas.offsetWidth, height);
        break;
      case 'bar':
        drawBarChart(ctx, canvas.offsetWidth, height);
        break;
      case 'area':
        drawAreaChart(ctx, canvas.offsetWidth, height);
        break;
      case 'pie':
        drawPieChart(ctx, canvas.offsetWidth, height);
        break;
    }
  };

  const drawLineChart = (ctx: CanvasRenderingContext2D, width: number, height: number) => {
    if (data.length === 0) return;

    const padding = 40;
    const chartWidth = width - padding * 2;
    const chartHeight = height - padding * 2;

    // Find min/max values
    const values = data.map(d => d.value);
    const minValue = Math.min(...values);
    const maxValue = Math.max(...values);
    const valueRange = maxValue - minValue;

    // Draw grid
    if (showGrid) {
      ctx.strokeStyle = 'rgba(51, 65, 85, 0.3)';
      ctx.lineWidth = 1;
      
      // Horizontal grid lines
      for (let i = 0; i <= 5; i++) {
        const y = padding + (chartHeight / 5) * i;
        ctx.beginPath();
        ctx.moveTo(padding, y);
        ctx.lineTo(width - padding, y);
        ctx.stroke();
      }
    }

    // Draw line
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.beginPath();

    data.forEach((point, index) => {
      const x = padding + (chartWidth / (data.length - 1)) * index;
      const y = padding + chartHeight - ((point.value - minValue) / valueRange) * chartHeight;
      
      if (index === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    });

    ctx.stroke();

    // Draw points
    ctx.fillStyle = color;
    data.forEach((point, index) => {
      const x = padding + (chartWidth / (data.length - 1)) * index;
      const y = padding + chartHeight - ((point.value - minValue) / valueRange) * chartHeight;
      
      ctx.beginPath();
      ctx.arc(x, y, 3, 0, 2 * Math.PI);
      ctx.fill();
    });
  };

  const drawBarChart = (ctx: CanvasRenderingContext2D, width: number, height: number) => {
    if (data.length === 0) return;

    const padding = 40;
    const chartWidth = width - padding * 2;
    const chartHeight = height - padding * 2;
    const barWidth = chartWidth / data.length * 0.8;
    const barSpacing = chartWidth / data.length * 0.2;

    // Find max value
    const maxValue = Math.max(...data.map(d => d.value));

    // Draw grid
    if (showGrid) {
      ctx.strokeStyle = 'rgba(51, 65, 85, 0.3)';
      ctx.lineWidth = 1;
      
      for (let i = 0; i <= 5; i++) {
        const y = padding + (chartHeight / 5) * i;
        ctx.beginPath();
        ctx.moveTo(padding, y);
        ctx.lineTo(width - padding, y);
        ctx.stroke();
      }
    }

    // Draw bars
    ctx.fillStyle = color;
    data.forEach((point, index) => {
      const x = padding + (chartWidth / data.length) * index + barSpacing / 2;
      const barHeight = (point.value / maxValue) * chartHeight;
      const y = padding + chartHeight - barHeight;
      
      ctx.fillRect(x, y, barWidth, barHeight);
    });
  };

  const drawAreaChart = (ctx: CanvasRenderingContext2D, width: number, height: number) => {
    if (data.length === 0) return;

    const padding = 40;
    const chartWidth = width - padding * 2;
    const chartHeight = height - padding * 2;

    // Find min/max values
    const values = data.map(d => d.value);
    const minValue = Math.min(...values);
    const maxValue = Math.max(...values);
    const valueRange = maxValue - minValue;

    // Draw grid
    if (showGrid) {
      ctx.strokeStyle = 'rgba(51, 65, 85, 0.3)';
      ctx.lineWidth = 1;
      
      for (let i = 0; i <= 5; i++) {
        const y = padding + (chartHeight / 5) * i;
        ctx.beginPath();
        ctx.moveTo(padding, y);
        ctx.lineTo(width - padding, y);
        ctx.stroke();
      }
    }

    // Draw area
    ctx.fillStyle = color + '40'; // Add transparency
    ctx.beginPath();
    ctx.moveTo(padding, padding + chartHeight);

    data.forEach((point, index) => {
      const x = padding + (chartWidth / (data.length - 1)) * index;
      const y = padding + chartHeight - ((point.value - minValue) / valueRange) * chartHeight;
      ctx.lineTo(x, y);
    });

    ctx.lineTo(padding + chartWidth, padding + chartHeight);
    ctx.closePath();
    ctx.fill();

    // Draw line
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.beginPath();

    data.forEach((point, index) => {
      const x = padding + (chartWidth / (data.length - 1)) * index;
      const y = padding + chartHeight - ((point.value - minValue) / valueRange) * chartHeight;
      
      if (index === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    });

    ctx.stroke();
  };

  const drawPieChart = (ctx: CanvasRenderingContext2D, width: number, height: number) => {
    if (data.length === 0) return;

    const centerX = width / 2;
    const centerY = height / 2;
    const radius = Math.min(width, height) / 2 - 40;

    // Calculate total value
    const totalValue = data.reduce((sum, point) => sum + point.value, 0);

    // Draw pie slices
    let currentAngle = -Math.PI / 2; // Start from top

    data.forEach((point, index) => {
      const sliceAngle = (point.value / totalValue) * 2 * Math.PI;
      const sliceColor = getSliceColor(index);

      // Draw slice
      ctx.fillStyle = sliceColor;
      ctx.beginPath();
      ctx.moveTo(centerX, centerY);
      ctx.arc(centerX, centerY, radius, currentAngle, currentAngle + sliceAngle);
      ctx.closePath();
      ctx.fill();

      // Draw slice border
      ctx.strokeStyle = 'rgba(15, 23, 42, 0.8)';
      ctx.lineWidth = 2;
      ctx.stroke();

      currentAngle += sliceAngle;
    });

    // Draw labels
    if (showLegend) {
      currentAngle = -Math.PI / 2;
      data.forEach((point, index) => {
        const sliceAngle = (point.value / totalValue) * 2 * Math.PI;
        const labelAngle = currentAngle + sliceAngle / 2;
        const labelX = centerX + Math.cos(labelAngle) * (radius + 20);
        const labelY = centerY + Math.sin(labelAngle) * (radius + 20);

        ctx.fillStyle = '#f8fafc';
        ctx.font = '12px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(point.label || `${point.value}`, labelX, labelY);

        currentAngle += sliceAngle;
      });
    }
  };

  const getSliceColor = (index: number): string => {
    const colors = [
      '#3b82f6',
      '#10b981',
      '#f59e0b',
      '#ef4444',
      '#8b5cf6',
      '#06b6d4',
      '#84cc16',
      '#f97316'
    ];
    return colors[index % colors.length];
  };

  if (data.length === 0) {
    return (
      <div 
        className={`metric-chart ${className}`}
        style={{ 
          height: `${height}px`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'rgba(15, 23, 42, 0.3)',
          borderRadius: '0.5rem',
          border: '1px solid rgba(51, 65, 85, 0.3)',
          color: '#94a3b8'
        }}
      >
        No data available
      </div>
    );
  }

  return (
    <div className={`metric-chart ${className}`} style={{ position: 'relative' }}>
      <canvas
        ref={canvasRef}
        style={{
          width: '100%',
          height: `${height}px`,
          background: 'rgba(15, 23, 42, 0.3)',
          borderRadius: '0.5rem',
          border: '1px solid rgba(51, 65, 85, 0.3)'
        }}
      />
      
      {showLegend && type !== 'pie' && (
        <div style={{
          position: 'absolute',
          top: '0.5rem',
          right: '0.5rem',
          background: 'rgba(15, 23, 42, 0.8)',
          padding: '0.25rem 0.5rem',
          borderRadius: '0.25rem',
          fontSize: '0.75rem',
          color: '#f8fafc'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <div style={{
              width: '12px',
              height: '12px',
              background: color,
              borderRadius: '2px'
            }}></div>
            <span>Data Points: {data.length}</span>
          </div>
        </div>
      )}
    </div>
  );
};
