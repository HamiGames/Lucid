import React, { useState, useEffect } from 'react';
import { EarningsCard } from '../components/EarningsCard';

// Types
interface EarningsData {
  total_earnings: number;
  pending_earnings: number;
  paid_earnings: number;
  current_period_earnings: number;
  last_payment_date: string;
  next_payment_date: string;
  payment_frequency: 'daily' | 'weekly' | 'monthly';
  payment_method: 'tron' | 'bitcoin' | 'ethereum';
  wallet_address: string;
}

interface EarningsHistory {
  id: string;
  date: string;
  amount: number;
  type: 'session' | 'block_reward' | 'pool_share' | 'bonus';
  status: 'pending' | 'confirmed' | 'paid';
  transaction_hash?: string;
  description: string;
}

interface PayoutHistory {
  id: string;
  date: string;
  amount: number;
  transaction_hash: string;
  status: 'pending' | 'confirmed' | 'failed';
  fee: number;
}

interface EarningsStats {
  total_sessions: number;
  average_earnings_per_session: number;
  best_day_earnings: number;
  best_day_date: string;
  total_payouts: number;
  average_payout_amount: number;
}

interface EarningsPageProps {
  nodeUser: any;
  systemHealth: any;
  onRouteChange: (route: string) => void;
  onNotification: (type: 'info' | 'warning' | 'error' | 'success', message: string) => void;
}

const EarningsPage: React.FC<EarningsPageProps> = ({
  nodeUser,
  systemHealth,
  onRouteChange,
  onNotification
}) => {
  const [earningsData, setEarningsData] = useState<EarningsData | null>(null);
  const [earningsHistory, setEarningsHistory] = useState<EarningsHistory[]>([]);
  const [payoutHistory, setPayoutHistory] = useState<PayoutHistory[]>([]);
  const [earningsStats, setEarningsStats] = useState<EarningsStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTimeRange, setSelectedTimeRange] = useState<'7d' | '30d' | '90d' | '1y'>('30d');
  const [activeTab, setActiveTab] = useState<'overview' | 'history' | 'payouts' | 'settings'>('overview');

  useEffect(() => {
    loadEarningsData();
  }, [selectedTimeRange]);

  const loadEarningsData = async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Load earnings overview
      const earningsResponse = await fetch(`/api/node/earnings?timeRange=${selectedTimeRange}`);
      if (earningsResponse.ok) {
        const data = await earningsResponse.json();
        setEarningsData(data.earnings);
        setEarningsHistory(data.history);
        setEarningsStats(data.stats);
      }

      // Load payout history
      const payoutsResponse = await fetch(`/api/node/payouts?timeRange=${selectedTimeRange}`);
      if (payoutsResponse.ok) {
        const payoutsData = await payoutsResponse.json();
        setPayoutHistory(payoutsData);
      }

      onNotification('success', 'Earnings data loaded successfully');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load earnings data';
      setError(errorMessage);
      onNotification('error', errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRequestPayout = async () => {
    try {
      const response = await fetch('/api/node/request-payout', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          amount: earningsData?.pending_earnings || 0,
        }),
      });

      if (response.ok) {
        onNotification('success', 'Payout request submitted successfully');
        loadEarningsData(); // Refresh data
      } else {
        throw new Error('Failed to request payout');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to request payout';
      onNotification('error', errorMessage);
    }
  };

  const handleUpdatePaymentSettings = async (settings: Partial<EarningsData>) => {
    try {
      const response = await fetch('/api/node/payment-settings', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(settings),
      });

      if (response.ok) {
        onNotification('success', 'Payment settings updated successfully');
        loadEarningsData(); // Refresh data
      } else {
        throw new Error('Failed to update payment settings');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to update payment settings';
      onNotification('error', errorMessage);
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

  const formatDateTime = (dateString: string): string => {
    return new Date(dateString).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getEarningsTypeIcon = (type: string): string => {
    const icons: Record<string, string> = {
      session: '📊',
      block_reward: '⛏️',
      pool_share: '🤝',
      bonus: '🎁',
    };
    return icons[type] || '💰';
  };

  const getStatusColor = (status: string): string => {
    const colors: Record<string, string> = {
      pending: '#f39c12',
      confirmed: '#27ae60',
      paid: '#27ae60',
      failed: '#e74c3c',
    };
    return colors[status] || '#95a5a6';
  };

  if (isLoading) {
    return (
      <div className="earnings-page">
        <div className="node-loading">
          <div className="spinner"></div>
          <span>Loading earnings data...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="earnings-page">
        <div className="node-error">
          <h3>Earnings Error</h3>
          <p>{error}</p>
          <button onClick={loadEarningsData} className="node-action-btn">
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="earnings-page">
      {/* Page Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Earnings & Payouts</h1>
          <p className="page-subtitle">Track your node earnings and manage payouts</p>
        </div>
        <div className="page-actions">
          <select
            value={selectedTimeRange}
            onChange={(e) => setSelectedTimeRange(e.target.value as any)}
            className="time-range-select"
          >
            <option value="7d">Last 7 Days</option>
            <option value="30d">Last 30 Days</option>
            <option value="90d">Last 90 Days</option>
            <option value="1y">Last Year</option>
          </select>
          <button
            onClick={loadEarningsData}
            className="node-action-btn"
            title="Refresh Data"
          >
            🔄 Refresh
          </button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="earnings-tabs">
        <button
          className={`tab-button ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          Overview
        </button>
        <button
          className={`tab-button ${activeTab === 'history' ? 'active' : ''}`}
          onClick={() => setActiveTab('history')}
        >
          Earnings History
        </button>
        <button
          className={`tab-button ${activeTab === 'payouts' ? 'active' : ''}`}
          onClick={() => setActiveTab('payouts')}
        >
          Payout History
        </button>
        <button
          className={`tab-button ${activeTab === 'settings' ? 'active' : ''}`}
          onClick={() => setActiveTab('settings')}
        >
          Payment Settings
        </button>
      </div>

      {/* Tab Content */}
      <div className="tab-content">
        {activeTab === 'overview' && (
          <div className="earnings-overview">
            {/* Earnings Summary */}
            <div className="earnings-summary">
              <div className="summary-card">
                <h3>Total Earnings</h3>
                <div className="summary-value">
                  {formatCurrency(earningsData?.total_earnings || 0)}
                </div>
              </div>
              <div className="summary-card">
                <h3>Pending Earnings</h3>
                <div className="summary-value pending">
                  {formatCurrency(earningsData?.pending_earnings || 0)}
                </div>
              </div>
              <div className="summary-card">
                <h3>Paid Earnings</h3>
                <div className="summary-value paid">
                  {formatCurrency(earningsData?.paid_earnings || 0)}
                </div>
              </div>
              <div className="summary-card">
                <h3>Current Period</h3>
                <div className="summary-value current">
                  {formatCurrency(earningsData?.current_period_earnings || 0)}
                </div>
              </div>
            </div>

            {/* Earnings Card */}
            <EarningsCard
              totalEarnings={earningsData?.total_earnings || 0}
              onViewDetails={() => setActiveTab('history')}
            />

            {/* Quick Actions */}
            <div className="earnings-actions">
              <button
                onClick={handleRequestPayout}
                className="node-action-btn"
                disabled={!earningsData?.pending_earnings || earningsData.pending_earnings <= 0}
                title="Request Payout"
              >
                💰 Request Payout ({formatCurrency(earningsData?.pending_earnings || 0)})
              </button>
              <button
                onClick={() => setActiveTab('settings')}
                className="node-action-btn"
                title="Payment Settings"
              >
                ⚙️ Payment Settings
              </button>
            </div>

            {/* Next Payment Info */}
            {earningsData && (
              <div className="next-payment-info">
                <h3>Next Payment</h3>
                <div className="payment-details">
                  <div className="payment-item">
                    <span className="payment-label">Scheduled:</span>
                    <span className="payment-value">
                      {formatDate(earningsData.next_payment_date)}
                    </span>
                  </div>
                  <div className="payment-item">
                    <span className="payment-label">Frequency:</span>
                    <span className="payment-value capitalize">
                      {earningsData.payment_frequency}
                    </span>
                  </div>
                  <div className="payment-item">
                    <span className="payment-label">Method:</span>
                    <span className="payment-value uppercase">
                      {earningsData.payment_method}
                    </span>
                  </div>
                  <div className="payment-item">
                    <span className="payment-label">Wallet:</span>
                    <span className="payment-value wallet-address">
                      {earningsData.wallet_address}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'history' && (
          <div className="earnings-history">
            <h3>Earnings History</h3>
            <div className="history-table">
              <div className="table-header">
                <div className="table-cell">Date</div>
                <div className="table-cell">Type</div>
                <div className="table-cell">Amount</div>
                <div className="table-cell">Status</div>
                <div className="table-cell">Transaction</div>
                <div className="table-cell">Description</div>
              </div>
              {earningsHistory.length > 0 ? (
                earningsHistory.map((earning) => (
                  <div key={earning.id} className="table-row">
                    <div className="table-cell">
                      {formatDateTime(earning.date)}
                    </div>
                    <div className="table-cell">
                      <span className="earnings-type">
                        {getEarningsTypeIcon(earning.type)} {earning.type.replace('_', ' ')}
                      </span>
                    </div>
                    <div className="table-cell amount">
                      {formatCurrency(earning.amount)}
                    </div>
                    <div className="table-cell">
                      <span
                        className="status-badge"
                        style={{ color: getStatusColor(earning.status) }}
                      >
                        {earning.status}
                      </span>
                    </div>
                    <div className="table-cell">
                      {earning.transaction_hash ? (
                        <a
                          href={`https://tronscan.org/#/transaction/${earning.transaction_hash}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="transaction-link"
                        >
                          {earning.transaction_hash.substring(0, 8)}...
                        </a>
                      ) : (
                        '-'
                      )}
                    </div>
                    <div className="table-cell description">
                      {earning.description}
                    </div>
                  </div>
                ))
              ) : (
                <div className="no-data">
                  <p>No earnings history found for the selected time range.</p>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'payouts' && (
          <div className="payouts-history">
            <h3>Payout History</h3>
            <div className="history-table">
              <div className="table-header">
                <div className="table-cell">Date</div>
                <div className="table-cell">Amount</div>
                <div className="table-cell">Fee</div>
                <div className="table-cell">Net Amount</div>
                <div className="table-cell">Status</div>
                <div className="table-cell">Transaction</div>
              </div>
              {payoutHistory.length > 0 ? (
                payoutHistory.map((payout) => (
                  <div key={payout.id} className="table-row">
                    <div className="table-cell">
                      {formatDateTime(payout.date)}
                    </div>
                    <div className="table-cell amount">
                      {formatCurrency(payout.amount)}
                    </div>
                    <div className="table-cell fee">
                      {formatCurrency(payout.fee)}
                    </div>
                    <div className="table-cell net-amount">
                      {formatCurrency(payout.amount - payout.fee)}
                    </div>
                    <div className="table-cell">
                      <span
                        className="status-badge"
                        style={{ color: getStatusColor(payout.status) }}
                      >
                        {payout.status}
                      </span>
                    </div>
                    <div className="table-cell">
                      <a
                        href={`https://tronscan.org/#/transaction/${payout.transaction_hash}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="transaction-link"
                      >
                        {payout.transaction_hash.substring(0, 8)}...
                      </a>
                    </div>
                  </div>
                ))
              ) : (
                <div className="no-data">
                  <p>No payout history found for the selected time range.</p>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'settings' && earningsData && (
          <div className="payment-settings">
            <h3>Payment Settings</h3>
            <div className="settings-form">
              <div className="form-group">
                <label>Payment Frequency</label>
                <select
                  value={earningsData.payment_frequency}
                  onChange={(e) => handleUpdatePaymentSettings({
                    payment_frequency: e.target.value as any
                  })}
                  className="form-select"
                >
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                </select>
              </div>
              <div className="form-group">
                <label>Payment Method</label>
                <select
                  value={earningsData.payment_method}
                  onChange={(e) => handleUpdatePaymentSettings({
                    payment_method: e.target.value as any
                  })}
                  className="form-select"
                >
                  <option value="tron">TRON (TRX)</option>
                  <option value="bitcoin">Bitcoin (BTC)</option>
                  <option value="ethereum">Ethereum (ETH)</option>
                </select>
              </div>
              <div className="form-group">
                <label>Wallet Address</label>
                <input
                  type="text"
                  value={earningsData.wallet_address}
                  onChange={(e) => handleUpdatePaymentSettings({
                    wallet_address: e.target.value
                  })}
                  className="form-input"
                  placeholder="Enter wallet address"
                />
              </div>
              <button
                onClick={() => handleUpdatePaymentSettings({})}
                className="node-action-btn"
                disabled
              >
                Save Settings
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default EarningsPage;
