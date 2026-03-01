import React, { useState, useEffect, useCallback } from 'react';
import { WalletBalance } from '../components/WalletBalance';
import { PaymentHistory } from '../components/PaymentHistory';

interface User {
  id: string;
  email: string;
  tron_address: string;
  role: string;
  status: string;
  created_at: string;
  last_login: string;
  session_count: number;
}

interface WalletInfo {
  tron_address: string;
  balance_trx: number;
  balance_usd: number;
  balance_usdt: number;
  hardware_wallet?: {
    type: 'ledger' | 'trezor' | 'keepkey';
    device_id: string;
    public_key: string;
    is_connected: boolean;
  };
}

interface PaymentTransaction {
  id: string;
  type: 'session_payment' | 'withdrawal' | 'deposit' | 'refund';
  amount: number;
  currency: 'TRX' | 'USDT';
  status: 'pending' | 'confirmed' | 'failed';
  transaction_hash?: string;
  from_address?: string;
  to_address?: string;
  session_id?: string;
  description: string;
  timestamp: string;
  block_height?: number;
  gas_used?: number;
  gas_price?: number;
}

interface WalletPageProps {
  user: User | null;
  onRouteChange: (routeId: string) => void;
  onNotification: (notification: any) => void;
  apiCall: (endpoint: string, method: string, data?: any) => Promise<any>;
}

export const WalletPage: React.FC<WalletPageProps> = ({
  user,
  onRouteChange,
  onNotification,
  apiCall
}) => {
  const [walletInfo, setWalletInfo] = useState<WalletInfo | null>(null);
  const [transactions, setTransactions] = useState<PaymentTransaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hardwareWalletConnected, setHardwareWalletConnected] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'transactions' | 'settings'>('overview');

  // Load wallet information
  const loadWalletInfo = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiCall('/wallet/info', 'GET');
      
      if (response.success) {
        setWalletInfo(response.wallet);
        setHardwareWalletConnected(response.wallet.hardware_wallet?.is_connected || false);
      } else {
        throw new Error(response.message || 'Failed to load wallet information');
      }
    } catch (err) {
      console.error('Failed to load wallet info:', err);
      setError(err instanceof Error ? err.message : 'Failed to load wallet information');
      onNotification({
        type: 'error',
        title: 'Error',
        message: 'Failed to load wallet information'
      });
    } finally {
      setLoading(false);
    }
  }, [apiCall, onNotification]);

  // Load transaction history
  const loadTransactions = useCallback(async () => {
    try {
      const response = await apiCall('/wallet/transactions', 'GET');
      
      if (response.success) {
        setTransactions(response.transactions || []);
      } else {
        throw new Error(response.message || 'Failed to load transactions');
      }
    } catch (err) {
      console.error('Failed to load transactions:', err);
      onNotification({
        type: 'error',
        title: 'Error',
        message: 'Failed to load transaction history'
      });
    }
  }, [apiCall, onNotification]);

  // Connect hardware wallet
  const handleConnectHardwareWallet = useCallback(async () => {
    try {
      const response = await apiCall('/wallet/hardware/connect', 'POST');
      
      if (response.success) {
        setHardwareWalletConnected(true);
        onNotification({
          type: 'success',
          title: 'Hardware Wallet Connected',
          message: 'Hardware wallet connected successfully'
        });
        loadWalletInfo();
      } else {
        throw new Error(response.message || 'Failed to connect hardware wallet');
      }
    } catch (err) {
      console.error('Failed to connect hardware wallet:', err);
      onNotification({
        type: 'error',
        title: 'Connection Failed',
        message: 'Failed to connect hardware wallet'
      });
    }
  }, [apiCall, onNotification, loadWalletInfo]);

  // Disconnect hardware wallet
  const handleDisconnectHardwareWallet = useCallback(async () => {
    try {
      const response = await apiCall('/wallet/hardware/disconnect', 'POST');
      
      if (response.success) {
        setHardwareWalletConnected(false);
        onNotification({
          type: 'info',
          title: 'Hardware Wallet Disconnected',
          message: 'Hardware wallet disconnected successfully'
        });
        loadWalletInfo();
      } else {
        throw new Error(response.message || 'Failed to disconnect hardware wallet');
      }
    } catch (err) {
      console.error('Failed to disconnect hardware wallet:', err);
      onNotification({
        type: 'error',
        title: 'Disconnection Failed',
        message: 'Failed to disconnect hardware wallet'
      });
    }
  }, [apiCall, onNotification, loadWalletInfo]);

  // Request withdrawal
  const handleWithdrawal = useCallback(async (amount: number, currency: string, address: string) => {
    try {
      const response = await apiCall('/wallet/withdraw', 'POST', {
        amount,
        currency,
        to_address: address
      });

      if (response.success) {
        onNotification({
          type: 'success',
          title: 'Withdrawal Requested',
          message: 'Withdrawal request submitted successfully'
        });
        loadTransactions();
      } else {
        throw new Error(response.message || 'Failed to process withdrawal');
      }
    } catch (err) {
      console.error('Failed to process withdrawal:', err);
      onNotification({
        type: 'error',
        title: 'Withdrawal Failed',
        message: 'Failed to process withdrawal request'
      });
    }
  }, [apiCall, onNotification, loadTransactions]);

  // Copy address to clipboard
  const handleCopyAddress = useCallback(() => {
    if (walletInfo?.tron_address) {
      navigator.clipboard.writeText(walletInfo.tron_address);
      onNotification({
        type: 'success',
        title: 'Address Copied',
        message: 'Wallet address copied to clipboard'
      });
    }
  }, [walletInfo, onNotification]);

  // Load data on mount
  useEffect(() => {
    loadWalletInfo();
    loadTransactions();
  }, [loadWalletInfo, loadTransactions]);

  if (loading) {
    return (
      <div className="user-content">
        <div className="user-page-header">
          <h1 className="user-page-title">Wallet</h1>
          <p className="user-page-subtitle">Manage your TRON wallet and transactions</p>
        </div>
        <div className="user-loading">
          <div className="user-loading-spinner"></div>
          Loading wallet information...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="user-content">
        <div className="user-page-header">
          <h1 className="user-page-title">Wallet</h1>
          <p className="user-page-subtitle">Manage your TRON wallet and transactions</p>
        </div>
        <div className="user-card">
          <div className="user-card-body">
            <div className="user-empty-state">
              <div className="user-empty-state-title">Error Loading Wallet</div>
              <p className="user-empty-state-description">{error}</p>
              <button className="user-btn user-btn-primary" onClick={loadWalletInfo}>
                Retry
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="user-content">
      <div className="user-page-header">
        <h1 className="user-page-title">Wallet</h1>
        <p className="user-page-subtitle">Manage your TRON wallet and transactions</p>
      </div>

      {/* Tab Navigation */}
      <div className="user-card">
        <div className="user-card-body">
          <div className="user-nav" style={{ marginBottom: '1rem' }}>
            <button
              className={`user-nav-item ${activeTab === 'overview' ? 'active' : ''}`}
              onClick={() => setActiveTab('overview')}
            >
              Overview
            </button>
            <button
              className={`user-nav-item ${activeTab === 'transactions' ? 'active' : ''}`}
              onClick={() => setActiveTab('transactions')}
            >
              Transactions
            </button>
            <button
              className={`user-nav-item ${activeTab === 'settings' ? 'active' : ''}`}
              onClick={() => setActiveTab('settings')}
            >
              Settings
            </button>
          </div>
        </div>
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && walletInfo && (
        <WalletBalance
          walletInfo={walletInfo}
          hardwareWalletConnected={hardwareWalletConnected}
          onConnectHardwareWallet={handleConnectHardwareWallet}
          onDisconnectHardwareWallet={handleDisconnectHardwareWallet}
          onCopyAddress={handleCopyAddress}
          onWithdrawal={handleWithdrawal}
        />
      )}

      {/* Transactions Tab */}
      {activeTab === 'transactions' && (
        <PaymentHistory
          transactions={transactions}
          onRefresh={loadTransactions}
        />
      )}

      {/* Settings Tab */}
      {activeTab === 'settings' && walletInfo && (
        <div className="user-card">
          <div className="user-card-header">
            <h3 className="user-card-title">Wallet Settings</h3>
            <p className="user-card-subtitle">Configure your wallet preferences</p>
          </div>
          <div className="user-card-body">
            <div style={{ display: 'grid', gap: '1.5rem' }}>
              {/* Hardware Wallet Section */}
              <div>
                <h4 style={{ marginBottom: '1rem', color: 'var(--user-text-primary)' }}>
                  Hardware Wallet
                </h4>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
                  <div style={{ flex: '1' }}>
                    <div style={{ fontWeight: '500', marginBottom: '0.25rem' }}>
                      {walletInfo.hardware_wallet?.type ? 
                        `${walletInfo.hardware_wallet.type.charAt(0).toUpperCase() + walletInfo.hardware_wallet.type.slice(1)} Wallet` : 
                        'No Hardware Wallet'
                      }
                    </div>
                    <div style={{ fontSize: '0.875rem', color: 'var(--user-text-secondary)' }}>
                      {hardwareWalletConnected ? 'Connected and ready' : 'Not connected'}
                    </div>
                  </div>
                  <button
                    className={`user-btn ${hardwareWalletConnected ? 'user-btn-error' : 'user-btn-primary'}`}
                    onClick={hardwareWalletConnected ? handleDisconnectHardwareWallet : handleConnectHardwareWallet}
                  >
                    {hardwareWalletConnected ? 'Disconnect' : 'Connect'}
                  </button>
                </div>
              </div>

              {/* Wallet Address Section */}
              <div>
                <h4 style={{ marginBottom: '1rem', color: 'var(--user-text-primary)' }}>
                  Wallet Address
                </h4>
                <div style={{ 
                  padding: '1rem', 
                  backgroundColor: 'var(--user-bg-secondary)', 
                  borderRadius: 'var(--user-radius-md)',
                  fontFamily: 'monospace',
                  fontSize: '0.875rem',
                  wordBreak: 'break-all',
                  marginBottom: '1rem'
                }}>
                  {walletInfo.tron_address}
                </div>
                <button className="user-btn user-btn-secondary" onClick={handleCopyAddress}>
                  Copy Address
                </button>
              </div>

              {/* Security Section */}
              <div>
                <h4 style={{ marginBottom: '1rem', color: 'var(--user-text-primary)' }}>
                  Security
                </h4>
                <div style={{ display: 'grid', gap: '0.5rem' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <input type="checkbox" checked={true} readOnly />
                    <span>Enable transaction confirmations</span>
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <input type="checkbox" checked={hardwareWalletConnected} readOnly />
                    <span>Hardware wallet protection</span>
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <input type="checkbox" checked={true} readOnly />
                    <span>Two-factor authentication</span>
                  </label>
                </div>
              </div>

              {/* Backup Section */}
              <div>
                <h4 style={{ marginBottom: '1rem', color: 'var(--user-text-primary)' }}>
                  Backup & Recovery
                </h4>
                <p style={{ marginBottom: '1rem', color: 'var(--user-text-secondary)' }}>
                  Keep your wallet secure by backing up your private keys and seed phrases.
                </p>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button className="user-btn user-btn-warning">
                    Export Private Keys
                  </button>
                  <button className="user-btn user-btn-secondary">
                    Generate Seed Phrase
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
