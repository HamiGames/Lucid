/**
 * Blockchain Service - Handles blockchain operations for admin interface
 * Provides blockchain monitoring, anchoring management, and blockchain analytics
 */

import { adminApi } from './adminApi';
import { Block, Transaction } from '../../../shared/types';

export interface BlockchainStatus {
  current_height: number;
  latest_block_hash: string;
  network_hashrate: number;
  difficulty: number;
  connected_peers: number;
  sync_status: 'synced' | 'syncing' | 'behind';
  last_block_time: string;
  average_block_time: number;
  network_health: 'healthy' | 'degraded' | 'critical';
}

export interface AnchoringQueueItem {
  session_id: string;
  user_id: string;
  priority: number;
  queued_at: string;
  estimated_anchor_time: string;
  data_size: number;
  merkle_root: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
}

export interface AnchoringResult {
  success: boolean;
  anchored_sessions: string[];
  failed_sessions: Array<{ session_id: string; error: string }>;
  total_transactions: number;
  gas_used: number;
  block_height: number;
}

export interface BlockchainAnalytics {
  total_blocks: number;
  blocks_today: number;
  blocks_this_week: number;
  blocks_this_month: number;
  average_block_time: number;
  total_transactions: number;
  transactions_today: number;
  anchoring_success_rate: number;
  network_hashrate_trend: Array<{ timestamp: string; hashrate: number }>;
  block_time_trend: Array<{ timestamp: string; block_time: number }>;
  transaction_volume_trend: Array<{ timestamp: string; count: number }>;
}

export interface BlockDetails {
  block_id: string;
  height: number;
  previous_hash: string;
  merkle_root: string;
  timestamp: string;
  transaction_count: number;
  size_bytes: number;
  gas_used: number;
  gas_limit: number;
  miner_address?: string;
  transactions: Transaction[];
  consensus_votes?: Array<{
    node_id: string;
    vote: 'approve' | 'reject';
    timestamp: string;
    signature: string;
  }>;
}

export interface TransactionDetails {
  transaction_id: string;
  type: 'session_anchor' | 'payout' | 'governance';
  from_address: string;
  to_address: string;
  amount?: number;
  gas_used: number;
  gas_price: number;
  timestamp: string;
  block_height: number;
  status: 'pending' | 'confirmed' | 'failed';
  data: any;
  signature: string;
}

export interface ForceAnchoringRequest {
  session_ids: string[];
  priority: 'low' | 'normal' | 'high' | 'urgent';
  reason?: string;
  max_gas_price?: number;
}

export interface BlockchainHealthCheck {
  overall_health: 'healthy' | 'degraded' | 'critical';
  sync_status: 'synced' | 'syncing' | 'behind';
  peer_connections: number;
  block_propagation_time: number;
  transaction_pool_size: number;
  memory_usage: number;
  disk_usage: number;
  network_latency: number;
  consensus_participation: number;
}

class BlockchainService {
  private blockchainStatusCache: BlockchainStatus | null = null;
  private anchoringQueueCache: AnchoringQueueItem[] = [];
  private recentBlocksCache: Block[] = [];
  private lastStatusUpdate: number = 0;
  private lastQueueUpdate: number = 0;
  private lastBlocksUpdate: number = 0;
  private readonly CACHE_DURATION = 10000; // 10 seconds for blockchain data

  /**
   * Get blockchain status
   */
  async getBlockchainStatus(forceRefresh: boolean = false): Promise<BlockchainStatus> {
    const now = Date.now();
    const isCacheValid = (now - this.lastStatusUpdate) < this.CACHE_DURATION;

    if (!forceRefresh && isCacheValid && this.blockchainStatusCache) {
      return this.blockchainStatusCache;
    }

    try {
      const status = await adminApi.getBlockchainStatus();
      
      this.blockchainStatusCache = status;
      this.lastStatusUpdate = now;
      
      return status;
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get anchoring queue
   */
  async getAnchoringQueue(forceRefresh: boolean = false): Promise<AnchoringQueueItem[]> {
    const now = Date.now();
    const isCacheValid = (now - this.lastQueueUpdate) < this.CACHE_DURATION;

    if (!forceRefresh && isCacheValid && this.anchoringQueueCache.length > 0) {
      return this.anchoringQueueCache;
    }

    try {
      const queue = await adminApi.getAnchoringQueue();
      
      this.anchoringQueueCache = queue;
      this.lastQueueUpdate = now;
      
      return queue;
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get recent blocks
   */
  async getRecentBlocks(limit: number = 10, forceRefresh: boolean = false): Promise<Block[]> {
    const now = Date.now();
    const isCacheValid = (now - this.lastBlocksUpdate) < this.CACHE_DURATION;

    if (!forceRefresh && isCacheValid && this.recentBlocksCache.length > 0) {
      return this.recentBlocksCache.slice(0, limit);
    }

    try {
      const blocks = await adminApi.getRecentBlocks(limit);
      
      this.recentBlocksCache = blocks;
      this.lastBlocksUpdate = now;
      
      return blocks;
    } catch (error) {
      throw error;
    }
  }

  /**
   * Force anchor sessions
   */
  async forceAnchorSessions(request: ForceAnchoringRequest): Promise<AnchoringResult> {
    try {
      const result = await adminApi.forceAnchoring(request.session_ids);
      
      // Clear cache to force refresh
      this.clearAnchoringCache();
      
      return {
        success: result.success,
        anchored_sessions: result.anchored_sessions,
        failed_sessions: result.failed_sessions,
        total_transactions: result.anchored_sessions.length,
        gas_used: 0, // Would be populated from actual result
        block_height: 0 // Would be populated from actual result
      };
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get block details by height
   */
  async getBlockDetails(height: number): Promise<BlockDetails> {
    try {
      // This would typically call a specific API endpoint
      // For now, we'll get it from recent blocks cache or fetch fresh
      const cached = this.recentBlocksCache.find(b => b.height === height);
      if (cached) {
        return this.enrichBlockDetails(cached);
      }

      // If not in cache, would fetch from API
      throw new Error(`Block ${height} not found in cache. API endpoint not implemented.`);
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get transaction details
   */
  async getTransactionDetails(transactionId: string): Promise<TransactionDetails> {
    try {
      // This would typically call a specific API endpoint
      // For now, we'll search through cached blocks
      for (const block of this.recentBlocksCache) {
        const transaction = block.transactions.find(t => t.transaction_id === transactionId);
        if (transaction) {
          return this.enrichTransactionDetails(transaction, block.height);
        }
      }

      throw new Error(`Transaction ${transactionId} not found in cache. API endpoint not implemented.`);
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get blockchain analytics
   */
  async getBlockchainAnalytics(timeRange: '1d' | '7d' | '30d' = '7d'): Promise<BlockchainAnalytics> {
    try {
      // Get recent blocks for analysis
      const blocks = await this.getRecentBlocks(1000, true);
      
      return this.calculateBlockchainAnalytics(blocks, timeRange);
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get blockchain health check
   */
  async getBlockchainHealthCheck(): Promise<BlockchainHealthCheck> {
    try {
      const status = await this.getBlockchainStatus();
      
      return {
        overall_health: this.determineOverallHealth(status),
        sync_status: status.sync_status,
        peer_connections: status.connected_peers,
        block_propagation_time: 2.5, // Would be calculated from actual metrics
        transaction_pool_size: 150, // Would be fetched from actual data
        memory_usage: 45.2, // Would be fetched from actual data
        disk_usage: 67.8, // Would be fetched from actual data
        network_latency: 120, // Would be calculated from actual metrics
        consensus_participation: 95.5 // Would be calculated from actual metrics
      };
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get anchoring statistics
   */
  async getAnchoringStatistics(): Promise<{
    total_anchored: number;
    pending_anchors: number;
    failed_anchors: number;
    success_rate: number;
    average_anchor_time: number;
    total_gas_used: number;
  }> {
    try {
      const queue = await this.getAnchoringQueue();
      
      return {
        total_anchored: queue.filter(item => item.status === 'completed').length,
        pending_anchors: queue.filter(item => item.status === 'queued' || item.status === 'processing').length,
        failed_anchors: queue.filter(item => item.status === 'failed').length,
        success_rate: 95.5, // Would be calculated from actual historical data
        average_anchor_time: 45.2, // Would be calculated from actual data
        total_gas_used: 125000 // Would be calculated from actual data
      };
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get network statistics
   */
  async getNetworkStatistics(): Promise<{
    total_nodes: number;
    active_miners: number;
    network_hashrate: number;
    difficulty: number;
    average_block_time: number;
    network_throughput: number;
  }> {
    try {
      const status = await this.getBlockchainStatus();
      
      return {
        total_nodes: status.connected_peers + 50, // Estimated total nodes
        active_miners: Math.floor(status.connected_peers * 0.3), // Estimated active miners
        network_hashrate: status.network_hashrate,
        difficulty: status.difficulty,
        average_block_time: status.average_block_time,
        network_throughput: status.network_hashrate / 1000 // Simplified throughput calculation
      };
    } catch (error) {
      throw error;
    }
  }

  /**
   * Monitor blockchain for new blocks
   */
  startBlockMonitoring(callback: (newBlock: Block) => void): () => void {
    const interval = setInterval(async () => {
      try {
        const blocks = await this.getRecentBlocks(1, true);
        if (blocks.length > 0) {
          const latestBlock = blocks[0];
          const cachedLatest = this.recentBlocksCache[0];
          
          if (!cachedLatest || latestBlock.block_id !== cachedLatest.block_id) {
            callback(latestBlock);
          }
        }
      } catch (error) {
        console.error('Block monitoring error:', error);
      }
    }, 5000); // Check every 5 seconds

    return () => clearInterval(interval);
  }

  /**
   * Monitor anchoring queue for changes
   */
  startQueueMonitoring(callback: (queue: AnchoringQueueItem[]) => void): () => void {
    const interval = setInterval(async () => {
      try {
        const queue = await this.getAnchoringQueue(true);
        callback(queue);
      } catch (error) {
        console.error('Queue monitoring error:', error);
      }
    }, 10000); // Check every 10 seconds

    return () => clearInterval(interval);
  }

  /**
   * Refresh blockchain data
   */
  async refreshBlockchainData(): Promise<void> {
    try {
      await Promise.all([
        this.getBlockchainStatus(true),
        this.getAnchoringQueue(true),
        this.getRecentBlocks(50, true)
      ]);
    } catch (error) {
      throw error;
    }
  }

  /**
   * Clear blockchain cache
   */
  clearCache(): void {
    this.blockchainStatusCache = null;
    this.anchoringQueueCache = [];
    this.recentBlocksCache = [];
    this.lastStatusUpdate = 0;
    this.lastQueueUpdate = 0;
    this.lastBlocksUpdate = 0;
  }

  /**
   * Clear anchoring-specific cache
   */
  clearAnchoringCache(): void {
    this.anchoringQueueCache = [];
    this.lastQueueUpdate = 0;
  }

  // Private helper methods
  private enrichBlockDetails(block: Block): BlockDetails {
    return {
      block_id: block.block_id,
      height: block.height,
      previous_hash: block.previous_hash,
      merkle_root: block.merkle_root,
      timestamp: block.timestamp,
      transaction_count: block.transactions.length,
      size_bytes: 1024 * 256, // Estimated block size
      gas_used: block.transactions.length * 21000, // Estimated gas usage
      gas_limit: 30000000, // Estimated gas limit
      miner_address: '0x0000000000000000000000000000000000000000', // Would be populated from actual data
      transactions: block.transactions,
      consensus_votes: block.consensus_votes
    };
  }

  private enrichTransactionDetails(transaction: Transaction, blockHeight: number): TransactionDetails {
    return {
      transaction_id: transaction.transaction_id,
      type: transaction.type,
      from_address: '0x0000000000000000000000000000000000000000', // Would be populated from actual data
      to_address: '0x0000000000000000000000000000000000000000', // Would be populated from actual data
      amount: 0, // Would be populated from actual data
      gas_used: 21000, // Estimated gas usage
      gas_price: 20000000000, // Estimated gas price (20 gwei)
      timestamp: transaction.timestamp,
      block_height: blockHeight,
      status: 'confirmed', // Would be determined from actual data
      data: transaction.data,
      signature: '0x0000000000000000000000000000000000000000000000000000000000000000' // Would be populated from actual data
    };
  }

  private calculateBlockchainAnalytics(blocks: Block[], timeRange: string): BlockchainAnalytics {
    const analytics: BlockchainAnalytics = {
      total_blocks: blocks.length,
      blocks_today: 0,
      blocks_this_week: 0,
      blocks_this_month: 0,
      average_block_time: 0,
      total_transactions: 0,
      transactions_today: 0,
      anchoring_success_rate: 95.5,
      network_hashrate_trend: [],
      block_time_trend: [],
      transaction_volume_trend: []
    };

    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const weekAgo = new Date(today.getTime() - (7 * 24 * 60 * 60 * 1000));
    const monthAgo = new Date(today.getTime() - (30 * 24 * 60 * 60 * 1000));

    let totalTransactions = 0;
    let blockTimes: number[] = [];

    blocks.forEach(block => {
      totalTransactions += block.transactions.length;
      
      // Count blocks by time period
      const blockDate = new Date(block.timestamp);
      if (blockDate >= today) {
        analytics.blocks_today++;
      }
      if (blockDate >= weekAgo) {
        analytics.blocks_this_week++;
      }
      if (blockDate >= monthAgo) {
        analytics.blocks_this_month++;
      }

      // Calculate block time (simplified)
      if (block.height > 0) {
        const prevBlock = blocks.find(b => b.height === block.height - 1);
        if (prevBlock) {
          const blockTime = new Date(block.timestamp).getTime() - new Date(prevBlock.timestamp).getTime();
          blockTimes.push(blockTime / 1000); // Convert to seconds
        }
      }
    });

    analytics.total_transactions = totalTransactions;
    analytics.transactions_today = totalTransactions; // Simplified

    if (blockTimes.length > 0) {
      analytics.average_block_time = blockTimes.reduce((sum, time) => sum + time, 0) / blockTimes.length;
    }

    // Generate trends (simplified)
    const daysBack = timeRange === '1d' ? 1 : timeRange === '7d' ? 7 : 30;
    for (let i = daysBack - 1; i >= 0; i--) {
      const date = new Date(today.getTime() - (i * 24 * 60 * 60 * 1000));
      const dayStart = new Date(date.getFullYear(), date.getMonth(), date.getDate());
      const dayEnd = new Date(dayStart.getTime() + (24 * 60 * 60 * 1000));
      
      const dayBlocks = blocks.filter(block => {
        const blockDate = new Date(block.timestamp);
        return blockDate >= dayStart && blockDate < dayEnd;
      });

      analytics.network_hashrate_trend.push({
        timestamp: dayStart.toISOString(),
        hashrate: 1000000 // Simplified
      });

      analytics.block_time_trend.push({
        timestamp: dayStart.toISOString(),
        block_time: dayBlocks.length > 0 ? 86400 / dayBlocks.length : 0 // Average block time for the day
      });

      analytics.transaction_volume_trend.push({
        timestamp: dayStart.toISOString(),
        count: dayBlocks.reduce((total, block) => total + block.transactions.length, 0)
      });
    }

    return analytics;
  }

  private determineOverallHealth(status: BlockchainStatus): 'healthy' | 'degraded' | 'critical' {
    if (status.sync_status === 'behind' || status.connected_peers < 3) {
      return 'critical';
    }
    
    if (status.sync_status === 'syncing' || status.connected_peers < 10) {
      return 'degraded';
    }
    
    return 'healthy';
  }
}

// Export singleton instance
export const blockchainService = new BlockchainService();
