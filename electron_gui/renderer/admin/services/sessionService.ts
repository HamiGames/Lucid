/**
 * Session Service - Handles session management operations for admin interface
 * Provides session monitoring, management, and analytics functionality
 */

import { adminApi, SessionManagementRequest, BulkOperationRequest } from './adminApi';
import { Session } from '../../../shared/types';

export interface SessionFilters {
  status?: 'active' | 'completed' | 'failed' | 'anchored';
  user_id?: string;
  date_from?: string;
  date_to?: string;
  search?: string;
  limit?: number;
  offset?: number;
}

export interface SessionAnalytics {
  total_sessions: number;
  active_sessions: number;
  completed_sessions: number;
  failed_sessions: number;
  anchored_sessions: number;
  average_session_duration: number;
  total_data_processed: number;
  sessions_by_status: Record<string, number>;
  sessions_by_hour: Array<{ hour: string; count: number }>;
  top_users: Array<{ user_id: string; session_count: number; data_volume: number }>;
}

export interface SessionExportOptions {
  format: 'json' | 'csv' | 'xlsx';
  include_chunks: boolean;
  include_metadata: boolean;
  date_range?: {
    start: string;
    end: string;
  };
}

export interface SessionManagementResult {
  success: boolean;
  message: string;
  affected_sessions: string[];
  errors?: Array<{ session_id: string; error: string }>;
}

class SessionService {
  private sessionsCache: Map<string, Session> = new Map();
  private sessionsListCache: Session[] = [];
  private lastListUpdate: number = 0;
  private readonly CACHE_DURATION = 30000; // 30 seconds

  /**
   * Get all sessions with optional filtering
   */
  async getSessions(filters: SessionFilters = {}): Promise<Session[]> {
    const now = Date.now();
    const isCacheValid = (now - this.lastListUpdate) < this.CACHE_DURATION;

    if (isCacheValid && this.sessionsListCache.length > 0 && !filters.search) {
      return this.applyFilters(this.sessionsListCache, filters);
    }

    try {
      const sessions = await adminApi.getAllSessions(filters);
      
      // Update cache
      this.sessionsListCache = sessions;
      this.lastListUpdate = now;
      
      // Update individual session cache
      sessions.forEach(session => {
        this.sessionsCache.set(session.session_id, session);
      });

      return sessions;
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get session details by ID
   */
  async getSessionDetails(sessionId: string): Promise<Session> {
    // Check cache first
    const cached = this.sessionsCache.get(sessionId);
    if (cached) {
      return cached;
    }

    try {
      const session = await adminApi.getSessionDetails(sessionId);
      
      // Update cache
      this.sessionsCache.set(sessionId, session);
      
      return session;
    } catch (error) {
      throw error;
    }
  }

  /**
   * Terminate a session
   */
  async terminateSession(sessionId: string, reason?: string): Promise<SessionManagementResult> {
    try {
      const request: SessionManagementRequest = {
        action: 'terminate',
        session_id: sessionId,
        reason
      };

      const result = await adminApi.manageSession(request);
      
      // Update cache
      this.invalidateSessionCache(sessionId);
      
      return {
        success: result.success,
        message: result.message,
        affected_sessions: [sessionId]
      };
    } catch (error) {
      return {
        success: false,
        message: `Failed to terminate session: ${error.message}`,
        affected_sessions: [],
        errors: [{ session_id: sessionId, error: error.message }]
      };
    }
  }

  /**
   * Anchor a session to blockchain
   */
  async anchorSession(sessionId: string, reason?: string): Promise<SessionManagementResult> {
    try {
      const request: SessionManagementRequest = {
        action: 'anchor',
        session_id: sessionId,
        reason
      };

      const result = await adminApi.manageSession(request);
      
      // Update cache
      this.invalidateSessionCache(sessionId);
      
      return {
        success: result.success,
        message: result.message,
        affected_sessions: [sessionId]
      };
    } catch (error) {
      return {
        success: false,
        message: `Failed to anchor session: ${error.message}`,
        affected_sessions: [],
        errors: [{ session_id: sessionId, error: error.message }]
      };
    }
  }

  /**
   * Export session data
   */
  async exportSessionData(sessionId: string, format: 'json' | 'csv' = 'json'): Promise<Blob> {
    try {
      return await adminApi.exportSessionData(sessionId, format);
    } catch (error) {
      throw error;
    }
  }

  /**
   * Suspend a session
   */
  async suspendSession(sessionId: string, reason?: string): Promise<SessionManagementResult> {
    try {
      const request: SessionManagementRequest = {
        action: 'suspend',
        session_id: sessionId,
        reason
      };

      const result = await adminApi.manageSession(request);
      
      // Update cache
      this.invalidateSessionCache(sessionId);
      
      return {
        success: result.success,
        message: result.message,
        affected_sessions: [sessionId]
      };
    } catch (error) {
      return {
        success: false,
        message: `Failed to suspend session: ${error.message}`,
        affected_sessions: [],
        errors: [{ session_id: sessionId, error: error.message }]
      };
    }
  }

  /**
   * Bulk terminate sessions
   */
  async bulkTerminateSessions(sessionIds: string[], reason?: string): Promise<SessionManagementResult> {
    try {
      const request: BulkOperationRequest = {
        operation: 'terminate_sessions',
        target_ids: sessionIds,
        reason
      };

      const result = await adminApi.bulkUserOperation(request);
      
      // Invalidate cache for affected sessions
      sessionIds.forEach(id => this.invalidateSessionCache(id));
      
      return {
        success: result.success,
        message: `Bulk operation completed: ${result.processed} processed, ${result.failed} failed`,
        affected_sessions: result.results
          .filter(r => r.success)
          .map(r => r.id),
        errors: result.results
          .filter(r => !r.success)
          .map(r => ({ session_id: r.id, error: r.error || 'Unknown error' }))
      };
    } catch (error) {
      return {
        success: false,
        message: `Bulk terminate failed: ${error.message}`,
        affected_sessions: [],
        errors: sessionIds.map(id => ({ session_id: id, error: error.message }))
      };
    }
  }

  /**
   * Bulk anchor sessions
   */
  async bulkAnchorSessions(sessionIds: string[], reason?: string): Promise<SessionManagementResult> {
    try {
      const request: BulkOperationRequest = {
        operation: 'anchor_sessions',
        target_ids: sessionIds,
        reason
      };

      const result = await adminApi.bulkUserOperation(request);
      
      // Invalidate cache for affected sessions
      sessionIds.forEach(id => this.invalidateSessionCache(id));
      
      return {
        success: result.success,
        message: `Bulk anchoring completed: ${result.processed} processed, ${result.failed} failed`,
        affected_sessions: result.results
          .filter(r => r.success)
          .map(r => r.id),
        errors: result.results
          .filter(r => !r.success)
          .map(r => ({ session_id: r.id, error: r.error || 'Unknown error' }))
      };
    } catch (error) {
      return {
        success: false,
        message: `Bulk anchoring failed: ${error.message}`,
        affected_sessions: [],
        errors: sessionIds.map(id => ({ session_id: id, error: error.message }))
      };
    }
  }

  /**
   * Get session analytics
   */
  async getSessionAnalytics(timeRange: '1h' | '24h' | '7d' | '30d' = '24h'): Promise<SessionAnalytics> {
    try {
      const filters: SessionFilters = {
        limit: 1000 // Get more data for analytics
      };

      // Add date filter based on time range
      const now = new Date();
      const timeRanges = {
        '1h': 1,
        '24h': 24,
        '7d': 24 * 7,
        '30d': 24 * 30
      };

      const hoursBack = timeRanges[timeRange];
      const dateFrom = new Date(now.getTime() - (hoursBack * 60 * 60 * 1000));
      filters.date_from = dateFrom.toISOString();

      const sessions = await this.getSessions(filters);
      
      return this.calculateAnalytics(sessions);
    } catch (error) {
      throw error;
    }
  }

  /**
   * Search sessions
   */
  async searchSessions(query: string, filters: Omit<SessionFilters, 'search'> = {}): Promise<Session[]> {
    try {
      const searchFilters: SessionFilters = {
        ...filters,
        search: query
      };

      return await this.getSessions(searchFilters);
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get sessions by user
   */
  async getSessionsByUser(userId: string, filters: Omit<SessionFilters, 'user_id'> = {}): Promise<Session[]> {
    try {
      const userFilters: SessionFilters = {
        ...filters,
        user_id: userId
      };

      return await this.getSessions(userFilters);
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get active sessions count
   */
  async getActiveSessionsCount(): Promise<number> {
    try {
      const sessions = await this.getSessions({ status: 'active' });
      return sessions.length;
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get sessions requiring attention
   */
  async getSessionsRequiringAttention(): Promise<Session[]> {
    try {
      // Get failed sessions and long-running active sessions
      const [failedSessions, activeSessions] = await Promise.all([
        this.getSessions({ status: 'failed' }),
        this.getSessions({ status: 'active' })
      ]);

      // Filter active sessions that have been running for more than 24 hours
      const longRunningSessions = activeSessions.filter(session => {
        const createdAt = new Date(session.created_at);
        const hoursRunning = (Date.now() - createdAt.getTime()) / (1000 * 60 * 60);
        return hoursRunning > 24;
      });

      return [...failedSessions, ...longRunningSessions];
    } catch (error) {
      throw error;
    }
  }

  /**
   * Refresh session data
   */
  async refreshSessionData(): Promise<void> {
    this.sessionsCache.clear();
    this.sessionsListCache = [];
    this.lastListUpdate = 0;
    
    // Preload some data
    await this.getSessions({ limit: 50 });
  }

  /**
   * Get cached session data
   */
  getCachedSession(sessionId: string): Session | null {
    return this.sessionsCache.get(sessionId) || null;
  }

  /**
   * Clear session cache
   */
  clearCache(): void {
    this.sessionsCache.clear();
    this.sessionsListCache = [];
    this.lastListUpdate = 0;
  }

  // Private helper methods
  private applyFilters(sessions: Session[], filters: SessionFilters): Session[] {
    let filtered = [...sessions];

    if (filters.status) {
      filtered = filtered.filter(s => s.status === filters.status);
    }

    if (filters.user_id) {
      filtered = filtered.filter(s => s.user_id === filters.user_id);
    }

    if (filters.date_from) {
      const fromDate = new Date(filters.date_from);
      filtered = filtered.filter(s => new Date(s.created_at) >= fromDate);
    }

    if (filters.date_to) {
      const toDate = new Date(filters.date_to);
      filtered = filtered.filter(s => new Date(s.created_at) <= toDate);
    }

    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      filtered = filtered.filter(s => 
        s.session_id.toLowerCase().includes(searchLower) ||
        s.user_id.toLowerCase().includes(searchLower)
      );
    }

    // Apply pagination
    const offset = filters.offset || 0;
    const limit = filters.limit || filtered.length;
    
    return filtered.slice(offset, offset + limit);
  }

  private calculateAnalytics(sessions: Session[]): SessionAnalytics {
    const analytics: SessionAnalytics = {
      total_sessions: sessions.length,
      active_sessions: 0,
      completed_sessions: 0,
      failed_sessions: 0,
      anchored_sessions: 0,
      average_session_duration: 0,
      total_data_processed: 0,
      sessions_by_status: {},
      sessions_by_hour: [],
      top_users: []
    };

    // Calculate status counts
    sessions.forEach(session => {
      analytics.sessions_by_status[session.status] = (analytics.sessions_by_status[session.status] || 0) + 1;
      
      switch (session.status) {
        case 'active':
          analytics.active_sessions++;
          break;
        case 'completed':
          analytics.completed_sessions++;
          break;
        case 'failed':
          analytics.failed_sessions++;
          break;
        case 'anchored':
          analytics.anchored_sessions++;
          break;
      }

      // Calculate total data processed
      const chunkSize = session.chunks.reduce((total, chunk) => total + chunk.size, 0);
      analytics.total_data_processed += chunkSize;
    });

    // Calculate average session duration
    const completedSessions = sessions.filter(s => s.status === 'completed');
    if (completedSessions.length > 0) {
      const totalDuration = completedSessions.reduce((total, session) => {
        const start = new Date(session.created_at);
        const end = new Date(session.updated_at);
        return total + (end.getTime() - start.getTime());
      }, 0);
      
      analytics.average_session_duration = totalDuration / completedSessions.length / 1000 / 60; // minutes
    }

    // Calculate sessions by hour (simplified)
    const now = new Date();
    for (let i = 23; i >= 0; i--) {
      const hour = new Date(now.getTime() - (i * 60 * 60 * 1000));
      const hourStr = hour.toISOString().slice(11, 13) + ':00';
      const hourSessions = sessions.filter(s => {
        const sessionHour = new Date(s.created_at).getHours();
        return sessionHour === hour.getHours();
      });
      
      analytics.sessions_by_hour.push({
        hour: hourStr,
        count: hourSessions.length
      });
    }

    // Calculate top users
    const userStats = new Map<string, { session_count: number; data_volume: number }>();
    sessions.forEach(session => {
      const userStats_ = userStats.get(session.user_id) || { session_count: 0, data_volume: 0 };
      userStats_.session_count++;
      userStats_.data_volume += session.chunks.reduce((total, chunk) => total + chunk.size, 0);
      userStats.set(session.user_id, userStats_);
    });

    analytics.top_users = Array.from(userStats.entries())
      .map(([user_id, stats]) => ({ user_id, ...stats }))
      .sort((a, b) => b.session_count - a.session_count)
      .slice(0, 10);

    return analytics;
  }

  private invalidateSessionCache(sessionId: string): void {
    this.sessionsCache.delete(sessionId);
    this.sessionsListCache = this.sessionsListCache.filter(s => s.session_id !== sessionId);
  }
}

// Export singleton instance
export const sessionService = new SessionService();
