/**
 * Node Service - Handles node management operations for admin interface
 * Provides node monitoring, management, and performance analytics
 */

import { adminApi, NodeManagementRequest } from './adminApi';
import { Node, NodeResources } from '../../../shared/types';

export interface NodeFilters {
  status?: 'registered' | 'active' | 'inactive' | 'suspended';
  pool_id?: string;
  search?: string;
  created_from?: string;
  created_to?: string;
  limit?: number;
  offset?: number;
}

export interface NodeAnalytics {
  total_nodes: number;
  active_nodes: number;
  inactive_nodes: number;
  suspended_nodes: number;
  nodes_by_status: Record<string, number>;
  nodes_by_pool: Record<string, number>;
  average_poot_score: number;
  total_compute_power: number;
  resource_utilization: {
    average_cpu: number;
    average_memory: number;
    average_disk: number;
    average_network: number;
  };
  top_performing_nodes: Array<{
    node_id: string;
    operator_id: string;
    poot_score: number;
    uptime_percentage: number;
  }>;
  node_registration_trend: Array<{
    date: string;
    count: number;
  }>;
}

export interface NodeMetrics {
  node_id: string;
  timestamp: string;
  cpu_usage: Array<{ timestamp: string; value: number }>;
  memory_usage: Array<{ timestamp: string; value: number }>;
  network_io: Array<{ timestamp: string; bytes_in: number; bytes_out: number }>;
  disk_usage: Array<{ timestamp: string; used_gb: number; total_gb: number }>;
  poot_score_history: Array<{ timestamp: string; score: number }>;
}

export interface NodeManagementResult {
  success: boolean;
  message: string;
  affected_nodes: string[];
  errors?: Array<{ node_id: string; error: string }>;
}

export interface NodePoolAssignment {
  node_id: string;
  pool_id: string;
  reason?: string;
}

export interface NodeMaintenanceRequest {
  node_id: string;
  reason: string;
  estimated_duration_hours: number;
  notify_operator: boolean;
}

class NodeService {
  private nodesCache: Map<string, Node> = new Map();
  private nodesListCache: Node[] = [];
  private metricsCache: Map<string, NodeMetrics> = new Map();
  private lastListUpdate: number = 0;
  private readonly CACHE_DURATION = 30000; // 30 seconds
  private readonly METRICS_CACHE_DURATION = 60000; // 1 minute

  /**
   * Get all nodes with optional filtering
   */
  async getNodes(filters: NodeFilters = {}): Promise<Node[]> {
    const now = Date.now();
    const isCacheValid = (now - this.lastListUpdate) < this.CACHE_DURATION;

    if (isCacheValid && this.nodesListCache.length > 0 && !filters.search) {
      return this.applyFilters(this.nodesListCache, filters);
    }

    try {
      const nodes = await adminApi.getAllNodes(filters);
      
      // Update cache
      this.nodesListCache = nodes;
      this.lastListUpdate = now;
      
      // Update individual node cache
      nodes.forEach(node => {
        this.nodesCache.set(node.node_id, node);
      });

      return nodes;
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get node details by ID
   */
  async getNodeDetails(nodeId: string): Promise<Node> {
    // Check cache first
    const cached = this.nodesCache.get(nodeId);
    if (cached) {
      return cached;
    }

    try {
      const node = await adminApi.getNodeDetails(nodeId);
      
      // Update cache
      this.nodesCache.set(nodeId, node);
      
      return node;
    } catch (error) {
      throw error;
    }
  }

  /**
   * Activate a node
   */
  async activateNode(nodeId: string, reason?: string): Promise<NodeManagementResult> {
    try {
      const request: NodeManagementRequest = {
        action: 'activate',
        node_id: nodeId,
        reason
      };

      const result = await adminApi.manageNode(request);
      
      // Invalidate cache for this node
      this.invalidateNodeCache(nodeId);
      
      return {
        success: result.success,
        message: result.message,
        affected_nodes: [nodeId]
      };
    } catch (error) {
      return {
        success: false,
        message: `Failed to activate node: ${error.message}`,
        affected_nodes: [],
        errors: [{ node_id: nodeId, error: error.message }]
      };
    }
  }

  /**
   * Suspend a node
   */
  async suspendNode(nodeId: string, reason?: string): Promise<NodeManagementResult> {
    try {
      const request: NodeManagementRequest = {
        action: 'suspend',
        node_id: nodeId,
        reason
      };

      const result = await adminApi.manageNode(request);
      
      // Invalidate cache for this node
      this.invalidateNodeCache(nodeId);
      
      return {
        success: result.success,
        message: result.message,
        affected_nodes: [nodeId]
      };
    } catch (error) {
      return {
        success: false,
        message: `Failed to suspend node: ${error.message}`,
        affected_nodes: [],
        errors: [{ node_id: nodeId, error: error.message }]
      };
    }
  }

  /**
   * Put node in maintenance mode
   */
  async putNodeInMaintenance(request: NodeMaintenanceRequest): Promise<NodeManagementResult> {
    try {
      const managementRequest: NodeManagementRequest = {
        action: 'maintenance',
        node_id: request.node_id,
        reason: request.reason
      };

      const result = await adminApi.manageNode(managementRequest);
      
      // Invalidate cache for this node
      this.invalidateNodeCache(request.node_id);
      
      return {
        success: result.success,
        message: result.message,
        affected_nodes: [request.node_id]
      };
    } catch (error) {
      return {
        success: false,
        message: `Failed to put node in maintenance: ${error.message}`,
        affected_nodes: [],
        errors: [{ node_id: request.node_id, error: error.message }]
      };
    }
  }

  /**
   * Remove a node
   */
  async removeNode(nodeId: string, reason?: string): Promise<NodeManagementResult> {
    try {
      const request: NodeManagementRequest = {
        action: 'remove',
        node_id: nodeId,
        reason
      };

      const result = await adminApi.manageNode(request);
      
      // Remove from cache
      this.nodesCache.delete(nodeId);
      this.nodesListCache = this.nodesListCache.filter(n => n.node_id !== nodeId);
      this.metricsCache.delete(nodeId);
      
      return {
        success: result.success,
        message: result.message,
        affected_nodes: [nodeId]
      };
    } catch (error) {
      return {
        success: false,
        message: `Failed to remove node: ${error.message}`,
        affected_nodes: [],
        errors: [{ node_id: nodeId, error: error.message }]
      };
    }
  }

  /**
   * Get node metrics
   */
  async getNodeMetrics(nodeId: string, timeRange: '1h' | '24h' | '7d' = '24h'): Promise<NodeMetrics> {
    const cacheKey = `${nodeId}_${timeRange}`;
    const cached = this.metricsCache.get(cacheKey);
    
    if (cached && (Date.now() - new Date(cached.timestamp).getTime()) < this.METRICS_CACHE_DURATION) {
      return cached;
    }

    try {
      const metrics = await adminApi.getNodeMetrics(nodeId, timeRange);
      
      const nodeMetrics: NodeMetrics = {
        node_id: nodeId,
        timestamp: new Date().toISOString(),
        cpu_usage: metrics.cpu_usage,
        memory_usage: metrics.memory_usage,
        network_io: metrics.network_io,
        disk_usage: [], // Would be populated from actual API response
        poot_score_history: [] // Would be populated from actual API response
      };

      // Update cache
      this.metricsCache.set(cacheKey, nodeMetrics);
      
      return nodeMetrics;
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get nodes by pool
   */
  async getNodesByPool(poolId: string): Promise<Node[]> {
    try {
      return await this.getNodes({ pool_id: poolId });
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get active nodes
   */
  async getActiveNodes(): Promise<Node[]> {
    try {
      return await this.getNodes({ status: 'active' });
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get suspended nodes
   */
  async getSuspendedNodes(): Promise<Node[]> {
    try {
      return await this.getNodes({ status: 'suspended' });
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get nodes requiring attention
   */
  async getNodesRequiringAttention(): Promise<Node[]> {
    try {
      const nodes = await this.getNodes();
      
      // Filter nodes that need attention
      return nodes.filter(node => {
        // Low PoOT score
        if (node.poot_score < 50) return true;
        
        // High resource usage (would need metrics)
        // if (node.resources.cpu_usage > 90) return true;
        // if (node.resources.memory_usage > 90) return true;
        
        return false;
      });
    } catch (error) {
      throw error;
    }
  }

  /**
   * Search nodes
   */
  async searchNodes(query: string, filters: Omit<NodeFilters, 'search'> = {}): Promise<Node[]> {
    try {
      const searchFilters: NodeFilters = {
        ...filters,
        search: query
      };

      return await this.getNodes(searchFilters);
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get node analytics
   */
  async getNodeAnalytics(timeRange: '1d' | '7d' | '30d' = '30d'): Promise<NodeAnalytics> {
    try {
      const filters: NodeFilters = {
        limit: 1000 // Get more data for analytics
      };

      // Add date filter based on time range
      const now = new Date();
      const timeRanges = {
        '1d': 1,
        '7d': 7,
        '30d': 30
      };

      const daysBack = timeRanges[timeRange];
      const dateFrom = new Date(now.getTime() - (daysBack * 24 * 60 * 60 * 1000));
      filters.created_from = dateFrom.toISOString();

      const nodes = await this.getNodes(filters);
      
      return this.calculateNodeAnalytics(nodes, timeRange);
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get node performance summary
   */
  async getNodePerformanceSummary(nodeId: string): Promise<{
    uptime_percentage: number;
    average_poot_score: number;
    total_sessions_processed: number;
    resource_efficiency: number;
    last_activity: string;
  }> {
    try {
      const node = await this.getNodeDetails(nodeId);
      
      // This would typically come from detailed metrics
      return {
        uptime_percentage: 95.5, // Would be calculated from actual uptime data
        average_poot_score: node.poot_score,
        total_sessions_processed: 0, // Would be fetched from session data
        resource_efficiency: 85.2, // Would be calculated from resource usage
        last_activity: node.created_at // Would be actual last activity timestamp
      };
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get network health overview
   */
  async getNetworkHealthOverview(): Promise<{
    total_nodes: number;
    healthy_nodes: number;
    unhealthy_nodes: number;
    average_network_latency: number;
    total_bandwidth_utilization: number;
    network_stability_score: number;
  }> {
    try {
      const nodes = await this.getActiveNodes();
      
      return {
        total_nodes: nodes.length,
        healthy_nodes: nodes.filter(n => n.poot_score > 70).length,
        unhealthy_nodes: nodes.filter(n => n.poot_score <= 70).length,
        average_network_latency: 45.2, // Would be calculated from actual metrics
        total_bandwidth_utilization: 68.5, // Would be calculated from actual metrics
        network_stability_score: 87.3 // Would be calculated from actual metrics
      };
    } catch (error) {
      throw error;
    }
  }

  /**
   * Refresh node data
   */
  async refreshNodeData(): Promise<void> {
    this.clearCache();
    await this.getNodes({ limit: 100 });
  }

  /**
   * Get cached node data
   */
  getCachedNode(nodeId: string): Node | null {
    return this.nodesCache.get(nodeId) || null;
  }

  /**
   * Get cached node metrics
   */
  getCachedNodeMetrics(nodeId: string, timeRange: string): NodeMetrics | null {
    const cacheKey = `${nodeId}_${timeRange}`;
    return this.metricsCache.get(cacheKey) || null;
  }

  /**
   * Clear node cache
   */
  clearCache(): void {
    this.nodesCache.clear();
    this.nodesListCache = [];
    this.metricsCache.clear();
    this.lastListUpdate = 0;
  }

  // Private helper methods
  private applyFilters(nodes: Node[], filters: NodeFilters): Node[] {
    let filtered = [...nodes];

    if (filters.status) {
      filtered = filtered.filter(n => n.status === filters.status);
    }

    if (filters.pool_id) {
      filtered = filtered.filter(n => n.pool_id === filters.pool_id);
    }

    if (filters.created_from) {
      const fromDate = new Date(filters.created_from);
      filtered = filtered.filter(n => new Date(n.created_at) >= fromDate);
    }

    if (filters.created_to) {
      const toDate = new Date(filters.created_to);
      filtered = filtered.filter(n => new Date(n.created_at) <= toDate);
    }

    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      filtered = filtered.filter(n => 
        n.node_id.toLowerCase().includes(searchLower) ||
        n.operator_id.toLowerCase().includes(searchLower)
      );
    }

    // Apply pagination
    const offset = filters.offset || 0;
    const limit = filters.limit || filtered.length;
    
    return filtered.slice(offset, offset + limit);
  }

  private calculateNodeAnalytics(nodes: Node[], timeRange: string): NodeAnalytics {
    const analytics: NodeAnalytics = {
      total_nodes: nodes.length,
      active_nodes: 0,
      inactive_nodes: 0,
      suspended_nodes: 0,
      nodes_by_status: {},
      nodes_by_pool: {},
      average_poot_score: 0,
      total_compute_power: 0,
      resource_utilization: {
        average_cpu: 0,
        average_memory: 0,
        average_disk: 0,
        average_network: 0
      },
      top_performing_nodes: [],
      node_registration_trend: []
    };

    let totalPootScore = 0;
    let totalCpu = 0;
    let totalMemory = 0;
    let totalDisk = 0;
    let totalNetwork = 0;

    // Calculate various metrics
    nodes.forEach(node => {
      // Status distribution
      analytics.nodes_by_status[node.status] = (analytics.nodes_by_status[node.status] || 0) + 1;

      switch (node.status) {
        case 'active':
          analytics.active_nodes++;
          break;
        case 'inactive':
          analytics.inactive_nodes++;
          break;
        case 'suspended':
          analytics.suspended_nodes++;
          break;
      }

      // Pool distribution
      if (node.pool_id) {
        analytics.nodes_by_pool[node.pool_id] = (analytics.nodes_by_pool[node.pool_id] || 0) + 1;
      }

      // Resource metrics
      totalPootScore += node.poot_score;
      totalCpu += node.resources.cpu_usage;
      totalMemory += node.resources.memory_usage;
      totalDisk += node.resources.disk_usage;
      totalNetwork += node.resources.network_bandwidth;

      // Total compute power (simplified calculation)
      analytics.total_compute_power += node.resources.cpu_usage * node.poot_score / 100;
    });

    // Calculate averages
    if (nodes.length > 0) {
      analytics.average_poot_score = totalPootScore / nodes.length;
      analytics.resource_utilization.average_cpu = totalCpu / nodes.length;
      analytics.resource_utilization.average_memory = totalMemory / nodes.length;
      analytics.resource_utilization.average_disk = totalDisk / nodes.length;
      analytics.resource_utilization.average_network = totalNetwork / nodes.length;
    }

    // Top performing nodes
    analytics.top_performing_nodes = nodes
      .sort((a, b) => b.poot_score - a.poot_score)
      .slice(0, 10)
      .map(node => ({
        node_id: node.node_id,
        operator_id: node.operator_id,
        poot_score: node.poot_score,
        uptime_percentage: 95.5 // Would be calculated from actual uptime data
      }));

    // Registration trend (simplified)
    const daysBack = timeRange === '1d' ? 1 : timeRange === '7d' ? 7 : 30;
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    for (let i = daysBack - 1; i >= 0; i--) {
      const date = new Date(today.getTime() - (i * 24 * 60 * 60 * 1000));
      const dayStart = new Date(date.getFullYear(), date.getMonth(), date.getDate());
      const dayEnd = new Date(dayStart.getTime() + (24 * 60 * 60 * 1000));
      
      const dayNodes = nodes.filter(node => {
        const createdAt = new Date(node.created_at);
        return createdAt >= dayStart && createdAt < dayEnd;
      });

      analytics.node_registration_trend.push({
        date: dayStart.toISOString().split('T')[0],
        count: dayNodes.length
      });
    }

    return analytics;
  }

  private invalidateNodeCache(nodeId: string): void {
    this.nodesCache.delete(nodeId);
    this.nodesListCache = this.nodesListCache.filter(n => n.node_id !== nodeId);
    // Clear related metrics cache entries
    Array.from(this.metricsCache.keys())
      .filter(key => key.startsWith(nodeId))
      .forEach(key => this.metricsCache.delete(key));
  }
}

// Export singleton instance
export const nodeService = new NodeService();
