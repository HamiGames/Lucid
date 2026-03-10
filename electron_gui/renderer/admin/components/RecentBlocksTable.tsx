import React, { useState, useMemo } from 'react';

interface Block {
  height: number;
  hash: string;
  timestamp: string;
  transactions: number;
  size: number;
  difficulty: number;
  nonce: number;
  merkleRoot: string;
  previousHash: string;
  miner: string;
  gasUsed?: number;
  gasLimit?: number;
}

interface RecentBlocksTableProps {
  blocks: Block[];
  loading?: boolean;
  onBlockSelect?: (block: Block) => void;
  onViewTransaction?: (blockHash: string) => void;
  onRefresh?: () => void;
  className?: string;
}

export const RecentBlocksTable: React.FC<RecentBlocksTableProps> = ({
  blocks,
  loading = false,
  onBlockSelect,
  onViewTransaction,
  onRefresh,
  className = ''
}) => {
  const [sortField, setSortField] = useState<keyof Block>('height');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [searchTerm, setSearchTerm] = useState<string>('');

  const handleSort = (field: keyof Block) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const filteredAndSortedBlocks = useMemo(() => {
    let filtered = blocks.filter(block => {
      if (searchTerm && !block.hash.toLowerCase().includes(searchTerm.toLowerCase()) &&
          !block.height.toString().includes(searchTerm) &&
          !block.miner.toLowerCase().includes(searchTerm.toLowerCase())) return false;
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
  }, [blocks, searchTerm, sortField, sortDirection]);

  const formatBlockSize = (size: number) => {
    if (size >= 1e6) return `${(size / 1e6).toFixed(2)} MB`;
    if (size >= 1e3) return `${(size / 1e3).toFixed(2)} KB`;
    return `${size} B`;
  };

  const formatDifficulty = (difficulty: number) => {
    if (difficulty >= 1e12) return `${(difficulty / 1e12).toFixed(2)}T`;
    if (difficulty >= 1e9) return `${(difficulty / 1e9).toFixed(2)}B`;
    if (difficulty >= 1e6) return `${(difficulty / 1e6).toFixed(2)}M`;
    if (difficulty >= 1e3) return `${(difficulty / 1e3).toFixed(2)}K`;
    return difficulty.toFixed(2);
  };

  const formatHash = (hash: string) => {
    return `${hash.substring(0, 8)}...${hash.substring(hash.length - 8)}`;
  };

  const getTimeAgo = (timestamp: string) => {
    const now = new Date();
    const blockTime = new Date(timestamp);
    const diffMs = now.getTime() - blockTime.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffDays > 0) return `${diffDays}d ago`;
    if (diffHours > 0) return `${diffHours}h ago`;
    if (diffMins > 0) return `${diffMins}m ago`;
    return 'Just now';
  };

  if (loading) {
    return (
      <div className={`recent-blocks-table loading ${className}`}>
        <div className="loading-spinner"></div>
        <div className="loading-text">Loading recent blocks...</div>
      </div>
    );
  }

  return (
    <div className={`recent-blocks-table ${className}`}>
      <div className="table-header">
        <div className="table-title">
          <h3>Recent Blocks</h3>
          <span className="block-count">{filteredAndSortedBlocks.length} blocks</span>
        </div>
        <div className="table-actions">
          <button className="btn secondary" onClick={onRefresh}>
            🔄 Refresh
          </button>
        </div>
      </div>

      <div className="table-filters">
        <div className="filter-group">
          <label>Search:</label>
          <input 
            type="text"
            placeholder="Search by height, hash, or miner..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>

      <div className="table-container">
        <table className="recent-blocks-content">
          <thead>
            <tr>
              <th 
                className="sortable"
                onClick={() => handleSort('height')}
              >
                Height {sortField === 'height' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th 
                className="sortable"
                onClick={() => handleSort('hash')}
              >
                Hash {sortField === 'hash' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th 
                className="sortable"
                onClick={() => handleSort('timestamp')}
              >
                Time {sortField === 'timestamp' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th 
                className="sortable"
                onClick={() => handleSort('transactions')}
              >
                Transactions {sortField === 'transactions' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th 
                className="sortable"
                onClick={() => handleSort('size')}
              >
                Size {sortField === 'size' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th 
                className="sortable"
                onClick={() => handleSort('difficulty')}
              >
                Difficulty {sortField === 'difficulty' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th 
                className="sortable"
                onClick={() => handleSort('miner')}
              >
                Miner {sortField === 'miner' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredAndSortedBlocks.map((block) => (
              <tr key={block.height} className="block-row">
                <td className="block-height">
                  <button 
                    className="height-link"
                    onClick={() => onBlockSelect?.(block)}
                  >
                    #{block.height}
                  </button>
                </td>
                <td className="block-hash">
                  <button 
                    className="hash-link"
                    onClick={() => onBlockSelect?.(block)}
                    title={block.hash}
                  >
                    {formatHash(block.hash)}
                  </button>
                </td>
                <td className="block-time">
                  <div className="time-info">
                    <div className="timestamp">{new Date(block.timestamp).toLocaleString()}</div>
                    <div className="time-ago">{getTimeAgo(block.timestamp)}</div>
                  </div>
                </td>
                <td className="transaction-count">
                  <button 
                    className="tx-link"
                    onClick={() => onViewTransaction?.(block.hash)}
                    title="View transactions"
                  >
                    {block.transactions} tx
                  </button>
                </td>
                <td className="block-size">{formatBlockSize(block.size)}</td>
                <td className="block-difficulty">{formatDifficulty(block.difficulty)}</td>
                <td className="block-miner">
                  <span className="miner-address" title={block.miner}>
                    {block.miner.substring(0, 12)}...
                  </span>
                </td>
                <td className="actions-cell">
                  <div className="action-buttons">
                    <button 
                      className="btn-icon"
                      onClick={() => onBlockSelect?.(block)}
                      title="View Block Details"
                    >
                      👁️
                    </button>
                    <button 
                      className="btn-icon"
                      onClick={() => onViewTransaction?.(block.hash)}
                      title="View Transactions"
                    >
                      📋
                    </button>
                    <button 
                      className="btn-icon"
                      onClick={() => navigator.clipboard.writeText(block.hash)}
                      title="Copy Hash"
                    >
                      📋
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {filteredAndSortedBlocks.length === 0 && (
        <div className="empty-state">
          <div className="empty-icon">⛓️</div>
          <div className="empty-text">No blocks found</div>
          <div className="empty-subtext">
            {blocks.length === 0 
              ? 'No blocks are available'
              : 'Try adjusting your search'
            }
          </div>
        </div>
      )}
    </div>
  );
};

export default RecentBlocksTable;
