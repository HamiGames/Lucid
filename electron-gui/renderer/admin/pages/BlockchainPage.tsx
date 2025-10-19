// electron-gui/renderer/admin/pages/BlockchainPage.tsx
// Admin Blockchain Management Page - Network status overview, anchoring queue management, recent blocks table

import React, { useState, useEffect, useMemo } from 'react';
import { DashboardLayout, GridLayout, CardLayout } from '../../common/components/Layout';
import { Modal, ConfirmModal } from '../../common/components/Modal';
import { TorIndicator } from '../../common/components/TorIndicator';
import { useToast } from '../../common/components/Toast';
import { useApi } from '../../common/hooks/useApi';
import { useTorStatus } from '../../common/hooks/useTorStatus';
import { useBlockchainInfo, useLatestBlock } from '../../common/hooks/useApi';
import { Block, Transaction, ConsensusVote } from '../../../shared/types';
import { TorStatus } from '../../../shared/tor-types';

interface BlockchainFilters {
  blockRange: {
    start: number;
    end: number;
  };
  transactionType: 'all' | 'session_anchor' | 'payout' | 'governance';
  status: 'all' | 'pending' | 'confirmed' | 'failed';
  search: string;
}

interface AnchoringQueueItem {
  sessionId: string;
  userId: string;
  merkleRoot: string;
  priority: 'low' | 'medium' | 'high' | 'critical';
  queuedAt: string;
  estimatedTime: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
}

interface NetworkStatus {
  totalBlocks: number;
  latestBlockHeight: number;
  totalTransactions: number;
  pendingTransactions: number;
  networkHashRate: number;
  averageBlockTime: number;
  consensusHealth: 'healthy' | 'degraded' | 'critical';
  activeValidators: number;
  totalValidators: number;
}

interface BulkAction {
  id: string;
  label: string;
  icon: string;
  action: (itemIds: string[]) => Promise<void>;
  requiresConfirmation: boolean;
  confirmationMessage: string;
}

const BlockchainPage: React.FC = () => {
  const [blocks, setBlocks] = useState<Block[]>([]);
  const [anchoringQueue, setAnchoringQueue] = useState<AnchoringQueueItem[]>([]);
  const [networkStatus, setNetworkStatus] = useState<NetworkStatus>({
    totalBlocks: 0,
    latestBlockHeight: 0,
    totalTransactions: 0,
    pendingTransactions: 0,
    networkHashRate: 0,
    averageBlockTime: 0,
    consensusHealth: 'healthy',
    activeValidators: 0,
    totalValidators: 0,
  });
  const [loading, setLoading] = useState(true);
  const [selectedQueueItems, setSelectedQueueItems] = useState<Set<string>>(new Set());
  const [showBlockDetails, setShowBlockDetails] = useState(false);
  const [selectedBlock, setSelectedBlock] = useState<Block | null>(null);

  const [filters, setFilters] = useState<BlockchainFilters>({
    blockRange: {
      start: 0,
      end: 0,
    },
    transactionType: 'all',
    status: 'all',
    search: '',
  });

  const torStatus = useTorStatus();
  const { showToast } = useToast();

  // API hooks
  const { data: blockchainInfo, loading: blockchainLoading } = useBlockchainInfo();
  const { data: latestBlock, loading: blockLoading } = useLatestBlock();

  // Update data when API responses change
  useEffect(() => {
    if (blockchainInfo && latestBlock) {
      setNetworkStatus({
        totalBlocks: blockchainInfo.total_blocks || 0,
        latestBlockHeight: blockchainInfo.latest_block_height || 0,
        totalTransactions: blockchainInfo.total_transactions || 0,
        pendingTransactions: blockchainInfo.pending_transactions || 0,
        networkHashRate: blockchainInfo.network_hash_rate || 0,
        averageBlockTime: blockchainInfo.average_block_time || 0,
        consensusHealth: blockchainInfo.consensus_health || 'healthy',
        activeValidators: blockchainInfo.active_validators || 0,
        totalValidators: blockchainInfo.total_validators || 0,
      });

      // Mock recent blocks data
      const mockBlocks: Block[] = Array.from({ length: 10 }, (_, i) => ({
        block_id: `block_${latestBlock.height - i}`,
        height: latestBlock.height - i,
        previous_hash: `hash_${latestBlock.height - i - 1}`,
        merkle_root: `merkle_${latestBlock.height - i}`,
        transactions: [],
        timestamp: new Date(Date.now() - i * 60000).toISOString(),
        consensus_votes: [],
      }));
      setBlocks(mockBlocks);

      // Mock anchoring queue data
      const mockQueue: AnchoringQueueItem[] = [
        {
          sessionId: 'session_001',
          userId: 'user_001',
          merkleRoot: 'merkle_root_001',
          priority: 'high',
          queuedAt: new Date(Date.now() - 300000).toISOString(),
          estimatedTime: '5 minutes',
          status: 'queued',
        },
        {
          sessionId: 'session_002',
          userId: 'user_002',
          merkleRoot: 'merkle_root_002',
          priority: 'medium',
          queuedAt: new Date(Date.now() - 600000).toISOString(),
          estimatedTime: '10 minutes',
          status: 'processing',
        },
        {
          sessionId: 'session_003',
          userId: 'user_003',
          merkleRoot: 'merkle_root_003',
          priority: 'critical',
          queuedAt: new Date(Date.now() - 120000).toISOString(),
          estimatedTime: '2 minutes',
          status: 'queued',
        },
      ];
      setAnchoringQueue(mockQueue);
    }
  }, [blockchainInfo, latestBlock]);

  // Filter blocks based on current filters
  const filteredBlocks = useMemo(() => {
    return blocks.filter(block => {
      // Block range filter
      if (filters.blockRange.start && block.height < filters.blockRange.start) {
        return false;
      }
      if (filters.blockRange.end && block.height > filters.blockRange.end) {
        return false;
      }

      // Search filter
      if (filters.search && !block.block_id.toLowerCase().includes(filters.search.toLowerCase())) {
        return false;
      }

      return true;
    });
  }, [blocks, filters]);

  // Filter anchoring queue
  const filteredQueue = useMemo(() => {
    return anchoringQueue.filter(item => {
      if (filters.search && !item.sessionId.toLowerCase().includes(filters.search.toLowerCase())) {
        return false;
      }
      if (filters.status !== 'all' && item.status !== filters.status) {
        return false;
      }
      return true;
    });
  }, [anchoringQueue, filters]);

  // Bulk actions for anchoring queue
  const bulkActions: BulkAction[] = [
    {
      id: 'process',
      label: 'Process Selected',
      icon: '⚡',
      action: handleProcessQueueItems,
      requiresConfirmation: true,
      confirmationMessage: 'Are you sure you want to process the selected anchoring queue items?',
    },
    {
      id: 'prioritize',
      label: 'Set High Priority',
      icon: '🔴',
      action: handlePrioritizeQueueItems,
      requiresConfirmation: true,
      confirmationMessage: 'Are you sure you want to set high priority for the selected items?',
    },
    {
      id: 'remove',
      label: 'Remove from Queue',
      icon: '🗑️',
      action: handleRemoveQueueItems,
      requiresConfirmation: true,
      confirmationMessage: 'Are you sure you want to remove the selected items from the anchoring queue?',
    },
  ];

  async function handleProcessQueueItems(itemIds: string[]): Promise<void> {
    try {
      // Implement queue processing logic
      showToast({
        type: 'success',
        title: 'Queue Items Processed',
        message: `${itemIds.length} anchoring queue items have been processed`,
      });
    } catch (error) {
      showToast({
        type: 'error',
        title: 'Processing Failed',
        message: error instanceof Error ? error.message : 'Failed to process queue items',
      });
    }
  }

  async function handlePrioritizeQueueItems(itemIds: string[]): Promise<void> {
    try {
      // Implement prioritization logic
      showToast({
        type: 'success',
        title: 'Priority Updated',
        message: `${itemIds.length} items have been set to high priority`,
      });
    } catch (error) {
      showToast({
        type: 'error',
        title: 'Priority Update Failed',
        message: error instanceof Error ? error.message : 'Failed to update priority',
      });
    }
  }

  async function handleRemoveQueueItems(itemIds: string[]): Promise<void> {
    try {
      // Implement removal logic
      showToast({
        type: 'success',
        title: 'Items Removed',
        message: `${itemIds.length} items have been removed from the anchoring queue`,
      });
    } catch (error) {
      showToast({
        type: 'error',
        title: 'Removal Failed',
        message: error instanceof Error ? error.message : 'Failed to remove items',
      });
    }
  }

  const handleQueueItemSelect = (itemId: string) => {
    const newSelected = new Set(selectedQueueItems);
    if (newSelected.has(itemId)) {
      newSelected.delete(itemId);
    } else {
      newSelected.add(itemId);
    }
    setSelectedQueueItems(newSelected);
  };

  const handleSelectAllQueue = () => {
    if (selectedQueueItems.size === filteredQueue.length) {
      setSelectedQueueItems(new Set());
    } else {
      setSelectedQueueItems(new Set(filteredQueue.map(item => item.sessionId)));
    }
  };

  const handleBulkAction = (action: BulkAction) => {
    if (selectedQueueItems.size === 0) {
      showToast({
        type: 'warning',
        title: 'No Items Selected',
        message: 'Please select at least one item to perform this action',
      });
      return;
    }

    if (action.requiresConfirmation) {
      setPendingBulkAction(action);
      setShowConfirmModal(true);
    } else {
      action.action(Array.from(selectedQueueItems));
    }
  };

  const confirmBulkAction = async () => {
    if (pendingBulkAction) {
      await pendingBulkAction.action(Array.from(selectedQueueItems));
      setShowConfirmModal(false);
      setPendingBulkAction(null);
    }
  };

  const handleBlockClick = (block: Block) => {
    setSelectedBlock(block);
    setShowBlockDetails(true);
  };

  const getPriorityColor = (priority: string): string => {
    switch (priority) {
      case 'critical': return 'bg-red-100 text-red-800';
      case 'high': return 'bg-orange-100 text-orange-800';
      case 'medium': return 'bg-yellow-100 text-yellow-800';
      case 'low': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'completed': return 'bg-green-100 text-green-800';
      case 'processing': return 'bg-blue-100 text-blue-800';
      case 'queued': return 'bg-yellow-100 text-yellow-800';
      case 'failed': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getConsensusHealthColor = (health: string): string => {
    switch (health) {
      case 'healthy': return 'bg-green-100 text-green-800';
      case 'degraded': return 'bg-yellow-100 text-yellow-800';
      case 'critical': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString();
  };

  const formatHashRate = (hashRate: number): string => {
    if (hashRate >= 1e9) return `${(hashRate / 1e9).toFixed(2)} GH/s`;
    if (hashRate >= 1e6) return `${(hashRate / 1e6).toFixed(2)} MH/s`;
    if (hashRate >= 1e3) return `${(hashRate / 1e3).toFixed(2)} KH/s`;
    return `${hashRate.toFixed(2)} H/s`;
  };

  const formatBlockTime = (seconds: number): string => {
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    return `${(seconds / 60).toFixed(1)}m`;
  };

  if (loading || blockchainLoading || blockLoading) {
    return (
      <DashboardLayout
        title="Blockchain Management"
        torStatus={torStatus}
        headerActions={
          <div className="flex items-center space-x-4">
            <TorIndicator status={torStatus} size="small" />
          </div>
        }
      >
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Loading blockchain data...</p>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout
      title="Blockchain Management"
      torStatus={torStatus}
      headerActions={
        <div className="flex items-center space-x-4">
          <TorIndicator status={torStatus} size="small" />
        </div>
      }
    >
      <div className="space-y-6">
        {/* Network Status Overview */}
        <GridLayout columns={4} gap="lg">
          <CardLayout
            title="Total Blocks"
            subtitle="Blockchain height"
            className="bg-gradient-to-r from-blue-500 to-blue-600 text-white"
          >
            <div className="text-3xl font-bold">{networkStatus.totalBlocks.toLocaleString()}</div>
            <div className="text-blue-100 text-sm">Blocks mined</div>
          </CardLayout>

          <CardLayout
            title="Transactions"
            subtitle="Total processed"
            className="bg-gradient-to-r from-green-500 to-green-600 text-white"
          >
            <div className="text-3xl font-bold">{networkStatus.totalTransactions.toLocaleString()}</div>
            <div className="text-green-100 text-sm">{networkStatus.pendingTransactions} pending</div>
          </CardLayout>

          <CardLayout
            title="Hash Rate"
            subtitle="Network power"
            className="bg-gradient-to-r from-purple-500 to-purple-600 text-white"
          >
            <div className="text-3xl font-bold">{formatHashRate(networkStatus.networkHashRate)}</div>
            <div className="text-purple-100 text-sm">Mining power</div>
          </CardLayout>

          <CardLayout
            title="Block Time"
            subtitle="Average time"
            className="bg-gradient-to-r from-orange-500 to-orange-600 text-white"
          >
            <div className="text-3xl font-bold">{formatBlockTime(networkStatus.averageBlockTime)}</div>
            <div className="text-orange-100 text-sm">Per block</div>
          </CardLayout>
        </GridLayout>

        {/* Consensus Health */}
        <CardLayout
          title="Consensus Health"
          subtitle="Network validation status"
          className="bg-white border border-gray-200"
        >
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex items-center space-x-3">
              <span className="text-sm font-medium text-gray-700">Consensus Status:</span>
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${getConsensusHealthColor(networkStatus.consensusHealth)}`}>
                {networkStatus.consensusHealth}
              </span>
            </div>
            <div className="flex items-center space-x-3">
              <span className="text-sm font-medium text-gray-700">Active Validators:</span>
              <span className="text-sm font-medium">{networkStatus.activeValidators}/{networkStatus.totalValidators}</span>
            </div>
            <div className="flex items-center space-x-3">
              <span className="text-sm font-medium text-gray-700">Latest Block:</span>
              <span className="text-sm font-medium font-mono">#{networkStatus.latestBlockHeight}</span>
            </div>
          </div>
        </CardLayout>

        {/* Anchoring Queue Management */}
        <CardLayout
          title="Anchoring Queue"
          subtitle="Session anchoring management"
          className="bg-white border border-gray-200"
        >
          <div className="mb-4">
            <div className="flex justify-between items-center mb-4">
              <div className="flex space-x-4">
                <select
                  value={filters.status}
                  onChange={(e) => setFilters(prev => ({ ...prev, status: e.target.value as any }))}
                  className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="all">All Statuses</option>
                  <option value="queued">Queued</option>
                  <option value="processing">Processing</option>
                  <option value="completed">Completed</option>
                  <option value="failed">Failed</option>
                </select>
                <input
                  type="text"
                  value={filters.search}
                  onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
                  placeholder="Search session IDs"
                  className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div className="text-sm text-gray-600">
                {filteredQueue.length} items in queue
              </div>
            </div>

            {/* Bulk Actions */}
            {selectedQueueItems.size > 0 && (
              <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-blue-800">
                    {selectedQueueItems.size} items selected
                  </span>
                  <button
                    onClick={() => setSelectedQueueItems(new Set())}
                    className="text-sm text-blue-600 hover:text-blue-800"
                  >
                    Clear Selection
                  </button>
                </div>
                <div className="flex flex-wrap gap-2">
                  {bulkActions.map((action) => (
                    <button
                      key={action.id}
                      onClick={() => handleBulkAction(action)}
                      className="flex items-center space-x-1 px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 transition-colors"
                    >
                      <span>{action.icon}</span>
                      <span>{action.label}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Queue Table */}
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left p-3">
                      <input
                        type="checkbox"
                        checked={selectedQueueItems.size === filteredQueue.length && filteredQueue.length > 0}
                        onChange={handleSelectAllQueue}
                        className="rounded border-gray-300"
                      />
                    </th>
                    <th className="text-left p-3 font-medium">Session ID</th>
                    <th className="text-left p-3 font-medium">User ID</th>
                    <th className="text-left p-3 font-medium">Priority</th>
                    <th className="text-left p-3 font-medium">Status</th>
                    <th className="text-left p-3 font-medium">Queued At</th>
                    <th className="text-left p-3 font-medium">Est. Time</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredQueue.map((item) => (
                    <tr key={item.sessionId} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="p-3">
                        <input
                          type="checkbox"
                          checked={selectedQueueItems.has(item.sessionId)}
                          onChange={() => handleQueueItemSelect(item.sessionId)}
                          className="rounded border-gray-300"
                        />
                      </td>
                      <td className="p-3 font-mono text-sm">{item.sessionId.substring(0, 12)}...</td>
                      <td className="p-3 font-mono text-sm">{item.userId.substring(0, 12)}...</td>
                      <td className="p-3">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getPriorityColor(item.priority)}`}>
                          {item.priority}
                        </span>
                      </td>
                      <td className="p-3">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(item.status)}`}>
                          {item.status}
                        </span>
                      </td>
                      <td className="p-3 text-sm">{formatDate(item.queuedAt)}</td>
                      <td className="p-3 text-sm">{item.estimatedTime}</td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {filteredQueue.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  <div className="text-4xl mb-2">⛓️</div>
                  <p>No anchoring queue items found</p>
                  <p className="text-sm">Try adjusting your filters</p>
                </div>
              )}
            </div>
          </div>
        </CardLayout>

        {/* Recent Blocks */}
        <CardLayout
          title="Recent Blocks"
          subtitle="Latest blockchain blocks"
          className="bg-white border border-gray-200"
        >
          <div className="mb-4">
            <div className="flex space-x-4 mb-4">
              <input
                type="number"
                placeholder="Start block height"
                value={filters.blockRange.start || ''}
                onChange={(e) => setFilters(prev => ({ 
                  ...prev, 
                  blockRange: { ...prev.blockRange, start: Number(e.target.value) }
                }))}
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <input
                type="number"
                placeholder="End block height"
                value={filters.blockRange.end || ''}
                onChange={(e) => setFilters(prev => ({ 
                  ...prev, 
                  blockRange: { ...prev.blockRange, end: Number(e.target.value) }
                }))}
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <input
                type="text"
                value={filters.search}
                onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
                placeholder="Search block IDs"
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left p-3 font-medium">Height</th>
                    <th className="text-left p-3 font-medium">Block ID</th>
                    <th className="text-left p-3 font-medium">Previous Hash</th>
                    <th className="text-left p-3 font-medium">Merkle Root</th>
                    <th className="text-left p-3 font-medium">Transactions</th>
                    <th className="text-left p-3 font-medium">Timestamp</th>
                    <th className="text-left p-3 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredBlocks.map((block) => (
                    <tr key={block.block_id} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="p-3 font-mono text-sm">#{block.height}</td>
                      <td className="p-3 font-mono text-sm">{block.block_id.substring(0, 12)}...</td>
                      <td className="p-3 font-mono text-sm">{block.previous_hash.substring(0, 12)}...</td>
                      <td className="p-3 font-mono text-sm">{block.merkle_root.substring(0, 12)}...</td>
                      <td className="p-3 text-sm">{block.transactions.length}</td>
                      <td className="p-3 text-sm">{formatDate(block.timestamp)}</td>
                      <td className="p-3">
                        <button
                          onClick={() => handleBlockClick(block)}
                          className="px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 transition-colors"
                        >
                          View
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {filteredBlocks.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  <div className="text-4xl mb-2">🧱</div>
                  <p>No blocks found</p>
                  <p className="text-sm">Try adjusting your filters</p>
                </div>
              )}
            </div>
          </div>
        </CardLayout>
      </div>

      {/* Block Details Modal */}
      <Modal
        isOpen={showBlockDetails}
        onClose={() => setShowBlockDetails(false)}
        title="Block Details"
        size="lg"
      >
        {selectedBlock && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Block Height</label>
                <p className="mt-1 text-sm text-gray-900 font-mono">#{selectedBlock.height}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Block ID</label>
                <p className="mt-1 text-sm text-gray-900 font-mono">{selectedBlock.block_id}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Previous Hash</label>
                <p className="mt-1 text-sm text-gray-900 font-mono">{selectedBlock.previous_hash}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Merkle Root</label>
                <p className="mt-1 text-sm text-gray-900 font-mono">{selectedBlock.merkle_root}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Transactions</label>
                <p className="mt-1 text-sm text-gray-900">{selectedBlock.transactions.length}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Timestamp</label>
                <p className="mt-1 text-sm text-gray-900">{formatDate(selectedBlock.timestamp)}</p>
              </div>
            </div>

            {selectedBlock.transactions.length > 0 && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Transactions</label>
                <div className="space-y-2 max-h-40 overflow-y-auto">
                  {selectedBlock.transactions.map((tx, index) => (
                    <div key={index} className="p-2 bg-gray-50 rounded border">
                      <div className="text-sm">
                        <div><strong>Type:</strong> {tx.type}</div>
                        <div><strong>ID:</strong> {tx.transaction_id}</div>
                        <div><strong>Timestamp:</strong> {formatDate(tx.timestamp)}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {selectedBlock.consensus_votes && selectedBlock.consensus_votes.length > 0 && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Consensus Votes</label>
                <div className="space-y-2 max-h-40 overflow-y-auto">
                  {selectedBlock.consensus_votes.map((vote, index) => (
                    <div key={index} className="p-2 bg-gray-50 rounded border">
                      <div className="text-sm">
                        <div><strong>Node:</strong> {vote.node_id}</div>
                        <div><strong>Vote:</strong> {vote.vote}</div>
                        <div><strong>Timestamp:</strong> {formatDate(vote.timestamp)}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* Bulk Action Confirmation Modal */}
      <ConfirmModal
        isOpen={showConfirmModal}
        onClose={() => setShowConfirmModal(false)}
        onConfirm={confirmBulkAction}
        title="Confirm Bulk Action"
        message={pendingBulkAction?.confirmationMessage || ''}
        confirmText="Confirm"
        cancelText="Cancel"
        type="warning"
      />
    </DashboardLayout>
  );
};

export default BlockchainPage;
