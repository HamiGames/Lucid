/**
 * Dashboard Service - Handles dashboard data fetching and caching
 * Provides real-time system metrics and overview data for admin dashboard
 */

import { adminApi, AdminDashboardData, SystemMetrics, ActivityLog } from './adminApi';
import { SystemHealth, ServiceStatus } from '../../../shared/types';

export interface DashboardFilters {
  timeRange: '1h' | '24h' | '7d' | '30d';
  refreshInterval: number; // in milliseconds
  includeDetails: boolean;
}

export interface RealTimeMetrics {
  timestamp: string;
  system_health: SystemHealth;
  metrics: SystemMetrics;
  active_services: number;
  alerts_count: number;
}

export interface DashboardCache {
  data: AdminDashboardData | null;
  lastUpdated: number;
  isStale: boolean;
  error: Error | null;
}

class DashboardService {
  private cache: DashboardCache = {
    data: null,
    lastUpdated: 0,
    isStale: true,
    error: null
  };

  private refreshInterval: NodeJS.Timeout | null = null;
  private subscribers: Array<(data: AdminDashboardData | null, error: Error | null) => void> = [];
  private filters: DashboardFilters = {
    timeRange: '24h',
    refreshInterval: 30000, // 30 seconds
    includeDetails: true
  };

  // Cache management
  private readonly CACHE_DURATION = 30000; // 30 seconds
  private readonly MAX_RETRY_ATTEMPTS = 3;
  private retryCount = 0;

  /**
   * Get dashboard data with caching
   */
  async getDashboardData(forceRefresh: boolean = false): Promise<AdminDashboardData> {
    const now = Date.now();
    const isCacheValid = !this.cache.isStale && 
                        (now - this.cache.lastUpdated) < this.CACHE_DURATION;

    if (!forceRefresh && isCacheValid && this.cache.data) {
      return this.cache.data;
    }

    try {
      this.cache.error = null;
      const data = await adminApi.getDashboardData();
      
      this.cache.data = data;
      this.cache.lastUpdated = now;
      this.cache.isStale = false;
      this.retryCount = 0;

      // Notify subscribers
      this.notifySubscribers(data, null);

      return data;
    } catch (error) {
      this.cache.error = error as Error;
      this.cache.isStale = true;
      
      // Notify subscribers of error
      this.notifySubscribers(null, error as Error);

      // Retry logic
      if (this.retryCount < this.MAX_RETRY_ATTEMPTS) {
        this.retryCount++;
        setTimeout(() => {
          this.getDashboardData(true);
        }, 2000 * this.retryCount); // Exponential backoff
      }

      throw error;
    }
  }

  /**
   * Get system health with caching
   */
  async getSystemHealth(forceRefresh: boolean = false): Promise<SystemHealth> {
    const now = Date.now();
    const isCacheValid = !this.cache.isStale && 
                        (now - this.cache.lastUpdated) < this.CACHE_DURATION;

    if (!forceRefresh && isCacheValid && this.cache.data) {
      return this.cache.data.system_health;
    }

    try {
      const health = await adminApi.getSystemHealth();
      
      // Update cache if we have dashboard data
      if (this.cache.data) {
        this.cache.data.system_health = health;
        this.cache.lastUpdated = now;
        this.notifySubscribers(this.cache.data, null);
      }

      return health;
    } catch (error) {
      this.cache.error = error as Error;
      throw error;
    }
  }

  /**
   * Get service status with caching
   */
  async getServiceStatus(serviceName?: string, forceRefresh: boolean = false): Promise<ServiceStatus[]> {
    try {
      const services = await adminApi.getServiceStatus(serviceName);
      
      // Update cache if we have dashboard data
      if (this.cache.data) {
        this.cache.data.system_health.services = services;
        this.cache.lastUpdated = Date.now();
        this.notifySubscribers(this.cache.data, null);
      }

      return services;
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get real-time metrics for charts
   */
  async getRealTimeMetrics(): Promise<RealTimeMetrics> {
    try {
      const [systemHealth, serviceStatus] = await Promise.all([
        this.getSystemHealth(),
        this.getServiceStatus()
      ]);

      const activeServices = serviceStatus.filter(s => s.status === 'healthy').length;
      const alertsCount = serviceStatus.filter(s => s.status === 'unhealthy').length;

      const metrics: SystemMetrics = {
        cpu_usage: this.calculateAverageMetric(serviceStatus, 'cpu'),
        memory_usage: this.calculateAverageMetric(serviceStatus, 'memory'),
        disk_usage: this.calculateAverageMetric(serviceStatus, 'disk'),
        network_throughput: this.calculateNetworkThroughput(serviceStatus),
        active_connections: activeServices,
        tor_circuits: systemHealth.tor_status === 'connected' ? 3 : 0 // Estimated
      };

      return {
        timestamp: new Date().toISOString(),
        system_health: systemHealth,
        metrics,
        active_services: activeServices,
        alerts_count: alertsCount
      };
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get activity logs for dashboard
   */
  async getActivityLogs(limit: number = 10): Promise<ActivityLog[]> {
    try {
      if (this.cache.data?.recent_activity) {
        return this.cache.data.recent_activity.slice(0, limit);
      }

      // If no cached data, fetch fresh data
      const dashboardData = await this.getDashboardData(true);
      return dashboardData.recent_activity.slice(0, limit);
    } catch (error) {
      throw error;
    }
  }

  /**
   * Start auto-refresh for real-time updates
   */
  startAutoRefresh(): void {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
    }

    this.refreshInterval = setInterval(async () => {
      try {
        await this.getDashboardData(true);
      } catch (error) {
        console.error('Dashboard auto-refresh failed:', error);
      }
    }, this.filters.refreshInterval);
  }

  /**
   * Stop auto-refresh
   */
  stopAutoRefresh(): void {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
      this.refreshInterval = null;
    }
  }

  /**
   * Update dashboard filters
   */
  updateFilters(newFilters: Partial<DashboardFilters>): void {
    this.filters = { ...this.filters, ...newFilters };
    
    // Restart auto-refresh with new interval
    if (this.refreshInterval) {
      this.startAutoRefresh();
    }

    // Mark cache as stale to force refresh
    this.cache.isStale = true;
  }

  /**
   * Subscribe to dashboard data updates
   */
  subscribe(callback: (data: AdminDashboardData | null, error: Error | null) => void): () => void {
    this.subscribers.push(callback);

    // Return unsubscribe function
    return () => {
      const index = this.subscribers.indexOf(callback);
      if (index > -1) {
        this.subscribers.splice(index, 1);
      }
    };
  }

  /**
   * Get cached data without making API calls
   */
  getCachedData(): AdminDashboardData | null {
    return this.cache.data;
  }

  /**
   * Check if data is currently being fetched
   */
  isLoading(): boolean {
    return this.cache.isStale && !this.cache.error;
  }

  /**
   * Get cache status
   */
  getCacheStatus(): {
    hasData: boolean;
    isStale: boolean;
    lastUpdated: Date | null;
    error: Error | null;
  } {
    return {
      hasData: !!this.cache.data,
      isStale: this.cache.isStale,
      lastUpdated: this.cache.lastUpdated ? new Date(this.cache.lastUpdated) : null,
      error: this.cache.error
    };
  }

  /**
   * Clear cache and force refresh
   */
  clearCache(): void {
    this.cache = {
      data: null,
      lastUpdated: 0,
      isStale: true,
      error: null
    };
  }

  /**
   * Preload dashboard data
   */
  async preloadData(): Promise<void> {
    try {
      await this.getDashboardData(true);
    } catch (error) {
      console.error('Failed to preload dashboard data:', error);
    }
  }

  /**
   * Get dashboard summary for quick overview
   */
  async getDashboardSummary(): Promise<{
    total_users: number;
    active_sessions: number;
    active_nodes: number;
    system_status: 'healthy' | 'degraded' | 'critical';
    alerts_count: number;
  }> {
    try {
      const data = await this.getDashboardData();
      const systemStatus = data.system_health.overall;
      
      const alertsCount = data.system_health.services.filter(
        s => s.status === 'unhealthy' || s.status === 'stopped'
      ).length;

      return {
        total_users: data.total_users,
        active_sessions: data.active_sessions,
        active_nodes: data.active_nodes,
        system_status: systemStatus,
        alerts_count: alertsCount
      };
    } catch (error) {
      throw error;
    }
  }

  // Private helper methods
  private notifySubscribers(data: AdminDashboardData | null, error: Error | null): void {
    this.subscribers.forEach(callback => {
      try {
        callback(data, error);
      } catch (callbackError) {
        console.error('Dashboard subscriber callback error:', callbackError);
      }
    });
  }

  private calculateAverageMetric(services: ServiceStatus[], metric: 'cpu' | 'memory' | 'disk'): number {
    if (services.length === 0) return 0;

    const total = services.reduce((sum, service) => {
      switch (metric) {
        case 'cpu':
          return sum + service.cpu;
        case 'memory':
          return sum + service.memory;
        case 'disk':
          return sum + (service as any).disk || 0;
        default:
          return sum;
      }
    }, 0);

    return Math.round(total / services.length);
  }

  private calculateNetworkThroughput(services: ServiceStatus[]): number {
    // This is a simplified calculation
    // In a real implementation, you'd track network I/O metrics
    const activeServices = services.filter(s => s.status === 'healthy').length;
    return activeServices * 100; // Estimated MB/s per service
  }

  /**
   * Cleanup resources
   */
  destroy(): void {
    this.stopAutoRefresh();
    this.subscribers = [];
    this.clearCache();
  }
}

// Export singleton instance
export const dashboardService = new DashboardService();
