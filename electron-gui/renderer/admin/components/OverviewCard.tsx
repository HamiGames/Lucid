import React from 'react';

interface Metric {
  label: string;
  value: string | number;
  unit?: string;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
}

interface OverviewCardProps {
  title: string;
  icon?: string;
  metrics: Metric[];
  actions?: Array<{
    label: string;
    icon?: string;
    onClick: () => void;
    variant?: 'primary' | 'secondary' | 'danger';
  }>;
  loading?: boolean;
  error?: string;
  className?: string;
}

export const OverviewCard: React.FC<OverviewCardProps> = ({
  title,
  icon,
  metrics,
  actions,
  loading = false,
  error,
  className = ''
}) => {
  const getTrendIcon = (trend?: string) => {
    switch (trend) {
      case 'up':
        return '📈';
      case 'down':
        return '📉';
      case 'neutral':
        return '➡️';
      default:
        return null;
    }
  };

  const getTrendClass = (trend?: string) => {
    switch (trend) {
      case 'up':
        return 'trend-up';
      case 'down':
        return 'trend-down';
      case 'neutral':
        return 'trend-neutral';
      default:
        return '';
    }
  };

  if (loading) {
    return (
      <div className={`overview-card loading ${className}`}>
        <div className="card-header">
          <h3>{title}</h3>
        </div>
        <div className="card-content">
          <div className="loading-spinner"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`overview-card error ${className}`}>
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
    <div className={`overview-card ${className}`}>
      <div className="card-header">
        <div className="header-left">
          {icon && <span className="card-icon">{icon}</span>}
          <h3>{title}</h3>
        </div>
        {actions && actions.length > 0 && (
          <div className="card-actions">
            {actions.map((action, index) => (
              <button
                key={index}
                className={`action-btn ${action.variant || 'secondary'}`}
                onClick={action.onClick}
                title={action.label}
              >
                {action.icon && <span className="btn-icon">{action.icon}</span>}
                <span className="btn-text">{action.label}</span>
              </button>
            ))}
          </div>
        )}
      </div>
      
      <div className="card-content">
        <div className="metrics-grid">
          {metrics.map((metric, index) => (
            <div key={index} className="metric">
              <div className="metric-header">
                <span className="metric-label">{metric.label}</span>
                {metric.trend && (
                  <span className={`metric-trend ${getTrendClass(metric.trend)}`}>
                    {getTrendIcon(metric.trend)}
                    {metric.trendValue}
                  </span>
                )}
              </div>
              <div className="metric-value">
                <span className="value">{metric.value}</span>
                {metric.unit && <span className="unit">{metric.unit}</span>}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default OverviewCard;
