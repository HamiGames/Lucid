import React from 'react';

interface BlockchainMetrics {
  networkHeight: number;
  syncStatus: 'synced' | 'syncing' | 'behind';
  pendingTransactions: number;
  blockTime: number;
  difficulty: number;
  hashRate: number;
  networkSize: number;
  lastBlockTime: string;
}

interface BlockchainStatusCardProps {
  metrics: BlockchainMetrics;
  loading?: boolean;
  error?: string;
  onRefresh?: () => void;
  onViewDetails?: () => void;
  className?: string;
}

export const BlockchainStatusCard: React.FC<BlockchainStatusCardProps> = ({
  metrics,
  loading = false,
  error,
  onRefresh,
  onViewDetails,
  className = ''
}) => {
  const getSyncStatusClass = (status: string) => {
    switch (status) {
      case 'synced':
        return 'sync-synced';
      case 'syncing':
        return 'sync-syncing';
      case 'behind':
        return 'sync-behind';
      default:
        return '';
    }
  };

  const getSyncStatusIcon = (status: string) => {
    switch (status) {
      case 'synced':
        return '✅';
      case 'syncing':
        return '🔄';
      case 'behind':
        return '⚠️';
      default:
        return '❓';
    }
  };

  const formatHashRate = (hashRate: number) => {
    if (hashRate >= 1e9) return `${(hashRate / 1e9).toFixed(2)} GH/s`;
    if (hashRate >= 1e6) return `${(hashRate / 1e6).toFixed(2)} MH/s`;
    if (hashRate >= 1e3) return `${(hashRate / 1e3).toFixed(2)} KH/s`;
    return `${hashRate.toFixed(2)} H/s`;
  };

  const formatDifficulty = (difficulty: number) => {
    if (difficulty >= 1e12) return `${(difficulty / 1e12).toFixed(2)}T`;
    if (difficulty >= 1e9) return `${(difficulty / 1e9).toFixed(2)}B`;
    if (difficulty >= 1e6) return `${(difficulty / 1e6).toFixed(2)}M`;
    if (difficulty >= 1e3) return `${(difficulty / 1e3).toFixed(2)}K`;
    return difficulty.toFixed(2);
  };

  if (loading) {
    return (
      <div className={`blockchain-status-card loading ${className}`}>
        <div className="card-header">
          <h3>Blockchain Status</h3>
        </div>
        <div className="card-content">
          <div className="loading-spinner"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`blockchain-status-card error ${className}`}>
        <div className="card-header">
          <h3>Blockchain Status</h3>
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
    <div className={`blockchain-status-card ${className}`}>
      <div className="card-header">
        <div className="header-left">
          <span className="card-icon">⛓️</span>
          <h3>Blockchain Status</h3>
        </div>
        <div className="card-actions">
          <button 
            className="btn secondary"
            onClick={onRefresh}
            title="Refresh blockchain data"
          >
            🔄
          </button>
          <button 
            className="btn primary"
            onClick={onViewDetails}
            title="View blockchain details"
          >
            View Details
          </button>
        </div>
      </div>
      
      <div className="card-content">
        <div className="blockchain-metrics">
          <div className="metric-row primary">
            <div className="metric">
              <span className="metric-label">Network Height</span>
              <span className="metric-value large">{metrics.networkHeight.toLocaleString()}</span>
            </div>
            <div className="metric">
              <span className="metric-label">Sync Status</span>
              <span className={`metric-value ${getSyncStatusClass(metrics.syncStatus)}`}>
                {getSyncStatusIcon(metrics.syncStatus)} {metrics.syncStatus}
              </span>
            </div>
          </div>
          
          <div className="metric-row">
            <div className="metric">
              <span className="metric-label">Pending Transactions</span>
              <span className="metric-value">{metrics.pendingTransactions.toLocaleString()}</span>
            </div>
            <div className="metric">
              <span className="metric-label">Block Time</span>
              <span className="metric-value">{metrics.blockTime}s</span>
            </div>
          </div>
          
          <div className="metric-row">
            <div className="metric">
              <span className="metric-label">Difficulty</span>
              <span className="metric-value">{formatDifficulty(metrics.difficulty)}</span>
            </div>
            <div className="metric">
              <span className="metric-label">Hash Rate</span>
              <span className="metric-value">{formatHashRate(metrics.hashRate)}</span>
            </div>
          </div>
          
          <div className="metric-row">
            <div className="metric">
              <span className="metric-label">Network Size</span>
              <span className="metric-value">{metrics.networkSize.toLocaleString()} nodes</span>
            </div>
            <div className="metric">
              <span className="metric-label">Last Block</span>
              <span className="metric-value">{metrics.lastBlockTime}</span>
            </div>
          </div>
        </div>
        
        <div className="blockchain-health">
          <div className="health-indicator">
            <span className="health-label">Network Health:</span>
            <span className={`health-status ${getSyncStatusClass(metrics.syncStatus)}`}>
              {metrics.syncStatus === 'synced' ? 'Excellent' : 
               metrics.syncStatus === 'syncing' ? 'Good' : 'Poor'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BlockchainStatusCard;
