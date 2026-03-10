/**
 * Audit Service - Handles audit log operations for admin interface
 * Provides audit log querying, filtering, and export functionality
 */

import { adminApi, AuditLogQuery, AuditLogEntry } from './adminApi';

export interface AuditLogFilters {
  start_date?: string;
  end_date?: string;
  user_id?: string;
  event_type?: string;
  severity?: 'info' | 'warning' | 'error' | 'critical';
  action?: string;
  resource?: string;
  result?: 'success' | 'failure';
  ip_address?: string;
  limit?: number;
  offset?: number;
}

export interface AuditLogExportOptions {
  format: 'json' | 'csv' | 'xlsx';
  filters: AuditLogFilters;
  include_details: boolean;
  compress: boolean;
}

export interface AuditLogStatistics {
  total_events: number;
  events_by_type: Record<string, number>;
  events_by_severity: Record<string, number>;
  events_by_result: Record<string, number>;
  events_today: number;
  events_this_week: number;
  events_this_month: number;
  top_users: Array<{
    user_id: string;
    event_count: number;
    last_activity: string;
  }>;
  top_actions: Array<{
    action: string;
    count: number;
    success_rate: number;
  }>;
  security_events: {
    failed_logins: number;
    unauthorized_access: number;
    suspicious_activities: number;
    policy_violations: number;
  };
  audit_trend: Array<{
    date: string;
    count: number;
    severity_breakdown: Record<string, number>;
  }>;
}

export interface AuditLogSummary {
  period: string;
  total_events: number;
  critical_events: number;
  failed_events: number;
  unique_users: number;
  most_common_action: string;
  security_score: number;
}

export interface AuditLogSearchResult {
  logs: AuditLogEntry[];
  total_count: number;
  has_more: boolean;
  search_time_ms: number;
  facets?: {
    event_types: Record<string, number>;
    severities: Record<string, number>;
    users: Record<string, number>;
    actions: Record<string, number>;
  };
}

class AuditService {
  private auditCache: Map<string, AuditLogEntry[]> = new Map();
  private statisticsCache: AuditLogStatistics | null = null;
  private lastCacheUpdate: number = 0;
  private readonly CACHE_DURATION = 300000; // 5 minutes

  /**
   * Get audit logs with filtering
   */
  async getAuditLogs(filters: AuditLogFilters = {}): Promise<AuditLogSearchResult> {
    const cacheKey = this.generateCacheKey(filters);
    const now = Date.now();
    const isCacheValid = (now - this.lastCacheUpdate) < this.CACHE_DURATION;

    if (isCacheValid && this.auditCache.has(cacheKey)) {
      const cached = this.auditCache.get(cacheKey)!;
      return {
        logs: cached,
        total_count: cached.length,
        has_more: false,
        search_time_ms: 0,
        facets: this.generateFacets(cached)
      };
    }

    try {
      const startTime = Date.now();
      
      const query: AuditLogQuery = {
        start_date: filters.start_date,
        end_date: filters.end_date,
        user_id: filters.user_id,
        event_type: filters.event_type,
        severity: filters.severity,
        limit: filters.limit || 100,
        offset: filters.offset || 0
      };

      const result = await adminApi.getAuditLogs(query);
      
      // Update cache
      this.auditCache.set(cacheKey, result.logs);
      this.lastCacheUpdate = now;
      
      return {
        logs: result.logs,
        total_count: result.total_count,
        has_more: result.has_more,
        search_time_ms: Date.now() - startTime,
        facets: this.generateFacets(result.logs)
      };
    } catch (error) {
      throw error;
    }
  }

  /**
   * Search audit logs with text query
   */
  async searchAuditLogs(
    searchQuery: string, 
    filters: Omit<AuditLogFilters, 'search'> = {}
  ): Promise<AuditLogSearchResult> {
    try {
      const allLogs = await this.getAuditLogs({ ...filters, limit: 1000 });
      
      // Perform client-side text search
      const searchLower = searchQuery.toLowerCase();
      const filteredLogs = allLogs.logs.filter(log => 
        log.action.toLowerCase().includes(searchLower) ||
        log.resource.toLowerCase().includes(searchLower) ||
        (log.details && JSON.stringify(log.details).toLowerCase().includes(searchLower)) ||
        (log.user_agent && log.user_agent.toLowerCase().includes(searchLower))
      );

      return {
        logs: filteredLogs,
        total_count: filteredLogs.length,
        has_more: false,
        search_time_ms: 0,
        facets: this.generateFacets(filteredLogs)
      };
    } catch (error) {
      throw error;
    }
  }

  /**
   * Export audit logs
   */
  async exportAuditLogs(options: AuditLogExportOptions): Promise<Blob> {
    try {
      const query: AuditLogQuery = {
        start_date: options.filters.start_date,
        end_date: options.filters.end_date,
        user_id: options.filters.user_id,
        event_type: options.filters.event_type,
        severity: options.filters.severity,
        limit: 10000 // Large limit for export
      };

      return await adminApi.exportAuditLogs(query, options.format);
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get audit log statistics
   */
  async getAuditStatistics(timeRange: '1d' | '7d' | '30d' = '7d'): Promise<AuditLogStatistics> {
    const now = Date.now();
    const isCacheValid = (now - this.lastCacheUpdate) < this.CACHE_DURATION;

    if (isCacheValid && this.statisticsCache) {
      return this.statisticsCache;
    }

    try {
      // Calculate date range
      const endDate = new Date();
      const startDate = new Date();
      const timeRanges = { '1d': 1, '7d': 7, '30d': 30 };
      startDate.setDate(endDate.getDate() - timeRanges[timeRange]);

      const filters: AuditLogFilters = {
        start_date: startDate.toISOString(),
        end_date: endDate.toISOString(),
        limit: 10000 // Get more data for statistics
      };

      const result = await this.getAuditLogs(filters);
      const statistics = this.calculateAuditStatistics(result.logs, timeRange);
      
      this.statisticsCache = statistics;
      return statistics;
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get audit log summary for dashboard
   */
  async getAuditSummary(timeRange: '1h' | '24h' | '7d' = '24h'): Promise<AuditLogSummary> {
    try {
      // Calculate date range
      const endDate = new Date();
      const startDate = new Date();
      const timeRanges = { '1h': 1/24, '24h': 1, '7d': 7 };
      startDate.setDate(endDate.getDate() - timeRanges[timeRange]);

      const filters: AuditLogFilters = {
        start_date: startDate.toISOString(),
        end_date: endDate.toISOString()
      };

      const result = await this.getAuditLogs(filters);
      
      return this.calculateAuditSummary(result.logs, timeRange);
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get security events
   */
  async getSecurityEvents(limit: number = 50): Promise<AuditLogEntry[]> {
    try {
      const filters: AuditLogFilters = {
        severity: 'critical',
        limit
      };

      const result = await this.getAuditLogs(filters);
      
      // Filter for security-related events
      return result.logs.filter(log => 
        log.action.includes('login') ||
        log.action.includes('access') ||
        log.action.includes('permission') ||
        log.action.includes('security') ||
        log.action.includes('auth')
      );
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get failed login attempts
   */
  async getFailedLogins(timeRange: '1h' | '24h' | '7d' = '24h'): Promise<AuditLogEntry[]> {
    try {
      const endDate = new Date();
      const startDate = new Date();
      const timeRanges = { '1h': 1/24, '24h': 1, '7d': 7 };
      startDate.setDate(endDate.getDate() - timeRanges[timeRange]);

      const filters: AuditLogFilters = {
        start_date: startDate.toISOString(),
        end_date: endDate.toISOString(),
        action: 'login',
        result: 'failure'
      };

      const result = await this.getAuditLogs(filters);
      return result.logs;
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get user activity logs
   */
  async getUserActivityLogs(userId: string, limit: number = 100): Promise<AuditLogEntry[]> {
    try {
      const filters: AuditLogFilters = {
        user_id: userId,
        limit
      };

      const result = await this.getAuditLogs(filters);
      return result.logs;
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get admin action logs
   */
  async getAdminActionLogs(limit: number = 100): Promise<AuditLogEntry[]> {
    try {
      const filters: AuditLogFilters = {
        event_type: 'admin_action',
        limit
      };

      const result = await this.getAuditLogs(filters);
      return result.logs;
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get system event logs
   */
  async getSystemEventLogs(limit: number = 100): Promise<AuditLogEntry[]> {
    try {
      const filters: AuditLogFilters = {
        event_type: 'system_event',
        limit
      };

      const result = await this.getAuditLogs(filters);
      return result.logs;
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get audit log trends
   */
  async getAuditTrends(timeRange: '7d' | '30d' | '90d' = '30d'): Promise<Array<{
    date: string;
    count: number;
    severity_breakdown: Record<string, number>;
  }>> {
    try {
      const endDate = new Date();
      const startDate = new Date();
      const timeRanges = { '7d': 7, '30d': 30, '90d': 90 };
      startDate.setDate(endDate.getDate() - timeRanges[timeRange]);

      const filters: AuditLogFilters = {
        start_date: startDate.toISOString(),
        end_date: endDate.toISOString(),
        limit: 10000
      };

      const result = await this.getAuditLogs(filters);
      return this.calculateAuditTrends(result.logs, timeRange);
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get compliance report
   */
  async getComplianceReport(): Promise<{
    total_events: number;
    compliance_score: number;
    violations: Array<{
      type: string;
      count: number;
      severity: string;
    }>;
    recommendations: string[];
  }> {
    try {
      const statistics = await this.getAuditStatistics('30d');
      
      return {
        total_events: statistics.total_events,
        compliance_score: this.calculateComplianceScore(statistics),
        violations: this.identifyViolations(statistics),
        recommendations: this.generateRecommendations(statistics)
      };
    } catch (error) {
      throw error;
    }
  }

  /**
   * Clear audit cache
   */
  clearCache(): void {
    this.auditCache.clear();
    this.statisticsCache = null;
    this.lastCacheUpdate = 0;
  }

  /**
   * Refresh audit data
   */
  async refreshAuditData(): Promise<void> {
    this.clearCache();
    // Preload some common data
    await this.getAuditLogs({ limit: 100 });
  }

  // Private helper methods
  private generateCacheKey(filters: AuditLogFilters): string {
    return JSON.stringify(filters);
  }

  private generateFacets(logs: AuditLogEntry[]): AuditLogSearchResult['facets'] {
    const facets = {
      event_types: {} as Record<string, number>,
      severities: {} as Record<string, number>,
      users: {} as Record<string, number>,
      actions: {} as Record<string, number>
    };

    logs.forEach(log => {
      // Count event types (would need to extract from action or details)
      const eventType = log.action.split('_')[0] || 'unknown';
      facets.event_types[eventType] = (facets.event_types[eventType] || 0) + 1;

      // Count severities
      const severity = this.extractSeverity(log);
      facets.severities[severity] = (facets.severities[severity] || 0) + 1;

      // Count users
      if (log.user_id) {
        facets.users[log.user_id] = (facets.users[log.user_id] || 0) + 1;
      }

      // Count actions
      facets.actions[log.action] = (facets.actions[log.action] || 0) + 1;
    });

    return facets;
  }

  private extractSeverity(log: AuditLogEntry): string {
    // This would typically be determined by the log entry itself
    // For now, we'll use a simple heuristic
    if (log.result === 'failure') return 'error';
    if (log.action.includes('login') || log.action.includes('access')) return 'warning';
    return 'info';
  }

  private calculateAuditStatistics(logs: AuditLogEntry[], timeRange: string): AuditLogStatistics {
    const statistics: AuditLogStatistics = {
      total_events: logs.length,
      events_by_type: {},
      events_by_severity: {},
      events_by_result: {},
      events_today: 0,
      events_this_week: 0,
      events_this_month: 0,
      top_users: [],
      top_actions: [],
      security_events: {
        failed_logins: 0,
        unauthorized_access: 0,
        suspicious_activities: 0,
        policy_violations: 0
      },
      audit_trend: []
    };

    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const weekAgo = new Date(today.getTime() - (7 * 24 * 60 * 60 * 1000));
    const monthAgo = new Date(today.getTime() - (30 * 24 * 60 * 60 * 1000));

    const userStats = new Map<string, { count: number; last_activity: string }>();
    const actionStats = new Map<string, { count: number; success_count: number }>();

    logs.forEach(log => {
      // Count by type
      const eventType = log.action.split('_')[0] || 'unknown';
      statistics.events_by_type[eventType] = (statistics.events_by_type[eventType] || 0) + 1;

      // Count by severity
      const severity = this.extractSeverity(log);
      statistics.events_by_severity[severity] = (statistics.events_by_severity[severity] || 0) + 1;

      // Count by result
      statistics.events_by_result[log.result] = (statistics.events_by_result[log.result] || 0) + 1;

      // Count by time period
      const logDate = new Date(log.timestamp);
      if (logDate >= today) {
        statistics.events_today++;
      }
      if (logDate >= weekAgo) {
        statistics.events_this_week++;
      }
      if (logDate >= monthAgo) {
        statistics.events_this_month++;
      }

      // User statistics
      if (log.user_id) {
        const userStat = userStats.get(log.user_id) || { count: 0, last_activity: log.timestamp };
        userStat.count++;
        if (new Date(log.timestamp) > new Date(userStat.last_activity)) {
          userStat.last_activity = log.timestamp;
        }
        userStats.set(log.user_id, userStat);
      }

      // Action statistics
      const actionStat = actionStats.get(log.action) || { count: 0, success_count: 0 };
      actionStat.count++;
      if (log.result === 'success') {
        actionStat.success_count++;
      }
      actionStats.set(log.action, actionStat);

      // Security events
      if (log.action.includes('login') && log.result === 'failure') {
        statistics.security_events.failed_logins++;
      }
      if (log.action.includes('unauthorized')) {
        statistics.security_events.unauthorized_access++;
      }
      if (log.action.includes('suspicious')) {
        statistics.security_events.suspicious_activities++;
      }
      if (log.action.includes('violation')) {
        statistics.security_events.policy_violations++;
      }
    });

    // Top users
    statistics.top_users = Array.from(userStats.entries())
      .map(([user_id, stats]) => ({ user_id, ...stats }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 10);

    // Top actions
    statistics.top_actions = Array.from(actionStats.entries())
      .map(([action, stats]) => ({
        action,
        count: stats.count,
        success_rate: (stats.success_count / stats.count) * 100
      }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 10);

    // Audit trend
    const daysBack = timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90;
    for (let i = daysBack - 1; i >= 0; i--) {
      const date = new Date(today.getTime() - (i * 24 * 60 * 60 * 1000));
      const dayStart = new Date(date.getFullYear(), date.getMonth(), date.getDate());
      const dayEnd = new Date(dayStart.getTime() + (24 * 60 * 60 * 1000));
      
      const dayLogs = logs.filter(log => {
        const logDate = new Date(log.timestamp);
        return logDate >= dayStart && logDate < dayEnd;
      });

      const severityBreakdown = { info: 0, warning: 0, error: 0, critical: 0 };
      dayLogs.forEach(log => {
        const severity = this.extractSeverity(log);
        severityBreakdown[severity as keyof typeof severityBreakdown]++;
      });

      statistics.audit_trend.push({
        date: dayStart.toISOString().split('T')[0],
        count: dayLogs.length,
        severity_breakdown: severityBreakdown
      });
    }

    return statistics;
  }

  private calculateAuditSummary(logs: AuditLogEntry[], timeRange: string): AuditLogSummary {
    const summary: AuditLogSummary = {
      period: timeRange,
      total_events: logs.length,
      critical_events: 0,
      failed_events: 0,
      unique_users: 0,
      most_common_action: '',
      security_score: 0
    };

    const userSet = new Set<string>();
    const actionCounts = new Map<string, number>();

    logs.forEach(log => {
      // Count critical events
      if (this.extractSeverity(log) === 'critical') {
        summary.critical_events++;
      }

      // Count failed events
      if (log.result === 'failure') {
        summary.failed_events++;
      }

      // Count unique users
      if (log.user_id) {
        userSet.add(log.user_id);
      }

      // Count actions
      actionCounts.set(log.action, (actionCounts.get(log.action) || 0) + 1);
    });

    summary.unique_users = userSet.size;
    summary.most_common_action = Array.from(actionCounts.entries())
      .sort((a, b) => b[1] - a[1])[0]?.[0] || '';

    // Calculate security score (simplified)
    const securityEvents = logs.filter(log => 
      log.action.includes('login') || 
      log.action.includes('access') || 
      log.action.includes('security')
    );
    summary.security_score = Math.max(0, 100 - (securityEvents.length / logs.length) * 100);

    return summary;
  }

  private calculateAuditTrends(logs: AuditLogEntry[], timeRange: string): Array<{
    date: string;
    count: number;
    severity_breakdown: Record<string, number>;
  }> {
    const trends: Array<{
      date: string;
      count: number;
      severity_breakdown: Record<string, number>;
    }> = [];

    const daysBack = timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90;
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    for (let i = daysBack - 1; i >= 0; i--) {
      const date = new Date(today.getTime() - (i * 24 * 60 * 60 * 1000));
      const dayStart = new Date(date.getFullYear(), date.getMonth(), date.getDate());
      const dayEnd = new Date(dayStart.getTime() + (24 * 60 * 60 * 1000));
      
      const dayLogs = logs.filter(log => {
        const logDate = new Date(log.timestamp);
        return logDate >= dayStart && logDate < dayEnd;
      });

      const severityBreakdown = { info: 0, warning: 0, error: 0, critical: 0 };
      dayLogs.forEach(log => {
        const severity = this.extractSeverity(log);
        severityBreakdown[severity as keyof typeof severityBreakdown]++;
      });

      trends.push({
        date: dayStart.toISOString().split('T')[0],
        count: dayLogs.length,
        severity_breakdown: severityBreakdown
      });
    }

    return trends;
  }

  private calculateComplianceScore(statistics: AuditLogStatistics): number {
    // Simplified compliance score calculation
    const totalEvents = statistics.total_events;
    const criticalEvents = statistics.events_by_severity.critical || 0;
    const errorEvents = statistics.events_by_severity.error || 0;
    
    const score = Math.max(0, 100 - (criticalEvents * 10) - (errorEvents * 2));
    return Math.min(100, score);
  }

  private identifyViolations(statistics: AuditLogStatistics): Array<{
    type: string;
    count: number;
    severity: string;
  }> {
    const violations = [];

    if (statistics.security_events.failed_logins > 10) {
      violations.push({
        type: 'Excessive Failed Logins',
        count: statistics.security_events.failed_logins,
        severity: 'high'
      });
    }

    if (statistics.security_events.unauthorized_access > 0) {
      violations.push({
        type: 'Unauthorized Access Attempts',
        count: statistics.security_events.unauthorized_access,
        severity: 'critical'
      });
    }

    if (statistics.security_events.policy_violations > 5) {
      violations.push({
        type: 'Policy Violations',
        count: statistics.security_events.policy_violations,
        severity: 'medium'
      });
    }

    return violations;
  }

  private generateRecommendations(statistics: AuditLogStatistics): string[] {
    const recommendations = [];

    if (statistics.security_events.failed_logins > 10) {
      recommendations.push('Consider implementing account lockout policies for failed login attempts');
    }

    if (statistics.security_events.unauthorized_access > 0) {
      recommendations.push('Review and strengthen access control policies');
    }

    if (statistics.events_by_severity.critical > 5) {
      recommendations.push('Investigate critical events and implement preventive measures');
    }

    if (statistics.events_by_result.failure > statistics.events_by_result.success * 0.1) {
      recommendations.push('Review system reliability and error handling procedures');
    }

    return recommendations;
  }
}

// Export singleton instance
export const auditService = new AuditService();
