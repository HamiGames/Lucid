import { LucidAPIClient } from '../../../shared/api-client';

// Types
interface PoolInfo {
  pool_id: string;
  name: string;
  description: string;
  operator_id: string;
  total_nodes: number;
  active_nodes: number;
  total_poot_score: number;
  average_poot_score: number;
  pool_performance: number;
  created_at: string;
  status: 'active' | 'inactive' | 'maintenance';
}

interface PoolNode {
  node_id: string;
  operator_id: string;
  status: 'active' | 'inactive' | 'maintenance';
  poot_score: number;
  uptime_percentage: number;
  last_activity: string;
  contribution_percentage: number;
}

interface PoolStats {
  total_sessions_processed: number;
  total_data_processed: number;
  average_response_time: number;
  success_rate: number;
  total_earnings: number;
  pool_share_percentage: number;
}

interface PoolLeaderboard {
  rank: number;
  node_id: string;
  operator_id: string;
  poot_score: number;
  contribution_percentage: number;
  uptime_percentage: number;
}

interface PoolJoinRequest {
  pool_id: string;
  reason?: string;
}

interface PoolLeaveRequest {
  reason?: string;
}

interface PoolActionResponse {
  success: boolean;
  message: string;
  action_id?: string;
}

class PoolService {
  private apiClient: LucidAPIClient;
  private currentPoolCache: PoolInfo | null = null;
  private poolsListCache: PoolInfo[] = [];
  private lastCacheUpdate: number = 0;
  private readonly CACHE_DURATION = 60000; // 1 minute

  constructor(apiClient: LucidAPIClient) {
    this.apiClient = apiClient;
  }

  // Pool Information
  async getCurrentPool(forceRefresh: boolean = false): Promise<PoolInfo | null> {
    const now = Date.now();
    
    if (!forceRefresh && this.currentPoolCache && (now - this.lastCacheUpdate) < this.CACHE_DURATION) {
      return this.currentPoolCache;
    }

    try {
      const response = await this.apiClient.get('/node/pool/current');
      this.currentPoolCache = response.data;
      this.lastCacheUpdate = now;
      return this.currentPoolCache;
    } catch (error) {
      if (error.response?.status === 404) {
        this.currentPoolCache = null;
        return null;
      }
      throw new Error(`Failed to get current pool: ${error}`);
    }
  }

  async getPoolInfo(poolId: string): Promise<PoolInfo> {
    try {
      const response = await this.apiClient.get(`/node/pool/${poolId}`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get pool info: ${error}`);
    }
  }

  async getAvailablePools(forceRefresh: boolean = false): Promise<PoolInfo[]> {
    const now = Date.now();
    
    if (!forceRefresh && this.poolsListCache.length > 0 && (now - this.lastCacheUpdate) < this.CACHE_DURATION) {
      return this.poolsListCache;
    }

    try {
      const response = await this.apiClient.get('/node/pools/available');
      this.poolsListCache = response.data;
      this.lastCacheUpdate = now;
      return this.poolsListCache;
    } catch (error) {
      throw new Error(`Failed to get available pools: ${error}`);
    }
  }

  // Pool Management
  async joinPool(request: PoolJoinRequest): Promise<PoolActionResponse> {
    try {
      const response = await this.apiClient.post(`/node/pool/${request.pool_id}/join`, {
        reason: request.reason,
      });
      this.currentPoolCache = null; // Invalidate cache
      this.poolsListCache = []; // Invalidate pools list cache
      return response.data;
    } catch (error) {
      throw new Error(`Failed to join pool: ${error}`);
    }
  }

  async leavePool(request: PoolLeaveRequest = {}): Promise<PoolActionResponse> {
    try {
      const response = await this.apiClient.post('/node/pool/leave', {
        reason: request.reason,
      });
      this.currentPoolCache = null; // Invalidate cache
      return response.data;
    } catch (error) {
      throw new Error(`Failed to leave pool: ${error}`);
    }
  }

  async switchPool(poolId: string, reason?: string): Promise<PoolActionResponse> {
    try {
      // First leave current pool, then join new pool
      await this.leavePool({ reason: `Switching to pool ${poolId}` });
      return await this.joinPool({ pool_id: poolId, reason });
    } catch (error) {
      throw new Error(`Failed to switch pool: ${error}`);
    }
  }

  // Pool Statistics
  async getPoolStats(poolId: string): Promise<PoolStats> {
    try {
      const response = await this.apiClient.get(`/node/pool/${poolId}/stats`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get pool stats: ${error}`);
    }
  }

  async getPoolNodes(poolId: string): Promise<PoolNode[]> {
    try {
      const response = await this.apiClient.get(`/node/pool/${poolId}/nodes`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get pool nodes: ${error}`);
    }
  }

  async getPoolLeaderboard(poolId: string): Promise<PoolLeaderboard[]> {
    try {
      const response = await this.apiClient.get(`/node/pool/${poolId}/leaderboard`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get pool leaderboard: ${error}`);
    }
  }

  // Pool Performance
  async getPoolPerformance(poolId: string, timeRange: '1h' | '6h' | '24h' | '7d' = '24h'): Promise<{
    performance_history: Array<{
      timestamp: string;
      performance: number;
      active_nodes: number;
      total_sessions: number;
      success_rate: number;
    }>;
    average_performance: number;
    performance_trend: 'up' | 'down' | 'stable';
  }> {
    try {
      const response = await this.apiClient.get(`/node/pool/${poolId}/performance?timeRange=${timeRange}`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get pool performance: ${error}`);
    }
  }

  async getPoolEarnings(poolId: string, timeRange: '1h' | '6h' | '24h' | '7d' = '24h'): Promise<{
    total_earnings: number;
    earnings_history: Array<{
      timestamp: string;
      earnings: number;
      session_count: number;
      average_per_session: number;
    }>;
    earnings_distribution: Array<{
      node_id: string;
      operator_id: string;
      earnings: number;
      percentage: number;
    }>;
  }> {
    try {
      const response = await this.apiClient.get(`/node/pool/${poolId}/earnings?timeRange=${timeRange}`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get pool earnings: ${error}`);
    }
  }

  // Pool Activities
  async getPoolActivities(poolId: string, limit: number = 50): Promise<Array<{
    id: string;
    type: 'node_joined' | 'node_left' | 'performance_update' | 'earnings_update';
    description: string;
    timestamp: string;
    metadata?: Record<string, any>;
  }>> {
    try {
      const response = await this.apiClient.get(`/node/pool/${poolId}/activities?limit=${limit}`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get pool activities: ${error}`);
    }
  }

  // Pool Recommendations
  async getPoolRecommendations(): Promise<Array<{
    pool_id: string;
    pool_name: string;
    recommendation_score: number;
    reasons: string[];
    benefits: string[];
  }>> {
    try {
      const response = await this.apiClient.get('/node/pool/recommendations');
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get pool recommendations: ${error}`);
    }
  }

  async analyzePoolCompatibility(poolId: string): Promise<{
    compatibility_score: number;
    compatibility_factors: Array<{
      factor: string;
      score: number;
      weight: number;
      description: string;
    }>;
    recommendations: string[];
    potential_benefits: string[];
    potential_risks: string[];
  }> {
    try {
      const response = await this.apiClient.get(`/node/pool/${poolId}/compatibility`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to analyze pool compatibility: ${error}`);
    }
  }

  // Pool Settings
  async getPoolSettings(poolId: string): Promise<{
    auto_join: boolean;
    notification_preferences: {
      performance_updates: boolean;
      earnings_updates: boolean;
      pool_activities: boolean;
      maintenance_notices: boolean;
    };
    contribution_settings: {
      max_contribution: number;
      min_contribution: number;
      auto_adjust: boolean;
    };
  }> {
    try {
      const response = await this.apiClient.get(`/node/pool/${poolId}/settings`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get pool settings: ${error}`);
    }
  }

  async updatePoolSettings(poolId: string, settings: Partial<{
    auto_join: boolean;
    notification_preferences: Partial<{
      performance_updates: boolean;
      earnings_updates: boolean;
      pool_activities: boolean;
      maintenance_notices: boolean;
    }>;
    contribution_settings: Partial<{
      max_contribution: number;
      min_contribution: number;
      auto_adjust: boolean;
    }>;
  }>): Promise<{ success: boolean; message: string }> {
    try {
      const response = await this.apiClient.put(`/node/pool/${poolId}/settings`, settings);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to update pool settings: ${error}`);
    }
  }

  // Pool Monitoring
  async startPoolMonitoring(poolId: string): Promise<{ success: boolean; message: string }> {
    try {
      const response = await this.apiClient.post(`/node/pool/${poolId}/monitoring/start`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to start pool monitoring: ${error}`);
    }
  }

  async stopPoolMonitoring(poolId: string): Promise<{ success: boolean; message: string }> {
    try {
      const response = await this.apiClient.post(`/node/pool/${poolId}/monitoring/stop`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to stop pool monitoring: ${error}`);
    }
  }

  async getPoolMonitoringStatus(poolId: string): Promise<{
    is_monitoring: boolean;
    monitoring_started: string | null;
    last_update: string | null;
    update_frequency: number;
  }> {
    try {
      const response = await this.apiClient.get(`/node/pool/${poolId}/monitoring/status`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get pool monitoring status: ${error}`);
    }
  }

  // Pool Health Check
  async checkPoolHealth(poolId: string): Promise<{
    overall_health: 'healthy' | 'warning' | 'critical';
    health_checks: Array<{
      check_name: string;
      status: 'pass' | 'warning' | 'fail';
      message: string;
      recommendation?: string;
    }>;
    performance_metrics: {
      response_time: number;
      success_rate: number;
      active_nodes_ratio: number;
      pool_stability: number;
    };
  }> {
    try {
      const response = await this.apiClient.get(`/node/pool/${poolId}/health`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to check pool health: ${error}`);
    }
  }

  // Cache Management
  clearCache(): void {
    this.currentPoolCache = null;
    this.poolsListCache = [];
    this.lastCacheUpdate = 0;
  }

  getCachedCurrentPool(): PoolInfo | null {
    return this.currentPoolCache;
  }

  getCachedAvailablePools(): PoolInfo[] {
    return this.poolsListCache;
  }

  isCacheValid(): boolean {
    const now = Date.now();
    return (now - this.lastCacheUpdate) < this.CACHE_DURATION;
  }

  // Utility Methods
  async isNodeInPool(): Promise<boolean> {
    const currentPool = await this.getCurrentPool();
    return currentPool !== null;
  }

  async getNodePoolRank(poolId: string): Promise<number | null> {
    try {
      const leaderboard = await this.getPoolLeaderboard(poolId);
      const nodeId = (await this.apiClient.get('/node/info')).data.node_id;
      
      const rank = leaderboard.findIndex(node => node.node_id === nodeId);
      return rank >= 0 ? rank + 1 : null;
    } catch (error) {
      return null;
    }
  }

  async getNodeContributionPercentage(poolId: string): Promise<number> {
    try {
      const nodes = await this.getPoolNodes(poolId);
      const nodeId = (await this.apiClient.get('/node/info')).data.node_id;
      
      const node = nodes.find(n => n.node_id === nodeId);
      return node ? node.contribution_percentage : 0;
    } catch (error) {
      return 0;
    }
  }
}

export { PoolService };
export type {
  PoolInfo,
  PoolNode,
  PoolStats,
  PoolLeaderboard,
  PoolJoinRequest,
  PoolLeaveRequest,
  PoolActionResponse,
};
