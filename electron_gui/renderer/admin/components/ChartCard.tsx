import React, { useRef, useEffect, useState } from 'react';

interface ChartData {
  labels: string[];
  datasets: Array<{
    label: string;
    data: number[];
    backgroundColor?: string | string[];
    borderColor?: string | string[];
    borderWidth?: number;
    fill?: boolean;
    tension?: number;
  }>;
}

interface ChartOptions {
  responsive?: boolean;
  maintainAspectRatio?: boolean;
  plugins?: {
    legend?: {
      display?: boolean;
      position?: 'top' | 'bottom' | 'left' | 'right';
    };
    title?: {
      display?: boolean;
      text?: string;
    };
  };
  scales?: {
    x?: {
      display?: boolean;
      title?: {
        display?: boolean;
        text?: string;
      };
    };
    y?: {
      display?: boolean;
      title?: {
        display?: boolean;
        text?: string;
      };
      beginAtZero?: boolean;
    };
  };
}

interface ChartCardProps {
  title: string;
  data: ChartData;
  type: 'line' | 'bar' | 'pie' | 'doughnut' | 'area';
  options?: ChartOptions;
  loading?: boolean;
  error?: string;
  onRefresh?: () => void;
  onExport?: () => void;
  className?: string;
}

export const ChartCard: React.FC<ChartCardProps> = ({
  title,
  data,
  type,
  options = {},
  loading = false,
  error,
  onRefresh,
  onExport,
  className = ''
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const chartRef = useRef<any>(null);
  const [chartLoaded, setChartLoaded] = useState(false);

  useEffect(() => {
    if (!canvasRef.current || loading || error) return;

    const loadChart = async () => {
      try {
        // Dynamically import Chart.js
        const { Chart, registerables } = await import('chart.js');
        Chart.register(...registerables);

        if (chartRef.current) {
          chartRef.current.destroy();
        }

        const ctx = canvasRef.current!.getContext('2d');
        if (!ctx) return;

        const defaultOptions: ChartOptions = {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              display: true,
              position: 'top'
            },
            title: {
              display: true,
              text: title
            }
          },
          scales: type !== 'pie' && type !== 'doughnut' ? {
            x: {
              display: true,
              title: {
                display: true,
                text: 'Time'
              }
            },
            y: {
              display: true,
              title: {
                display: true,
                text: 'Value'
              },
              beginAtZero: true
            }
          } : undefined,
          ...options
        };

        chartRef.current = new Chart(ctx, {
          type: type,
          data: data,
          options: defaultOptions
        });

        setChartLoaded(true);
      } catch (err) {
        console.error('Failed to load chart:', err);
      }
    };

    loadChart();

    return () => {
      if (chartRef.current) {
        chartRef.current.destroy();
        chartRef.current = null;
      }
    };
  }, [data, type, options, loading, error, title]);

  const handleExport = () => {
    if (chartRef.current && onExport) {
      const url = chartRef.current.toBase64Image();
      const link = document.createElement('a');
      link.download = `${title.toLowerCase().replace(/\s+/g, '-')}-chart.png`;
      link.href = url;
      link.click();
    }
  };

  if (loading) {
    return (
      <div className={`chart-card loading ${className}`}>
        <div className="card-header">
          <h3>{title}</h3>
        </div>
        <div className="card-content">
          <div className="loading-spinner"></div>
          <div className="loading-text">Loading chart...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`chart-card error ${className}`}>
        <div className="card-header">
          <h3>{title}</h3>
        </div>
        <div className="card-content">
          <div className="error-message">
            <span className="error-icon">⚠️</span>
            <span className="error-text">{error}</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`chart-card ${className}`}>
      <div className="card-header">
        <div className="header-left">
          <h3>{title}</h3>
          {chartLoaded && (
            <span className="chart-status">📊</span>
          )}
        </div>
        <div className="card-actions">
          <button 
            className="btn-icon"
            onClick={onRefresh}
            title="Refresh chart data"
          >
            🔄
          </button>
          <button 
            className="btn-icon"
            onClick={handleExport}
            title="Export chart"
          >
            📥
          </button>
        </div>
      </div>
      
      <div className="card-content">
        <div className="chart-container">
          <canvas 
            ref={canvasRef}
            className="chart-canvas"
            style={{ width: '100%', height: '300px' }}
          />
        </div>
        
        {data.datasets.length > 0 && (
          <div className="chart-legend">
            {data.datasets.map((dataset, index) => (
              <div key={index} className="legend-item">
                <div 
                  className="legend-color"
                  style={{ 
                    backgroundColor: Array.isArray(dataset.backgroundColor) 
                      ? dataset.backgroundColor[0] 
                      : dataset.backgroundColor || '#000'
                  }}
                ></div>
                <span className="legend-label">{dataset.label}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default ChartCard;
