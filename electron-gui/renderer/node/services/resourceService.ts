import { LucidAPIClient } from '../../../shared/api-client';

// Types
interface ResourceData {
  cpu: {
    usage: number;
    cores: number;
    temperature: number;
    load_average: number[];
    frequency: number;
    cache_size: number;
  };
  memory: {
    total: number;
    used: number;
    free: number;
    cached: number;
    buffer: number;
    swap_total: number;
    swap_used: number;
    swap_free: number;
  };
  disk: {
    total: number;
    used: number;
    free: number;
    read_speed: number;
    write_speed: number;
    io_wait: number;
    iops: number;
    queue_depth: number;
  };
  network: {
    bandwidth: number;
    latency: number;
    packets_sent: number;
    packets_received: number;
    bytes_sent: number;
    bytes_received: number;
    errors: number;
    drops: number;
    interface_name: string;
    connection_type: string;
  };
}

interface ResourceMetrics {
  timestamp: string;
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  network_bandwidth: number;
  temperature: number;
  uptime: number;
}

interface ResourceAlert {
  id: string;
  type: 'cpu' | 'memory' | 'disk' | 'network' | 'temperature';
  severity: 'low' | 'medium' | 'high' | 'critical';
  message: string;
  threshold: number;
  current_value: number;
  timestamp: string;
  is_acknowledged: boolean;
}

interface ResourceThresholds {
  cpu: {
    warning: number;
    critical: number;
  };
  memory: {
    warning: number;
    critical: number;
  };
  disk: {
    warning: number;
    critical: number;
  };
  temperature: {
    warning: number;
    critical: number;
  };
  network: {
    latency_warning: number;
    latency_critical: number;
    packet_loss_warning: number;
    packet_loss_critical: number;
  };
}

interface ResourceOptimization {
  recommendations: Array<{
    category: 'cpu' | 'memory' | 'disk' | 'network';
    priority: 'low' | 'medium' | 'high' | 'critical';
    title: string;
    description: string;
    impact: string;
    effort: 'low' | 'medium' | 'high';
    estimated_improvement: string;
  }>;
  current_efficiency: number;
  potential_efficiency: number;
}

class ResourceService {
  private apiClient: LucidAPIClient;
  private resourceCache: ResourceData | null = null;
  private metricsCache: ResourceMetrics[] = [];
  private alertsCache: ResourceAlert[] = [];
  private lastCacheUpdate: number = 0;
  private readonly CACHE_DURATION = 10000; // 10 seconds for real-time data

  constructor(apiClient: LucidAPIClient) {
    this.apiClient = apiClient;
  }

  // Real-time Resource Data
  async getCurrentResources(forceRefresh: boolean = false): Promise<ResourceData> {
    const now = Date.now();
    
    if (!forceRefresh && this.resourceCache && (now - this.lastCacheUpdate) < this.CACHE_DURATION) {
      return this.resourceCache;
    }

    try {
      const response = await this.apiClient.get('/node/resources/current');
      this.resourceCache = response.data;
      this.lastCacheUpdate = now;
      return this.resourceCache;
    } catch (error) {
      throw new Error(`Failed to get current resources: ${error}`);
    }
  }

  async getResourceMetrics(
    timeRange: '1h' | '6h' | '24h' | '7d' = '1h',
    forceRefresh: boolean = false
  ): Promise<ResourceMetrics[]> {
    const now = Date.now();
    
    if (!forceRefresh && this.metricsCache.length > 0 && (now - this.lastCacheUpdate) < this.CACHE_DURATION) {
      return this.metricsCache;
    }

    try {
      const response = await this.apiClient.get(`/node/resources/metrics?timeRange=${timeRange}`);
      this.metricsCache = response.data;
      this.lastCacheUpdate = now;
      return this.metricsCache;
    } catch (error) {
      throw new Error(`Failed to get resource metrics: ${error}`);
    }
  }

  // Resource Monitoring
  async startResourceMonitoring(): Promise<{ success: boolean; message: string }> {
    try {
      const response = await this.apiClient.post('/node/resources/monitoring/start');
      return response.data;
    } catch (error) {
      throw new Error(`Failed to start resource monitoring: ${error}`);
    }
  }

  async stopResourceMonitoring(): Promise<{ success: boolean; message: string }> {
    try {
      const response = await this.apiClient.post('/node/resources/monitoring/stop');
      return response.data;
    } catch (error) {
      throw new Error(`Failed to stop resource monitoring: ${error}`);
    }
  }

  async getMonitoringStatus(): Promise<{
    is_monitoring: boolean;
    monitoring_started: string | null;
    last_update: string | null;
    update_frequency: number;
    metrics_collected: number;
  }> {
    try {
      const response = await this.apiClient.get('/node/resources/monitoring/status');
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get monitoring status: ${error}`);
    }
  }

  // Resource Alerts
  async getResourceAlerts(forceRefresh: boolean = false): Promise<ResourceAlert[]> {
    const now = Date.now();
    
    if (!forceRefresh && this.alertsCache.length >= 0 && (now - this.lastCacheUpdate) < this.CACHE_DURATION) {
      return this.alertsCache;
    }

    try {
      const response = await this.apiClient.get('/node/resources/alerts');
      this.alertsCache = response.data;
      this.lastCacheUpdate = now;
      return this.alertsCache;
    } catch (error) {
      throw new Error(`Failed to get resource alerts: ${error}`);
    }
  }

  async acknowledgeAlert(alertId: string): Promise<{ success: boolean; message: string }> {
    try {
      const response = await this.apiClient.post(`/node/resources/alerts/${alertId}/acknowledge`);
      this.alertsCache = []; // Invalidate cache
      return response.data;
    } catch (error) {
      throw new Error(`Failed to acknowledge alert: ${error}`);
    }
  }

  async dismissAlert(alertId: string): Promise<{ success: boolean; message: string }> {
    try {
      const response = await this.apiClient.post(`/node/resources/alerts/${alertId}/dismiss`);
      this.alertsCache = []; // Invalidate cache
      return response.data;
    } catch (error) {
      throw new Error(`Failed to dismiss alert: ${error}`);
    }
  }

  // Resource Thresholds
  async getResourceThresholds(): Promise<ResourceThresholds> {
    try {
      const response = await this.apiClient.get('/node/resources/thresholds');
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get resource thresholds: ${error}`);
    }
  }

  async updateResourceThresholds(thresholds: Partial<ResourceThresholds>): Promise<{ success: boolean; message: string }> {
    try {
      const response = await this.apiClient.put('/node/resources/thresholds', thresholds);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to update resource thresholds: ${error}`);
    }
  }

  async resetResourceThresholds(): Promise<{ success: boolean; message: string }> {
    try {
      const response = await this.apiClient.post('/node/resources/thresholds/reset');
      return response.data;
    } catch (error) {
      throw new Error(`Failed to reset resource thresholds: ${error}`);
    }
  }

  // Resource Optimization
  async getResourceOptimization(): Promise<ResourceOptimization> {
    try {
      const response = await this.apiClient.get('/node/resources/optimization');
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get resource optimization: ${error}`);
    }
  }

  async applyOptimization(optimizationId: string): Promise<{ success: boolean; message: string }> {
    try {
      const response = await this.apiClient.post(`/node/resources/optimization/${optimizationId}/apply`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to apply optimization: ${error}`);
    }
  }

  // Resource Analysis
  async analyzeResourceUsage(timeRange: '1h' | '6h' | '24h' | '7d' = '24h'): Promise<{
    usage_patterns: {
      peak_hours: number[];
      low_usage_hours: number[];
      average_usage: {
        cpu: number;
        memory: number;
        disk: number;
        network: number;
      };
    };
    bottlenecks: Array<{
      resource: 'cpu' | 'memory' | 'disk' | 'network';
      severity: 'low' | 'medium' | 'high' | 'critical';
      description: string;
      recommendation: string;
    }>;
    efficiency_score: number;
    capacity_utilization: {
      cpu: number;
      memory: number;
      disk: number;
      network: number;
    };
  }> {
    try {
      const response = await this.apiClient.get(`/node/resources/analysis?timeRange=${timeRange}`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to analyze resource usage: ${error}`);
    }
  }

  async getResourceTrends(timeRange: '1h' | '6h' | '24h' | '7d' = '24h'): Promise<{
    trends: {
      cpu: 'increasing' | 'decreasing' | 'stable';
      memory: 'increasing' | 'decreasing' | 'stable';
      disk: 'increasing' | 'decreasing' | 'stable';
      network: 'increasing' | 'decreasing' | 'stable';
    };
    trend_data: Array<{
      timestamp: string;
      cpu_trend: number;
      memory_trend: number;
      disk_trend: number;
      network_trend: number;
    }>;
  }> {
    try {
      const response = await this.apiClient.get(`/node/resources/trends?timeRange=${timeRange}`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get resource trends: ${error}`);
    }
  }

  // Resource Health Check
  async checkResourceHealth(): Promise<{
    overall_health: 'healthy' | 'warning' | 'critical';
    resource_health: {
      cpu: 'healthy' | 'warning' | 'critical';
      memory: 'healthy' | 'warning' | 'critical';
      disk: 'healthy' | 'warning' | 'critical';
      network: 'healthy' | 'warning' | 'critical';
      temperature: 'healthy' | 'warning' | 'critical';
    };
    health_checks: Array<{
      resource: string;
      check_name: string;
      status: 'pass' | 'warning' | 'fail';
      message: string;
      recommendation?: string;
    }>;
  }> {
    try {
      const response = await this.apiClient.get('/node/resources/health');
      return response.data;
    } catch (error) {
      throw new Error(`Failed to check resource health: ${error}`);
    }
  }

  // Resource Capacity Planning
  async getCapacityPlanning(): Promise<{
    current_capacity: {
      cpu: number;
      memory: number;
      disk: number;
      network: number;
    };
    projected_usage: {
      cpu: number;
      memory: number;
      disk: number;
      network: number;
    };
    recommendations: Array<{
      resource: 'cpu' | 'memory' | 'disk' | 'network';
      action: 'upgrade' | 'optimize' | 'monitor';
      priority: 'low' | 'medium' | 'high' | 'critical';
      description: string;
      estimated_cost?: number;
      estimated_benefit: string;
    }>;
  }> {
    try {
      const response = await this.apiClient.get('/node/resources/capacity-planning');
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get capacity planning: ${error}`);
    }
  }

  // Resource Reports
  async generateResourceReport(
    options: {
      format: 'json' | 'csv' | 'pdf';
      timeRange: '1h' | '6h' | '24h' | '7d';
      include_recommendations: boolean;
      include_trends: boolean;
    }
  ): Promise<Blob> {
    try {
      const response = await this.apiClient.post('/node/resources/report', options, {
        responseType: 'blob',
      });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to generate resource report: ${error}`);
    }
  }

  async exportResourceData(
    format: 'json' | 'csv' = 'csv',
    timeRange: '1h' | '6h' | '24h' | '7d' = '24h'
  ): Promise<Blob> {
    try {
      const params = new URLSearchParams();
      params.append('format', format);
      params.append('timeRange', timeRange);

      const response = await this.apiClient.get(`/node/resources/export?${params.toString()}`, {
        responseType: 'blob',
      });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to export resource data: ${error}`);
    }
  }

  // Cache Management
  clearCache(): void {
    this.resourceCache = null;
    this.metricsCache = [];
    this.alertsCache = [];
    this.lastCacheUpdate = 0;
  }

  getCachedResources(): ResourceData | null {
    return this.resourceCache;
  }

  getCachedMetrics(): ResourceMetrics[] {
    return this.metricsCache;
  }

  getCachedAlerts(): ResourceAlert[] {
    return this.alertsCache;
  }

  isCacheValid(): boolean {
    const now = Date.now();
    return (now - this.lastCacheUpdate) < this.CACHE_DURATION;
  }

  // Utility Methods
  async getResourceUtilization(): Promise<{
    cpu: number;
    memory: number;
    disk: number;
    network: number;
  }> {
    const resources = await this.getCurrentResources();
    return {
      cpu: resources.cpu.usage,
      memory: (resources.memory.used / resources.memory.total) * 100,
      disk: (resources.disk.used / resources.disk.total) * 100,
      network: Math.min(100, resources.network.bandwidth / 1000), // Assuming 1000 Mbps max
    };
  }

  async hasResourceAlerts(): Promise<boolean> {
    const alerts = await this.getResourceAlerts();
    return alerts.some(alert => !alert.is_acknowledged);
  }

  async getCriticalAlerts(): Promise<ResourceAlert[]> {
    const alerts = await this.getResourceAlerts();
    return alerts.filter(alert => alert.severity === 'critical' && !alert.is_acknowledged);
  }

  async getResourceEfficiency(): Promise<number> {
    const optimization = await this.getResourceOptimization();
    return optimization.current_efficiency;
  }

  async isResourceHealthy(): Promise<boolean> {
    const health = await this.checkResourceHealth();
    return health.overall_health === 'healthy';
  }

  // Real-time Updates
  subscribeToResourceUpdates(callback: (resources: ResourceData) => void): () => void {
    // This would typically use WebSocket or Server-Sent Events
    // For now, we'll simulate with polling
    const interval = setInterval(async () => {
      try {
        const resources = await this.getCurrentResources(true);
        callback(resources);
      } catch (error) {
        console.error('Failed to get resource updates:', error);
      }
    }, this.CACHE_DURATION);

    return () => clearInterval(interval);
  }
}

export { ResourceService };
export type {
  ResourceData,
  ResourceMetrics,
  ResourceAlert,
  ResourceThresholds,
  ResourceOptimization,
};
