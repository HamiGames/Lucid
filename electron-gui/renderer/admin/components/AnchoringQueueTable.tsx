import React, { useState, useMemo } from 'react';

interface AnchoringItem {
  id: string;
  sessionId: string;
  userId: string;
  nodeId: string;
  dataSize: number;
  priority: 'high' | 'medium' | 'low';
  status: 'pending' | 'processing' | 'completed' | 'failed';
  createdAt: string;
  estimatedTime: string;
  blockHeight?: number;
  transactionHash?: string;
  errorMessage?: string;
}

interface AnchoringQueueTableProps {
  items: AnchoringItem[];
  loading?: boolean;
  onItemSelect?: (item: AnchoringItem) => void;
  onPriorityChange?: (itemId: string, priority: string) => void;
  onCancelItem?: (itemId: string) => void;
  onRetryItem?: (itemId: string) => void;
  onBulkAction?: (action: string, itemIds: string[]) => void;
  onRefresh?: () => void;
  className?: string;
}

export const AnchoringQueueTable: React.FC<AnchoringQueueTableProps> = ({
  items,
  loading = false,
  onItemSelect,
  onPriorityChange,
  onCancelItem,
  onRetryItem,
  onBulkAction,
  onRefresh,
  className = ''
}) => {
  const [selectedItems, setSelectedItems] = useState<string[]>([]);
  const [sortField, setSortField] = useState<keyof AnchoringItem>('createdAt');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [filterStatus, setFilterStatus] = useState<string>('');
  const [filterPriority, setFilterPriority] = useState<string>('');

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedItems(items.map(item => item.id));
    } else {
      setSelectedItems([]);
    }
  };

  const handleSelectItem = (itemId: string, checked: boolean) => {
    if (checked) {
      setSelectedItems(prev => [...prev, itemId]);
    } else {
      setSelectedItems(prev => prev.filter(id => id !== itemId));
    }
  };

  const handleSort = (field: keyof AnchoringItem) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const filteredAndSortedItems = useMemo(() => {
    let filtered = items.filter(item => {
      if (filterStatus && item.status !== filterStatus) return false;
      if (filterPriority && item.priority !== filterPriority) return false;
      return true;
    });

    return filtered.sort((a, b) => {
      const aValue = a[sortField];
      const bValue = b[sortField];
      
      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return sortDirection === 'asc' 
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue);
      }
      
      return sortDirection === 'asc' 
        ? (aValue < bValue ? -1 : 1)
        : (aValue > bValue ? -1 : 1);
    });
  }, [items, filterStatus, filterPriority, sortField, sortDirection]);

  const getPriorityClass = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'priority-high';
      case 'medium':
        return 'priority-medium';
      case 'low':
        return 'priority-low';
      default:
        return '';
    }
  };

  const getPriorityIcon = (priority: string) => {
    switch (priority) {
      case 'high':
        return '🔴';
      case 'medium':
        return '🟡';
      case 'low':
        return '🟢';
      default:
        return '⚪';
    }
  };

  const getStatusClass = (status: string) => {
    switch (status) {
      case 'pending':
        return 'status-pending';
      case 'processing':
        return 'status-processing';
      case 'completed':
        return 'status-completed';
      case 'failed':
        return 'status-failed';
      default:
        return '';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pending':
        return '⏳';
      case 'processing':
        return '🔄';
      case 'completed':
        return '✅';
      case 'failed':
        return '❌';
      default:
        return '⚪';
    }
  };

  const formatDataSize = (size: number) => {
    if (size >= 1e9) return `${(size / 1e9).toFixed(2)} GB`;
    if (size >= 1e6) return `${(size / 1e6).toFixed(2)} MB`;
    if (size >= 1e3) return `${(size / 1e3).toFixed(2)} KB`;
    return `${size} B`;
  };

  const handleBulkAction = (action: string) => {
    if (onBulkAction && selectedItems.length > 0) {
      onBulkAction(action, selectedItems);
      setSelectedItems([]);
    }
  };

  if (loading) {
    return (
      <div className={`anchoring-queue-table loading ${className}`}>
        <div className="loading-spinner"></div>
        <div className="loading-text">Loading anchoring queue...</div>
      </div>
    );
  }

  return (
    <div className={`anchoring-queue-table ${className}`}>
      <div className="table-header">
        <div className="table-title">
          <h3>Anchoring Queue</h3>
          <span className="queue-count">{filteredAndSortedItems.length} items</span>
        </div>
        <div className="table-actions">
          {selectedItems.length > 0 && (
            <div className="bulk-actions">
              <button 
                className="btn danger"
                onClick={() => handleBulkAction('cancel')}
              >
                Cancel Selected ({selectedItems.length})
              </button>
              <button 
                className="btn secondary"
                onClick={() => handleBulkAction('retry')}
              >
                Retry Selected
              </button>
            </div>
          )}
          <button className="btn secondary" onClick={onRefresh}>
            🔄 Refresh
          </button>
        </div>
      </div>

      <div className="table-filters">
        <div className="filter-group">
          <label>Status:</label>
          <select 
            value={filterStatus} 
            onChange={(e) => setFilterStatus(e.target.value)}
          >
            <option value="">All Status</option>
            <option value="pending">Pending</option>
            <option value="processing">Processing</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
          </select>
        </div>
        <div className="filter-group">
          <label>Priority:</label>
          <select 
            value={filterPriority} 
            onChange={(e) => setFilterPriority(e.target.value)}
          >
            <option value="">All Priorities</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
      </div>

      <div className="table-container">
        <table className="anchoring-queue-content">
          <thead>
            <tr>
              <th className="checkbox-col">
                <input 
                  type="checkbox"
                  checked={selectedItems.length === items.length && items.length > 0}
                  onChange={(e) => handleSelectAll(e.target.checked)}
                />
              </th>
              <th 
                className="sortable"
                onClick={() => handleSort('sessionId')}
              >
                Session ID {sortField === 'sessionId' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th 
                className="sortable"
                onClick={() => handleSort('priority')}
              >
                Priority {sortField === 'priority' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th 
                className="sortable"
                onClick={() => handleSort('status')}
              >
                Status {sortField === 'status' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th 
                className="sortable"
                onClick={() => handleSort('dataSize')}
              >
                Data Size {sortField === 'dataSize' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th 
                className="sortable"
                onClick={() => handleSort('createdAt')}
              >
                Created {sortField === 'createdAt' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th 
                className="sortable"
                onClick={() => handleSort('estimatedTime')}
              >
                ETA {sortField === 'estimatedTime' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th>Block Info</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredAndSortedItems.map((item) => (
              <tr key={item.id} className="anchoring-item-row">
                <td className="checkbox-col">
                  <input 
                    type="checkbox"
                    checked={selectedItems.includes(item.id)}
                    onChange={(e) => handleSelectItem(item.id, e.target.checked)}
                  />
                </td>
                <td className="session-id">
                  <button 
                    className="session-link"
                    onClick={() => onItemSelect?.(item)}
                  >
                    {item.sessionId}
                  </button>
                </td>
                <td className="priority-cell">
                  <span className={`priority-badge ${getPriorityClass(item.priority)}`}>
                    {getPriorityIcon(item.priority)} {item.priority}
                  </span>
                </td>
                <td className="status-cell">
                  <span className={`status-badge ${getStatusClass(item.status)}`}>
                    {getStatusIcon(item.status)} {item.status}
                  </span>
                </td>
                <td className="data-size">{formatDataSize(item.dataSize)}</td>
                <td className="created-at">{item.createdAt}</td>
                <td className="estimated-time">{item.estimatedTime}</td>
                <td className="block-info">
                  {item.blockHeight ? (
                    <div className="block-details">
                      <div className="block-height">#{item.blockHeight}</div>
                      {item.transactionHash && (
                        <div className="tx-hash" title={item.transactionHash}>
                          {item.transactionHash.substring(0, 8)}...
                        </div>
                      )}
                    </div>
                  ) : (
                    <span className="no-block">Not anchored</span>
                  )}
                </td>
                <td className="actions-cell">
                  <div className="action-buttons">
                    <button 
                      className="btn-icon"
                      onClick={() => onItemSelect?.(item)}
                      title="View Details"
                    >
                      👁️
                    </button>
                    {item.status === 'pending' && (
                      <select 
                        className="priority-select"
                        value={item.priority}
                        onChange={(e) => onPriorityChange?.(item.id, e.target.value)}
                        title="Change Priority"
                      >
                        <option value="low">Low</option>
                        <option value="medium">Medium</option>
                        <option value="high">High</option>
                      </select>
                    )}
                    {item.status === 'pending' && (
                      <button 
                        className="btn-icon danger"
                        onClick={() => onCancelItem?.(item.id)}
                        title="Cancel Item"
                      >
                        ❌
                      </button>
                    )}
                    {item.status === 'failed' && (
                      <button 
                        className="btn-icon success"
                        onClick={() => onRetryItem?.(item.id)}
                        title="Retry Item"
                      >
                        🔄
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {filteredAndSortedItems.length === 0 && (
        <div className="empty-state">
          <div className="empty-icon">⛓️</div>
          <div className="empty-text">No anchoring items found</div>
          <div className="empty-subtext">
            {items.length === 0 
              ? 'No items in the anchoring queue'
              : 'Try adjusting your filters'
            }
          </div>
        </div>
      )}
    </div>
  );
};

export default AnchoringQueueTable;
