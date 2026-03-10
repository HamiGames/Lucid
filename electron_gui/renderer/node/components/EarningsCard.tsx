import React, { useState, useEffect } from 'react';

// Types
interface EarningsCardProps {
  totalEarnings: number;
  onViewDetails?: () => void;
  className?: string;
}

const EarningsCard: React.FC<EarningsCardProps> = ({
  totalEarnings,
  onViewDetails,
  className = ''
}) => {
  const [earningsData, setEarningsData] = useState({
    pending: 0,
    paid: 0,
    currentPeriod: 0,
    lastPayment: null as string | null,
    nextPayment: null as string | null,
    paymentMethod: 'tron' as 'tron' | 'bitcoin' | 'ethereum',
    walletAddress: '',
  });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadEarningsData();
  }, []);

  const loadEarningsData = async () => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await fetch('/api/node/earnings/summary');
      if (response.ok) {
        const data = await response.json();
        setEarningsData(data);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load earnings data');
    } finally {
      setIsLoading(false);
    }
  };

  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 6,
    }).format(amount);
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const getPaymentMethodIcon = (method: string): string => {
    const icons: Record<string, string> = {
      tron: '🔺',
      bitcoin: '₿',
      ethereum: 'Ξ',
    };
    return icons[method] || '💰';
  };

  const getPaymentMethodColor = (method: string): string => {
    const colors: Record<string, string> = {
      tron: '#ff060a',
      bitcoin: '#f7931a',
      ethereum: '#627eea',
    };
    return colors[method] || '#3498db';
  };

  const getEarningsTrend = (): 'up' | 'down' | 'stable' => {
    // This would typically come from historical data
    // For now, return a mock trend
    return 'up';
  };

  const getTrendIcon = (trend: 'up' | 'down' | 'stable'): string => {
    const icons: Record<string, string> = {
      up: '📈',
      down: '📉',
      stable: '➡️',
    };
    return icons[trend] || '➡️';
  };

  const getTrendColor = (trend: 'up' | 'down' | 'stable'): string => {
    const colors: Record<string, string> = {
      up: '#27ae60',
      down: '#e74c3c',
      stable: '#f39c12',
    };
    return colors[trend] || '#f39c12';
  };

  if (isLoading) {
    return (
      <div className={`earnings-card ${className}`}>
        <div className="card-header">
          <h3 className="card-title">Earnings</h3>
        </div>
        <div className="card-body">
          <div className="loading-state">
            <div className="spinner"></div>
            <span>Loading earnings...</span>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`earnings-card ${className}`}>
        <div className="card-header">
          <h3 className="card-title">Earnings</h3>
        </div>
        <div className="card-body">
          <div className="error-state">
            <span className="error-icon">❌</span>
            <span className="error-message">{error}</span>
            <button onClick={loadEarningsData} className="retry-btn">
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  const trend = getEarningsTrend();

  return (
    <div className={`earnings-card ${className}`}>
      <div className="card-header">
        <h3 className="card-title">Earnings</h3>
        <div className="earnings-trend">
          <span className="trend-icon">{getTrendIcon(trend)}</span>
          <span
            className="trend-text"
            style={{ color: getTrendColor(trend) }}
          >
            {trend}
          </span>
        </div>
      </div>

      <div className="card-body">
        {/* Total Earnings */}
        <div className="earnings-total">
          <div className="total-label">Total Earnings</div>
          <div className="total-value">{formatCurrency(totalEarnings)}</div>
        </div>

        {/* Earnings Breakdown */}
        <div className="earnings-breakdown">
          <div className="breakdown-item">
            <div className="breakdown-label">Pending</div>
            <div className="breakdown-value pending">
              {formatCurrency(earningsData.pending)}
            </div>
          </div>
          <div className="breakdown-item">
            <div className="breakdown-label">Paid</div>
            <div className="breakdown-value paid">
              {formatCurrency(earningsData.paid)}
            </div>
          </div>
          <div className="breakdown-item">
            <div className="breakdown-label">Current Period</div>
            <div className="breakdown-value current">
              {formatCurrency(earningsData.currentPeriod)}
            </div>
          </div>
        </div>

        {/* Payment Information */}
        <div className="payment-info">
          <div className="payment-method">
            <span className="payment-label">Payment Method:</span>
            <span
              className="payment-method-value"
              style={{ color: getPaymentMethodColor(earningsData.paymentMethod) }}
            >
              {getPaymentMethodIcon(earningsData.paymentMethod)} {earningsData.paymentMethod.toUpperCase()}
            </span>
          </div>
          
          {earningsData.walletAddress && (
            <div className="wallet-address">
              <span className="wallet-label">Wallet:</span>
              <span className="wallet-value">
                {earningsData.walletAddress.substring(0, 8)}...{earningsData.walletAddress.substring(earningsData.walletAddress.length - 8)}
              </span>
            </div>
          )}
        </div>

        {/* Payment Schedule */}
        <div className="payment-schedule">
          {earningsData.lastPayment && (
            <div className="schedule-item">
              <span className="schedule-label">Last Payment:</span>
              <span className="schedule-value">
                {formatDate(earningsData.lastPayment)}
              </span>
            </div>
          )}
          {earningsData.nextPayment && (
            <div className="schedule-item">
              <span className="schedule-label">Next Payment:</span>
              <span className="schedule-value">
                {formatDate(earningsData.nextPayment)}
              </span>
            </div>
          )}
        </div>

        {/* Earnings Progress */}
        <div className="earnings-progress">
          <div className="progress-label">Current Period Progress</div>
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${Math.min(100, (earningsData.currentPeriod / Math.max(earningsData.pending + earningsData.paid, 1)) * 100)}%` }}
            ></div>
          </div>
          <div className="progress-text">
            {Math.min(100, (earningsData.currentPeriod / Math.max(earningsData.pending + earningsData.paid, 1)) * 100).toFixed(1)}% of total earnings
          </div>
        </div>

        {/* Quick Stats */}
        <div className="earnings-stats">
          <div className="stat-item">
            <div className="stat-icon">📊</div>
            <div className="stat-content">
              <div className="stat-label">Sessions</div>
              <div className="stat-value">0</div>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-icon">⚡</div>
            <div className="stat-content">
              <div className="stat-label">Avg/Session</div>
              <div className="stat-value">$0.00</div>
            </div>
          </div>
          <div className="stat-item">
            <div className="stat-icon">📈</div>
            <div className="stat-content">
              <div className="stat-label">Growth</div>
              <div className="stat-value">+0%</div>
            </div>
          </div>
        </div>

        {/* Action Button */}
        {onViewDetails && (
          <div className="card-actions">
            <button
              onClick={onViewDetails}
              className="node-action-btn"
              title="View Detailed Earnings Information"
            >
              💰 View Details
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export { EarningsCard };
