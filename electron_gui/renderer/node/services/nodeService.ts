import { LucidAPIClient } from '../../../shared/api-client';

// Types
interface NodeInfo {
  node_id: string;
  operator_id: string;
  pool_id?: string;
  status: 'active' | 'inactive' | 'maintenance' | 'suspended';
  hardware_info: {
    cpu_cores: number;
    memory_gb: number;
    disk_gb: number;
    network_speed_mbps: number;
  };
  location: {
    country: string;
    region: string;
    timezone: string;
  };
  poot_score: number;
  total_earnings: number;
  uptime_percentage: number;
  created_at: string;
  last_activity: string;
}

interface NodeMetrics {
  sessions_processed: number;
  data_processed: number;
  average_response_time: number;
  error_rate: number;
  network_latency: number;
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  network_bandwidth: number;
  temperature: number;
  uptime: number;
}

interface NodeActivity {
  id: string;
  type: 'session' | 'maintenance' | 'earnings' | 'system';
  description: string;
  timestamp: string;
  status: 'success' | 'warning' | 'error';
  metadata?: Record<string, any>;
}

interface NodeConfiguration {
  node_settings: {
    node_name: string;
    auto_start: boolean;
    max_concurrent_sessions: number;
    session_timeout: number;
    maintenance_mode: boolean;
    log_level: 'debug' | 'info' | 'warn' | 'error';
  };
  network_settings: {
    port: number;
    max_bandwidth: number;
    enable_tor: boolean;
    tor_socks_port: number;
    enable_ipv6: boolean;
  };
  resource_settings: {
    cpu_limit: number;
    memory_limit: number;
    disk_limit: number;
    auto_scale: boolean;
    min_resources: number;
    max_resources: number;
  };
  security_settings: {
    enable_encryption: boolean;
    encryption_key: string;
    enable_authentication: boolean;
    api_key: string;
    allowed_ips: string[];
    enable_ssl: boolean;
    ssl_certificate: string;
    ssl_private_key: string;
  };
  backup_settings: {
    enable_backup: boolean;
    backup_interval: number;
    backup_retention: number;
    backup_location: string;
    enable_compression: boolean;
  };
}

interface NodeActionRequest {
  action: 'restart' | 'stop' | 'start' | 'maintenance' | 'update' | 'backup';
  reason?: string;
  force?: boolean;
}

interface NodeActionResponse {
  success: boolean;
  message: string;
  action_id?: string;
  estimated_duration?: number;
}

class NodeService {
  private apiClient: LucidAPIClient;
  private nodeInfoCache: NodeInfo | null = null;
  private metricsCache: NodeMetrics | null = null;
  private lastCacheUpdate: number = 0;
  private readonly CACHE_DURATION = 30000; // 30 seconds

  constructor(apiClient: LucidAPIClient) {
    this.apiClient = apiClient;
  }

  // Node Information
  async getNodeInfo(forceRefresh: boolean = false): Promise<NodeInfo> {
    const now = Date.now();
    
    if (!forceRefresh && this.nodeInfoCache && (now - this.lastCacheUpdate) < this.CACHE_DURATION) {
      return this.nodeInfoCache;
    }

    try {
      const response = await this.apiClient.get('/node/info');
      this.nodeInfoCache = response.data;
      this.lastCacheUpdate = now;
      return this.nodeInfoCache;
    } catch (error) {
      throw new Error(`Failed to get node info: ${error}`);
    }
  }

  async updateNodeInfo(updates: Partial<NodeInfo>): Promise<{ success: boolean; message: string }> {
    try {
      const response = await this.apiClient.put('/node/info', updates);
      this.nodeInfoCache = null; // Invalidate cache
      return response.data;
    } catch (error) {
      throw new Error(`Failed to update node info: ${error}`);
    }
  }

  // Node Metrics
  async getNodeMetrics(forceRefresh: boolean = false): Promise<NodeMetrics> {
    const now = Date.now();
    
    if (!forceRefresh && this.metricsCache && (now - this.lastCacheUpdate) < this.CACHE_DURATION) {
      return this.metricsCache;
    }

    try {
      const response = await this.apiClient.get('/node/metrics');
      this.metricsCache = response.data;
      this.lastCacheUpdate = now;
      return this.metricsCache;
    } catch (error) {
      throw new Error(`Failed to get node metrics: ${error}`);
    }
  }

  async getNodeMetricsHistory(timeRange: '1h' | '6h' | '24h' | '7d' = '24h'): Promise<{
    timestamp: string;
    metrics: NodeMetrics;
  }[]> {
    try {
      const response = await this.apiClient.get(`/node/metrics/history?timeRange=${timeRange}`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get node metrics history: ${error}`);
    }
  }

  // Node Activity
  async getNodeActivity(limit: number = 50): Promise<NodeActivity[]> {
    try {
      const response = await this.apiClient.get(`/node/activity?limit=${limit}`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get node activity: ${error}`);
    }
  }

  async getNodeActivityByType(type: NodeActivity['type'], limit: number = 20): Promise<NodeActivity[]> {
    try {
      const response = await this.apiClient.get(`/node/activity?type=${type}&limit=${limit}`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get node activity by type: ${error}`);
    }
  }

  // Node Configuration
  async getNodeConfiguration(): Promise<NodeConfiguration> {
    try {
      const response = await this.apiClient.get('/node/configuration');
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get node configuration: ${error}`);
    }
  }

  async updateNodeConfiguration(config: Partial<NodeConfiguration>): Promise<{ success: boolean; message: string }> {
    try {
      const response = await this.apiClient.put('/node/configuration', config);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to update node configuration: ${error}`);
    }
  }

  async resetNodeConfiguration(): Promise<{ success: boolean; message: string }> {
    try {
      const response = await this.apiClient.post('/node/configuration/reset');
      return response.data;
    } catch (error) {
      throw new Error(`Failed to reset node configuration: ${error}`);
    }
  }

  // Node Actions
  async performNodeAction(action: NodeActionRequest): Promise<NodeActionResponse> {
    try {
      const response = await this.apiClient.post('/node/action', action);
      this.nodeInfoCache = null; // Invalidate cache after action
      return response.data;
    } catch (error) {
      throw new Error(`Failed to perform node action: ${error}`);
    }
  }

  async restartNode(reason?: string, force: boolean = false): Promise<NodeActionResponse> {
    return this.performNodeAction({
      action: 'restart',
      reason,
      force,
    });
  }

  async stopNode(reason?: string, force: boolean = false): Promise<NodeActionResponse> {
    return this.performNodeAction({
      action: 'stop',
      reason,
      force,
    });
  }

  async startNode(): Promise<NodeActionResponse> {
    return this.performNodeAction({
      action: 'start',
    });
  }

  async enterMaintenanceMode(reason?: string): Promise<NodeActionResponse> {
    return this.performNodeAction({
      action: 'maintenance',
      reason,
    });
  }

  async exitMaintenanceMode(): Promise<NodeActionResponse> {
    return this.performNodeAction({
      action: 'start',
      reason: 'Exiting maintenance mode',
    });
  }

  async updateNode(): Promise<NodeActionResponse> {
    return this.performNodeAction({
      action: 'update',
    });
  }

  async createBackup(): Promise<NodeActionResponse> {
    return this.performNodeAction({
      action: 'backup',
    });
  }

  // Node Status
  async getNodeStatus(): Promise<{
    status: NodeInfo['status'];
    is_online: boolean;
    last_heartbeat: string;
    uptime: number;
    health_score: number;
  }> {
    try {
      const response = await this.apiClient.get('/node/status');
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get node status: ${error}`);
    }
  }

  async checkNodeHealth(): Promise<{
    overall_health: 'healthy' | 'warning' | 'critical';
    checks: Array<{
      name: string;
      status: 'pass' | 'warning' | 'fail';
      message: string;
      recommendation?: string;
    }>;
  }> {
    try {
      const response = await this.apiClient.get('/node/health');
      return response.data;
    } catch (error) {
      throw new Error(`Failed to check node health: ${error}`);
    }
  }

  // Node Performance
  async getNodePerformance(): Promise<{
    poot_score: number;
    performance_rating: 'excellent' | 'good' | 'average' | 'poor' | 'critical';
    score_breakdown: {
      uptime: number;
      performance: number;
      reliability: number;
      participation: number;
    };
    score_history: Array<{
      timestamp: string;
      score: number;
    }>;
  }> {
    try {
      const response = await this.apiClient.get('/node/performance');
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get node performance: ${error}`);
    }
  }

  // Node Diagnostics
  async runNodeDiagnostics(): Promise<{
    diagnostics_id: string;
    status: 'running' | 'completed' | 'failed';
    results?: Array<{
      check_name: string;
      status: 'pass' | 'warning' | 'fail';
      message: string;
      recommendation?: string;
      details?: any;
    }>;
  }> {
    try {
      const response = await this.apiClient.post('/node/diagnostics');
      return response.data;
    } catch (error) {
      throw new Error(`Failed to run node diagnostics: ${error}`);
    }
  }

  async getDiagnosticsResults(diagnosticsId: string): Promise<{
    status: 'running' | 'completed' | 'failed';
    results?: Array<{
      check_name: string;
      status: 'pass' | 'warning' | 'fail';
      message: string;
      recommendation?: string;
      details?: any;
    }>;
  }> {
    try {
      const response = await this.apiClient.get(`/node/diagnostics/${diagnosticsId}`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get diagnostics results: ${error}`);
    }
  }

  // Node Logs
  async getNodeLogs(logType: 'system' | 'application' | 'error' = 'system', limit: number = 100): Promise<Array<{
    timestamp: string;
    level: 'debug' | 'info' | 'warn' | 'error';
    message: string;
    source: string;
    metadata?: Record<string, any>;
  }>> {
    try {
      const response = await this.apiClient.get(`/node/logs?type=${logType}&limit=${limit}`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get node logs: ${error}`);
    }
  }

  async downloadNodeLogs(logType: 'system' | 'application' | 'error' = 'system'): Promise<Blob> {
    try {
      const response = await this.apiClient.get(`/node/logs/download?type=${logType}`, {
        responseType: 'blob',
      });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to download node logs: ${error}`);
    }
  }

  // Node Backup
  async createNodeBackup(options?: {
    include_logs: boolean;
    include_config: boolean;
    include_data: boolean;
    compression: boolean;
  }): Promise<{
    backup_id: string;
    status: 'creating' | 'completed' | 'failed';
    size?: number;
    created_at?: string;
  }> {
    try {
      const response = await this.apiClient.post('/node/backup', options || {});
      return response.data;
    } catch (error) {
      throw new Error(`Failed to create node backup: ${error}`);
    }
  }

  async getBackupStatus(backupId: string): Promise<{
    backup_id: string;
    status: 'creating' | 'completed' | 'failed';
    size?: number;
    created_at?: string;
    download_url?: string;
  }> {
    try {
      const response = await this.apiClient.get(`/node/backup/${backupId}`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get backup status: ${error}`);
    }
  }

  async downloadBackup(backupId: string): Promise<Blob> {
    try {
      const response = await this.apiClient.get(`/node/backup/${backupId}/download`, {
        responseType: 'blob',
      });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to download backup: ${error}`);
    }
  }

  // Cache Management
  clearCache(): void {
    this.nodeInfoCache = null;
    this.metricsCache = null;
    this.lastCacheUpdate = 0;
  }

  getCachedNodeInfo(): NodeInfo | null {
    return this.nodeInfoCache;
  }

  getCachedMetrics(): NodeMetrics | null {
    return this.metricsCache;
  }

  isCacheValid(): boolean {
    const now = Date.now();
    return (now - this.lastCacheUpdate) < this.CACHE_DURATION;
  }
}

export { NodeService };
export type {
  NodeInfo,
  NodeMetrics,
  NodeActivity,
  NodeConfiguration,
  NodeActionRequest,
  NodeActionResponse,
};
