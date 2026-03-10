import React, { useState } from 'react';

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

interface WalletBalanceProps {
  walletInfo: WalletInfo;
  hardwareWalletConnected: boolean;
  onConnectHardwareWallet: () => void;
  onDisconnectHardwareWallet: () => void;
  onCopyAddress: () => void;
  onWithdrawal: (amount: number, currency: string, address: string) => void;
}

export const WalletBalance: React.FC<WalletBalanceProps> = ({
  walletInfo,
  hardwareWalletConnected,
  onConnectHardwareWallet,
  onDisconnectHardwareWallet,
  onCopyAddress,
  onWithdrawal
}) => {
  const [showWithdrawalForm, setShowWithdrawalForm] = useState(false);
  const [withdrawalAmount, setWithdrawalAmount] = useState('');
  const [withdrawalCurrency, setWithdrawalCurrency] = useState('TRX');
  const [withdrawalAddress, setWithdrawalAddress] = useState('');
  const [withdrawalLoading, setWithdrawalLoading] = useState(false);

  const formatBalance = (amount: number, currency: string): string => {
    if (currency === 'TRX') {
      return `${amount.toFixed(6)} TRX`;
    } else if (currency === 'USDT') {
      return `${amount.toFixed(2)} USDT`;
    } else {
      return `$${amount.toFixed(2)}`;
    }
  };

  const handleWithdrawalSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    
    if (!withdrawalAmount || !withdrawalAddress) {
      return;
    }

    try {
      setWithdrawalLoading(true);
      await onWithdrawal(parseFloat(withdrawalAmount), withdrawalCurrency, withdrawalAddress);
      setShowWithdrawalForm(false);
      setWithdrawalAmount('');
      setWithdrawalAddress('');
    } catch (error) {
      console.error('Withdrawal failed:', error);
    } finally {
      setWithdrawalLoading(false);
    }
  };

  return (
    <div>
      {/* Wallet Overview */}
      <div className="user-card">
        <div className="user-card-header">
          <h3 className="user-card-title">Wallet Overview</h3>
          <p className="user-card-subtitle">Your TRON wallet balance and information</p>
        </div>
        <div className="user-card-body">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem' }}>
            {/* TRX Balance */}
            <div style={{
              padding: '1.5rem',
              backgroundColor: 'var(--user-bg-secondary)',
              borderRadius: 'var(--user-radius-lg)',
              textAlign: 'center',
              border: '2px solid var(--user-primary)'
            }}>
              <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>🪙</div>
              <div style={{ fontSize: '1.5rem', fontWeight: '700', color: 'var(--user-primary)', marginBottom: '0.25rem' }}>
                {formatBalance(walletInfo.balance_trx, 'TRX')}
              </div>
              <div style={{ fontSize: '0.875rem', color: 'var(--user-text-secondary)' }}>
                TRON (TRX)
              </div>
            </div>

            {/* USDT Balance */}
            <div style={{
              padding: '1.5rem',
              backgroundColor: 'var(--user-bg-secondary)',
              borderRadius: 'var(--user-radius-lg)',
              textAlign: 'center',
              border: '2px solid var(--user-success)'
            }}>
              <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>💵</div>
              <div style={{ fontSize: '1.5rem', fontWeight: '700', color: 'var(--user-success)', marginBottom: '0.25rem' }}>
                {formatBalance(walletInfo.balance_usdt, 'USDT')}
              </div>
              <div style={{ fontSize: '0.875rem', color: 'var(--user-text-secondary)' }}>
                Tether (USDT)
              </div>
            </div>

            {/* USD Value */}
            <div style={{
              padding: '1.5rem',
              backgroundColor: 'var(--user-bg-secondary)',
              borderRadius: 'var(--user-radius-lg)',
              textAlign: 'center',
              border: '2px solid var(--user-info)'
            }}>
              <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>💰</div>
              <div style={{ fontSize: '1.5rem', fontWeight: '700', color: 'var(--user-info)', marginBottom: '0.25rem' }}>
                {formatBalance(walletInfo.balance_usd, 'USD')}
              </div>
              <div style={{ fontSize: '0.875rem', color: 'var(--user-text-secondary)' }}>
                Total USD Value
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Wallet Address */}
      <div className="user-card">
        <div className="user-card-header">
          <h3 className="user-card-title">Wallet Address</h3>
          <p className="user-card-subtitle">Your TRON wallet address for receiving funds</p>
        </div>
        <div className="user-card-body">
          <div style={{
            padding: '1rem',
            backgroundColor: 'var(--user-bg-secondary)',
            borderRadius: 'var(--user-radius-md)',
            marginBottom: '1rem'
          }}>
            <div style={{ fontSize: '0.875rem', color: 'var(--user-text-secondary)', marginBottom: '0.5rem' }}>
              Your TRON Address:
            </div>
            <div style={{
              fontFamily: 'monospace',
              fontSize: '0.875rem',
              wordBreak: 'break-all',
              color: 'var(--user-text-primary)',
              backgroundColor: 'var(--user-bg-primary)',
              padding: '0.75rem',
              borderRadius: 'var(--user-radius-sm)',
              border: '1px solid var(--user-border-primary)'
            }}>
              {walletInfo.tron_address}
            </div>
          </div>
          <button className="user-btn user-btn-secondary" onClick={onCopyAddress}>
            <span style={{ marginRight: '0.5rem' }}>📋</span>
            Copy Address
          </button>
        </div>
      </div>

      {/* Hardware Wallet Status */}
      {walletInfo.hardware_wallet && (
        <div className="user-card">
          <div className="user-card-header">
            <h3 className="user-card-title">Hardware Wallet</h3>
            <p className="user-card-subtitle">Manage your hardware wallet connection</p>
          </div>
          <div className="user-card-body">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div style={{ fontWeight: '500', marginBottom: '0.25rem' }}>
                  {walletInfo.hardware_wallet.type.charAt(0).toUpperCase() + walletInfo.hardware_wallet.type.slice(1)} Wallet
                </div>
                <div style={{ fontSize: '0.875rem', color: 'var(--user-text-secondary)' }}>
                  Device ID: {walletInfo.hardware_wallet.device_id}
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <span className={`user-status user-status-${hardwareWalletConnected ? 'active' : 'inactive'}`}>
                  <span className="user-status-dot"></span>
                  {hardwareWalletConnected ? 'Connected' : 'Disconnected'}
                </span>
                <button
                  className={`user-btn ${hardwareWalletConnected ? 'user-btn-error' : 'user-btn-primary'}`}
                  onClick={hardwareWalletConnected ? onDisconnectHardwareWallet : onConnectHardwareWallet}
                >
                  {hardwareWalletConnected ? 'Disconnect' : 'Connect'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="user-card">
        <div className="user-card-header">
          <h3 className="user-card-title">Quick Actions</h3>
          <p className="user-card-subtitle">Common wallet operations</p>
        </div>
        <div className="user-card-body">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
            <button
              className="user-btn user-btn-primary"
              onClick={() => setShowWithdrawalForm(true)}
            >
              <span style={{ marginRight: '0.5rem' }}>💸</span>
              Withdraw Funds
            </button>
            <button className="user-btn user-btn-secondary">
              <span style={{ marginRight: '0.5rem' }}>📊</span>
              View Transactions
            </button>
            <button className="user-btn user-btn-secondary">
              <span style={{ marginRight: '0.5rem' }}>🔍</span>
              Check Balance
            </button>
            <button className="user-btn user-btn-secondary">
              <span style={{ marginRight: '0.5rem' }}>📈</span>
              Price History
            </button>
          </div>
        </div>
      </div>

      {/* Withdrawal Form Modal */}
      {showWithdrawalForm && (
        <div className="user-modal-overlay" onClick={() => setShowWithdrawalForm(false)}>
          <div className="user-modal" onClick={(e) => e.stopPropagation()}>
            <div className="user-modal-header">
              <h3 className="user-modal-title">Withdraw Funds</h3>
              <button className="user-modal-close" onClick={() => setShowWithdrawalForm(false)}>
                ×
              </button>
            </div>
            <div className="user-modal-body">
              <form onSubmit={handleWithdrawalSubmit}>
                <div style={{ display: 'grid', gap: '1rem' }}>
                  <div className="user-form-group">
                    <label className="user-form-label">Currency</label>
                    <select
                      className="user-form-input user-form-select"
                      value={withdrawalCurrency}
                      onChange={(e) => setWithdrawalCurrency(e.target.value)}
                    >
                      <option value="TRX">TRX</option>
                      <option value="USDT">USDT</option>
                    </select>
                  </div>

                  <div className="user-form-group">
                    <label className="user-form-label">Amount</label>
                    <input
                      type="number"
                      className="user-form-input"
                      value={withdrawalAmount}
                      onChange={(e) => setWithdrawalAmount(e.target.value)}
                      placeholder="Enter amount to withdraw"
                      step="0.000001"
                      min="0"
                      required
                    />
                    <div style={{ fontSize: '0.875rem', color: 'var(--user-text-secondary)', marginTop: '0.25rem' }}>
                      Available: {formatBalance(
                        withdrawalCurrency === 'TRX' ? walletInfo.balance_trx : walletInfo.balance_usdt,
                        withdrawalCurrency
                      )}
                    </div>
                  </div>

                  <div className="user-form-group">
                    <label className="user-form-label">Destination Address</label>
                    <input
                      type="text"
                      className="user-form-input"
                      value={withdrawalAddress}
                      onChange={(e) => setWithdrawalAddress(e.target.value)}
                      placeholder="Enter TRON address"
                      required
                    />
                  </div>
                </div>
              </form>
            </div>
            <div className="user-modal-footer">
              <button
                className="user-btn user-btn-primary"
                onClick={handleWithdrawalSubmit}
                disabled={withdrawalLoading || !withdrawalAmount || !withdrawalAddress}
              >
                {withdrawalLoading ? 'Processing...' : 'Withdraw'}
              </button>
              <button
                className="user-btn user-btn-secondary"
                onClick={() => setShowWithdrawalForm(false)}
                disabled={withdrawalLoading}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
