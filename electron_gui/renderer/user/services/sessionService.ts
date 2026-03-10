import { LucidAPIClient } from '../../../shared/api-client';

export interface Session {
  id: string;
  name?: string;
  status: 'active' | 'completed' | 'failed' | 'anchored';
  start_time: string;
  end_time?: string;
  duration?: number;
  data_size: number;
  chunks_count: number;
  node_id: string;
  merkle_root?: string;
  blockchain_anchor?: {
    block_height: number;
    transaction_hash: string;
    timestamp: string;
  };
  created_at: string;
  updated_at: string;
}

export interface SessionCreateRequest {
  name: string;
  description?: string;
  data: string;
  encryption_enabled: boolean;
  auto_anchor: boolean;
  chunk_size: number;
  priority: 'low' | 'normal' | 'high';
}

export interface SessionFilters {
  status?: 'active' | 'completed' | 'failed' | 'anchored';
  date_from?: string;
  date_to?: string;
  search?: string;
  limit?: number;
  offset?: number;
}

export interface SessionManagementRequest {
  session_ids: string[];
  action: 'terminate' | 'anchor' | 'export';
  reason?: string;
}

export interface SessionExportOptions {
  format: 'json' | 'csv' | 'xml';
  include_chunks: boolean;
  include_metadata: boolean;
  include_anchors: boolean;
}

class SessionService {
  private apiClient: LucidAPIClient;

  constructor() {
    this.apiClient = new LucidAPIClient('/api/user');
  }

  // Get user sessions with optional filters
  async getSessions(filters: SessionFilters = {}): Promise<Session[]> {
    try {
      const params = new URLSearchParams();
      
      if (filters.status) params.append('status', filters.status);
      if (filters.date_from) params.append('date_from', filters.date_from);
      if (filters.date_to) params.append('date_to', filters.date_to);
      if (filters.search) params.append('search', filters.search);
      if (filters.limit) params.append('limit', filters.limit.toString());
      if (filters.offset) params.append('offset', filters.offset.toString());

      const response = await this.apiClient.get(`/sessions?${params}`);
      return response.sessions || [];
    } catch (error) {
      console.error('Failed to get sessions:', error);
      throw error;
    }
  }

  // Get session details by ID
  async getSessionDetails(sessionId: string): Promise<Session> {
    try {
      const response = await this.apiClient.get(`/sessions/${sessionId}`);
      return response.session;
    } catch (error) {
      console.error('Failed to get session details:', error);
      throw error;
    }
  }

  // Create a new session
  async createSession(request: SessionCreateRequest): Promise<Session> {
    try {
      const response = await this.apiClient.post('/sessions', request);
      return response.session;
    } catch (error) {
      console.error('Failed to create session:', error);
      throw error;
    }
  }

  // Terminate active sessions
  async terminateSessions(sessionIds: string[], reason?: string): Promise<{
    success: boolean;
    terminated_sessions: string[];
    failed_sessions: Array<{ session_id: string; error: string }>;
  }> {
    try {
      const response = await this.apiClient.post('/sessions/terminate', {
        session_ids: sessionIds,
        reason
      });
      return response;
    } catch (error) {
      console.error('Failed to terminate sessions:', error);
      throw error;
    }
  }

  // Anchor sessions to blockchain
  async anchorSessions(sessionIds: string[], reason?: string): Promise<{
    success: boolean;
    anchored_sessions: string[];
    failed_sessions: Array<{ session_id: string; error: string }>;
  }> {
    try {
      const response = await this.apiClient.post('/sessions/anchor', {
        session_ids: sessionIds,
        reason
      });
      return response;
    } catch (error) {
      console.error('Failed to anchor sessions:', error);
      throw error;
    }
  }

  // Export session data
  async exportSession(sessionId: string, options: SessionExportOptions): Promise<Blob> {
    try {
      const response = await this.apiClient.post(`/sessions/${sessionId}/export`, options, {
        responseType: 'blob'
      });
      return response;
    } catch (error) {
      console.error('Failed to export session:', error);
      throw error;
    }
  }

  // Get session history with pagination
  async getSessionHistory(page: number = 1, limit: number = 10, filters: SessionFilters = {}): Promise<{
    sessions: Session[];
    total_count: number;
    total_pages: number;
    current_page: number;
  }> {
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        limit: limit.toString(),
        ...filters
      });

      const response = await this.apiClient.get(`/sessions/history?${params}`);
      return response;
    } catch (error) {
      console.error('Failed to get session history:', error);
      throw error;
    }
  }

  // Search sessions
  async searchSessions(query: string, filters: Omit<SessionFilters, 'search'> = {}): Promise<Session[]> {
    try {
      const searchFilters = { ...filters, search: query };
      return await this.getSessions(searchFilters);
    } catch (error) {
      console.error('Failed to search sessions:', error);
      throw error;
    }
  }

  // Get session statistics
  async getSessionStats(): Promise<{
    total_sessions: number;
    active_sessions: number;
    completed_sessions: number;
    failed_sessions: number;
    anchored_sessions: number;
    total_data_processed: number;
    average_session_duration: number;
  }> {
    try {
      const response = await this.apiClient.get('/sessions/stats');
      return response.stats;
    } catch (error) {
      console.error('Failed to get session stats:', error);
      throw error;
    }
  }

  // Get active sessions count
  async getActiveSessionsCount(): Promise<number> {
    try {
      const response = await this.apiClient.get('/sessions/active/count');
      return response.count;
    } catch (error) {
      console.error('Failed to get active sessions count:', error);
      throw error;
    }
  }

  // Get session chunks
  async getSessionChunks(sessionId: string): Promise<Array<{
    id: string;
    index: number;
    data: string;
    hash: string;
    created_at: string;
  }>> {
    try {
      const response = await this.apiClient.get(`/sessions/${sessionId}/chunks`);
      return response.chunks;
    } catch (error) {
      console.error('Failed to get session chunks:', error);
      throw error;
    }
  }

  // Get session merkle proof
  async getSessionMerkleProof(sessionId: string): Promise<{
    merkle_root: string;
    proof: Array<{
      hash: string;
      position: 'left' | 'right';
    }>;
    leaf_hash: string;
  }> {
    try {
      const response = await this.apiClient.get(`/sessions/${sessionId}/merkle-proof`);
      return response.proof;
    } catch (error) {
      console.error('Failed to get merkle proof:', error);
      throw error;
    }
  }

  // Get session blockchain anchor
  async getSessionBlockchainAnchor(sessionId: string): Promise<{
    block_height: number;
    transaction_hash: string;
    timestamp: string;
    merkle_root: string;
    session_id: string;
  }> {
    try {
      const response = await this.apiClient.get(`/sessions/${sessionId}/blockchain-anchor`);
      return response.anchor;
    } catch (error) {
      console.error('Failed to get blockchain anchor:', error);
      throw error;
    }
  }

  // Validate session data
  async validateSessionData(data: string): Promise<{
    valid: boolean;
    size: number;
    chunks_count: number;
    estimated_duration: number;
    errors?: string[];
  }> {
    try {
      const response = await this.apiClient.post('/sessions/validate', { data });
      return response.validation;
    } catch (error) {
      console.error('Failed to validate session data:', error);
      throw error;
    }
  }

  // Get session performance metrics
  async getSessionMetrics(sessionId: string): Promise<{
    upload_speed: number;
    processing_time: number;
    chunk_processing_time: number;
    network_latency: number;
    node_performance: number;
  }> {
    try {
      const response = await this.apiClient.get(`/sessions/${sessionId}/metrics`);
      return response.metrics;
    } catch (error) {
      console.error('Failed to get session metrics:', error);
      throw error;
    }
  }

  // Cancel active session
  async cancelSession(sessionId: string, reason?: string): Promise<{
    success: boolean;
    message: string;
  }> {
    try {
      const response = await this.apiClient.post(`/sessions/${sessionId}/cancel`, { reason });
      return response;
    } catch (error) {
      console.error('Failed to cancel session:', error);
      throw error;
    }
  }

  // Resume failed session
  async resumeSession(sessionId: string): Promise<{
    success: boolean;
    message: string;
    new_session_id?: string;
  }> {
    try {
      const response = await this.apiClient.post(`/sessions/${sessionId}/resume`);
      return response;
    } catch (error) {
      console.error('Failed to resume session:', error);
      throw error;
    }
  }

  // Get session logs
  async getSessionLogs(sessionId: string): Promise<Array<{
    timestamp: string;
    level: 'info' | 'warning' | 'error';
    message: string;
    details?: any;
  }>> {
    try {
      const response = await this.apiClient.get(`/sessions/${sessionId}/logs`);
      return response.logs;
    } catch (error) {
      console.error('Failed to get session logs:', error);
      throw error;
    }
  }
}

export const sessionService = new SessionService();
