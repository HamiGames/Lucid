/**
 * User Service - Handles user management operations for admin interface
 * Provides user administration, role management, and user analytics
 */

import { adminApi, UserManagementRequest, BulkOperationRequest } from './adminApi';
import { User } from '../../../shared/types';

export interface UserFilters {
  role?: 'user' | 'node_operator' | 'admin' | 'super_admin';
  status?: 'active' | 'suspended' | 'inactive';
  search?: string;
  created_from?: string;
  created_to?: string;
  limit?: number;
  offset?: number;
}

export interface UserAnalytics {
  total_users: number;
  active_users: number;
  suspended_users: number;
  users_by_role: Record<string, number>;
  users_by_status: Record<string, number>;
  new_users_today: number;
  new_users_this_week: number;
  new_users_this_month: number;
  top_active_users: Array<{
    user_id: string;
    email: string;
    session_count: number;
    last_activity: string;
  }>;
  user_registration_trend: Array<{
    date: string;
    count: number;
  }>;
}

export interface UserCreateRequest {
  email: string;
  role: 'user' | 'node_operator' | 'admin' | 'super_admin';
  tron_address?: string;
  hardware_wallet?: {
    type: 'ledger' | 'trezor' | 'keepkey';
    device_id: string;
    public_key: string;
  };
  metadata?: Record<string, any>;
}

export interface UserUpdateRequest {
  user_id: string;
  email?: string;
  role?: 'user' | 'node_operator' | 'admin' | 'super_admin';
  tron_address?: string;
  hardware_wallet?: {
    type: 'ledger' | 'trezor' | 'keepkey';
    device_id: string;
    public_key: string;
    is_connected: boolean;
  };
  metadata?: Record<string, any>;
}

export interface UserManagementResult {
  success: boolean;
  message: string;
  affected_users: string[];
  errors?: Array<{ user_id: string; error: string }>;
}

export interface UserSuspensionRequest {
  user_id: string;
  reason: string;
  duration_hours?: number; // 0 for indefinite
  notify_user: boolean;
}

class UserService {
  private usersCache: Map<string, User> = new Map();
  private usersListCache: User[] = [];
  private lastListUpdate: number = 0;
  private readonly CACHE_DURATION = 60000; // 1 minute

  /**
   * Get all users with optional filtering
   */
  async getUsers(filters: UserFilters = {}): Promise<User[]> {
    const now = Date.now();
    const isCacheValid = (now - this.lastListUpdate) < this.CACHE_DURATION;

    if (isCacheValid && this.usersListCache.length > 0 && !filters.search) {
      return this.applyFilters(this.usersListCache, filters);
    }

    try {
      const users = await adminApi.getAllUsers(filters);
      
      // Update cache
      this.usersListCache = users;
      this.lastListUpdate = now;
      
      // Update individual user cache
      users.forEach(user => {
        this.usersCache.set(user.user_id, user);
      });

      return users;
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get user details by ID
   */
  async getUserDetails(userId: string): Promise<User> {
    // Check cache first
    const cached = this.usersCache.get(userId);
    if (cached) {
      return cached;
    }

    try {
      const user = await adminApi.getUserDetails(userId);
      
      // Update cache
      this.usersCache.set(userId, user);
      
      return user;
    } catch (error) {
      throw error;
    }
  }

  /**
   * Create a new user
   */
  async createUser(request: UserCreateRequest): Promise<UserManagementResult> {
    try {
      const managementRequest: UserManagementRequest = {
        action: 'create',
        user_data: {
          email: request.email,
          role: request.role,
          tron_address: request.tron_address,
          hardware_wallet: request.hardware_wallet,
          created_at: new Date().toISOString()
        }
      };

      const result = await adminApi.manageUser(managementRequest);
      
      // Clear cache to force refresh
      this.clearCache();
      
      return {
        success: result.success,
        message: result.message,
        affected_users: []
      };
    } catch (error) {
      return {
        success: false,
        message: `Failed to create user: ${error.message}`,
        affected_users: [],
        errors: [{ user_id: '', error: error.message }]
      };
    }
  }

  /**
   * Update user information
   */
  async updateUser(request: UserUpdateRequest): Promise<UserManagementResult> {
    try {
      const managementRequest: UserManagementRequest = {
        action: 'update',
        user_id: request.user_id,
        user_data: {
          email: request.email,
          role: request.role,
          tron_address: request.tron_address,
          hardware_wallet: request.hardware_wallet
        }
      };

      const result = await adminApi.manageUser(managementRequest);
      
      // Invalidate cache for this user
      this.invalidateUserCache(request.user_id);
      
      return {
        success: result.success,
        message: result.message,
        affected_users: [request.user_id]
      };
    } catch (error) {
      return {
        success: false,
        message: `Failed to update user: ${error.message}`,
        affected_users: [],
        errors: [{ user_id: request.user_id, error: error.message }]
      };
    }
  }

  /**
   * Suspend a user
   */
  async suspendUser(request: UserSuspensionRequest): Promise<UserManagementResult> {
    try {
      const managementRequest: UserManagementRequest = {
        action: 'suspend',
        user_id: request.user_id,
        reason: request.reason
      };

      const result = await adminApi.manageUser(managementRequest);
      
      // Invalidate cache for this user
      this.invalidateUserCache(request.user_id);
      
      return {
        success: result.success,
        message: result.message,
        affected_users: [request.user_id]
      };
    } catch (error) {
      return {
        success: false,
        message: `Failed to suspend user: ${error.message}`,
        affected_users: [],
        errors: [{ user_id: request.user_id, error: error.message }]
      };
    }
  }

  /**
   * Activate a suspended user
   */
  async activateUser(userId: string, reason?: string): Promise<UserManagementResult> {
    try {
      const managementRequest: UserManagementRequest = {
        action: 'activate',
        user_id: userId,
        reason
      };

      const result = await adminApi.manageUser(managementRequest);
      
      // Invalidate cache for this user
      this.invalidateUserCache(userId);
      
      return {
        success: result.success,
        message: result.message,
        affected_users: [userId]
      };
    } catch (error) {
      return {
        success: false,
        message: `Failed to activate user: ${error.message}`,
        affected_users: [],
        errors: [{ user_id: userId, error: error.message }]
      };
    }
  }

  /**
   * Delete a user
   */
  async deleteUser(userId: string, reason?: string): Promise<UserManagementResult> {
    try {
      const managementRequest: UserManagementRequest = {
        action: 'delete',
        user_id: userId,
        reason
      };

      const result = await adminApi.manageUser(managementRequest);
      
      // Remove from cache
      this.usersCache.delete(userId);
      this.usersListCache = this.usersListCache.filter(u => u.user_id !== userId);
      
      return {
        success: result.success,
        message: result.message,
        affected_users: [userId]
      };
    } catch (error) {
      return {
        success: false,
        message: `Failed to delete user: ${error.message}`,
        affected_users: [],
        errors: [{ user_id: userId, error: error.message }]
      };
    }
  }

  /**
   * Bulk suspend users
   */
  async bulkSuspendUsers(userIds: string[], reason?: string): Promise<UserManagementResult> {
    try {
      const request: BulkOperationRequest = {
        operation: 'suspend_users',
        target_ids: userIds,
        reason
      };

      const result = await adminApi.bulkUserOperation(request);
      
      // Invalidate cache for affected users
      userIds.forEach(id => this.invalidateUserCache(id));
      
      return {
        success: result.success,
        message: `Bulk suspension completed: ${result.processed} processed, ${result.failed} failed`,
        affected_users: result.results
          .filter(r => r.success)
          .map(r => r.id),
        errors: result.results
          .filter(r => !r.success)
          .map(r => ({ user_id: r.id, error: r.error || 'Unknown error' }))
      };
    } catch (error) {
      return {
        success: false,
        message: `Bulk suspension failed: ${error.message}`,
        affected_users: [],
        errors: userIds.map(id => ({ user_id: id, error: error.message }))
      };
    }
  }

  /**
   * Search users
   */
  async searchUsers(query: string, filters: Omit<UserFilters, 'search'> = {}): Promise<User[]> {
    try {
      const searchFilters: UserFilters = {
        ...filters,
        search: query
      };

      return await this.getUsers(searchFilters);
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get users by role
   */
  async getUsersByRole(role: 'user' | 'node_operator' | 'admin' | 'super_admin'): Promise<User[]> {
    try {
      return await this.getUsers({ role });
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get suspended users
   */
  async getSuspendedUsers(): Promise<User[]> {
    try {
      return await this.getUsers({ status: 'suspended' });
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get user analytics
   */
  async getUserAnalytics(timeRange: '1d' | '7d' | '30d' | '90d' = '30d'): Promise<UserAnalytics> {
    try {
      const filters: UserFilters = {
        limit: 1000 // Get more data for analytics
      };

      // Add date filter based on time range
      const now = new Date();
      const timeRanges = {
        '1d': 1,
        '7d': 7,
        '30d': 30,
        '90d': 90
      };

      const daysBack = timeRanges[timeRange];
      const dateFrom = new Date(now.getTime() - (daysBack * 24 * 60 * 60 * 1000));
      filters.created_from = dateFrom.toISOString();

      const users = await this.getUsers(filters);
      
      return this.calculateUserAnalytics(users, timeRange);
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get user activity summary
   */
  async getUserActivitySummary(userId: string): Promise<{
    total_sessions: number;
    last_activity: string;
    account_age_days: number;
    status: string;
    role: string;
  }> {
    try {
      const user = await this.getUserDetails(userId);
      const createdAt = new Date(user.created_at);
      const accountAgeDays = Math.floor((Date.now() - createdAt.getTime()) / (1000 * 60 * 60 * 24));

      // This would typically come from session data
      // For now, we'll return basic info
      return {
        total_sessions: 0, // Would be fetched from session service
        last_activity: user.created_at,
        account_age_days: accountAgeDays,
        status: 'active', // Would be determined by user status
        role: user.role
      };
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get users requiring attention
   */
  async getUsersRequiringAttention(): Promise<User[]> {
    try {
      const suspendedUsers = await this.getSuspendedUsers();
      // Could add more criteria like users with failed login attempts, etc.
      return suspendedUsers;
    } catch (error) {
      throw error;
    }
  }

  /**
   * Refresh user data
   */
  async refreshUserData(): Promise<void> {
    this.clearCache();
    await this.getUsers({ limit: 100 });
  }

  /**
   * Get cached user data
   */
  getCachedUser(userId: string): User | null {
    return this.usersCache.get(userId) || null;
  }

  /**
   * Clear user cache
   */
  clearCache(): void {
    this.usersCache.clear();
    this.usersListCache = [];
    this.lastListUpdate = 0;
  }

  // Private helper methods
  private applyFilters(users: User[], filters: UserFilters): User[] {
    let filtered = [...users];

    if (filters.role) {
      filtered = filtered.filter(u => u.role === filters.role);
    }

    if (filters.status) {
      // Note: This assumes we have a status field on User
      // filtered = filtered.filter(u => u.status === filters.status);
    }

    if (filters.created_from) {
      const fromDate = new Date(filters.created_from);
      filtered = filtered.filter(u => new Date(u.created_at) >= fromDate);
    }

    if (filters.created_to) {
      const toDate = new Date(filters.created_to);
      filtered = filtered.filter(u => new Date(u.created_at) <= toDate);
    }

    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      filtered = filtered.filter(u => 
        u.email.toLowerCase().includes(searchLower) ||
        u.user_id.toLowerCase().includes(searchLower) ||
        (u.tron_address && u.tron_address.toLowerCase().includes(searchLower))
      );
    }

    // Apply pagination
    const offset = filters.offset || 0;
    const limit = filters.limit || filtered.length;
    
    return filtered.slice(offset, offset + limit);
  }

  private calculateUserAnalytics(users: User[], timeRange: string): UserAnalytics {
    const analytics: UserAnalytics = {
      total_users: users.length,
      active_users: 0,
      suspended_users: 0,
      users_by_role: {},
      users_by_status: {},
      new_users_today: 0,
      new_users_this_week: 0,
      new_users_this_month: 0,
      top_active_users: [],
      user_registration_trend: []
    };

    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const weekAgo = new Date(today.getTime() - (7 * 24 * 60 * 60 * 1000));
    const monthAgo = new Date(today.getTime() - (30 * 24 * 60 * 60 * 1000));

    // Calculate various metrics
    users.forEach(user => {
      // Role distribution
      analytics.users_by_role[user.role] = (analytics.users_by_role[user.role] || 0) + 1;

      // Status distribution (assuming active by default)
      const status = 'active'; // Would be determined by actual user status
      analytics.users_by_status[status] = (analytics.users_by_status[status] || 0) + 1;

      if (status === 'active') {
        analytics.active_users++;
      } else if (status === 'suspended') {
        analytics.suspended_users++;
      }

      // New user counts
      const createdAt = new Date(user.created_at);
      if (createdAt >= today) {
        analytics.new_users_today++;
      }
      if (createdAt >= weekAgo) {
        analytics.new_users_this_week++;
      }
      if (createdAt >= monthAgo) {
        analytics.new_users_this_month++;
      }
    });

    // Calculate registration trend (simplified)
    const daysBack = timeRange === '1d' ? 1 : timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90;
    for (let i = daysBack - 1; i >= 0; i--) {
      const date = new Date(today.getTime() - (i * 24 * 60 * 60 * 1000));
      const dayStart = new Date(date.getFullYear(), date.getMonth(), date.getDate());
      const dayEnd = new Date(dayStart.getTime() + (24 * 60 * 60 * 1000));
      
      const dayUsers = users.filter(user => {
        const createdAt = new Date(user.created_at);
        return createdAt >= dayStart && createdAt < dayEnd;
      });

      analytics.user_registration_trend.push({
        date: dayStart.toISOString().split('T')[0],
        count: dayUsers.length
      });
    }

    // Top active users (simplified - would need session data)
    analytics.top_active_users = users
      .slice(0, 10)
      .map(user => ({
        user_id: user.user_id,
        email: user.email,
        session_count: 0, // Would be fetched from session service
        last_activity: user.created_at
      }));

    return analytics;
  }

  private invalidateUserCache(userId: string): void {
    this.usersCache.delete(userId);
    this.usersListCache = this.usersListCache.filter(u => u.user_id !== userId);
  }
}

// Export singleton instance
export const userService = new UserService();
