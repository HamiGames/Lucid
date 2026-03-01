/**
 * Admin API Service - Core admin interface API methods
 * Extends the base LucidAPIClient with admin-specific functionality
 * Based on SPEC-1B Admin Interface requirements
 */

import { LucidAPIClient } from '../../../shared/api-client';
import {
  User,
  Session,
  Node,
  Block,
  SystemHealth,
  ServiceStatus,
  LucidError,
} from '../../../shared/types';
import { API_ENDPOINTS, LUCID_ERROR_CODES } from '../../../shared/constants';

// Admin-specific types
export interface AdminDashboardData {
  system_health: SystemHealth;
  active_sessions: number;
  total_users: number;
  active_nodes: number;
  recent_activity: ActivityLog[];
  system_metrics: SystemMetrics;
}

export interface ActivityLog {
  id: string;
  type: 'user_action' | 'system_event' | 'admin_action';
  description: string;
  user_id?: string;
  timestamp: string;
  severity: 'info' | 'warning' | 'error' | 'critical';
}

export interface SystemMetrics {
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  network_throughput: number;
  active_connections: number;
  tor_circuits: number;
}

export interface UserManagementRequest {
  action: 'create' | 'update' | 'suspend' | 'activate' | 'delete';
  user_id?: string;
  user_data?: Partial<User>;
  reason?: string;
}

export interface SessionManagementRequest {
  action: 'terminate' | 'anchor' | 'export' | 'suspend';
  session_id: string;
  reason?: string;
}

export interface NodeManagementRequest {
  action: 'activate' | 'suspend' | 'maintenance' | 'remove';
  node_id: string;
  reason?: string;
}

export interface BulkOperationRequest {
  operation: 'terminate_sessions' | 'suspend_users' | 'anchor_sessions';
  target_ids: string[];
  reason?: string;
}

export interface AuditLogQuery {
  start_date?: string;
  end_date?: string;
  user_id?: string;
  event_type?: string;
  severity?: string;
  limit?: number;
  offset?: number;
}

export interface AuditLogEntry {
  id: string;
  timestamp: string;
  user_id?: string;
  action: string;
  resource: string;
  result: 'success' | 'failure';
  details: Record<string, any>;
  ip_address?: string;
  user_agent?: string;
}

export interface ConfigurationBackup {
  backup_id: string;
  created_at: string;
  config_version: string;
  backup_size: number;
  services_included: string[];
}

export interface EmergencyControlRequest {
  action: 'system_shutdown' | 'service_stop' | 'emergency_lockdown';
  target_service?: string;
  reason: string;
  admin_confirmation: boolean;
}

export class AdminAPIService extends LucidAPIClient {
  private adminToken: string | null = null;
  private tokenExpiry: Date | null = null;
  private tokenRefreshTimer: NodeJS.Timeout | null = null;
  private readonly tokenRefreshThreshold = 300000; // 5 minutes before expiry

  constructor(baseURL: string = API_ENDPOINTS.ADMIN) {
    super(baseURL);
    this.adminToken = this.getAdminToken();
    this.setupTokenRefresh();
  }

  private getAdminToken(): string | null {
    return localStorage.getItem('lucid_admin_token');
  }

  private async validateAdminAccess(): Promise<void> {
    if (!this.adminToken) {
      throw new Error(`${LUCID_ERROR_CODES.AUTHORIZATION_DENIED}: Admin authentication required`);
    }

    // Check if token is expired
    if (this.tokenExpiry && new Date() > this.tokenExpiry) {
      await this.refreshToken();
    }
  }

  private setupTokenRefresh(): void {
    // Check every minute if token needs refresh
    setInterval(() => {
      if (this.adminToken && this.tokenExpiry) {
        const timeUntilExpiry = this.tokenExpiry.getTime() - Date.now();
        if (timeUntilExpiry < this.tokenRefreshThreshold && timeUntilExpiry > 0) {
          this.refreshToken().catch((error) => {
            console.error('Auto token refresh failed:', error);
          });
        }
      }
    }, 60000);
  }

  private async refreshToken(): Promise<void> {
    try {
      console.log('Refreshing admin token...');
      
      // TODO: Implement actual token refresh with backend
      // For now, extend the current token expiry
      if (this.tokenExpiry) {
        this.tokenExpiry = new Date(Date.now() + 3600000); // Extend by 1 hour
      }
    } catch (error) {
      console.error('Failed to refresh admin token:', error);
      throw error;
    }
  }

  // Dashboard API methods
  async getDashboardData(): Promise<AdminDashboardData> {
    await this.validateAdminAccess();
    
    try {
      const response = await this.client.get('/api/v1/admin/dashboard');
      return response.data;
    } catch (error: any) {
      throw this.handleAdminError(error, 'Failed to fetch dashboard data');
    }
  }

  async getSystemHealth(): Promise<SystemHealth> {
    await this.validateAdminAccess();
    
    try {
      const response = await this.client.get('/api/v1/admin/system/health');
      return response.data;
    } catch (error: any) {
      throw this.handleAdminError(error, 'Failed to fetch system health');
    }
  }

  async getServiceStatus(serviceName?: string): Promise<ServiceStatus[]> {
    await this.validateAdminAccess();
    
    try {
      const endpoint = serviceName 
        ? `/api/v1/admin/services/${serviceName}/status`
        : '/api/v1/admin/services/status';
      const response = await this.client.get(endpoint);
      return response.data;
    } catch (error: any) {
      throw this.handleAdminError(error, 'Failed to fetch service status');
    }
  }

  // User Management API methods
  async getAllUsers(filters?: {
    role?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<User[]> {
    await this.validateAdminAccess();
    
    try {
      const response = await this.client.get('/api/v1/admin/users', { params: filters });
      return response.data;
    } catch (error: any) {
      throw this.handleAdminError(error, 'Failed to fetch users');
    }
  }

  async getUserDetails(userId: string): Promise<User> {
    await this.validateAdminAccess();
    
    try {
      const response = await this.client.get(`/api/v1/admin/users/${userId}`);
      return response.data;
    } catch (error: any) {
      throw this.handleAdminError(error, 'Failed to fetch user details');
    }
  }

  async manageUser(request: UserManagementRequest): Promise<{ success: boolean; message: string }> {
    await this.validateAdminAccess();
    
    try {
      const response = await this.client.post('/api/v1/admin/users/manage', request);
      return response.data;
    } catch (error: any) {
      throw this.handleAdminError(error, 'Failed to manage user');
    }
  }

  async bulkUserOperation(request: BulkOperationRequest): Promise<{
    success: boolean;
    processed: number;
    failed: number;
    results: Array<{ id: string; success: boolean; error?: string }>;
  }> {
    await this.validateAdminAccess();
    
    try {
      const response = await this.client.post('/api/v1/admin/users/bulk', request);
      return response.data;
    } catch (error: any) {
      throw this.handleAdminError(error, 'Failed to perform bulk user operation');
    }
  }

  // Session Management API methods
  async getAllSessions(filters?: {
    status?: string;
    user_id?: string;
    date_from?: string;
    date_to?: string;
    limit?: number;
    offset?: number;
  }): Promise<Session[]> {
    await this.validateAdminAccess();
    
    try {
      const response = await this.client.get('/api/v1/admin/sessions', { params: filters });
      return response.data;
    } catch (error: any) {
      throw this.handleAdminError(error, 'Failed to fetch sessions');
    }
  }

  async getSessionDetails(sessionId: string): Promise<Session> {
    await this.validateAdminAccess();
    
    try {
      const response = await this.client.get(`/api/v1/admin/sessions/${sessionId}`);
      return response.data;
    } catch (error: any) {
      throw this.handleAdminError(error, 'Failed to fetch session details');
    }
  }

  async manageSession(request: SessionManagementRequest): Promise<{ success: boolean; message: string }> {
    await this.validateAdminAccess();
    
    try {
      const response = await this.client.post('/api/v1/admin/sessions/manage', request);
      return response.data;
    } catch (error: any) {
      throw this.handleAdminError(error, 'Failed to manage session');
    }
  }

  async exportSessionData(sessionId: string, format: 'json' | 'csv' = 'json'): Promise<Blob> {
    await this.validateAdminAccess();
    
    try {
      const response = await this.client.get(`/api/v1/admin/sessions/${sessionId}/export`, {
        params: { format },
        responseType: 'blob'
      });
      return response.data;
    } catch (error: any) {
      throw this.handleAdminError(error, 'Failed to export session data');
    }
  }

  // Node Management API methods
  async getAllNodes(filters?: {
    status?: string;
    pool_id?: string;
    limit?: number;
    offset?: number;
  }): Promise<Node[]> {
    await this.validateAdminAccess();
    
    try {
      const response = await this.client.get('/api/v1/admin/nodes', { params: filters });
      return response.data;
    } catch (error: any) {
      throw this.handleAdminError(error, 'Failed to fetch nodes');
    }
  }

  async getNodeDetails(nodeId: string): Promise<Node> {
    await this.validateAdminAccess();
    
    try {
      const response = await this.client.get(`/api/v1/admin/nodes/${nodeId}`);
      return response.data;
    } catch (error: any) {
      throw this.handleAdminError(error, 'Failed to fetch node details');
    }
  }

  async manageNode(request: NodeManagementRequest): Promise<{ success: boolean; message: string }> {
    await this.validateAdminAccess();
    
    try {
      const response = await this.client.post('/api/v1/admin/nodes/manage', request);
      return response.data;
    } catch (error: any) {
      throw this.handleAdminError(error, 'Failed to manage node');
    }
  }

  async getNodeMetrics(nodeId: string, timeRange: '1h' | '24h' | '7d' = '24h'): Promise<{
    cpu_usage: Array<{ timestamp: string; value: number }>;
    memory_usage: Array<{ timestamp: string; value: number }>;
    network_io: Array<{ timestamp: string; bytes_in: number; bytes_out: number }>;
  }> {
    await this.validateAdminAccess();
    
    try {
      const response = await this.client.get(`/api/v1/admin/nodes/${nodeId}/metrics`, {
        params: { time_range: timeRange }
      });
      return response.data;
    } catch (error: any) {
      throw this.handleAdminError(error, 'Failed to fetch node metrics');
    }
  }

  // Blockchain Management API methods
  async getBlockchainStatus(): Promise<{
    current_height: number;
    latest_block_hash: string;
    network_hashrate: number;
    difficulty: number;
    connected_peers: number;
    sync_status: 'synced' | 'syncing' | 'behind';
  }> {
    await this.validateAdminAccess();
    
    try {
      const response = await this.client.get('/api/v1/admin/blockchain/status');
      return response.data;
    } catch (error: any) {
      throw this.handleAdminError(error, 'Failed to fetch blockchain status');
    }
  }

  async getAnchoringQueue(): Promise<Array<{
    session_id: string;
    user_id: string;
    priority: number;
    queued_at: string;
    estimated_anchor_time: string;
  }>> {
    await this.validateAdminAccess();
    
    try {
      const response = await this.client.get('/api/v1/admin/blockchain/anchoring-queue');
      return response.data;
    } catch (error: any) {
      throw this.handleAdminError(error, 'Failed to fetch anchoring queue');
    }
  }

  async getRecentBlocks(limit: number = 10): Promise<Block[]> {
    await this.validateAdminAccess();
    
    try {
      const response = await this.client.get('/api/v1/admin/blockchain/recent-blocks', {
        params: { limit }
      });
      return response.data;
    } catch (error: any) {
      throw this.handleAdminError(error, 'Failed to fetch recent blocks');
    }
  }

  async forceAnchoring(sessionIds: string[]): Promise<{
    success: boolean;
    anchored_sessions: string[];
    failed_sessions: Array<{ session_id: string; error: string }>;
  }> {
    await this.validateAdminAccess();
    
    try {
      const response = await this.client.post('/api/v1/admin/blockchain/force-anchor', {
        session_ids: sessionIds
      });
      return response.data;
    } catch (error: any) {
      throw this.handleAdminError(error, 'Failed to force anchoring');
    }
  }

  // Audit Log API methods
  async getAuditLogs(query: AuditLogQuery): Promise<{
    logs: AuditLogEntry[];
    total_count: number;
    has_more: boolean;
  }> {
    await this.validateAdminAccess();
    
    try {
      const response = await this.client.get('/api/v1/admin/audit/logs', { params: query });
      return response.data;
    } catch (error: any) {
      throw this.handleAdminError(error, 'Failed to fetch audit logs');
    }
  }

  async exportAuditLogs(query: AuditLogQuery, format: 'json' | 'csv' = 'json'): Promise<Blob> {
    await this.validateAdminAccess();
    
    try {
      const response = await this.client.get('/api/v1/admin/audit/export', {
        params: { ...query, format },
        responseType: 'blob'
      });
      return response.data;
    } catch (error: any) {
      throw this.handleAdminError(error, 'Failed to export audit logs');
    }
  }

  // Configuration Management API methods
  async getSystemConfiguration(): Promise<Record<string, any>> {
    await this.validateAdminAccess();
    
    try {
      const response = await this.client.get('/api/v1/admin/config/system');
      return response.data;
    } catch (error: any) {
      throw this.handleAdminError(error, 'Failed to fetch system configuration');
    }
  }

  async updateSystemConfiguration(config: Record<string, any>): Promise<{ success: boolean; message: string }> {
    await this.validateAdminAccess();
    
    try {
      const response = await this.client.put('/api/v1/admin/config/system', config);
      return response.data;
    } catch (error: any) {
      throw this.handleAdminError(error, 'Failed to update system configuration');
    }
  }

  async createConfigurationBackup(): Promise<ConfigurationBackup> {
    await this.validateAdminAccess();
    
    try {
      const response = await this.client.post('/api/v1/admin/config/backup');
      return response.data;
    } catch (error: any) {
      throw this.handleAdminError(error, 'Failed to create configuration backup');
    }
  }

  async restoreConfigurationBackup(backupId: string): Promise<{ success: boolean; message: string }> {
    await this.validateAdminAccess();
    
    try {
      const response = await this.client.post('/api/v1/admin/config/restore', { backup_id: backupId });
      return response.data;
    } catch (error: any) {
      throw this.handleAdminError(error, 'Failed to restore configuration backup');
    }
  }

  async listConfigurationBackups(): Promise<ConfigurationBackup[]> {
    await this.validateAdminAccess();
    
    try {
      const response = await this.client.get('/api/v1/admin/config/backups');
      return response.data;
    } catch (error: any) {
      throw this.handleAdminError(error, 'Failed to list configuration backups');
    }
  }

  // Emergency Controls API methods
  async executeEmergencyControl(request: EmergencyControlRequest): Promise<{
    success: boolean;
    message: string;
    confirmation_required: boolean;
  }> {
    await this.validateAdminAccess();
    
    try {
      const response = await this.client.post('/api/v1/admin/emergency/control', request);
      return response.data;
    } catch (error: any) {
      throw this.handleAdminError(error, 'Failed to execute emergency control');
    }
  }

  async getEmergencyStatus(): Promise<{
    is_locked_down: boolean;
    active_controls: string[];
    last_emergency_action?: {
      action: string;
      timestamp: string;
      admin_id: string;
    };
  }> {
    await this.validateAdminAccess();
    
    try {
      const response = await this.client.get('/api/v1/admin/emergency/status');
      return response.data;
    } catch (error: any) {
      throw this.handleAdminError(error, 'Failed to fetch emergency status');
    }
  }

  // Authentication API methods
  async adminLogin(email: string, signature: string): Promise<{ 
    token: string; 
    admin: { 
      admin_id: string; 
      username: string; 
      role: string; 
      permissions: string[] 
    } 
  }> {
    try {
      const response = await this.client.post('/api/v1/admin/auth/login', {
        email,
        signature
      });
      
      const { token, admin } = response.data;
      localStorage.setItem('lucid_admin_token', token);
      this.adminToken = token;
      
      return response.data;
    } catch (error: any) {
      throw this.handleAdminError(error, 'Admin login failed');
    }
  }

  async adminLogout(): Promise<void> {
    try {
      await this.client.post('/api/v1/admin/auth/logout');
    } finally {
      localStorage.removeItem('lucid_admin_token');
      this.adminToken = null;
    }
  }

  async verifyAdminToken(): Promise<{
    valid: boolean;
    admin?: { admin_id: string; username: string; role: string; permissions: string[] };
  }> {
    try {
      const response = await this.client.post('/api/v1/admin/auth/verify');
      return response.data;
    } catch (error: any) {
      return { valid: false };
    }
  }

  // Error handling
  private handleAdminError(error: any, context: string): Error {
    if (error.response?.data?.error) {
      const lucidError: LucidError = error.response.data.error;
      return new Error(`${context}: ${lucidError.code} - ${lucidError.message}`);
    }
    
    if (error.code === 'ECONNREFUSED') {
      return new Error(`${context}: ${LUCID_ERROR_CODES.TOR_CONNECTION_ERROR} - Tor connection failed`);
    }
    
    return new Error(`${context}: ${LUCID_ERROR_CODES.INTERNAL_SERVER_ERROR} - ${error.message}`);
  }
}

// Export singleton instance
export const adminApi = new AdminAPIService();
