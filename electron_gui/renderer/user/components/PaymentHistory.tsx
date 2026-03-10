import React, { useState } from 'react';

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

interface PaymentHistoryProps {
  transactions: PaymentTransaction[];
  onRefresh: () => void;
}

export const PaymentHistory: React.FC<PaymentHistoryProps> = ({
  transactions,
  onRefresh
}) => {
  const [filter, setFilter] = useState<'all' | 'session_payment' | 'withdrawal' | 'deposit' | 'refund'>('all');
  const [statusFilter, setStatusFilter] = useState<'all' | 'pending' | 'confirmed' | 'failed'>('all');
  const [sortBy, setSortBy] = useState<'timestamp' | 'amount' | 'type'>('timestamp');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [selectedTransaction, setSelectedTransaction] = useState<PaymentTransaction | null>(null);

  const getTransactionIcon = (type: string): string => {
    switch (type) {
      case 'session_payment':
        return '💳';
      case 'withdrawal':
        return '💸';
      case 'deposit':
        return '💰';
      case 'refund':
        return '🔄';
      default:
        return '💵';
    }
  };

  const getTransactionTypeLabel = (type: string): string => {
    switch (type) {
      case 'session_payment':
        return 'Session Payment';
      case 'withdrawal':
        return 'Withdrawal';
      case 'deposit':
        return 'Deposit';
      case 'refund':
        return 'Refund';
      default:
        return type;
    }
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'confirmed':
        return 'var(--user-success)';
      case 'pending':
        return 'var(--user-warning)';
      case 'failed':
        return 'var(--user-error)';
      default:
        return 'var(--user-secondary)';
    }
  };

  const getStatusIcon = (status: string): string => {
    switch (status) {
      case 'confirmed':
        return '✅';
      case 'pending':
        return '⏳';
      case 'failed':
        return '❌';
      default:
        return '❓';
    }
  };

  const formatAmount = (amount: number, currency: string): string => {
    if (currency === 'TRX') {
      return `${amount.toFixed(6)} TRX`;
    } else if (currency === 'USDT') {
      return `${amount.toFixed(2)} USDT`;
    } else {
      return `${amount.toFixed(2)} ${currency}`;
    }
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString();
  };

  const getFilteredTransactions = () => {
    let filtered = transactions;

    if (filter !== 'all') {
      filtered = filtered.filter(tx => tx.type === filter);
    }

    if (statusFilter !== 'all') {
      filtered = filtered.filter(tx => tx.status === statusFilter);
    }

    return filtered.sort((a, b) => {
      let aValue: any = a[sortBy];
      let bValue: any = b[sortBy];

      if (sortBy === 'timestamp') {
        aValue = new Date(aValue).getTime();
        bValue = new Date(bValue).getTime();
      }

      if (sortOrder === 'asc') {
        return aValue > bValue ? 1 : -1;
      } else {
        return aValue < bValue ? 1 : -1;
      }
    });
  };

  const filteredTransactions = getFilteredTransactions();

  const handleTransactionClick = (transaction: PaymentTransaction) => {
    setSelectedTransaction(transaction);
  };

  const handleCloseDetails = () => {
    setSelectedTransaction(null);
  };

  return (
    <div>
      {/* Filters and Controls */}
      <div className="user-card">
        <div className="user-card-body">
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap' }}>
            <div>
              <label className="user-form-label">Transaction Type:</label>
              <select
                className="user-form-input user-form-select"
                value={filter}
                onChange={(e) => setFilter(e.target.value as any)}
                style={{ width: 'auto', minWidth: '150px' }}
              >
                <option value="all">All Types</option>
                <option value="session_payment">Session Payments</option>
                <option value="withdrawal">Withdrawals</option>
                <option value="deposit">Deposits</option>
                <option value="refund">Refunds</option>
              </select>
            </div>

            <div>
              <label className="user-form-label">Status:</label>
              <select
                className="user-form-input user-form-select"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value as any)}
                style={{ width: 'auto', minWidth: '120px' }}
              >
                <option value="all">All Status</option>
                <option value="confirmed">Confirmed</option>
                <option value="pending">Pending</option>
                <option value="failed">Failed</option>
              </select>
            </div>

            <div>
              <label className="user-form-label">Sort by:</label>
              <select
                className="user-form-input user-form-select"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                style={{ width: 'auto', minWidth: '120px' }}
              >
                <option value="timestamp">Date</option>
                <option value="amount">Amount</option>
                <option value="type">Type</option>
              </select>
            </div>

            <div>
              <label className="user-form-label">Order:</label>
              <select
                className="user-form-input user-form-select"
                value={sortOrder}
                onChange={(e) => setSortOrder(e.target.value as any)}
                style={{ width: 'auto', minWidth: '100px' }}
              >
                <option value="desc">Newest First</option>
                <option value="asc">Oldest First</option>
              </select>
            </div>

            <button className="user-btn user-btn-secondary" onClick={onRefresh}>
              <span style={{ marginRight: '0.5rem' }}>🔄</span>
              Refresh
            </button>
          </div>
        </div>
      </div>

      {/* Transactions List */}
      {filteredTransactions.length === 0 ? (
        <div className="user-card">
          <div className="user-card-body">
            <div className="user-empty-state">
              <div className="user-empty-state-title">No Transactions Found</div>
              <p className="user-empty-state-description">
                {filter === 'all' && statusFilter === 'all'
                  ? "You haven't made any transactions yet."
                  : `No ${filter === 'all' ? '' : filter.replace('_', ' ')} transactions found${statusFilter === 'all' ? '.' : ` with ${statusFilter} status.`}`
                }
              </p>
            </div>
          </div>
        </div>
      ) : (
        <div className="user-table-container">
          <table className="user-table">
            <thead>
              <tr>
                <th>Type</th>
                <th>Amount</th>
                <th>Status</th>
                <th>Date</th>
                <th>Description</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredTransactions.map(transaction => (
                <tr key={transaction.id}>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span style={{ fontSize: '1.25rem' }}>{getTransactionIcon(transaction.type)}</span>
                      <span>{getTransactionTypeLabel(transaction.type)}</span>
                    </div>
                  </td>
                  <td>
                    <div style={{ 
                      color: transaction.type === 'deposit' ? 'var(--user-success)' : 
                             transaction.type === 'withdrawal' ? 'var(--user-error)' : 
                             'var(--user-text-primary)',
                      fontWeight: '500'
                    }}>
                      {transaction.type === 'deposit' ? '+' : transaction.type === 'withdrawal' ? '-' : ''}
                      {formatAmount(transaction.amount, transaction.currency)}
                    </div>
                  </td>
                  <td>
                    <span className={`user-status user-status-${transaction.status === 'confirmed' ? 'active' : transaction.status === 'pending' ? 'warning' : 'error'}`}>
                      <span className="user-status-dot"></span>
                      {getStatusIcon(transaction.status)} {transaction.status}
                    </span>
                  </td>
                  <td>{formatDate(transaction.timestamp)}</td>
                  <td>
                    <div style={{ maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {transaction.description}
                    </div>
                  </td>
                  <td>
                    <button
                      className="user-btn user-btn-sm user-btn-secondary"
                      onClick={() => handleTransactionClick(transaction)}
                    >
                      View Details
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Transaction Details Modal */}
      {selectedTransaction && (
        <div className="user-modal-overlay" onClick={handleCloseDetails}>
          <div className="user-modal" onClick={(e) => e.stopPropagation()}>
            <div className="user-modal-header">
              <h3 className="user-modal-title">Transaction Details</h3>
              <button className="user-modal-close" onClick={handleCloseDetails}>
                ×
              </button>
            </div>
            <div className="user-modal-body">
              <div style={{ display: 'grid', gap: '1rem' }}>
                <div>
                  <strong>Transaction ID:</strong> {selectedTransaction.id}
                </div>
                <div>
                  <strong>Type:</strong> 
                  <span style={{ marginLeft: '0.5rem' }}>
                    {getTransactionIcon(selectedTransaction.type)} {getTransactionTypeLabel(selectedTransaction.type)}
                  </span>
                </div>
                <div>
                  <strong>Amount:</strong> 
                  <span style={{ 
                    marginLeft: '0.5rem',
                    color: selectedTransaction.type === 'deposit' ? 'var(--user-success)' : 
                           selectedTransaction.type === 'withdrawal' ? 'var(--user-error)' : 
                           'var(--user-text-primary)',
                    fontWeight: '500'
                  }}>
                    {selectedTransaction.type === 'deposit' ? '+' : selectedTransaction.type === 'withdrawal' ? '-' : ''}
                    {formatAmount(selectedTransaction.amount, selectedTransaction.currency)}
                  </span>
                </div>
                <div>
                  <strong>Status:</strong>
                  <span className={`user-status user-status-${selectedTransaction.status === 'confirmed' ? 'active' : selectedTransaction.status === 'pending' ? 'warning' : 'error'}`} style={{ marginLeft: '0.5rem' }}>
                    <span className="user-status-dot"></span>
                    {getStatusIcon(selectedTransaction.status)} {selectedTransaction.status}
                  </span>
                </div>
                <div>
                  <strong>Date:</strong> {formatDate(selectedTransaction.timestamp)}
                </div>
                <div>
                  <strong>Description:</strong> {selectedTransaction.description}
                </div>
                
                {selectedTransaction.transaction_hash && (
                  <div>
                    <strong>Transaction Hash:</strong>
                    <div style={{ fontFamily: 'monospace', fontSize: '0.875rem', marginTop: '0.25rem', wordBreak: 'break-all' }}>
                      {selectedTransaction.transaction_hash}
                    </div>
                  </div>
                )}

                {selectedTransaction.from_address && (
                  <div>
                    <strong>From Address:</strong>
                    <div style={{ fontFamily: 'monospace', fontSize: '0.875rem', marginTop: '0.25rem', wordBreak: 'break-all' }}>
                      {selectedTransaction.from_address}
                    </div>
                  </div>
                )}

                {selectedTransaction.to_address && (
                  <div>
                    <strong>To Address:</strong>
                    <div style={{ fontFamily: 'monospace', fontSize: '0.875rem', marginTop: '0.25rem', wordBreak: 'break-all' }}>
                      {selectedTransaction.to_address}
                    </div>
                  </div>
                )}

                {selectedTransaction.session_id && (
                  <div>
                    <strong>Session ID:</strong> {selectedTransaction.session_id}
                  </div>
                )}

                {selectedTransaction.block_height && (
                  <div>
                    <strong>Block Height:</strong> {selectedTransaction.block_height}
                  </div>
                )}

                {selectedTransaction.gas_used && (
                  <div>
                    <strong>Gas Used:</strong> {selectedTransaction.gas_used}
                  </div>
                )}

                {selectedTransaction.gas_price && (
                  <div>
                    <strong>Gas Price:</strong> {selectedTransaction.gas_price}
                  </div>
                )}
              </div>
            </div>
            <div className="user-modal-footer">
              <button className="user-btn user-btn-secondary" onClick={handleCloseDetails}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
